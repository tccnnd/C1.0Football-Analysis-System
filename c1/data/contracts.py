from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CanonicalMatch:
    match_id: str
    source: str
    source_id: str
    home_team: str
    away_team: str
    league: str
    match_date: str
    match_time: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OddsSnapshot:
    match_id: str
    source: str
    recorded_at: str | None
    odds_home: float
    odds_draw: float
    odds_away: float
    opening_odds_home: float = 0.0
    opening_odds_draw: float = 0.0
    opening_odds_away: float = 0.0
    handicap_line: float = 0.0
    total_goals_line: float = 2.5
    return_rate: float = 0.0
    kelly_home: float = 0.0
    kelly_draw: float = 0.0
    kelly_away: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TeamAvailability:
    team: str
    known: bool
    updated_at: str | None = None
    freshness_hours: float | None = None
    absences: int = 0
    key_absences: int = 0
    availability_score: float = 0.0
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MatchContext:
    match_id: str
    lineup_known: bool
    lineup_updated_at: str | None = None
    lineup_freshness_hours: float | None = None
    team_availability_quality: float = 0.0
    injury_conflict_score: float = 0.0
    schedule_pressure: float = 0.0
    weather_risk: float = 0.0
    environment_safe: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
