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
) -> dict[str, Any]:
    input_path = input_path.resolve()
    records = _read_input_records(input_path)
    samples, ratings_map, summary = build_xgb_samples_from_historical_records(records)

    store = StateStore(project_dir)
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
