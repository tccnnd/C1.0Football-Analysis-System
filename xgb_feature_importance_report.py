from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from c1.audit.feature_importance import (
    built_in_importance_from_booster,
    feature_quality_report,
    permutation_importance,
    rank_feature_report,
    samples_to_xy,
)
from c1.inference.engines.xgboost_engine import FEATURE_ORDER

PROJECT_ROOT = Path(__file__).resolve().parent


def _load_samples(path: Path, *, limit: int, since: str = "", until: str = "") -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []
    selected: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        timestamp = str(item.get("timestamp") or "")
        day = timestamp[:10]
        if since and day and day < since:
            continue
        if until and day and day >= until:
            continue
        selected.append(item)
        if limit > 0 and len(selected) >= limit:
            break
    return selected


def _load_xgb_model(model_path: Path) -> Any:
    try:
        import xgboost as xgb
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("xgboost is required for model/permutation importance") from exc
    model = xgb.XGBClassifier(objective="multi:softprob", num_class=3)
    model.load_model(str(model_path))
    return model


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    baseline = report.get("permutation", {}).get("baseline", {})
    rows = report.get("ranked_features", [])
    bottom = rows[: max(int(len(rows) * 0.4), 1)]
    top = list(reversed(rows[-10:]))
    lines = [
        "# XGBoost Feature Importance Report",
        "",
        f"- generated: {report['generated_at']}",
        f"- samples: {report['sample_count']}",
        f"- model: `{report['model_path']}`",
        f"- baseline logloss: {baseline.get('logloss', 'N/A')}",
        f"- baseline accuracy: {baseline.get('accuracy', 'N/A')}",
        "",
        "## Top Features",
        "",
        "| feature | score | gain | weight | perm logloss Δ | perm acc Δ | zero rate | unique |",
        "|---------|-------|------|--------|----------------|------------|-----------|--------|",
    ]
    for item in top:
        lines.append(
            f"| {item['feature']} | {item['score']} | {item['gain']} | {item['weight']} | "
            f"{item['permutation_logloss_delta']} | {item['permutation_accuracy_delta']} | "
            f"{item['zero_rate']} | {item['unique_count']} |"
        )
    lines += [
        "",
        "## Bottom 40 Percent Candidates",
        "",
        "> These are review candidates only. Do not remove features without a windowed ablation proving no regression.",
        "",
        "| feature | score | gain | weight | perm logloss Δ | perm acc Δ | zero rate | unique |",
        "|---------|-------|------|--------|----------------|------------|-----------|--------|",
    ]
    for item in bottom:
        lines.append(
            f"| {item['feature']} | {item['score']} | {item['gain']} | {item['weight']} | "
            f"{item['permutation_logloss_delta']} | {item['permutation_accuracy_delta']} | "
            f"{item['zero_rate']} | {item['unique_count']} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build XGBoost feature importance and ablation report")
    parser.add_argument("--samples", type=Path, default=PROJECT_ROOT / "data" / "state" / "xgb_training_samples.json")
    parser.add_argument("--model", type=Path, default=PROJECT_ROOT / "data" / "models" / "xgb_v0_match_outcome.json")
    parser.add_argument("--limit", type=int, default=5000, help="max samples to load for permutation importance")
    parser.add_argument("--since", type=str, default="", help="inclusive YYYY-MM-DD sample lower bound")
    parser.add_argument("--until", type=str, default="", help="exclusive YYYY-MM-DD sample upper bound")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "feature_importance")
    args = parser.parse_args()

    if not args.samples.exists():
        raise SystemExit(f"samples not found: {args.samples}")
    if not args.model.exists():
        raise SystemExit(f"model not found: {args.model}")

    samples = _load_samples(args.samples, limit=args.limit, since=args.since, until=args.until)
    x_rows, labels = samples_to_xy(samples, FEATURE_ORDER)
    quality = feature_quality_report(samples, FEATURE_ORDER)
    model = _load_xgb_model(args.model)
    booster = model.get_booster()
    built_in = built_in_importance_from_booster(booster, FEATURE_ORDER)
    permutation = permutation_importance(
        model=model,
        x_rows=x_rows,
        labels=labels,
        feature_order=FEATURE_ORDER,
        repeats=args.repeats,
    )
    ranked = rank_feature_report(
        feature_order=FEATURE_ORDER,
        built_in=built_in,
        permutation=permutation,
        quality=quality,
    )
    report = {
        "version": "xgb_feature_importance.v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_path": str(args.samples),
        "model_path": str(args.model),
        "sample_count": len(samples),
        "valid_sample_count": len(labels),
        "feature_count": len(FEATURE_ORDER),
        "since": args.since,
        "until": args.until,
        "quality": quality,
        "built_in_importance": built_in,
        "permutation": permutation,
        "ranked_features": ranked,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"xgb_feature_importance_{stamp}.json"
    md_path = args.output_dir / f"xgb_feature_importance_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(f"JSON: {json_path}")
    print(f"MD  : {md_path}")


if __name__ == "__main__":
    main()
