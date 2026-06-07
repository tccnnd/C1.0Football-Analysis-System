from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from c1.audit.calibration_drift import build_calibration_drift_report

PROJECT_ROOT = Path(__file__).resolve().parent


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("cells"), list):
        raise ValueError("accuracy matrix files contain aggregate cells, not per-match probability rows")
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise ValueError(f"unsupported report shape: {path}")


def _pct(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.2%}"


def _write_markdown(report: dict[str, Any], source: Path, output_path: Path) -> None:
    v24 = report["models"]["v24"]
    c1 = report["models"]["c1"]
    comparison = report.get("comparison", {})
    lines = [
        "# Calibration Drift Report",
        "",
        f"- generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- source: `{source}`",
        f"- rows: {report['row_count']}",
        "",
        "## Summary",
        "",
        "| model | n | accuracy | avg confidence | gap(actual-conf) | ECE | Brier | Logloss |",
        "|-------|---|----------|----------------|------------------|-----|-------|---------|",
        (
            f"| V24 | {v24['count']} | {_pct(v24['accuracy'])} | {_pct(v24['avg_confidence'])} | "
            f"{_pct(v24['calibration_gap'])} | {_pct(v24['ece'])} | {v24['brier']} | {v24['logloss']} |"
        ),
        (
            f"| C1 | {c1['count']} | {_pct(c1['accuracy'])} | {_pct(c1['avg_confidence'])} | "
            f"{_pct(c1['calibration_gap'])} | {_pct(c1['ece'])} | {c1['brier']} | {c1['logloss']} |"
        ),
        "",
        "## C1 vs V24 Delta",
        "",
        f"- accuracy_delta: {comparison.get('accuracy_delta', 'N/A')}",
        f"- ece_delta: {comparison.get('ece_delta', 'N/A')}",
        f"- brier_delta: {comparison.get('brier_delta', 'N/A')}",
        f"- logloss_delta: {comparison.get('logloss_delta', 'N/A')}",
        "",
        "## Buckets",
        "",
    ]
    for model_name, model in (("V24", v24), ("C1", c1)):
        lines += [
            f"### {model_name}",
            "",
            "| confidence bucket | n | avg confidence | actual rate | gap | Brier | Logloss |",
            "|-------------------|---|----------------|-------------|-----|-------|---------|",
        ]
        for label, bucket in model.get("buckets", {}).items():
            lines.append(
                f"| {label} | {bucket['n']} | {_pct(bucket['avg_confidence'])} | "
                f"{_pct(bucket['actual_rate'])} | {_pct(bucket['gap'])} | "
                f"{bucket['brier']} | {bucket['logloss']} |"
            )
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build calibration drift report from shadow-history rows")
    parser.add_argument("input", type=Path, help="shadow_history JSON file containing per-match rows")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports" / "calibration_drift")
    args = parser.parse_args()

    rows = _load_rows(args.input)
    report = build_calibration_drift_report(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"calibration_drift_{stamp}.json"
    md_path = args.output_dir / f"calibration_drift_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, args.input, md_path)
    print(f"JSON: {json_path}")
    print(f"MD  : {md_path}")


if __name__ == "__main__":
    main()
