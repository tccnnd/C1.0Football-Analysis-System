from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .availability import build_match_context
from .contracts import CanonicalMatch, MatchContext, OddsSnapshot, TeamAvailability


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _merge_sources(primary: Any, extra_fields: Mapping[str, Any] | None) -> Any:
    if not extra_fields:
        return primary
    merged: dict[str, Any] = {}
    if isinstance(primary, Mapping):
        merged.update(primary)
    else:
        for key in dir(primary):
            if key.startswith("_"):
                continue
            try:
                value = getattr(primary, key)
            except Exception:
                continue
            if callable(value):
                continue
            merged[key] = value
    merged.update(dict(extra_fields))
    return merged


def _normalize_side_from_odds(odds_home: float, odds_draw: float, odds_away: float) -> str:
    odds_map = {
        "home": odds_home if odds_home > 1.0 else 999.0,
        "draw": odds_draw if odds_draw > 1.0 else 999.0,
        "away": odds_away if odds_away > 1.0 else 999.0,
    }
    return min(odds_map.items(), key=lambda item: item[1])[0]


def _context_completeness(home_team: str, away_team: str, league: str, match_date: str, match_time: str) -> float:
    required = [home_team, away_team, league, match_date, match_time]
    present = sum(1 for item in required if item)
    return round(present / len(required), 4)


def _odds_snapshot_quality(odds_home: float, odds_draw: float, odds_away: float) -> float:
    valid = sum(1 for item in (odds_home, odds_draw, odds_away) if item > 1.0)
    return round(valid / 3.0, 4)


def _source_reliability(source: str) -> float:
    text = source.lower()
    if "titan" in text:
        return 0.86
    if "500" in text:
        return 0.80
    if "cache" in text:
        return 0.72
    return 0.68


def _league_strength(league: str) -> float:
    text = _text(league).lower()
    if any(token in text for token in ("英超", "西甲", "德甲", "意甲", "法甲", "premier", "laliga", "bundesliga", "serie a", "ligue 1")):
        return 0.98
    if any(token in text for token in ("欧冠", "欧联", "champions", "uefa")):
        return 1.0
    if any(token in text for token in ("中超", "日职", "j联赛", "mls", "美职")):
        return 0.9
    return 0.92


def _build_match_id(match_date: str, league: str, home_team: str, away_team: str) -> str:
    return f"{match_date}|{league}|{home_team}|{away_team}"


@dataclass(slots=True)
class LegacyMatchAdapterOutput:
    match_id: str
    raw_fields: dict[str, Any]
    source: str = "legacy"
    canonical_match: CanonicalMatch | None = None
    odds_snapshot: OddsSnapshot | None = None
    match_context: MatchContext | None = None
    home_availability: TeamAvailability | None = None
    away_availability: TeamAvailability | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def adapt_legacy_match(match: Any, extra_fields: Mapping[str, Any] | None = None) -> LegacyMatchAdapterOutput:
    source_payload = _merge_sources(match, extra_fields)
    home_team = _text(_get_value(source_payload, "home_team"))
    away_team = _text(_get_value(source_payload, "away_team"))
    league = _text(_get_value(source_payload, "league"))
    match_date = _text(_get_value(source_payload, "match_date"))
    match_time = _text(_get_value(source_payload, "match_time")) or "00:00"
    source = _text(_get_value(source_payload, "source", "legacy")) or "legacy"
    source_id = _text(_get_value(source_payload, "source_id"))

    odds_home = _safe_float(_get_value(source_payload, "odds_home"), 0.0)
    odds_draw = _safe_float(_get_value(source_payload, "odds_draw"), 0.0)
    odds_away = _safe_float(_get_value(source_payload, "odds_away"), 0.0)
    handicap_line = _safe_float(_get_value(source_payload, "handicap_line"), 0.0)

    opening_odds_home = _safe_float(_get_value(source_payload, "opening_odds_home"), odds_home)
    opening_odds_draw = _safe_float(_get_value(source_payload, "opening_odds_draw"), odds_draw)
    opening_odds_away = _safe_float(_get_value(source_payload, "opening_odds_away"), odds_away)
    return_rate = _safe_float(_get_value(source_payload, "return_rate"), 0.0)
    kelly_home = _safe_float(_get_value(source_payload, "kelly_home"), 0.0)
    kelly_draw = _safe_float(_get_value(source_payload, "kelly_draw"), 0.0)
    kelly_away = _safe_float(_get_value(source_payload, "kelly_away"), 0.0)

    market_side = _normalize_side_from_odds(odds_home, odds_draw, odds_away)
    match_id = _text(_get_value(source_payload, "match_id")) or _build_match_id(match_date, league, home_team, away_team)
    match_context, home_availability, away_availability = build_match_context(
        source_payload,
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
    )
    raw_fields = {
        "home_team": home_team,
        "away_team": away_team,
        "league": league,
        "match_date": match_date,
        "match_time": match_time,
        "odds_home": odds_home,
        "odds_draw": odds_draw,
        "odds_away": odds_away,
        "current_odds_home": odds_home,
        "current_odds_draw": odds_draw,
        "current_odds_away": odds_away,
        "opening_odds_home": opening_odds_home,
        "opening_odds_draw": opening_odds_draw,
        "opening_odds_away": opening_odds_away,
        "handicap_line": handicap_line,
        "current_handicap_line": handicap_line,
        "opening_handicap_line": handicap_line,
        "goal": handicap_line,
        "return_rate": return_rate,
        "kelly_home": kelly_home,
        "kelly_draw": kelly_draw,
        "kelly_away": kelly_away,
        "source": source,
        "source_id": source_id,
        "league_strength": _league_strength(league),
        "home_rating": _safe_float(_get_value(source_payload, "home_rating"), 1500.0),
        "away_rating": _safe_float(_get_value(source_payload, "away_rating"), 1500.0),
        "context_completeness": _context_completeness(home_team, away_team, league, match_date, match_time),
        "odds_snapshot_quality": _odds_snapshot_quality(odds_home, odds_draw, odds_away),
        "team_availability_quality": match_context.team_availability_quality,
        "source_reliability": _source_reliability(source),
        "data_freshness_hours": 1.0,
        "lineup_known": match_context.lineup_known,
        "lineup_updated_at": match_context.lineup_updated_at,
        "lineup_freshness_hours": match_context.lineup_freshness_hours,
        "market_side": market_side,
        "market_divergence": 0.0,
        "injury_conflict_score": match_context.injury_conflict_score,
        "schedule_pressure": match_context.schedule_pressure,
        "weather_risk": match_context.weather_risk,
        "environment_safe": match_context.environment_safe,
        "home_absent_count": home_availability.absences,
        "away_absent_count": away_availability.absences,
        "home_key_absent_count": home_availability.key_absences,
        "away_key_absent_count": away_availability.key_absences,
        "home_availability_score": home_availability.availability_score,
        "away_availability_score": away_availability.availability_score,
    }
    canonical_match = CanonicalMatch(
        match_id=match_id,
        source=source,
        source_id=source_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        match_date=match_date,
        match_time=match_time,
    )
    odds_snapshot = OddsSnapshot(
        match_id=match_id,
        source=source,
        recorded_at=None,
        odds_home=odds_home,
        odds_draw=odds_draw,
        odds_away=odds_away,
        opening_odds_home=opening_odds_home,
        opening_odds_draw=opening_odds_draw,
        opening_odds_away=opening_odds_away,
        handicap_line=handicap_line,
        total_goals_line=_safe_float(_get_value(source_payload, "total_goals_line"), 2.5),
        return_rate=return_rate,
        kelly_home=kelly_home,
        kelly_draw=kelly_draw,
        kelly_away=kelly_away,
        metadata={"source_id": source_id},
    )
    return LegacyMatchAdapterOutput(
        match_id=match_id,
        raw_fields=raw_fields,
        source=source,
        canonical_match=canonical_match,
        odds_snapshot=odds_snapshot,
        match_context=match_context,
        home_availability=home_availability,
        away_availability=away_availability,
        metadata={
            "source_id": source_id,
            "adapter": "c1.data.legacy_match",
        },
    )


def adapt_legacy_matches(matches: list[Any], extra_fields_by_match_id: Mapping[str, Mapping[str, Any]] | None = None) -> list[LegacyMatchAdapterOutput]:
    outputs: list[LegacyMatchAdapterOutput] = []
    for item in matches:
        match_id = _text(_get_value(item, "match_id")) or _build_match_id(
            _text(_get_value(item, "match_date")),
            _text(_get_value(item, "league")),
            _text(_get_value(item, "home_team")),
            _text(_get_value(item, "away_team")),
        )
        extra_fields = dict((extra_fields_by_match_id or {}).get(match_id, {}))
        outputs.append(adapt_legacy_match(item, extra_fields=extra_fields))
    return outputs
