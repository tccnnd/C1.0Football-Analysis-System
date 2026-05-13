from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models.elo_rating import EloRatingEngine
from .models.xgboost_v0 import XGBoostProbabilityModel
from .market_features import build_market_intent_feature_map, compute_return_rate
from .storage.state_store import StateStore


DEFAULT_LEAGUE_STRENGTH = 0.92
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "match_id": ("match_id", "id", "fixture_id", "event_id"),
    "year": ("year", "年份"),
    "match_date": ("match_date", "date", "kickoff_date", "matchday", "dt"),
    "match_time": ("match_time", "time", "kickoff_time"),
    "match_time_raw": ("match_time_raw", "比赛时间"),
    "kickoff": ("kickoff", "kickoff_datetime", "match_datetime", "datetime", "start_time"),
    "league": ("league", "competition", "league_name", "tournament", "赛事"),
    "home_team": ("home_team", "home", "home_name", "homeClub", "host_team", "主队"),
    "away_team": ("away_team", "away", "away_name", "awayClub", "guest_team", "客队"),
    "odds_home": ("odds_home", "home_odds", "win_odds", "sp_home", "竞官方终胜"),
    "odds_draw": ("odds_draw", "draw_odds", "tie_odds", "sp_draw", "竞官方终平"),
    "odds_away": ("odds_away", "away_odds", "lose_odds", "sp_away", "竞官方终负"),
    "home_goals": ("home_goals", "home_score", "full_home_score", "ft_home_goals", "score_home"),
    "away_goals": ("away_goals", "away_score", "full_away_score", "ft_away_goals", "score_away"),
    "home_ht_goals": ("home_ht_goals", "ht_home_goals", "half_home_score", "score_ht_home"),
    "away_ht_goals": ("away_ht_goals", "ht_away_goals", "half_away_score", "score_ht_away"),
    "full_score_text": ("full_score_text", "全场比分", "全场"),
    "half_score_text": ("half_score_text", "半场比分", "半场"),
    "handicap_line": ("handicap_line", "asian_handicap", "ah_line", "rq", "goal", "让球数"),
    "league_strength": ("league_strength", "league_factor", "competition_strength"),
    "home_rating": ("home_rating", "elo_home", "pre_home_rating"),
    "away_rating": ("away_rating", "elo_away", "pre_away_rating"),
}

FIELD_ALIASES.update(
    {
        "opening_odds_home": ("opening_odds_home", "open_odds_home", "opening_home_odds", "初赔主胜", "初赔主"),
        "opening_odds_draw": ("opening_odds_draw", "open_odds_draw", "opening_draw_odds", "初赔平局", "初赔平"),
        "opening_odds_away": ("opening_odds_away", "open_odds_away", "opening_away_odds", "初赔客胜", "初赔客"),
        "return_rate": ("return_rate", "payout_rate", "return", "返还率"),
        "kelly_home": ("kelly_home", "kelly_win", "home_kelly", "凯利主胜", "凯利主"),
        "kelly_draw": ("kelly_draw", "kelly_draw_index", "draw_kelly", "凯利平局", "凯利平"),
        "kelly_away": ("kelly_away", "kelly_lose", "away_kelly", "凯利客胜", "凯利客"),
    }
)

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d")
TIME_FORMATS = ("%H:%M", "%H%M", "%H:%M:%S")
DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y.%m.%d %H:%M:%S",
    "%Y%m%d %H:%M",
    "%Y%m%d %H%M",
)

RECENT_FORM_WINDOW = 5
RECENT_FORM_FEATURE_ORDER = [
    "home_recent_match_count",
    "away_recent_match_count",
    "home_recent_points_pg",
    "away_recent_points_pg",
    "recent_points_diff",
    "home_recent_goal_diff_pg",
    "away_recent_goal_diff_pg",
    "recent_goal_diff_diff",
    "home_recent_goals_for_pg",
    "away_recent_goals_for_pg",
    "home_recent_win_rate",
    "away_recent_win_rate",
]
STATSBOMB_REVIEW_FEATURE_ORDER = [
    "statsbomb_available",
    "event_count",
    "home_xg",
    "away_xg",
    "xg_diff",
    "xg_total",
    "home_shots",
    "away_shots",
    "shot_diff",
    "shot_total",
    "home_shots_on_target",
    "away_shots_on_target",
    "shots_on_target_diff",
    "home_passes",
    "away_passes",
    "pass_diff",
    "home_carries",
    "away_carries",
    "carry_diff",
    "home_pressures",
    "away_pressures",
    "pressure_diff",
    "home_fouls_committed",
    "away_fouls_committed",
    "foul_diff",
    "home_yellow_cards",
    "away_yellow_cards",
    "card_diff",
    "home_red_cards",
    "away_red_cards",
    "red_card_diff",
    "first_goal_minute",
    "last_goal_minute",
    "prediction_confidence",
    "market_entropy_score",
    "handicap_margin_score",
    "high_strategy_count",
    "high_strategy_miss_count",
]

MARKET_COMPANY_PREFIXES = ("威欧", "澳欧", "立欧", "B36欧", "皇欧")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except Exception:
        return default


def _pick_value(row: dict[str, Any], field_name: str) -> Any:
    for key in FIELD_ALIASES.get(field_name, (field_name,)):
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _average_present(values: list[float | None]) -> float:
    usable = [float(item) for item in values if item is not None]
    if not usable:
        return 0.0
    return sum(usable) / float(len(usable))


def _company_market_average(row: dict[str, Any]) -> dict[str, float]:
    opening_home: list[float | None] = []
    opening_draw: list[float | None] = []
    opening_away: list[float | None] = []
    return_rate: list[float | None] = []
    kelly_home: list[float | None] = []
    kelly_draw: list[float | None] = []
    kelly_away: list[float | None] = []
    for prefix in MARKET_COMPANY_PREFIXES:
        opening_home.append(_safe_float(row.get(f"{prefix}初胜")))
        opening_draw.append(_safe_float(row.get(f"{prefix}初平")))
        opening_away.append(_safe_float(row.get(f"{prefix}初负")))
        return_rate.append(_safe_float(row.get(f"{prefix}终返还率")))
        kelly_home.append(_safe_float(row.get(f"{prefix}终胜凯利")))
        kelly_draw.append(_safe_float(row.get(f"{prefix}终平凯利")))
        kelly_away.append(_safe_float(row.get(f"{prefix}终负凯利")))
    return {
        "opening_odds_home": round(_average_present(opening_home), 4),
        "opening_odds_draw": round(_average_present(opening_draw), 4),
        "opening_odds_away": round(_average_present(opening_away), 4),
        "return_rate": round(_average_present(return_rate), 4),
        "kelly_home": round(_average_present(kelly_home), 4),
        "kelly_draw": round(_average_present(kelly_draw), 4),
        "kelly_away": round(_average_present(kelly_away), 4),
    }


def _parse_date(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern).strftime("%Y-%m-%d")
        except Exception:
            continue
    if " " in text:
        left = text.split(" ", 1)[0].strip()
        for pattern in DATE_FORMATS:
            try:
                return datetime.strptime(left, pattern).strftime("%Y-%m-%d")
            except Exception:
                continue
    return ""


def _parse_time(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    for pattern in TIME_FORMATS:
        try:
            return datetime.strptime(text, pattern).strftime("%H:%M")
        except Exception:
            continue
    return ""


def _parse_kickoff(value: Any) -> tuple[str, str]:
    text = _normalize_text(value)
    if not text:
        return "", ""
    for pattern in DATETIME_FORMATS:
        try:
            dt = datetime.strptime(text, pattern)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
        except Exception:
            continue
    return "", ""


def _parse_year_and_match_time(year_value: Any, match_time_raw: Any) -> tuple[str, str]:
    year_text = _normalize_text(year_value)
    raw_text = _normalize_text(match_time_raw)
    if not year_text or not raw_text or " " not in raw_text:
        return "", ""
    parts = raw_text.split(" ", 1)
    if len(parts) != 2:
        return "", ""
    date_part = parts[0].strip()
    time_part = parts[1].strip()
    if len(date_part) >= 8:
        for pattern in DATE_FORMATS:
            try:
                date_obj = datetime.strptime(date_part, pattern)
                return date_obj.strftime("%Y-%m-%d"), _parse_time(time_part)
            except Exception:
                continue
    for pattern in ("%m-%d", "%m/%d", "%m.%d"):
        try:
            date_obj = datetime.strptime(f"{year_text}-{date_part}", f"%Y-{pattern}")
            return date_obj.strftime("%Y-%m-%d"), _parse_time(time_part)
        except Exception:
            continue
    return "", ""


def _parse_score_pair(value: Any) -> tuple[int | None, int | None]:
    text = _normalize_text(value)
    if not text:
        return None, None
    normalized = text.replace("：", ":").replace("-", ":").replace(" ", "")
    if ":" not in normalized:
        return None, None
    left, right = normalized.split(":", 1)
    left_val = _safe_int(left)
    right_val = _safe_int(right)
    return left_val, right_val


def _normalize_market_probs(odds_home: float, odds_draw: float, odds_away: float) -> tuple[float, float, float]:
    home = 1.0 / max(float(odds_home), 1.01)
    draw = 1.0 / max(float(odds_draw), 1.01)
    away = 1.0 / max(float(odds_away), 1.01)
    total = max(home + draw + away, 1e-9)
    return home / total, draw / total, away / total


def _result_to_label(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return 0
    if home_goals < away_goals:
        return 2
    return 1


def _parse_match_minutes(match_time: str) -> float:
    if not match_time or ":" not in match_time:
        return 0.0
    hour_text, minute_text = match_time.split(":", 1)
    try:
        return float(int(hour_text) * 60 + int(minute_text))
    except Exception:
        return 0.0


def _is_weekend(match_date: str) -> float:
    try:
        date_obj = datetime.strptime(match_date, "%Y-%m-%d")
    except Exception:
        return 0.0
    return 1.0 if date_obj.weekday() >= 5 else 0.0


def _match_sort_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(item.get("match_date", "")),
        str(item.get("match_time", "")),
        str(item.get("league", "")),
        str(item.get("match_id", "")),
    )


def _match_datetime_key(match_date: str, match_time: str, match_id: str = "") -> tuple[str, str, str]:
    return str(match_date or ""), str(match_time or "00:00"), str(match_id or "")


def _result_points(goals_for: int, goals_against: int) -> int:
    if goals_for > goals_against:
        return 3
    if goals_for < goals_against:
        return 0
    return 1


def _append_team_history(
    team_histories: dict[str, list[dict[str, Any]]],
    team_name: str,
    match_date: str,
    match_time: str,
    match_id: str,
    goals_for: int,
    goals_against: int,
) -> None:
    team_histories.setdefault(team_name, []).append(
        {
            "match_date": match_date,
            "match_time": match_time,
            "match_id": match_id,
            "goals_for": int(goals_for),
            "goals_against": int(goals_against),
        }
    )


def _take_recent_history(
    entries: list[dict[str, Any]],
    cutoff: tuple[str, str, str] | None = None,
    window: int = RECENT_FORM_WINDOW,
) -> list[dict[str, Any]]:
    if not entries:
        return []
    if cutoff is None:
        return entries[-window:]
    filtered = [
        item
        for item in entries
        if _match_datetime_key(
            str(item.get("match_date", "")),
            str(item.get("match_time", "00:00")),
            str(item.get("match_id", "")),
        )
        < cutoff
    ]
    return filtered[-window:]


def _summarize_recent_history(entries: list[dict[str, Any]]) -> dict[str, float]:
    count = len(entries)
    if count <= 0:
        return {
            "match_count": 0.0,
            "points_pg": 0.0,
            "goal_diff_pg": 0.0,
            "goals_for_pg": 0.0,
            "win_rate": 0.0,
        }

    points_total = 0.0
    goal_diff_total = 0.0
    goals_for_total = 0.0
    win_total = 0.0
    for item in entries:
        goals_for = int(item.get("goals_for", 0))
        goals_against = int(item.get("goals_against", 0))
        points_total += _result_points(goals_for, goals_against)
        goal_diff_total += goals_for - goals_against
        goals_for_total += goals_for
        if goals_for > goals_against:
            win_total += 1.0

    games = float(count)
    return {
        "match_count": games / float(RECENT_FORM_WINDOW),
        "points_pg": points_total / games,
        "goal_diff_pg": goal_diff_total / games,
        "goals_for_pg": goals_for_total / games,
        "win_rate": win_total / games,
    }


def build_recent_form_feature_map(
    team_histories: dict[str, list[dict[str, Any]]],
    home_team: str,
    away_team: str,
    cutoff_date: str | None = None,
    cutoff_time: str | None = None,
    match_id: str = "",
    window: int = RECENT_FORM_WINDOW,
) -> dict[str, float]:
    cutoff = None
    if cutoff_date:
        cutoff = _match_datetime_key(cutoff_date, cutoff_time or "00:00", match_id)
    home_recent = _take_recent_history(team_histories.get(home_team, []), cutoff=cutoff, window=window)
    away_recent = _take_recent_history(team_histories.get(away_team, []), cutoff=cutoff, window=window)
    home_summary = _summarize_recent_history(home_recent)
    away_summary = _summarize_recent_history(away_recent)
    return {
        "home_recent_match_count": round(home_summary["match_count"], 4),
        "away_recent_match_count": round(away_summary["match_count"], 4),
        "home_recent_points_pg": round(home_summary["points_pg"], 4),
        "away_recent_points_pg": round(away_summary["points_pg"], 4),
        "recent_points_diff": round(home_summary["points_pg"] - away_summary["points_pg"], 4),
        "home_recent_goal_diff_pg": round(home_summary["goal_diff_pg"], 4),
        "away_recent_goal_diff_pg": round(away_summary["goal_diff_pg"], 4),
        "recent_goal_diff_diff": round(home_summary["goal_diff_pg"] - away_summary["goal_diff_pg"], 4),
        "home_recent_goals_for_pg": round(home_summary["goals_for_pg"], 4),
        "away_recent_goals_for_pg": round(away_summary["goals_for_pg"], 4),
        "home_recent_win_rate": round(home_summary["win_rate"], 4),
        "away_recent_win_rate": round(away_summary["win_rate"], 4),
    }


def build_team_histories_from_state(
    sample_items: list[dict[str, Any]],
    settlement_items: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    merged_matches: dict[str, dict[str, Any]] = {}

    for item in sample_items:
        if not isinstance(item, dict):
            continue
        meta = item.get("meta")
        if not isinstance(meta, dict):
            continue
        match_id = _normalize_text(item.get("match_id"))
        match_date = _normalize_text(meta.get("match_date"))
        home_team = _normalize_text(meta.get("home_team"))
        away_team = _normalize_text(meta.get("away_team"))
        if not match_id or not match_date or not home_team or not away_team:
            continue
        home_goals = _safe_int(meta.get("home_goals"))
        away_goals = _safe_int(meta.get("away_goals"))
        if home_goals is None or away_goals is None:
            continue
        merged_matches[match_id] = {
            "match_id": match_id,
            "match_date": match_date,
            "match_time": _normalize_text(meta.get("match_time")) or "00:00",
            "home_team": home_team,
            "away_team": away_team,
            "home_goals": int(home_goals),
            "away_goals": int(away_goals),
        }

    for item in settlement_items or []:
        if not isinstance(item, dict):
            continue
        match_id = _normalize_text(item.get("match_id"))
        match_date = _normalize_text(item.get("match_date"))
        home_team = _normalize_text(item.get("home_team"))
        away_team = _normalize_text(item.get("away_team"))
        if not match_id or not match_date or not home_team or not away_team:
            continue
        home_goals = _safe_int(item.get("home_goals"))
        away_goals = _safe_int(item.get("away_goals"))
        if home_goals is None or away_goals is None:
            continue
        merged_matches[match_id] = {
            "match_id": match_id,
            "match_date": match_date,
            "match_time": _normalize_text(item.get("match_time")) or "00:00",
            "home_team": home_team,
            "away_team": away_team,
            "home_goals": int(home_goals),
            "away_goals": int(away_goals),
        }

    ordered_matches = sorted(merged_matches.values(), key=lambda item: _match_datetime_key(item["match_date"], item["match_time"], item["match_id"]))
    team_histories: dict[str, list[dict[str, Any]]] = {}
    for item in ordered_matches:
        _append_team_history(
            team_histories,
            item["home_team"],
            item["match_date"],
            item["match_time"],
            item["match_id"],
            item["home_goals"],
            item["away_goals"],
        )
        _append_team_history(
            team_histories,
            item["away_team"],
            item["match_date"],
            item["match_time"],
            item["match_id"],
            item["away_goals"],
            item["home_goals"],
        )
    return team_histories


def _statsbomb_summary_from_settlement(item: dict[str, Any]) -> dict[str, Any]:
    summary = item.get("statsbomb_event_summary")
    return summary if isinstance(summary, dict) else {}


def _statsbomb_team_stats(item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = _statsbomb_summary_from_settlement(item)
    team_stats = summary.get("team_stats")
    if not isinstance(team_stats, dict):
        return {}, {}
    home_team = _normalize_text(item.get("home_team"))
    away_team = _normalize_text(item.get("away_team"))
    home_stats = team_stats.get(home_team) if home_team else None
    away_stats = team_stats.get(away_team) if away_team else None
    if not isinstance(home_stats, dict) or not isinstance(away_stats, dict):
        values = [value for value in team_stats.values() if isinstance(value, dict)]
        if len(values) >= 2:
            if not isinstance(home_stats, dict):
                home_stats = values[0]
            if not isinstance(away_stats, dict):
                away_stats = values[1]
    return (home_stats if isinstance(home_stats, dict) else {}, away_stats if isinstance(away_stats, dict) else {})


def _known_bool_label(value: Any) -> int | None:
    if isinstance(value, bool):
        return 0 if value else 1
    return None


def _statsbomb_review_feature_map(item: dict[str, Any]) -> dict[str, float]:
    summary = _statsbomb_summary_from_settlement(item)
    home_stats, away_stats = _statsbomb_team_stats(item)
    home_xg = _safe_float(home_stats.get("xg"), default=0.0) or 0.0
    away_xg = _safe_float(away_stats.get("xg"), default=0.0) or 0.0
    home_shots = _safe_float(home_stats.get("shots"), default=0.0) or 0.0
    away_shots = _safe_float(away_stats.get("shots"), default=0.0) or 0.0
    home_sot = _safe_float(home_stats.get("shots_on_target"), default=0.0) or 0.0
    away_sot = _safe_float(away_stats.get("shots_on_target"), default=0.0) or 0.0
    home_passes = _safe_float(home_stats.get("passes"), default=0.0) or 0.0
    away_passes = _safe_float(away_stats.get("passes"), default=0.0) or 0.0
    home_carries = _safe_float(home_stats.get("carries"), default=0.0) or 0.0
    away_carries = _safe_float(away_stats.get("carries"), default=0.0) or 0.0
    home_pressures = _safe_float(home_stats.get("pressures"), default=0.0) or 0.0
    away_pressures = _safe_float(away_stats.get("pressures"), default=0.0) or 0.0
    home_fouls = _safe_float(home_stats.get("fouls_committed"), default=0.0) or 0.0
    away_fouls = _safe_float(away_stats.get("fouls_committed"), default=0.0) or 0.0
    home_yellow = _safe_float(home_stats.get("yellow_cards"), default=0.0) or 0.0
    away_yellow = _safe_float(away_stats.get("yellow_cards"), default=0.0) or 0.0
    home_red = _safe_float(home_stats.get("red_cards"), default=0.0) or 0.0
    away_red = _safe_float(away_stats.get("red_cards"), default=0.0) or 0.0
    high_items = item.get("high_accuracy_strategy_items")
    strategy_items = [row for row in high_items if isinstance(row, dict)] if isinstance(high_items, list) else []
    strategy_misses = sum(1 for row in strategy_items if row.get("is_hit") is False)
    return {
        "statsbomb_available": 1.0,
        "event_count": _safe_float(summary.get("event_count"), default=0.0) or 0.0,
        "home_xg": round(home_xg, 4),
        "away_xg": round(away_xg, 4),
        "xg_diff": round(home_xg - away_xg, 4),
        "xg_total": round(home_xg + away_xg, 4),
        "home_shots": home_shots,
        "away_shots": away_shots,
        "shot_diff": home_shots - away_shots,
        "shot_total": home_shots + away_shots,
        "home_shots_on_target": home_sot,
        "away_shots_on_target": away_sot,
        "shots_on_target_diff": home_sot - away_sot,
        "home_passes": home_passes,
        "away_passes": away_passes,
        "pass_diff": home_passes - away_passes,
        "home_carries": home_carries,
        "away_carries": away_carries,
        "carry_diff": home_carries - away_carries,
        "home_pressures": home_pressures,
        "away_pressures": away_pressures,
        "pressure_diff": home_pressures - away_pressures,
        "home_fouls_committed": home_fouls,
        "away_fouls_committed": away_fouls,
        "foul_diff": home_fouls - away_fouls,
        "home_yellow_cards": home_yellow,
        "away_yellow_cards": away_yellow,
        "card_diff": (home_yellow + home_red) - (away_yellow + away_red),
        "home_red_cards": home_red,
        "away_red_cards": away_red,
        "red_card_diff": home_red - away_red,
        "first_goal_minute": _safe_float(summary.get("first_goal_minute"), default=-1.0) or -1.0,
        "last_goal_minute": _safe_float(summary.get("last_goal_minute"), default=-1.0) or -1.0,
        "prediction_confidence": _safe_float(item.get("prediction_confidence") or item.get("confidence"), default=0.0) or 0.0,
        "market_entropy_score": _safe_float(item.get("market_entropy_score"), default=0.0) or 0.0,
        "handicap_margin_score": _safe_float(item.get("handicap_margin_score"), default=0.0) or 0.0,
        "high_strategy_count": float(len(strategy_items)),
        "high_strategy_miss_count": float(strategy_misses),
    }


def build_statsbomb_review_training_samples(
    settlements: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    skipped_missing_statsbomb = 0
    skipped_unknown_label = 0
    label_counts = {"prediction_miss": {0: 0, 1: 0}, "handicap_miss": {0: 0, 1: 0}, "ou_miss": {0: 0, 1: 0}}
    for item in settlements:
        if not isinstance(item, dict):
            continue
        if not _statsbomb_summary_from_settlement(item):
            skipped_missing_statsbomb += 1
            continue
        prediction_miss = _known_bool_label(item.get("is_correct"))
        handicap_miss = _known_bool_label(item.get("handicap_is_correct"))
        ou_miss = _known_bool_label(item.get("ou_is_correct"))
        if prediction_miss is None and handicap_miss is None and ou_miss is None:
            skipped_unknown_label += 1
            continue
        labels = {
            "prediction_miss": prediction_miss,
            "handicap_miss": handicap_miss,
            "ou_miss": ou_miss,
        }
        for key, value in labels.items():
            if value in (0, 1):
                label_counts[key][int(value)] += 1
        features = _statsbomb_review_feature_map(item)
        samples.append(
            {
                "timestamp": _normalize_text(item.get("timestamp")) or f"{_normalize_text(item.get('match_date'))} {_normalize_text(item.get('match_time'))}",
                "match_id": _normalize_text(item.get("match_id")),
                "features": {key: float(features.get(key, 0.0)) for key in STATSBOMB_REVIEW_FEATURE_ORDER},
                "labels": labels,
                "meta": {
                    "source": "statsbomb_review_training",
                    "match_date": _normalize_text(item.get("match_date")),
                    "match_time": _normalize_text(item.get("match_time")),
                    "league": _normalize_text(item.get("league")),
                    "home_team": _normalize_text(item.get("home_team")),
                    "away_team": _normalize_text(item.get("away_team")),
                    "home_goals": _safe_int(item.get("home_goals")),
                    "away_goals": _safe_int(item.get("away_goals")),
                    "statsbomb_source_match_id": item.get("statsbomb_source_match_id"),
                },
            }
        )
    summary = {
        "sample_count": len(samples),
        "skipped_missing_statsbomb": skipped_missing_statsbomb,
        "skipped_unknown_label": skipped_unknown_label,
        "feature_order": list(STATSBOMB_REVIEW_FEATURE_ORDER),
        "label_counts": label_counts,
    }
    return samples, summary


def export_statsbomb_review_training_samples(
    project_dir: Path,
    settlements: list[dict[str, Any]],
    output_path: Path | None = None,
) -> dict[str, Any]:
    samples, summary = build_statsbomb_review_training_samples(settlements)
    resolved_output = output_path or project_dir / "data" / "state" / "statsbomb_review_training_samples.json"
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb Open Data + app settlements",
        "purpose": "post_match_review_error_attribution",
        "leakage_note": "These samples use post-match event data and must not be used as pre-match prediction features.",
        "summary": summary,
        "items": samples,
    }
    resolved_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**summary, "output_path": str(resolved_output)}


def _statsbomb_baseline_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _statsbomb_side_from_margin(value: float, *, threshold: float = 0.0) -> str:
    if value > threshold:
        return "home"
    if value < -threshold:
        return "away"
    return "draw"


def _statsbomb_side_label(value: str) -> str:
    if value == "home":
        return "HOME"
    if value == "away":
        return "AWAY"
    if value == "draw":
        return "DRAW"
    return "-"


def _statsbomb_fewshot_tags(row: dict[str, Any], *, is_hit: bool, simulated_pick: str, actual: str) -> list[str]:
    tags: list[str] = ["statsbomb_post_match_review"]
    xg_aligned = bool(row.get("xg_aligned_with_score"))
    shot_aligned = bool(row.get("shot_aligned_with_score"))
    finishing_variance = bool(row.get("finishing_variance"))
    xg_margin = _safe_float(row.get("xg_margin"), 0.0) or 0.0
    shot_margin = _safe_float(row.get("shot_margin"), 0.0) or 0.0
    if not is_hit:
        tags.append("strategy_miss")
    else:
        tags.append("strategy_hit")
    if finishing_variance:
        tags.append("statsbomb_finishing_variance")
    if not xg_aligned:
        tags.append("xg_result_divergence")
    if not shot_aligned:
        tags.append("shot_result_divergence")
    if abs(xg_margin) >= 0.35 and abs(shot_margin) >= 4:
        tags.append("event_control_gap")
    if simulated_pick != actual and simulated_pick in {"home", "away"}:
        tags.append("xg_direction_failed")
    deduped: list[str] = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def build_statsbomb_sandbox_fewshot_samples(
    baseline_payload: dict[str, Any],
    *,
    limit: int = 80,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _statsbomb_baseline_items(baseline_payload)
    baseline_summary = baseline_payload.get("summary") if isinstance(baseline_payload.get("summary"), dict) else {}
    samples: list[dict[str, Any]] = []
    tag_counts: dict[str, int] = {}
    for row in rows:
        score_winner = _normalize_text(row.get("score_winner")).lower()
        if score_winner not in {"home", "away", "draw"}:
            score_winner = _statsbomb_side_from_margin(float(_safe_float(row.get("goal_margin"), 0.0) or 0.0))
        xg_winner = _normalize_text(row.get("xg_winner")).lower()
        if xg_winner not in {"home", "away", "draw"}:
            xg_winner = _statsbomb_side_from_margin(float(_safe_float(row.get("xg_margin"), 0.0) or 0.0), threshold=0.25)
        simulated_pick = xg_winner if xg_winner in {"home", "away", "draw"} else score_winner
        actual = score_winner
        is_hit = simulated_pick == actual
        tags = _statsbomb_fewshot_tags(row, is_hit=is_hit, simulated_pick=simulated_pick, actual=actual)
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        match_title = f"{_normalize_text(row.get('home_team'))} vs {_normalize_text(row.get('away_team'))}"
        prompt = (
            "请作为 Evaluation Agent 复盘一场使用 StatsBomb 赛后事件的历史沙盒案例。\n"
            f"比赛: {row.get('match_date') or '-'} | {row.get('league') or '-'} | {match_title}\n"
            f"比分: {row.get('score') or '-'} | 模拟策略: 按 xG 方向选择 {_statsbomb_side_label(simulated_pick)} | 实际: {_statsbomb_side_label(actual)}\n"
            f"xG: {float(_safe_float(row.get('home_xg'), 0.0) or 0.0):.2f}-{float(_safe_float(row.get('away_xg'), 0.0) or 0.0):.2f} | "
            f"射门: {_safe_int(row.get('home_shots'), 0)}-{_safe_int(row.get('away_shots'), 0)} | "
            f"历史基线终结波动率: {baseline_summary.get('finishing_variance_rate') or '-'}"
        )
        if is_hit:
            root_cause = "event_evidence_aligned"
            recommendation = "保持赛后事件证据归档，作为模型正确样本。"
            completion = "结论: 模拟策略命中。StatsBomb 事件方向与赛果一致，可作为正向复盘样本。"
        else:
            root_cause = "statsbomb_finishing_variance" if bool(row.get("finishing_variance")) else "event_result_divergence"
            recommendation = "标记为赛后归因样本，不应回灌到赛前预测特征；用于提醒模型区分方向错误与终结波动。"
            completion = (
                "结论: 模拟策略未命中。StatsBomb 显示 xG 或射门质量支持模拟方向，但赛果相反，"
                "应优先归因为终结波动/事件与结果背离，而不是简单扩大赛前预测惩罚。"
            )
        samples.append(
            {
                "id": f"statsbomb_sandbox:{row.get('source_match_id') or row.get('match_id') or len(samples) + 1}",
                "prompt": prompt,
                "completion": completion,
                "labels": {
                    "simulated_pick": _statsbomb_side_label(simulated_pick),
                    "actual": _statsbomb_side_label(actual),
                    "is_hit": bool(is_hit),
                    "root_cause": root_cause,
                    "tags": tags,
                },
                "features": {
                    "home_xg": float(_safe_float(row.get("home_xg"), 0.0) or 0.0),
                    "away_xg": float(_safe_float(row.get("away_xg"), 0.0) or 0.0),
                    "xg_margin": float(_safe_float(row.get("xg_margin"), 0.0) or 0.0),
                    "home_shots": float(_safe_float(row.get("home_shots"), 0.0) or 0.0),
                    "away_shots": float(_safe_float(row.get("away_shots"), 0.0) or 0.0),
                    "shot_margin": float(_safe_float(row.get("shot_margin"), 0.0) or 0.0),
                    "event_count": float(_safe_float(row.get("event_count"), 0.0) or 0.0),
                },
                "meta": {
                    "source": "statsbomb_event_sandbox",
                    "match_id": row.get("match_id"),
                    "source_match_id": row.get("source_match_id"),
                    "match_date": row.get("match_date"),
                    "league": row.get("league"),
                    "season": row.get("season"),
                    "home_team": row.get("home_team"),
                    "away_team": row.get("away_team"),
                    "score": row.get("score"),
                    "recommendation": recommendation,
                },
            }
        )
    samples.sort(
        key=lambda item: (
            not bool(item.get("labels", {}).get("is_hit") is False),
            "statsbomb_finishing_variance" not in item.get("labels", {}).get("tags", []),
            -abs(float(item.get("features", {}).get("xg_margin") or 0.0)),
            str(item.get("meta", {}).get("match_date") or ""),
        )
    )
    limited = samples[: max(0, int(limit))]
    summary = {
        "sample_count": len(limited),
        "source_count": len(rows),
        "baseline_match_count": _safe_int(baseline_summary.get("match_count"), len(rows)),
        "tag_counts": dict(sorted(tag_counts.items())),
        "leakage_note": "These few-shot samples use post-match event data and must not be used as pre-match prediction features.",
    }
    return limited, summary


def export_statsbomb_sandbox_fewshot_samples(
    project_dir: Path,
    baseline_payload: dict[str, Any],
    output_path: Path | None = None,
    *,
    limit: int = 80,
) -> dict[str, Any]:
    samples, summary = build_statsbomb_sandbox_fewshot_samples(baseline_payload, limit=limit)
    resolved_output = output_path or project_dir / "data" / "state" / "statsbomb_sandbox_fewshot_samples.json"
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb Open Data event baseline",
        "purpose": "evaluation_agent_fewshot_post_match_review",
        "leakage_note": summary["leakage_note"],
        "summary": summary,
        "items": samples,
    }
    resolved_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**summary, "output_path": str(resolved_output)}


VIDEO_REVIEW_EVENT_ROOT_CAUSES = {
    "tempo_shift": "video_tempo_shift",
    "finishing_variance": "video_finishing_variance",
    "set_piece_or_transition_risk": "video_margin_risk",
    "low_quality_video_evidence": "video_low_quality_evidence",
    "manual_tactical_review_needed": "video_manual_review_needed",
}


def _video_review_match_payload(review: dict[str, Any]) -> dict[str, Any]:
    match = review.get("match") if isinstance(review.get("match"), dict) else {}
    return {
        "match_date": _normalize_text(match.get("match_date")),
        "league": _normalize_text(match.get("league")),
        "home_team": _normalize_text(match.get("home_team")),
        "away_team": _normalize_text(match.get("away_team")),
        "score": _normalize_text(match.get("score")),
        "result": _normalize_text(match.get("result")),
    }


def _video_review_event_tags(root_cause: str, *, is_hit: bool, source_kind: str, event_type: str = "") -> list[str]:
    tags = ["video_post_match_review", source_kind]
    tags.append("strategy_hit" if is_hit else "strategy_miss")
    if root_cause:
        tags.append(root_cause)
    if event_type:
        tags.append(f"video_event_{event_type}")
    deduped: list[str] = []
    for tag in tags:
        if tag and tag not in deduped:
            deduped.append(tag)
    return deduped


def _video_review_sample_from_signal(
    review: dict[str, Any],
    *,
    signal: dict[str, Any],
    source_kind: str,
    index: int,
) -> dict[str, Any]:
    agent = review.get("agent_review") if isinstance(review.get("agent_review"), dict) else {}
    visual = review.get("visual_analysis") if isinstance(review.get("visual_analysis"), dict) else {}
    match = _video_review_match_payload(review)
    review_id = _normalize_text(review.get("review_id")) or f"review-{index}"
    hypothesis_code = _normalize_text(signal.get("code")) or "manual_tactical_review_needed"
    root_cause = VIDEO_REVIEW_EVENT_ROOT_CAUSES.get(hypothesis_code, hypothesis_code)
    event_type = _normalize_text(signal.get("event_type"))
    annotation_id = _normalize_text(signal.get("annotation_id"))
    prediction_alignment = _normalize_text(agent.get("prediction_alignment")) or "unknown"
    is_hit = prediction_alignment == "aligned"
    confidence = float(_safe_float(signal.get("confidence"), 0.0) or 0.0)
    evidence_score = float(_safe_float(agent.get("evidence_score"), 0.0) or 0.0)
    frame_index = _safe_int(signal.get("frame_index"), _safe_int(signal.get("frame"), None))
    timestamp_seconds = _safe_float(signal.get("timestamp_seconds"), _safe_float(signal.get("time_seconds"), None))
    title = _normalize_text(signal.get("title")) or f"Video signal: {hypothesis_code}"
    evidence = _normalize_text(signal.get("evidence")) or _normalize_text(signal.get("note")) or "-"
    match_title = f"{match['home_team'] or '-'} vs {match['away_team'] or '-'}"
    prompt = (
        "请作为 Evaluation Agent 复盘一场使用 AI 视频证据的赛后案例。\n"
        f"比赛: {match['match_date'] or '-'} | {match['league'] or '-'} | {match_title}\n"
        f"比分: {match['score'] or '-'} | 预测对齐: {prediction_alignment}\n"
        f"视频证据: {agent.get('evidence_level') or '-'} / {evidence_score:.2f} | "
        f"事件: {title} | 证据: {evidence}"
    )
    completion = (
        f"结论: 该视频复盘样本根因为 {root_cause}。"
        f"事件假设 {hypothesis_code} 置信度 {confidence:.2f}，"
        "仅用于赛后错因归类与 Evaluation Agent 记忆，不进入赛前预测特征。"
    )
    if source_kind == "video_manual_annotation":
        completion = (
            f"结论: 人工视频标注支持 {root_cause}。"
            f"标注事件 {event_type or hypothesis_code} 置信度 {confidence:.2f}，"
            "应作为赛后复盘记忆，用于修正类似比赛的错因解释。"
        )
    sample_id_suffix = annotation_id or f"{source_kind}:{index}:{hypothesis_code}"
    return {
        "id": f"video_review:{review_id}:{sample_id_suffix}",
        "prompt": prompt,
        "completion": completion,
        "review_status": "draft",
        "labels": {
            "simulated_pick": prediction_alignment.upper() if prediction_alignment else "UNKNOWN",
            "actual": match["result"] or match["score"] or "-",
            "is_hit": bool(is_hit),
            "root_cause": root_cause,
            "tags": _video_review_event_tags(root_cause, is_hit=is_hit, source_kind=source_kind, event_type=event_type),
        },
        "features": {
            "evidence_score": evidence_score,
            "review_confidence": float(_safe_float(agent.get("review_confidence"), evidence_score) or 0.0),
            "hypothesis_confidence": confidence,
            "manual_annotation_count": float(_safe_int(agent.get("manual_annotation_count"), 0) or 0),
            "frame_index": float(frame_index or 0),
            "timestamp_seconds": float(timestamp_seconds or 0.0),
            "frame_count": float(_safe_int(visual.get("frame_count"), 0) or 0),
            "usable_frame_count": float(_safe_int(visual.get("usable_frame_count"), 0) or 0),
            "key_frame_count": float(_safe_int(agent.get("key_frame_count"), 0) or 0),
        },
        "meta": {
            "source": source_kind,
            "match_id": _normalize_text(review.get("match_id")),
            "review_id": review_id,
            "annotation_id": annotation_id,
            "event_type": event_type,
            "hypothesis_code": hypothesis_code,
            "match_date": match["match_date"],
            "league": match["league"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "score": match["score"],
            "recommendation": _normalize_text((agent.get("recommended_followup") or {}).get("message") if isinstance(agent.get("recommended_followup"), dict) else ""),
        },
    }


def build_video_review_fewshot_samples(
    video_reviews: list[dict[str, Any]],
    *,
    limit: int = 80,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    tag_counts: dict[str, int] = {}
    skipped_no_signal = 0
    source_counts = {"video_manual_annotation": 0, "video_auto_hypothesis": 0}
    for review in video_reviews:
        if not isinstance(review, dict):
            continue
        agent = review.get("agent_review") if isinstance(review.get("agent_review"), dict) else {}
        annotations = [item for item in review.get("manual_annotations", []) if isinstance(item, dict)]
        if annotations:
            for index, annotation in enumerate(annotations, start=1):
                signal = dict(annotation)
                event_type = _normalize_text(signal.get("event_type"))
                mapped = {
                    "goal": "finishing_variance",
                    "shot_quality": "finishing_variance",
                    "set_piece": "set_piece_or_transition_risk",
                    "counter_attack": "set_piece_or_transition_risk",
                    "defensive_error": "set_piece_or_transition_risk",
                    "tempo_shift": "tempo_shift",
                    "tactical_shift": "tempo_shift",
                }.get(event_type, "manual_tactical_review_needed")
                signal["code"] = mapped
                signal["title"] = signal.get("event_label") or event_type or mapped
                sample = _video_review_sample_from_signal(review, signal=signal, source_kind="video_manual_annotation", index=index)
                samples.append(sample)
                source_counts["video_manual_annotation"] += 1
            continue
        hypotheses = [item for item in agent.get("event_hypotheses", []) if isinstance(item, dict)]
        if not hypotheses:
            skipped_no_signal += 1
            continue
        for index, hypothesis in enumerate(hypotheses[:3], start=1):
            sample = _video_review_sample_from_signal(review, signal=dict(hypothesis), source_kind="video_auto_hypothesis", index=index)
            samples.append(sample)
            source_counts["video_auto_hypothesis"] += 1
    for sample in samples:
        labels = sample.get("labels") if isinstance(sample.get("labels"), dict) else {}
        for tag in labels.get("tags", []) if isinstance(labels.get("tags"), list) else []:
            tag_counts[str(tag)] = tag_counts.get(str(tag), 0) + 1
    samples.sort(
        key=lambda item: (
            _normalize_text((item.get("meta") or {}).get("source") if isinstance(item.get("meta"), dict) else "") != "video_manual_annotation",
            -float((item.get("features") or {}).get("hypothesis_confidence", 0.0) if isinstance(item.get("features"), dict) else 0.0),
            str((item.get("meta") or {}).get("match_date") if isinstance(item.get("meta"), dict) else ""),
        )
    )
    limited = samples[: max(0, int(limit))]
    summary = {
        "sample_count": len(limited),
        "source_review_count": len([item for item in video_reviews if isinstance(item, dict)]),
        "manual_annotation_sample_count": source_counts["video_manual_annotation"],
        "auto_hypothesis_sample_count": source_counts["video_auto_hypothesis"],
        "skipped_no_signal": skipped_no_signal,
        "tag_counts": dict(sorted(tag_counts.items())),
        "leakage_note": "These few-shot samples use post-match video evidence and must not be used as pre-match prediction features.",
    }
    return limited, summary


def export_video_review_fewshot_samples(
    project_dir: Path,
    video_reviews: list[dict[str, Any]],
    output_path: Path | None = None,
    *,
    limit: int = 80,
) -> dict[str, Any]:
    samples, summary = build_video_review_fewshot_samples(video_reviews, limit=limit)
    resolved_output = output_path or project_dir / "data" / "state" / "video_review_fewshot_samples.json"
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "AI VideoReview Agent manual annotations and event hypotheses",
        "purpose": "evaluation_agent_video_fewshot_post_match_review",
        "leakage_note": summary["leakage_note"],
        "summary": summary,
        "items": samples,
    }
    resolved_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**summary, "output_path": str(resolved_output)}


def _read_input_records(input_path: Path) -> list[dict[str, Any]]:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        with input_path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        header_index = 0
        for index, row in enumerate(rows[:10]):
            if {"年份", "赛事", "比赛时间", "主队", "客队"}.issubset({str(item).strip() for item in row}):
                header_index = index
                break
        if header_index >= len(rows):
            return []
        header = [str(item).strip() for item in rows[header_index]]
        records: list[dict[str, Any]] = []
        for row in rows[header_index + 1 :]:
            if not row:
                continue
            padded = list(row) + [""] * max(0, len(header) - len(row))
            record = {header[i]: padded[i] for i in range(len(header))}
            if any(str(value).strip() for value in record.values()):
                records.append(record)
        return records
    if suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        with input_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                text = line.strip()
                if not text:
                    continue
                payload = json.loads(text)
                if isinstance(payload, dict):
                    records.append(payload)
        return records
    if suffix == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            items = payload.get("items")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []
    raise ValueError(f"Unsupported file type: {input_path.suffix}")


def _normalize_historical_row(row: dict[str, Any], row_index: int) -> dict[str, Any] | None:
    kickoff_date, kickoff_time = _parse_kickoff(_pick_value(row, "kickoff"))
    short_date, short_time = _parse_year_and_match_time(_pick_value(row, "year"), _pick_value(row, "match_time_raw"))
    match_date = _parse_date(_pick_value(row, "match_date")) or kickoff_date or short_date
    match_time = _parse_time(_pick_value(row, "match_time")) or kickoff_time or short_time or "00:00"
    league = _normalize_text(_pick_value(row, "league"))
    home_team = _normalize_text(_pick_value(row, "home_team"))
    away_team = _normalize_text(_pick_value(row, "away_team"))
    odds_home = _safe_float(_pick_value(row, "odds_home"))
    odds_draw = _safe_float(_pick_value(row, "odds_draw"))
    odds_away = _safe_float(_pick_value(row, "odds_away"))
    home_goals = _safe_int(_pick_value(row, "home_goals"))
    away_goals = _safe_int(_pick_value(row, "away_goals"))
    if home_goals is None or away_goals is None:
        home_goals, away_goals = _parse_score_pair(_pick_value(row, "full_score_text"))
    home_ht_goals = _safe_int(_pick_value(row, "home_ht_goals"))
    away_ht_goals = _safe_int(_pick_value(row, "away_ht_goals"))
    if home_ht_goals is None or away_ht_goals is None:
        home_ht_goals, away_ht_goals = _parse_score_pair(_pick_value(row, "half_score_text"))

    if not match_date or not league or not home_team or not away_team:
        return None
    if odds_home is None or odds_draw is None or odds_away is None or min(odds_home, odds_draw, odds_away) <= 1.0:
        return None
    if home_goals is None or away_goals is None:
        return None

    company_market = _company_market_average(row)
    opening_odds_home = _safe_float(_pick_value(row, "opening_odds_home"), default=0.0) or company_market["opening_odds_home"]
    opening_odds_draw = _safe_float(_pick_value(row, "opening_odds_draw"), default=0.0) or company_market["opening_odds_draw"]
    opening_odds_away = _safe_float(_pick_value(row, "opening_odds_away"), default=0.0) or company_market["opening_odds_away"]
    raw_return_rate = _safe_float(_pick_value(row, "return_rate"), default=0.0) or company_market["return_rate"]
    kelly_home = _safe_float(_pick_value(row, "kelly_home"), default=0.0) or company_market["kelly_home"]
    kelly_draw = _safe_float(_pick_value(row, "kelly_draw"), default=0.0) or company_market["kelly_draw"]
    kelly_away = _safe_float(_pick_value(row, "kelly_away"), default=0.0) or company_market["kelly_away"]

    explicit_match_id = _normalize_text(_pick_value(row, "match_id"))
    match_id = explicit_match_id or f"{match_date}|{league}|{home_team}|{away_team}"
    return {
        "row_index": row_index,
        "source": _normalize_text(row.get("source")),
        "match_id": match_id,
        "match_date": match_date,
        "match_time": match_time,
        "league": league,
        "home_team": home_team,
        "away_team": away_team,
        "odds_home": float(odds_home),
        "odds_draw": float(odds_draw),
        "odds_away": float(odds_away),
        "home_goals": int(home_goals),
        "away_goals": int(away_goals),
        "home_ht_goals": home_ht_goals,
        "away_ht_goals": away_ht_goals,
        "handicap_line": _safe_float(_pick_value(row, "handicap_line"), default=0.0) or 0.0,
        "league_strength": _safe_float(_pick_value(row, "league_strength"), default=DEFAULT_LEAGUE_STRENGTH)
        or DEFAULT_LEAGUE_STRENGTH,
        "home_rating": _safe_float(_pick_value(row, "home_rating")),
        "away_rating": _safe_float(_pick_value(row, "away_rating")),
        "opening_odds_home": opening_odds_home,
        "opening_odds_draw": opening_odds_draw,
        "opening_odds_away": opening_odds_away,
        "return_rate": compute_return_rate(
            odds_home,
            odds_draw,
            odds_away,
            raw_return_rate=raw_return_rate,
        ),
        "kelly_home": kelly_home,
        "kelly_draw": kelly_draw,
        "kelly_away": kelly_away,
    }


def _resolve_pre_match_ratings(
    elo_engine: EloRatingEngine,
    ratings_map: dict[str, float],
    row: dict[str, Any],
) -> tuple[float, float]:
    explicit_home = _safe_float(row.get("home_rating"))
    explicit_away = _safe_float(row.get("away_rating"))
    if explicit_home is not None and explicit_away is not None:
        return float(explicit_home), float(explicit_away)

    market_home, market_draw, market_away = _normalize_market_probs(
        float(row["odds_home"]),
        float(row["odds_draw"]),
        float(row["odds_away"]),
    )
    seeded = elo_engine.from_market(
        market_home,
        market_draw,
        market_away,
        float(row.get("league_strength", DEFAULT_LEAGUE_STRENGTH)),
    )

    home_team = str(row["home_team"])
    away_team = str(row["away_team"])
    home_rating = ratings_map.get(home_team)
    away_rating = ratings_map.get(away_team)

    if explicit_home is not None:
        home_rating = float(explicit_home)
    if explicit_away is not None:
        away_rating = float(explicit_away)

    if home_rating is None and away_rating is None:
        home_rating = seeded.home_rating
        away_rating = seeded.away_rating
    elif home_rating is None:
        home_rating = elo_engine.base_rating + (seeded.home_rating - seeded.away_rating) * 0.35
    elif away_rating is None:
        away_rating = elo_engine.base_rating - (seeded.home_rating - seeded.away_rating) * 0.35

    return float(home_rating), float(away_rating)


def build_xgb_samples_from_historical_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    skipped_invalid = 0
    for index, row in enumerate(records, start=1):
        if not isinstance(row, dict):
            skipped_invalid += 1
            continue
        normalized = _normalize_historical_row(row, index)
        if normalized is None:
            skipped_invalid += 1
            continue
        normalized_rows.append(normalized)

    normalized_rows.sort(key=_match_sort_key)

    elo_engine = EloRatingEngine()
    ratings_map: dict[str, float] = {}
    team_histories: dict[str, list[dict[str, Any]]] = {}
    samples: list[dict[str, Any]] = []
    seen_match_ids: set[str] = set()
    skipped_duplicate = 0
    label_counts = {0: 0, 1: 0, 2: 0}
    date_values: list[str] = []

    for row in normalized_rows:
        match_id = str(row["match_id"])
        if match_id in seen_match_ids:
            skipped_duplicate += 1
            continue
        seen_match_ids.add(match_id)

        home_rating, away_rating = _resolve_pre_match_ratings(elo_engine, ratings_map, row)
        market_home, market_draw, market_away = _normalize_market_probs(
            float(row["odds_home"]),
            float(row["odds_draw"]),
            float(row["odds_away"]),
        )
        recent_form = build_recent_form_feature_map(
            team_histories=team_histories,
            home_team=str(row["home_team"]),
            away_team=str(row["away_team"]),
            cutoff_date=str(row["match_date"]),
            cutoff_time=str(row["match_time"]),
            match_id=match_id,
        )
        feature_map = {
            "market_home": market_home,
            "market_draw": market_draw,
            "market_away": market_away,
            "odds_home": float(row["odds_home"]),
            "odds_draw": float(row["odds_draw"]),
            "odds_away": float(row["odds_away"]),
            "home_rating": home_rating,
            "away_rating": away_rating,
            "rating_diff": home_rating - away_rating,
            "rating_gap_abs": abs(home_rating - away_rating),
            "league_strength": float(row.get("league_strength", DEFAULT_LEAGUE_STRENGTH)),
            "match_minutes": _parse_match_minutes(str(row["match_time"])),
            "is_weekend": _is_weekend(str(row["match_date"])),
        }
        feature_map.update(
            build_market_intent_feature_map(
                odds_home=row["odds_home"],
                odds_draw=row["odds_draw"],
                odds_away=row["odds_away"],
                opening_odds_home=row.get("opening_odds_home", 0.0),
                opening_odds_draw=row.get("opening_odds_draw", 0.0),
                opening_odds_away=row.get("opening_odds_away", 0.0),
                return_rate=row.get("return_rate", 0.0),
                kelly_home=row.get("kelly_home", 0.0),
                kelly_draw=row.get("kelly_draw", 0.0),
                kelly_away=row.get("kelly_away", 0.0),
            )
        )
        feature_map.update(recent_form)
        label = _result_to_label(int(row["home_goals"]), int(row["away_goals"]))
        label_counts[label] += 1
        date_values.append(str(row["match_date"]))
        samples.append(
            {
                "timestamp": f"{row['match_date']} {row['match_time']}",
                "match_id": match_id,
                "features": {
                    key: float(feature_map.get(key, 0.0))
                    for key in XGBoostProbabilityModel.FEATURE_ORDER
                },
                "label": label,
                "meta": {
                    "source": _normalize_text(row.get("source")) or "historical_import",
                    "match_date": row["match_date"],
                    "match_time": row["match_time"],
                    "league": row["league"],
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                    "home_goals": row["home_goals"],
                    "away_goals": row["away_goals"],
                    "home_ht_goals": row.get("home_ht_goals"),
                    "away_ht_goals": row.get("away_ht_goals"),
                    "handicap_line": row.get("handicap_line", 0.0),
                    "opening_odds_home": row.get("opening_odds_home", 0.0),
                    "opening_odds_draw": row.get("opening_odds_draw", 0.0),
                    "opening_odds_away": row.get("opening_odds_away", 0.0),
                    "return_rate": row.get("return_rate", 0.0),
                    "kelly_home": row.get("kelly_home", 0.0),
                    "kelly_draw": row.get("kelly_draw", 0.0),
                    "kelly_away": row.get("kelly_away", 0.0),
                },
            }
        )

        update = elo_engine.update_from_result(
            home_rating=home_rating,
            away_rating=away_rating,
            home_goals=int(row["home_goals"]),
            away_goals=int(row["away_goals"]),
            league_strength=float(row.get("league_strength", DEFAULT_LEAGUE_STRENGTH)),
        )
        ratings_map[str(row["home_team"])] = float(update.home_after)
        ratings_map[str(row["away_team"])] = float(update.away_after)
        _append_team_history(
            team_histories,
            str(row["home_team"]),
            str(row["match_date"]),
            str(row["match_time"]),
            match_id,
            int(row["home_goals"]),
            int(row["away_goals"]),
        )
        _append_team_history(
            team_histories,
            str(row["away_team"]),
            str(row["match_date"]),
            str(row["match_time"]),
            match_id,
            int(row["away_goals"]),
            int(row["home_goals"]),
        )

    summary = {
        "raw_count": len(records),
        "valid_rows": len(normalized_rows),
        "imported_samples": len(samples),
        "skipped_invalid": skipped_invalid,
        "skipped_duplicate": skipped_duplicate,
        "label_counts": label_counts,
        "feature_order": list(XGBoostProbabilityModel.FEATURE_ORDER),
        "date_range": {
            "start": min(date_values) if date_values else None,
            "end": max(date_values) if date_values else None,
        },
        "final_ratings_count": len(ratings_map),
    }
    return samples, ratings_map, summary


def import_historical_xgb_samples(
    project_dir: Path,
    input_path: Path,
    replace: bool = False,
    sync_ratings: bool = False,
    sample_limit: int | None = None,
) -> dict[str, Any]:
    input_path = input_path.resolve()
    records = _read_input_records(input_path)
    samples, ratings_map, summary = build_xgb_samples_from_historical_records(records)

    store = StateStore(project_dir, xgb_sample_limit=sample_limit)
    existing = [] if replace else store.load_xgb_samples()
    merged: dict[str, dict] = {}
    for item in existing:
        if not isinstance(item, dict):
            continue
        match_id = _normalize_text(item.get("match_id"))
        if not match_id:
            continue
        merged[match_id] = item
    existing_count = len(merged)
    for item in samples:
        match_id = str(item.get("match_id", ""))
        if match_id:
            merged[match_id] = item

    merged_items = list(merged.values())
    store.save_xgb_samples(merged_items)
    storage_limit = int(getattr(store, "xgb_sample_limit", len(merged_items)) or len(merged_items))
    saved_total = min(len(merged_items), storage_limit)
    if sync_ratings:
        store.save_ratings(ratings_map)

    return {
        "input_path": str(input_path),
        "replace": bool(replace),
        "sync_ratings": bool(sync_ratings),
        "sample_limit_override": sample_limit,
        "existing_samples_before": 0 if replace else existing_count,
        "imported_samples": summary["imported_samples"],
        "merged_total": len(merged_items),
        "saved_total": saved_total,
        "storage_limit": storage_limit,
        "dropped_by_limit": max(0, len(merged_items) - saved_total),
        "skipped_invalid": summary["skipped_invalid"],
        "skipped_duplicate": summary["skipped_duplicate"],
        "label_counts": summary["label_counts"],
        "date_range": summary["date_range"],
        "feature_order": summary["feature_order"],
        "final_ratings_count": summary["final_ratings_count"],
    }
