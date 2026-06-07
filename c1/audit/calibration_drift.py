from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Mapping

SIDES = ("home", "draw", "away")
DEFAULT_BUCKETS = (0.0, 0.38, 0.42, 0.46, 0.50, 0.55, 0.60, 0.65, 1.01)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def normalize_probabilities(probabilities: Mapping[str, Any] | None) -> dict[str, float] | None:
    if not isinstance(probabilities, Mapping):
        return None
    values = {side: max(_safe_float(probabilities.get(side), 0.0), 0.0) for side in SIDES}
    total = sum(values.values())
    if total <= 0.0:
        return None
    return {side: values[side] / total for side in SIDES}


def _bucket_label(value: float, edges: Iterable[float]) -> str:
    ordered = list(edges)
    for lower, upper in zip(ordered, ordered[1:]):
        if lower <= value < upper:
            if upper >= 1.0:
                return f">={lower:.2f}"
            return f"{lower:.2f}-{upper:.2f}"
    return "unknown"


def _logloss(probability: float) -> float:
    return -math.log(max(min(probability, 1.0 - 1e-15), 1e-15))


def _brier(probabilities: Mapping[str, float], actual: str) -> float:
    return sum((float(probabilities[side]) - (1.0 if side == actual else 0.0)) ** 2 for side in SIDES) / 3.0


def _side_from_probabilities(probabilities: Mapping[str, float]) -> str:
    return max(SIDES, key=lambda side: float(probabilities.get(side, 0.0)))


def _empty_model_report(model_name: str) -> dict[str, Any]:
    return {
        "model": model_name,
        "count": 0,
        "accuracy": None,
        "avg_confidence": None,
        "avg_actual_rate": None,
        "calibration_gap": None,
        "ece": None,
        "brier": None,
        "logloss": None,
        "buckets": {},
    }


def build_model_calibration_report(
    rows: Iterable[Mapping[str, Any]],
    *,
    model_name: str,
    probability_key: str,
    confidence_key: str | None = None,
    bucket_edges: Iterable[float] = DEFAULT_BUCKETS,
) -> dict[str, Any]:
    usable = []
    for row in rows:
        actual = str(row.get("actual") or "").strip()
        if actual not in SIDES:
            continue
        probabilities = normalize_probabilities(row.get(probability_key))
        if probabilities is None:
            continue
        predicted = str(row.get(f"{model_name}_side") or "").strip()
        if predicted not in SIDES:
            predicted = _side_from_probabilities(probabilities)
        confidence = _safe_float(row.get(confidence_key), 0.0) if confidence_key else _safe_float(probabilities[predicted], 0.0)
        if confidence <= 0.0 or confidence > 1.0:
            confidence = _safe_float(probabilities[predicted], 0.0)
        usable.append(
            {
                "actual": actual,
                "predicted": predicted,
                "confidence": max(min(confidence, 1.0), 0.0),
                "prob_true": _safe_float(probabilities.get(actual), 0.0),
                "correct": predicted == actual,
                "brier": _brier(probabilities, actual),
                "logloss": _logloss(_safe_float(probabilities.get(actual), 0.0)),
            }
        )

    if not usable:
        return _empty_model_report(model_name)

    bucket_stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {"n": 0.0, "confidence_sum": 0.0, "hit_sum": 0.0, "brier_sum": 0.0, "logloss_sum": 0.0}
    )
    for item in usable:
        label = _bucket_label(item["confidence"], bucket_edges)
        bucket = bucket_stats[label]
        bucket["n"] += 1.0
        bucket["confidence_sum"] += item["confidence"]
        bucket["hit_sum"] += 1.0 if item["correct"] else 0.0
        bucket["brier_sum"] += item["brier"]
        bucket["logloss_sum"] += item["logloss"]

    count = len(usable)
    buckets: dict[str, dict[str, Any]] = {}
    ece = 0.0
    for label, stat in sorted(bucket_stats.items()):
        n = int(stat["n"])
        avg_confidence = stat["confidence_sum"] / max(stat["n"], 1.0)
        actual_rate = stat["hit_sum"] / max(stat["n"], 1.0)
        gap = actual_rate - avg_confidence
        ece += (n / count) * abs(gap)
        buckets[label] = {
            "n": n,
            "avg_confidence": round(avg_confidence, 6),
            "actual_rate": round(actual_rate, 6),
            "gap": round(gap, 6),
            "brier": round(stat["brier_sum"] / max(stat["n"], 1.0), 6),
            "logloss": round(stat["logloss_sum"] / max(stat["n"], 1.0), 6),
        }

    accuracy = sum(1 for item in usable if item["correct"]) / count
    avg_confidence = sum(item["confidence"] for item in usable) / count
    return {
        "model": model_name,
        "count": count,
        "accuracy": round(accuracy, 6),
        "avg_confidence": round(avg_confidence, 6),
        "avg_actual_rate": round(accuracy, 6),
        "calibration_gap": round(accuracy - avg_confidence, 6),
        "ece": round(ece, 6),
        "brier": round(sum(item["brier"] for item in usable) / count, 6),
        "logloss": round(sum(item["logloss"] for item in usable) / count, 6),
        "buckets": buckets,
    }


def build_calibration_drift_report(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    materialized = list(rows)
    v24 = build_model_calibration_report(
        materialized,
        model_name="v24",
        probability_key="v24_probabilities",
        confidence_key="v24_confidence",
    )
    c1 = build_model_calibration_report(
        materialized,
        model_name="c1",
        probability_key="c1_probabilities",
        confidence_key="c1_confidence",
    )
    comparison: dict[str, Any] = {}
    if v24["count"] and c1["count"]:
        comparison = {
            "count_delta": int(c1["count"]) - int(v24["count"]),
            "accuracy_delta": round(float(c1["accuracy"]) - float(v24["accuracy"]), 6),
            "ece_delta": round(float(c1["ece"]) - float(v24["ece"]), 6),
            "brier_delta": round(float(c1["brier"]) - float(v24["brier"]), 6),
            "logloss_delta": round(float(c1["logloss"]) - float(v24["logloss"]), 6),
            "calibration_gap_delta": round(float(c1["calibration_gap"]) - float(v24["calibration_gap"]), 6),
        }
    return {
        "version": "calibration_drift.v1",
        "row_count": len(materialized),
        "models": {
            "v24": v24,
            "c1": c1,
        },
        "comparison": comparison,
    }
