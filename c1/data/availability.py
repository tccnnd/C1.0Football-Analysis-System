from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .contracts import MatchContext, TeamAvailability


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def build_team_availability(source: Any, *, side: str, team_name: str = "") -> TeamAvailability:
    prefix = "home" if side == "home" else "away"
    known = _safe_bool(_get_value(source, f"{prefix}_availability_known"), default=_safe_bool(_get_value(source, "lineup_known"), default=False))
    updated_at = _text(_get_value(source, f"{prefix}_availability_updated_at")) or _text(_get_value(source, "lineup_updated_at")) or None
    freshness_hours = _safe_float(_get_value(source, f"{prefix}_availability_freshness_hours"), default=_safe_float(_get_value(source, "lineup_freshness_hours"), default=24.0))
    absences = int(_safe_float(_get_value(source, f"{prefix}_absent_count"), default=0.0))
    key_absences = int(_safe_float(_get_value(source, f"{prefix}_key_absent_count"), default=0.0))
    explicit_score = _get_value(source, f"{prefix}_availability_score")
    if explicit_score not in (None, ""):
        availability_score = _clip(_safe_float(explicit_score, default=0.0))
    else:
        base = 0.92 if known else 0.45
        absence_penalty = min(absences * 0.08, 0.32)
        key_penalty = min(key_absences * 0.14, 0.42)
        staleness_penalty = min(max(freshness_hours - 6.0, 0.0) * 0.02, 0.25)
        availability_score = _clip(base - absence_penalty - key_penalty - staleness_penalty)
    return TeamAvailability(
        team=team_name or _text(_get_value(source, f"{prefix}_team")),
        known=known,
        updated_at=updated_at,
        freshness_hours=round(freshness_hours, 4),
        absences=absences,
        key_absences=key_absences,
        availability_score=round(availability_score, 4),
        metadata={"side": prefix},
    )


def build_match_context(
    source: Any,
    *,
    match_id: str,
    home_team: str = "",
    away_team: str = "",
) -> tuple[MatchContext, TeamAvailability, TeamAvailability]:
    home = build_team_availability(source, side="home", team_name=home_team)
    away = build_team_availability(source, side="away", team_name=away_team)
    lineup_known = bool(home.known and away.known)
    freshness_hours = max(home.freshness_hours or 0.0, away.freshness_hours or 0.0)
    updated_at = home.updated_at or away.updated_at
    explicit_quality = _get_value(source, "team_availability_quality")
    if explicit_quality not in (None, ""):
        team_availability_quality = _clip(_safe_float(explicit_quality, default=0.0))
    else:
        team_availability_quality = _clip((home.availability_score + away.availability_score) / 2.0)

    explicit_injury_conflict = _get_value(source, "injury_conflict_score")
    if explicit_injury_conflict not in (None, ""):
        injury_conflict_score = _clip(_safe_float(explicit_injury_conflict, default=0.0))
    else:
        imbalance = abs(home.key_absences - away.key_absences) * 0.12 + abs(home.absences - away.absences) * 0.05
        injury_conflict_score = _clip(imbalance)

    context = MatchContext(
        match_id=match_id,
        lineup_known=lineup_known,
        lineup_updated_at=updated_at,
        lineup_freshness_hours=round(freshness_hours, 4),
        team_availability_quality=round(team_availability_quality, 4),
        injury_conflict_score=round(injury_conflict_score, 4),
        schedule_pressure=round(_clip(_safe_float(_get_value(source, "schedule_pressure"), default=0.0)), 4),
        weather_risk=round(_clip(_safe_float(_get_value(source, "weather_risk"), default=0.0)), 4),
        environment_safe=_safe_bool(_get_value(source, "environment_safe"), default=True),
        metadata={
            "home_availability": asdict(home),
            "away_availability": asdict(away),
        },
    )
    return context, home, away
