from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from c1.inference.engines.xgboost_engine import FEATURE_ORDER
from xgb_ablation_matrix import (
    METRIC_KEYS,
    WINDOWS,
    _aggregate_results,
    _metric_deltas,
    _parse_seeds,
    _train_test_split,
    evaluate_feature_set,
)
from xgb_feature_importance_report import _load_samples

PROJECT_ROOT = Path(__file__).resolve().parent

MARKET_FEATURE_SETS: dict[str, list[str]] = {
    "market_implied_core": [
        "market_home",
        "market_draw",
        "market_away",
        "odds_home",
        "odds_draw",
        "odds_away",
    ],
    "market_movement": [
        "market_home",
        "market_draw",
        "market_away",
        "odds_home",
        "odds_draw",
        "odds_away",
        "opening_odds_home",
        "opening_odds_draw",
        "opening_odds_away",
        "home_odds_drop",
        "draw_odds_drop",
        "away_odds_drop",
        "market_balance",
        "return_rate",
        "market_overround",
    ],
    "market_movement_with_kelly": [
        "market_home",
        "market_draw",
        "market_away",
        "odds_home",
        "odds_draw",
        "odds_away",
        "opening_odds_home",
        "opening_odds_draw",
        "opening_odds_away",
        "home_odds_drop",
        "draw_odds_drop",
        "away_odds_drop",
        "market_balance",
        "return_rate",
        "market_overround",
        "kelly_home",
        "kelly_draw",
        "kelly_away",
        "kelly_draw_edge",
    ],
}


def _validate_feature_sets(feature_sets: dict[str, list[str]]) -> dict[str, list[str]]:
    known = set(FEATURE_ORDER)
    validated: dict[str, list[str]] = {}
    for name, features in feature_sets.items():
        missing = [feature for feature in features if feature not in known]
        if missing:
            raise ValueError(f"{name} contains unknown features: {', '.join(missing)}")
        validated[name] = list(features)
    return validated


def build_market_odds_specialist_matrix(
    *,
    samples_path: Path,
    limit: int,
    train_ratio: float,
    seed: int,
    seeds: Sequence[int] | None = None,
    windows: Sequence[tuple[str, str, str]] = WINDOWS,
    feature_sets: dict[str, list[str]] = MARKET_FEATURE_SETS,
) -> dict[str, Any]:
    seed_list = list(seeds) if seeds else [seed]
    validated_sets = _validate_feature_sets(feature_sets)
    cells: list[dict[str, Any]] = []
    for window_name, since, until in windows:
        samples = _load_samples(samples_path, limit=limit, since=since, until=until)
        full_results: list[dict[str, Any]] = []
        specialist_results: dict[str, list[dict[str, Any]]] = {name: [] for name in validated_sets}
        per_seed: list[dict[str, Any]] = []
        for current_seed in seed_list:
            train_samples, test_samples = _train_test_split(samples, train_ratio=train_ratio, seed=current_seed)
            full_result = evaluate_feature_set(
                train_samples=train_samples,
                test_samples=test_samples,
                feature_order=FEATURE_ORDER,
                seed=current_seed,
            )
            full_results.append(full_result)
            seed_payload: dict[str, Any] = {"seed": current_seed, "full_xgb": full_result, "specialists": {}}
            for name, feature_order in validated_sets.items():
                result = evaluate_feature_set(
                    train_samples=train_samples,
                    test_samples=test_samples,
                    feature_order=feature_order,
                    seed=current_seed,
                )
                if full_result.get("trained") and result.get("trained"):
                    result.update(_metric_deltas(result, full_result))
                specialist_results[name].append(result)
                seed_payload["specialists"][name] = result
            per_seed.append(seed_payload)

        full_summary = _aggregate_results(full_results)
        for name, results in specialist_results.items():
            summary = _aggregate_results(results)
            if full_summary.get("trained") and summary.get("trained"):
                summary.update(_metric_deltas(summary, full_summary))
            cells.append(
                {
                    "window": window_name,
                    "since": since,
                    "until": until,
                    "feature_set": name,
                    "features": validated_sets[name],
                    "sample_count": len(samples),
                    "full_xgb": full_summary,
                    "specialist": summary,
                    "seed_results": per_seed,
                }
            )
    return {
        "version": "market_odds_specialist.v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "samples_path": str(samples_path),
        "limit": limit,
        "train_ratio": train_ratio,
        "seed": seed,
        "seeds": seed_list,
        "full_feature_count": len(FEATURE_ORDER),
        "feature_sets": validated_sets,
        "cells": cells,
    }


def _write_markdown(report: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Market/Odds Specialist Report",
        "",
        f"- generated: {report['generated_at']}",
        f"- samples: `{report['samples_path']}`",
        f"- per-window limit: {report['limit']}",
        f"- train_ratio: {report['train_ratio']}",
        f"- seeds: {', '.join(str(seed) for seed in report['seeds'])}",
        "",
        "| window | specialist | samples | seeds | features | logloss delta | acc delta | Brier delta | ECE delta | specialist logloss | specialist acc |",
        "|--------|------------|--------:|------:|---------:|--------------:|----------:|------------:|----------:|-------------------:|---------------:|",
    ]
    for cell in report["cells"]:
        specialist = cell["specialist"]
        lines.append(
            f"| {cell['window']} | {cell['feature_set']} | {cell['sample_count']} | "
            f"{specialist.get('trained_seed_count', 0)}/{specialist.get('seed_count', 0)} | "
            f"{specialist.get('feature_count', '-')} | {specialist.get('logloss_delta', 'N/A')} | "
            f"{specialist.get('accuracy_delta', 'N/A')} | {specialist.get('brier_delta', 'N/A')} | "
            f"{specialist.get('ece_delta', 'N/A')} | {specialist.get('logloss', 'N/A')} | "
            f"{specialist.get('accuracy', 'N/A')} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Deltas compare the market/odds specialist against the full XGBoost feature set on the same split and seed.",
        "- Negative logloss/Brier/ECE delta means the specialist improved that metric.",
        "- The specialist is a candidate sidecar signal only; do not use it as primary until it wins across windows and calibration metrics.",
        "",
        "## Feature Sets",
        "",
    ]
    for name, features in report["feature_sets"].items():
        lines.append(f"- `{name}` ({len(features)}): {', '.join(features)}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _best_by_metric(report: dict[str, Any], metric: str) -> list[dict[str, Any]]:
    rows = []
    delta_key = f"{metric}_delta"
    for cell in report.get("cells", []):
        specialist = cell.get("specialist", {})
        if specialist.get(delta_key) is None:
            continue
        rows.append(
            {
                "window": cell["window"],
                "feature_set": cell["feature_set"],
                delta_key: specialist[delta_key],
                metric: specialist.get(metric),
            }
        )
    return sorted(rows, key=lambda item: float(item[delta_key]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate market/odds-only XGBoost specialist candidates")
    parser.add_argument("--samples", type=Path, default=PROJECT_ROOT / "data" / "state" / "xgb_training_samples.json")
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=str, default="17,42,101", help="comma-separated seeds for repeated train/test splits")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "market_odds_specialist")
    args = parser.parse_args()

    if not args.samples.exists():
        raise SystemExit(f"samples not found: {args.samples}")
    report = build_market_odds_specialist_matrix(
        samples_path=args.samples,
        limit=args.limit,
        train_ratio=args.train_ratio,
        seed=args.seed,
        seeds=_parse_seeds(args.seeds, args.seed),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"market_odds_specialist_{stamp}.json"
    md_path = args.output_dir / f"market_odds_specialist_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(f"JSON: {json_path}")
    print(f"MD  : {md_path}")
    for metric in METRIC_KEYS:
        best = _best_by_metric(report, metric)[:3]
        if best:
            print(f"best {metric}: {best}")


if __name__ == "__main__":
    main()
