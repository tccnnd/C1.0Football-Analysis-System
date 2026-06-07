from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Sequence

from c1.audit.feature_importance import multiclass_accuracy, multiclass_logloss, samples_to_xy
from c1.inference.engines.xgboost_engine import FEATURE_ORDER
from xgb_feature_importance_report import _load_samples

PROJECT_ROOT = Path(__file__).resolve().parent

ABLATION_GROUPS: dict[str, list[str]] = {
    "kelly_features": ["kelly_home", "kelly_draw", "kelly_away", "kelly_draw_edge"],
    "match_time": ["match_minutes"],
    "recent_form_low_signal": [
        "home_recent_match_count",
        "home_recent_points_pg",
        "recent_points_diff",
        "home_recent_goal_diff_pg",
        "away_recent_goals_for_pg",
        "home_recent_goals_for_pg",
        "recent_goal_diff_diff",
    ],
    "market_low_signal": ["return_rate", "market_overround"],
    "stable_bottom_40": [
        "away_recent_goals_for_pg",
        "home_recent_goal_diff_pg",
        "home_recent_goals_for_pg",
        "home_recent_match_count",
        "home_recent_points_pg",
        "is_weekend",
        "kelly_away",
        "kelly_draw",
        "kelly_draw_edge",
        "kelly_home",
        "market_overround",
        "match_minutes",
        "recent_goal_diff_diff",
        "recent_points_diff",
        "return_rate",
    ],
}

WINDOWS = [
    ("2016-2018", "2016-01-01", "2018-01-01"),
    ("2018-2020", "2018-01-01", "2020-05-01"),
    ("all-sample", "", ""),
]

METRIC_KEYS = ("logloss", "accuracy", "brier", "ece", "calibration_gap")


def _load_xgb_estimator(*, seed: int = 42) -> Any:
    try:
        import xgboost as xgb
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("xgboost is required for ablation matrix") from exc
    return xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        n_estimators=160,
        max_depth=4,
        learning_rate=0.06,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="mlogloss",
        random_state=seed,
        tree_method="hist",
    )


def _select_features(feature_order: Sequence[str], excluded: set[str]) -> list[str]:
    return [name for name in feature_order if name not in excluded]


def _train_test_split(samples: list[dict[str, Any]], *, train_ratio: float, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)
    split_at = int(len(shuffled) * train_ratio)
    return shuffled[:split_at], shuffled[split_at:]


def _label_counts(labels: Sequence[int]) -> dict[str, int]:
    return {str(label): sum(1 for item in labels if item == label) for label in (0, 1, 2)}


def _multiclass_brier(probabilities: Sequence[Sequence[float]], labels: Sequence[int]) -> float:
    if probabilities is None or labels is None or len(probabilities) == 0 or len(labels) == 0:
        return 0.0
    total = 0.0
    count = 0
    for probs, label in zip(probabilities, labels):
        if label not in (0, 1, 2) or len(probs) < 3:
            continue
        total += sum((float(probs[idx]) - (1.0 if idx == label else 0.0)) ** 2 for idx in (0, 1, 2)) / 3.0
        count += 1
    return total / max(count, 1)


def _calibration_metrics(probabilities: Sequence[Sequence[float]], labels: Sequence[int]) -> dict[str, float]:
    if probabilities is None or labels is None or len(probabilities) == 0 or len(labels) == 0:
        return {"ece": 0.0, "calibration_gap": 0.0, "avg_confidence": 0.0}
    buckets = [(0.0, 0.38), (0.38, 0.42), (0.42, 0.46), (0.46, 0.50), (0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 1.01)]
    bucket_stats = [{"n": 0, "confidence": 0.0, "hits": 0.0} for _ in buckets]
    total_confidence = 0.0
    total_hits = 0.0
    count = 0
    for probs, label in zip(probabilities, labels):
        if label not in (0, 1, 2) or len(probs) < 3:
            continue
        predicted = max(range(3), key=lambda idx: float(probs[idx]))
        confidence = max(0.0, min(float(probs[predicted]), 1.0))
        hit = 1.0 if predicted == label else 0.0
        total_confidence += confidence
        total_hits += hit
        count += 1
        for idx, (lower, upper) in enumerate(buckets):
            if lower <= confidence < upper:
                bucket_stats[idx]["n"] += 1
                bucket_stats[idx]["confidence"] += confidence
                bucket_stats[idx]["hits"] += hit
                break
    ece = 0.0
    for stat in bucket_stats:
        if not stat["n"]:
            continue
        avg_confidence = stat["confidence"] / stat["n"]
        actual_rate = stat["hits"] / stat["n"]
        ece += (stat["n"] / max(count, 1)) * abs(actual_rate - avg_confidence)
    avg_confidence = total_confidence / max(count, 1)
    accuracy = total_hits / max(count, 1)
    return {
        "ece": ece,
        "calibration_gap": accuracy - avg_confidence,
        "avg_confidence": avg_confidence,
    }


def evaluate_feature_set(
    *,
    train_samples: list[dict[str, Any]],
    test_samples: list[dict[str, Any]],
    feature_order: Sequence[str],
    seed: int = 42,
) -> dict[str, Any]:
    x_train, y_train = samples_to_xy(train_samples, feature_order)
    x_test, y_test = samples_to_xy(test_samples, feature_order)
    if not x_train or not x_test:
        return {
            "trained": False,
            "reason": "empty_train_or_test",
            "train_count": len(x_train),
            "test_count": len(x_test),
        }
    if set(y_train) != {0, 1, 2}:
        return {
            "trained": False,
            "reason": "unbalanced_train_labels",
            "train_count": len(x_train),
            "test_count": len(x_test),
            "train_label_counts": _label_counts(y_train),
        }
    model = _load_xgb_estimator(seed=seed)
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)
    calibration = _calibration_metrics(probabilities, y_test)
    return {
        "trained": True,
        "train_count": len(x_train),
        "test_count": len(x_test),
        "feature_count": len(feature_order),
        "train_label_counts": _label_counts(y_train),
        "test_label_counts": _label_counts(y_test),
        "logloss": round(multiclass_logloss(probabilities, y_test), 6),
        "accuracy": round(multiclass_accuracy(probabilities, y_test), 6),
        "brier": round(_multiclass_brier(probabilities, y_test), 6),
        "ece": round(calibration["ece"], 6),
        "calibration_gap": round(calibration["calibration_gap"], 6),
        "avg_confidence": round(calibration["avg_confidence"], 6),
    }


def _aggregate_results(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    trained = [item for item in results if item.get("trained")]
    if not trained:
        return {
            "trained": False,
            "reason": "no_trained_seed_results",
            "seed_count": len(results),
            "trained_seed_count": 0,
        }
    aggregate: dict[str, Any] = {
        "trained": True,
        "seed_count": len(results),
        "trained_seed_count": len(trained),
        "feature_count": trained[0].get("feature_count"),
        "train_count_mean": round(mean(float(item.get("train_count", 0.0)) for item in trained), 3),
        "test_count_mean": round(mean(float(item.get("test_count", 0.0)) for item in trained), 3),
    }
    for key in METRIC_KEYS:
        values = [float(item[key]) for item in trained if item.get(key) is not None]
        if not values:
            continue
        aggregate[key] = round(mean(values), 6)
        aggregate[f"{key}_std"] = round(pstdev(values), 6) if len(values) > 1 else 0.0
    return aggregate


def _metric_deltas(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for key in METRIC_KEYS:
        if candidate.get(key) is None or baseline.get(key) is None:
            continue
        deltas[f"{key}_delta"] = round(float(candidate[key]) - float(baseline[key]), 6)
    return deltas


def build_ablation_matrix(
    *,
    samples_path: Path,
    limit: int,
    train_ratio: float,
    seed: int,
    seeds: Sequence[int] | None = None,
    windows: Sequence[tuple[str, str, str]] = WINDOWS,
    groups: dict[str, list[str]] = ABLATION_GROUPS,
) -> dict[str, Any]:
    seed_list = list(seeds) if seeds else [seed]
    cells: list[dict[str, Any]] = []
    for window_name, since, until in windows:
        samples = _load_samples(samples_path, limit=limit, since=since, until=until)
        for group_name, excluded_features in groups.items():
            excluded = set(excluded_features)
            feature_order = _select_features(FEATURE_ORDER, excluded)
            seed_results: list[dict[str, Any]] = []
            baseline_results: list[dict[str, Any]] = []
            ablated_results: list[dict[str, Any]] = []
            for current_seed in seed_list:
                train_samples, test_samples = _train_test_split(samples, train_ratio=train_ratio, seed=current_seed)
                baseline_result = evaluate_feature_set(
                    train_samples=train_samples,
                    test_samples=test_samples,
                    feature_order=FEATURE_ORDER,
                    seed=current_seed,
                )
                ablated_result = evaluate_feature_set(
                    train_samples=train_samples,
                    test_samples=test_samples,
                    feature_order=feature_order,
                    seed=current_seed,
                )
                if baseline_result.get("trained") and ablated_result.get("trained"):
                    ablated_result.update(_metric_deltas(ablated_result, baseline_result))
                baseline_results.append(baseline_result)
                ablated_results.append(ablated_result)
                seed_results.append(
                    {
                        "seed": current_seed,
                        "baseline": baseline_result,
                        "ablated": ablated_result,
                    }
                )
            baseline = _aggregate_results(baseline_results)
            result = _aggregate_results(ablated_results)
            if baseline.get("trained") and result.get("trained"):
                result.update(_metric_deltas(result, baseline))
            cells.append(
                {
                    "window": window_name,
                    "since": since,
                    "until": until,
                    "group": group_name,
                    "excluded_features": list(excluded_features),
                    "sample_count": len(samples),
                    "baseline": baseline,
                    "ablated": result,
                    "seed_results": seed_results,
                }
            )
    return {
        "version": "xgb_ablation_matrix.v2",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "samples_path": str(samples_path),
        "limit": limit,
        "train_ratio": train_ratio,
        "seed": seed,
        "seeds": seed_list,
        "feature_count": len(FEATURE_ORDER),
        "groups": groups,
        "cells": cells,
    }


def _write_markdown(report: dict[str, Any], output_path: Path) -> None:
    seeds = report.get("seeds", [report.get("seed")])
    lines = [
        "# XGBoost Ablation Matrix",
        "",
        f"- generated: {report['generated_at']}",
        f"- samples: `{report['samples_path']}`",
        f"- per-window limit: {report['limit']}",
        f"- train_ratio: {report['train_ratio']}",
        f"- seeds: {', '.join(str(seed) for seed in seeds)}",
        "",
        "| window | group | samples | seeds | features | logloss delta | acc delta | Brier delta | ECE delta | cal gap delta | ablated logloss | ablated acc |",
        "|--------|-------|--------:|------:|---------:|--------------:|----------:|------------:|----------:|--------------:|----------------:|------------:|",
    ]
    for cell in report["cells"]:
        ablated = cell["ablated"]
        lines.append(
            f"| {cell['window']} | {cell['group']} | {cell['sample_count']} | {ablated.get('trained_seed_count', 0)}/{ablated.get('seed_count', 0)} | "
            f"{ablated.get('feature_count', '-')} | {ablated.get('logloss_delta', 'N/A')} | {ablated.get('accuracy_delta', 'N/A')} | "
            f"{ablated.get('brier_delta', 'N/A')} | {ablated.get('ece_delta', 'N/A')} | {ablated.get('calibration_gap_delta', 'N/A')} | "
            f"{ablated.get('logloss', 'N/A')} | {ablated.get('accuracy', 'N/A')} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Negative `logloss delta`, `Brier delta`, or `ECE delta` means the ablated feature set improved that metric.",
        "- Positive `acc delta` means the ablated feature set improved accuracy.",
        "- `cal gap delta` is directional; compare the absolute gap in JSON before treating it as an improvement.",
        "- Do not remove features unless multiple windows show no logloss/Brier/calibration regression after retraining.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _parse_seeds(raw: str, fallback: int) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    return seeds or [fallback]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline XGBoost feature ablation matrix")
    parser.add_argument("--samples", type=Path, default=PROJECT_ROOT / "data" / "state" / "xgb_training_samples.json")
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=str, default="17,42,101", help="comma-separated seeds for repeated train/test splits")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "feature_ablation")
    args = parser.parse_args()

    if not args.samples.exists():
        raise SystemExit(f"samples not found: {args.samples}")
    report = build_ablation_matrix(
        samples_path=args.samples,
        limit=args.limit,
        train_ratio=args.train_ratio,
        seed=args.seed,
        seeds=_parse_seeds(args.seeds, args.seed),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"xgb_ablation_matrix_{stamp}.json"
    md_path = args.output_dir / f"xgb_ablation_matrix_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(f"JSON: {json_path}")
    print(f"MD  : {md_path}")


if __name__ == "__main__":
    main()
