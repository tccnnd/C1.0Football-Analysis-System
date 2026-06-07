from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
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


def _load_xgb_estimator() -> Any:
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
        random_state=42,
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


def evaluate_feature_set(
    *,
    train_samples: list[dict[str, Any]],
    test_samples: list[dict[str, Any]],
    feature_order: Sequence[str],
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
    model = _load_xgb_estimator()
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)
    return {
        "trained": True,
        "train_count": len(x_train),
        "test_count": len(x_test),
        "feature_count": len(feature_order),
        "train_label_counts": _label_counts(y_train),
        "test_label_counts": _label_counts(y_test),
        "logloss": round(multiclass_logloss(probabilities, y_test), 6),
        "accuracy": round(multiclass_accuracy(probabilities, y_test), 6),
    }


def build_ablation_matrix(
    *,
    samples_path: Path,
    limit: int,
    train_ratio: float,
    seed: int,
    windows: Sequence[tuple[str, str, str]] = WINDOWS,
    groups: dict[str, list[str]] = ABLATION_GROUPS,
) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    for window_name, since, until in windows:
        samples = _load_samples(samples_path, limit=limit, since=since, until=until)
        train_samples, test_samples = _train_test_split(samples, train_ratio=train_ratio, seed=seed)
        baseline = evaluate_feature_set(
            train_samples=train_samples,
            test_samples=test_samples,
            feature_order=FEATURE_ORDER,
        )
        for group_name, excluded_features in groups.items():
            excluded = set(excluded_features)
            feature_order = _select_features(FEATURE_ORDER, excluded)
            result = evaluate_feature_set(
                train_samples=train_samples,
                test_samples=test_samples,
                feature_order=feature_order,
            )
            if baseline.get("trained") and result.get("trained"):
                result["logloss_delta"] = round(float(result["logloss"]) - float(baseline["logloss"]), 6)
                result["accuracy_delta"] = round(float(result["accuracy"]) - float(baseline["accuracy"]), 6)
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
                }
            )
    return {
        "version": "xgb_ablation_matrix.v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "samples_path": str(samples_path),
        "limit": limit,
        "train_ratio": train_ratio,
        "seed": seed,
        "feature_count": len(FEATURE_ORDER),
        "groups": groups,
        "cells": cells,
    }


def _write_markdown(report: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# XGBoost Ablation Matrix",
        "",
        f"- generated: {report['generated_at']}",
        f"- samples: `{report['samples_path']}`",
        f"- per-window limit: {report['limit']}",
        f"- train_ratio: {report['train_ratio']}",
        f"- seed: {report['seed']}",
        "",
        "| window | group | samples | features | baseline logloss | ablated logloss | logloss Δ | baseline acc | ablated acc | acc Δ |",
        "|--------|-------|--------:|---------:|-----------------:|----------------:|----------:|-------------:|------------:|------:|",
    ]
    for cell in report["cells"]:
        baseline = cell["baseline"]
        ablated = cell["ablated"]
        lines.append(
            f"| {cell['window']} | {cell['group']} | {cell['sample_count']} | {ablated.get('feature_count', '-')} | "
            f"{baseline.get('logloss', 'N/A')} | {ablated.get('logloss', 'N/A')} | {ablated.get('logloss_delta', 'N/A')} | "
            f"{baseline.get('accuracy', 'N/A')} | {ablated.get('accuracy', 'N/A')} | {ablated.get('accuracy_delta', 'N/A')} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Negative `logloss Δ` means the ablated feature set improved logloss.",
        "- Positive `acc Δ` means the ablated feature set improved accuracy.",
        "- Do not remove features unless multiple windows show no logloss/Brier/calibration regression after retraining.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline XGBoost feature ablation matrix")
    parser.add_argument("--samples", type=Path, default=PROJECT_ROOT / "data" / "state" / "xgb_training_samples.json")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "feature_ablation")
    args = parser.parse_args()

    if not args.samples.exists():
        raise SystemExit(f"samples not found: {args.samples}")
    report = build_ablation_matrix(
        samples_path=args.samples,
        limit=args.limit,
        train_ratio=args.train_ratio,
        seed=args.seed,
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
