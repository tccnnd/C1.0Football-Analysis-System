"""
Accuracy Baseline Matrix — C1.0 vs V24

在 signal-bearing 的 foot 原生数据上，跨多个时间窗口 / 样本量运行 shadow，
收集 C1/V24 准确率、差值、foot 覆盖率、approve rate、治理分离度，
判断 C1 是稳定接近/领先，还是存在窗口性落后。

不做任何 refit，不修改 runtime_mode.yaml。仅测量。

用法：
    set FOOT_MYSQL_PASSWORD=...
    python accuracy_baseline_matrix.py
    python accuracy_baseline_matrix.py --quick   # 只跑 1000 样本档，快速验证

输出：
    reports/accuracy_baseline/accuracy_matrix_<stamp>.json
    reports/accuracy_baseline/accuracy_matrix_<stamp>.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 静音 xg_bridge 的海量 WARNING（历史数据含大量 Understat 不支持的小联赛，
# 每场都会触发查询失败日志，污染输出且拖慢运行）。仅在本批量测量脚本中抬高级别。
import logging as _logging
_logging.getLogger("c1.data.xg_bridge").setLevel(_logging.ERROR)

import shadow_run_history as srh


# 时间窗口定义：(label, since_date, until_date_exclusive)
WINDOWS = [
    ("2016-2018", "2016-01-01", "2018-01-01"),
    ("2018-2020", "2018-01-01", "2020-05-01"),
    ("all-foot-native", "2006-01-01", "2020-05-01"),
]
SAMPLE_SIZES = [1000, 2000, 5000]
SAMPLE_SIZES_QUICK = [1000]


def run_cell(
    label: str,
    since: str,
    until: str,
    limit: int,
    v24_predict,
    shadow_runner,
) -> dict:
    """运行单个矩阵单元，返回精简指标。"""
    t0 = time.time()
    rows = srh.fetch_history_matches(
        limit, since, None, foot_native_only=True, until_date=until,
    )
    if not rows:
        return {
            "window": label, "since": since, "until": until, "limit": limit,
            "fetched": 0, "error": "no rows",
        }

    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(srh.run_one_match, row, v24_predict, shadow_runner, True)
            for row in rows
        ]
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)

    report = srh.build_report(results, enable_foot=True)
    valid = max(report.get("valid", 0), 1)
    coverage = (report.get("foot_stats", {}).get("available", 0) / valid) if report.get("foot_stats") else 0.0

    c1 = report.get("c1_accuracy")
    v24 = report.get("v24_accuracy")
    delta = (c1 - v24) if (c1 is not None and v24 is not None) else None

    return {
        "window": label,
        "since": since,
        "until": until,
        "limit": limit,
        "fetched": len(rows),
        "valid": report.get("valid"),
        "known_outcome": report.get("known_outcome"),
        "c1_accuracy": c1,
        "v24_accuracy": v24,
        "delta": round(delta, 4) if delta is not None else None,
        "c1_geq_v24": (delta is not None and delta >= 0),
        "foot_coverage": round(coverage, 4),
        "approve_rate": report.get("approve_rate"),
        "approve_n": report.get("approve_n"),
        "downgrade_n": report.get("downgrade_n"),
        "block_n": report.get("block_n"),
        "governance_separation": report.get("governance_separation"),
        "elapsed_s": round(time.time() - t0, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Accuracy Baseline Matrix")
    parser.add_argument("--quick", action="store_true", help="仅跑 1000 样本档")
    args = parser.parse_args()

    if not os.environ.get("FOOT_MYSQL_PASSWORD"):
        print("ERROR: FOOT_MYSQL_PASSWORD is required for accuracy baseline runs.")
        sys.exit(2)

    sizes = SAMPLE_SIZES_QUICK if args.quick else SAMPLE_SIZES
    out_dir = PROJECT_ROOT / "reports" / "accuracy_baseline"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_dir = out_dir / f"audit_{stamp}"

    print("=" * 60)
    print("  Accuracy Baseline Matrix (C1.0 vs V24, signal-bearing only)")
    print(f"  windows={len(WINDOWS)}  sizes={sizes}")
    print(f"  audit_dir={audit_dir}")
    print("=" * 60)

    # 初始化引擎一次，跨单元复用
    from v24_app.core import predict_match as v24_predict, _RATINGS_CACHE
    for pool in _RATINGS_CACHE:
        _RATINGS_CACHE[pool] = {"signature": None, "ratings": {}}
    from c1.runtime.shadow import C1ShadowRunner
    shadow_runner = C1ShadowRunner(PROJECT_ROOT, audit_dir=audit_dir)

    cells = []
    for label, since, until in WINDOWS:
        for limit in sizes:
            print(f"\n>>> window={label} limit={limit} ...", flush=True)
            try:
                cell = run_cell(label, since, until, limit, v24_predict, shadow_runner)
            except Exception as e:
                cell = {"window": label, "since": since, "until": until, "limit": limit, "error": str(e)}
            cells.append(cell)
            # 简洁进度（ASCII only，避免控制台编码问题）
            if "error" in cell:
                print(f"    ERROR: {cell['error']}")
            else:
                d = cell["delta"]
                dstr = f"{d:+.4f}" if d is not None else "N/A"
                print(f"    c1={cell['c1_accuracy']} v24={cell['v24_accuracy']} delta={dstr} "
                      f"cov={cell['foot_coverage']} appr_rate={cell['approve_rate']} sep={cell['governance_separation']} "
                      f"({cell['elapsed_s']}s)")

    # 汇总判定
    valid_cells = [c for c in cells if "error" not in c and c.get("delta") is not None]
    n_c1_geq = sum(1 for c in valid_cells if c["c1_geq_v24"])
    n_total = len(valid_cells)
    deltas = [c["delta"] for c in valid_cells]
    verdict = "INSUFFICIENT_DATA"
    if n_total:
        if n_c1_geq == n_total:
            verdict = "C1_CONSISTENTLY_GEQ"  # 全部窗口 C1 >= V24
        elif n_c1_geq == 0:
            verdict = "C1_CONSISTENTLY_BEHIND"  # 全部窗口落后 → 需要 refit
        else:
            verdict = "C1_WINDOW_DEPENDENT"  # 窗口性落后

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "windows": WINDOWS,
        "sample_sizes": sizes,
        "cells": cells,
        "n_cells_valid": n_total,
        "n_cells_c1_geq_v24": n_c1_geq,
        "delta_min": round(min(deltas), 4) if deltas else None,
        "delta_max": round(max(deltas), 4) if deltas else None,
        "delta_mean": round(sum(deltas) / len(deltas), 4) if deltas else None,
        "verdict": verdict,
        "audit_dir": str(audit_dir),
    }

    json_path = out_dir / f"accuracy_matrix_{stamp}.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    lines = [
        "# Accuracy Baseline Matrix (C1.0 vs V24)",
        "",
        f"- generated: {summary['generated_at']}",
        f"- sample sizes: {sizes}",
        "- data: foot-native only (signal-bearing); fdu_ excluded",
        "",
        "| window | limit | known | C1 acc | V24 acc | delta | C1>=V24 | foot cov | approve rate | separation |",
        "|--------|-------|-------|--------|---------|-------|---------|----------|--------------|------------|",
    ]
    for c in cells:
        if "error" in c:
            lines.append(f"| {c['window']} | {c['limit']} | - | ERROR | - | - | - | - | - | {c.get('error','')[:30]} |")
            continue
        def pct(v):
            return f"{v:.1%}" if isinstance(v, (int, float)) else "N/A"
        lines.append(
            f"| {c['window']} | {c['limit']} | {c.get('known_outcome')} | {pct(c['c1_accuracy'])} | "
            f"{pct(c['v24_accuracy'])} | {('%+.1f%%' % (c['delta']*100)) if c['delta'] is not None else 'N/A'} | "
            f"{'YES' if c['c1_geq_v24'] else 'no'} | {pct(c['foot_coverage'])} | "
            f"{pct(c['approve_rate']) if c['approve_rate'] is not None else 'N/A'} | "
            f"{('%+.1f%%' % (c['governance_separation']*100)) if c['governance_separation'] is not None else 'N/A'} |"
        )
    lines += [
        "",
        "## Verdict",
        "",
        f"- valid cells: {n_total}",
        f"- cells with C1 >= V24: {n_c1_geq}/{n_total}",
        f"- delta range: {summary['delta_min']} ~ {summary['delta_max']} (mean {summary['delta_mean']})",
        f"- **verdict: {verdict}**",
        "",
        "verdict 含义：",
        "- `C1_CONSISTENTLY_GEQ`：全部窗口 C1 >= V24，accuracy 门槛可进入正式验收。",
        "- `C1_WINDOW_DEPENDENT`：存在窗口性落后，需先定位是哪个窗口/联赛拖累，再决定是否 refit。",
        "- `C1_CONSISTENTLY_BEHIND`：全部窗口落后，确认需要 ensemble reweight / LightGBM-xG fusion。",
        "",
        "> 本脚本仅测量，不修改 runtime_mode.yaml，不做 refit。",
    ]
    md_path = out_dir / f"accuracy_matrix_{stamp}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"  VERDICT: {verdict}  ({n_c1_geq}/{n_total} cells C1>=V24)")
    print(f"  delta range: {summary['delta_min']} ~ {summary['delta_max']} (mean {summary['delta_mean']})")
    print(f"  JSON: {json_path}")
    print(f"  MD  : {md_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
