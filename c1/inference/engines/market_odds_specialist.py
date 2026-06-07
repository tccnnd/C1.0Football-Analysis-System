from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from c1.inference.schema import InferenceInput

SIDES = ("home", "draw", "away")
MARKET_IMPLIED_FEATURES = (
    "market_home",
    "market_draw",
    "market_away",
    "odds_home",
    "odds_draw",
    "odds_away",
)


@dataclass(slots=True)
class MarketOddsSpecialistResult:
    probabilities: dict[str, float]
    predicted_side: str
    confidence: float
    margin: float
    entropy: float
    disagreement: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _normalize(values: Mapping[str, float]) -> dict[str, float] | None:
    cleaned = {side: max(_safe_float(values.get(side), 0.0), 0.0) for side in SIDES}
    total = sum(cleaned.values())
    if total <= 0.0:
        return None
    return {side: cleaned[side] / total for side in SIDES}


def _probabilities_from_odds(odds_home: float, odds_draw: float, odds_away: float) -> dict[str, float] | None:
    odds = {
        "home": max(_safe_float(odds_home), 1.01),
        "draw": max(_safe_float(odds_draw), 1.01),
        "away": max(_safe_float(odds_away), 1.01),
    }
    implied = {side: 1.0 / value for side, value in odds.items()}
    return _normalize(implied)


def _entropy(probabilities: Mapping[str, float]) -> float:
    total = 0.0
    for side in SIDES:
        value = max(float(probabilities.get(side, 0.0)), 1e-15)
        total += -value * math.log(value)
    return total / math.log(3.0)


def _margin(probabilities: Mapping[str, float]) -> float:
    ordered = sorted((float(probabilities.get(side, 0.0)) for side in SIDES), reverse=True)
    if len(ordered) < 2:
        return 0.0
    return ordered[0] - ordered[1]


def _disagreement(left: Mapping[str, float], right: Mapping[str, Any] | None) -> float | None:
    normalized_right = _normalize({side: _safe_float((right or {}).get(side), 0.0) for side in SIDES})
    if normalized_right is None:
        return None
    return sum(abs(float(left[side]) - float(normalized_right[side])) for side in SIDES) / 2.0


class MarketOddsSpecialist:
    """Market/odds-only sidecar specialist.

    This intentionally uses only the implied-market core features proven by the
    offline baseline. It is not a production selector; it emits calibrated
    governance signals that can later be shadow-tested before runtime wiring.
    """

    model_name = "market_odds_specialist.v1"

    def predict(
        self,
        inference_input: InferenceInput,
        *,
        reference_probabilities: Mapping[str, Any] | None = None,
    ) -> MarketOddsSpecialistResult:
        fields = inference_input.feature_fields or {}
        market_probabilities = _normalize(
            {
                "home": _safe_float(fields.get("market_home"), 0.0),
                "draw": _safe_float(fields.get("market_draw"), 0.0),
                "away": _safe_float(fields.get("market_away"), 0.0),
            }
        )
        source = "market_implied_features"
        probabilities = market_probabilities
        if probabilities is None:
            probabilities = _probabilities_from_odds(
                _safe_float(fields.get("odds_home"), inference_input.odds_home),
                _safe_float(fields.get("odds_draw"), inference_input.odds_draw),
                _safe_float(fields.get("odds_away"), inference_input.odds_away),
            )
            source = "odds_implied_fallback"
        if probabilities is None:
            probabilities = {"home": 1.0 / 3.0, "draw": 1.0 / 3.0, "away": 1.0 / 3.0}
            source = "uniform_fallback"

        predicted_side = max(SIDES, key=lambda side: probabilities[side])
        confidence = probabilities[predicted_side]
        entropy = _entropy(probabilities)
        margin = _margin(probabilities)
        disagreement = _disagreement(probabilities, reference_probabilities)
        return MarketOddsSpecialistResult(
            probabilities={side: round(probabilities[side], 6) for side in SIDES},
            predicted_side=predicted_side,
            confidence=round(confidence, 6),
            margin=round(margin, 6),
            entropy=round(entropy, 6),
            disagreement=round(disagreement, 6) if disagreement is not None else None,
            metadata={
                "model_name": self.model_name,
                "source": source,
                "feature_set": "market_implied_core",
                "feature_count": len(MARKET_IMPLIED_FEATURES),
            },
        )
