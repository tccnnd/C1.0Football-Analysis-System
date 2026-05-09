from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _bootstrap() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    src_dir = base_dir / "src"
    os.chdir(base_dir)
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return base_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run JC stratified market strategy backtest.")
    parser.add_argument("--historical-limit", type=int, default=50000)
    parser.add_argument("--source", default="jc_results_csv")
    parser.add_argument("--min-samples", type=int, default=120)
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()

    _bootstrap()
    from v24_app.core import run_jc_stratified_strategy_backtest

    result = run_jc_stratified_strategy_backtest(
        historical_limit=args.historical_limit,
        source=args.source,
        min_samples=args.min_samples,
        write_report=not args.no_report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
