from __future__ import annotations

from math import log2


OUTCOMES = ("home", "draw", "away")


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _normalize(probabilities: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, _safe_float(probabilities.get(key), default=0.0)) for key in OUTCOMES)
    if total <= 0.0:
        return {"home": 1.0 / 3.0, "draw": 1.0 / 3.0, "away": 1.0 / 3.0}
    return {
        key: max(0.0, _safe_float(probabilities.get(key), default=0.0)) / total
        for key in OUTCOMES
    }


def _normalized_entropy(probabilities: dict[str, float]) -> float:
    entropy = 0.0
    for key in OUTCOMES:
        prob = max(_safe_float(probabilities.get(key), default=0.0), 1e-12)
        entropy -= prob * log2(prob)
    return _clamp(entropy / log2(3.0), 0.0, 1.0)


def _apply_min_probability(probabilities: dict[str, float], floor: float) -> dict[str, float]:
    floor_value = _clamp(_safe_float(floor, default=0.0), 0.0, 0.32)
    if floor_value <= 0.0:
        return _normalize(probabilities)
    if floor_value * 3.0 >= 1.0:
        return {"home": 1.0 / 3.0, "draw": 1.0 / 3.0, "away": 1.0 / 3.0}
    normalized = _normalize(probabilities)
    remaining_mass = 1.0 - floor_value * 3.0
    residual = {
        key: max(0.0, _safe_float(normalized.get(key), default=0.0) - floor_value)
        for key in OUTCOMES
    }
    residual_total = sum(residual.values())
    if residual_total <= 0.0:
        equal_extra = remaining_mass / 3.0
        return {key: floor_value + equal_extra for key in OUTCOMES}
    return {
        key: floor_value + remaining_mass * residual[key] / residual_total
        for key in OUTCOMES
    }


def calibrate_three_way_probabilities(
    model_probabilities: dict[str, float],
    market_probabilities: dict[str, float] | None = None,
    config: dict | None = None,
) -> tuple[dict[str, float], dict]:
    cfg = dict(config or {})
    enabled = bool(cfg.get("enabled", True))
    prior_source_requested = str(cfg.get("prior_source", "market")).strip() or "market"
    prior_strength = max(1.0, _safe_float(cfg.get("prior_strength"), default=24.0))
    model_strength = max(1.0, _safe_float(cfg.get("model_strength"), default=56.0))
    uncertainty_gain = _clamp(_safe_float(cfg.get("uncertainty_gain"), default=0.55), 0.0, 2.0)
    draw_bias_scale = _clamp(_safe_float(cfg.get("draw_bias_scale"), default=0.18), 0.0, 2.0)
    min_probability = _clamp(_safe_float(cfg.get("min_probability"), default=0.02), 0.0, 0.32)

    model_probs = _normalize(model_probabilities if isinstance(model_probabilities, dict) else {})
    if not enabled:
        return _apply_min_probability(model_probs, min_probability), {
            "enabled": False,
            "reason": "disabled",
            "prior_source_requested": prior_source_requested,
            "prior_source_used": "none",
        }

    market_probs = _normalize(market_probabilities if isinstance(market_probabilities, dict) else {})
    if prior_source_requested == "market" and isinstance(market_probabilities, dict):
        prior_probs = market_probs
        prior_source_used = "market"
    else:
        prior_probs = {"home": 1.0 / 3.0, "draw": 1.0 / 3.0, "away": 1.0 / 3.0}
        prior_source_used = "uniform"

    uncertainty = _normalized_entropy(model_probs)
    prior_strength_effective = prior_strength * (1.0 + uncertainty_gain * uncertainty)
    draw_delta = max(0.0, _safe_float(prior_probs.get("draw"), default=0.0) - _safe_float(model_probs.get("draw"), default=0.0))
    draw_bias_term = draw_bias_scale * draw_delta * prior_strength_effective

    pseudo_counts = {
        "home": prior_strength_effective * _safe_float(prior_probs.get("home"), default=0.0)
        + model_strength * _safe_float(model_probs.get("home"), default=0.0),
        "draw": prior_strength_effective * _safe_float(prior_probs.get("draw"), default=0.0)
        + model_strength * _safe_float(model_probs.get("draw"), default=0.0)
        + draw_bias_term,
        "away": prior_strength_effective * _safe_float(prior_probs.get("away"), default=0.0)
        + model_strength * _safe_float(model_probs.get("away"), default=0.0),
    }
    calibrated = _apply_min_probability(_normalize(pseudo_counts), min_probability)
    metadata = {
        "enabled": True,
        "prior_source_requested": prior_source_requested,
        "prior_source_used": prior_source_used,
        "prior_strength_effective": round(prior_strength_effective, 4),
        "model_strength": round(model_strength, 4),
        "uncertainty": round(uncertainty, 4),
        "draw_bias_term": round(draw_bias_term, 6),
        "min_probability": round(min_probability, 4),
    }
    return calibrated, metadata
