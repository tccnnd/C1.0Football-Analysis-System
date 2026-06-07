from __future__ import annotations

import math
import random
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except Exception:
        return default


def sample_to_vector(sample: Mapping[str, Any], feature_order: Sequence[str]) -> list[float] | None:
    features = sample.get("features")
    if not isinstance(features, Mapping):
        return None
    return [_safe_float(features.get(name), 0.0) for name in feature_order]


def samples_to_xy(samples: Iterable[Mapping[str, Any]], feature_order: Sequence[str]) -> tuple[list[list[float]], list[int]]:
    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    for sample in samples:
        if not isinstance(sample, Mapping):
            continue
        label = _safe_int(sample.get("label"), -1)
        if label not in (0, 1, 2):
            continue
        vector = sample_to_vector(sample, feature_order)
        if vector is None:
            continue
        x_rows.append(vector)
        y_rows.append(label)
    return x_rows, y_rows


def feature_quality_report(samples: Iterable[Mapping[str, Any]], feature_order: Sequence[str]) -> dict[str, Any]:
    values: dict[str, list[float]] = {name: [] for name in feature_order}
    total = 0
    for sample in samples:
        if not isinstance(sample, Mapping):
            continue
        features = sample.get("features")
        if not isinstance(features, Mapping):
            continue
        total += 1
        for name in feature_order:
            values[name].append(_safe_float(features.get(name), 0.0))

    features_report: dict[str, dict[str, Any]] = {}
    for name in feature_order:
        column = values[name]
        n = len(column)
        zero_count = sum(1 for item in column if abs(item) <= 1e-12)
        unique_count = len({round(item, 8) for item in column})
        features_report[name] = {
            "n": n,
            "zero_rate": round(zero_count / max(n, 1), 6),
            "unique_count": unique_count,
            "mean": round(mean(column), 6) if column else None,
            "std": round(pstdev(column), 6) if len(column) > 1 else 0.0,
        }
    return {
        "sample_count": total,
        "features": features_report,
    }


def multiclass_logloss(probabilities: Sequence[Sequence[float]], labels: Sequence[int]) -> float:
    if probabilities is None or labels is None or len(probabilities) == 0 or len(labels) == 0:
        return 0.0
    total = 0.0
    count = 0
    for probs, label in zip(probabilities, labels):
        if label not in (0, 1, 2) or len(probs) < 3:
            continue
        prob = max(min(float(probs[label]), 1.0 - 1e-15), 1e-15)
        total += -math.log(prob)
        count += 1
    return total / max(count, 1)


def multiclass_accuracy(probabilities: Sequence[Sequence[float]], labels: Sequence[int]) -> float:
    if probabilities is None or labels is None or len(probabilities) == 0 or len(labels) == 0:
        return 0.0
    hits = 0
    count = 0
    for probs, label in zip(probabilities, labels):
        if label not in (0, 1, 2) or len(probs) < 3:
            continue
        predicted = max(range(3), key=lambda idx: float(probs[idx]))
        hits += 1 if predicted == label else 0
        count += 1
    return hits / max(count, 1)


def built_in_importance_from_booster(booster: Any, feature_order: Sequence[str]) -> dict[str, dict[str, float]]:
    """Return XGBoost built-in importance mapped from fN keys to feature names."""
    importance_types = ("weight", "gain", "cover")
    result = {name: {kind: 0.0 for kind in importance_types} for name in feature_order}
    for kind in importance_types:
        try:
            scores = booster.get_score(importance_type=kind)
        except Exception:
            scores = {}
        if not isinstance(scores, Mapping):
            continue
        for raw_key, value in scores.items():
            key = str(raw_key)
            if key.startswith("f") and key[1:].isdigit():
                idx = int(key[1:])
                if 0 <= idx < len(feature_order):
                    result[feature_order[idx]][kind] = round(_safe_float(value), 6)
            elif key in result:
                result[key][kind] = round(_safe_float(value), 6)
    return result


def permutation_importance(
    *,
    model: Any,
    x_rows: Sequence[Sequence[float]],
    labels: Sequence[int],
    feature_order: Sequence[str],
    repeats: int = 1,
    seed: int = 42,
) -> dict[str, Any]:
    if not x_rows or not labels:
        return {"baseline": {}, "features": {}}
    try:
        import numpy as np
    except Exception:
        return {"baseline": {"reason": "numpy_missing"}, "features": {}}

    x_matrix = np.array(x_rows, dtype=float)
    y_vector = list(labels)
    baseline_probs = model.predict_proba(x_matrix)
    baseline_logloss = multiclass_logloss(baseline_probs, y_vector)
    baseline_accuracy = multiclass_accuracy(baseline_probs, y_vector)
    rng = random.Random(seed)
    features: dict[str, dict[str, float]] = {}

    for idx, name in enumerate(feature_order):
        logloss_deltas: list[float] = []
        accuracy_deltas: list[float] = []
        original_column = [float(row[idx]) for row in x_matrix.tolist()]
        for _ in range(max(int(repeats), 1)):
            shuffled = list(original_column)
            rng.shuffle(shuffled)
            permuted = x_matrix.copy()
            permuted[:, idx] = shuffled
            probs = model.predict_proba(permuted)
            logloss_deltas.append(multiclass_logloss(probs, y_vector) - baseline_logloss)
            accuracy_deltas.append(multiclass_accuracy(probs, y_vector) - baseline_accuracy)
        features[name] = {
            "logloss_delta": round(mean(logloss_deltas), 6),
            "accuracy_delta": round(mean(accuracy_deltas), 6),
        }

    return {
        "baseline": {
            "sample_count": len(y_vector),
            "logloss": round(baseline_logloss, 6),
            "accuracy": round(baseline_accuracy, 6),
        },
        "features": features,
    }


def rank_feature_report(
    *,
    feature_order: Sequence[str],
    built_in: Mapping[str, Mapping[str, Any]] | None = None,
    permutation: Mapping[str, Any] | None = None,
    quality: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    perm_features = (permutation or {}).get("features", {}) if isinstance(permutation, Mapping) else {}
    quality_features = (quality or {}).get("features", {}) if isinstance(quality, Mapping) else {}
    rows: list[dict[str, Any]] = []
    for name in feature_order:
        built = built_in.get(name, {}) if isinstance(built_in, Mapping) else {}
        perm = perm_features.get(name, {}) if isinstance(perm_features, Mapping) else {}
        q = quality_features.get(name, {}) if isinstance(quality_features, Mapping) else {}
        score = (
            max(_safe_float(perm.get("logloss_delta")), 0.0) * 10.0
            + max(_safe_float(built.get("gain")), 0.0)
            + max(_safe_float(built.get("weight")), 0.0) * 0.001
        )
        rows.append(
            {
                "feature": name,
                "score": round(score, 6),
                "gain": _safe_float(built.get("gain")),
                "weight": _safe_float(built.get("weight")),
                "cover": _safe_float(built.get("cover")),
                "permutation_logloss_delta": perm.get("logloss_delta"),
                "permutation_accuracy_delta": perm.get("accuracy_delta"),
                "zero_rate": q.get("zero_rate"),
                "unique_count": q.get("unique_count"),
                "std": q.get("std"),
            }
        )
    return sorted(rows, key=lambda item: (float(item["score"]), str(item["feature"])))
