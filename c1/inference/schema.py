from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from c1.core.schema import FeatureSnapshot


@dataclass(slots=True)
class InferenceInput:
    match_id: str
    odds_home: float
    odds_draw: float
    odds_away: float
    home_rating: float
    away_rating: float
    league_strength: float = 0.92
    feature_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InferenceComponent:
    name: str
    probabilities: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InferenceResult:
    match_id: str
    model_name: str
    raw_probabilities: dict[str, float]
    predicted_side: str
    confidence: float
    margin: float
    entropy: float
    ev_by_side: dict[str, float]
    components: list[InferenceComponent]
    calibration: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def build_inference_input(
    *,
    match_id: str,
    feature_snapshot: FeatureSnapshot,
    metadata: dict[str, Any] | None = None,
) -> InferenceInput:
    fields = dict(feature_snapshot.fields)
    return InferenceInput(
        match_id=match_id,
        odds_home=_safe_float(fields.get("odds_home"), default=_safe_float(fields.get("current_odds_home"), default=2.2)),
        odds_draw=_safe_float(fields.get("odds_draw"), default=_safe_float(fields.get("current_odds_draw"), default=3.2)),
        odds_away=_safe_float(fields.get("odds_away"), default=_safe_float(fields.get("current_odds_away"), default=3.1)),
        home_rating=_safe_float(fields.get("home_rating"), default=1500.0),
        away_rating=_safe_float(fields.get("away_rating"), default=1500.0),
        league_strength=_safe_float(fields.get("league_strength"), default=0.92),
        feature_fields=fields,
        metadata=metadata or {},
    )

