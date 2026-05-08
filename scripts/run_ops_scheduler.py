from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _bootstrap(project_root: Path) -> None:
    root = project_root.resolve()
    src = root / "src"
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run V24 operations scheduler loop.")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--interval-minutes", type=int, default=15, help="Cycle interval in minutes.")
    parser.add_argument("--lookback-days", type=int, default=2, help="Result settle lookback days.")
    parser.add_argument("--gate-window", type=int, default=30, help="Gate metrics window.")
    parser.add_argument("--report-days", type=int, default=14, help="Handicap report daily window.")
    parser.add_argument("--report-hour", type=int, default=8, help="Daily report trigger hour.")
    parser.add_argument("--report-minute", type=int, default=5, help="Daily report trigger minute.")
    parser.add_argument("--disable-bayes-calibration", action="store_true", help="Disable automatic bayes calibration.")
    parser.add_argument("--bayes-min-new-settled", type=int, default=1, help="Minimum new settled singles to trigger bayes calibration.")
    parser.add_argument("--bayes-cooldown-hours", type=int, default=6, help="Minimum hours between bayes calibrations.")
    parser.add_argument("--force-bayes-calibration", action="store_true", help="Force bayes calibration on current cycle.")
    parser.add_argument("--disable-bucket-tuning", action="store_true", help="Disable automatic weak-bucket threshold tuning.")
    parser.add_argument("--bucket-tuning-min-new-settled", type=int, default=1, help="Minimum new settled singles to trigger bucket tuning.")
    parser.add_argument("--bucket-tuning-cooldown-hours", type=int, default=6, help="Minimum hours between bucket tuning runs.")
    parser.add_argument("--force-bucket-tuning", action="store_true", help="Force bucket tuning on current cycle.")
    parser.add_argument("--disable-coverage-guardrail", action="store_true", help="Disable automatic threshold coverage guardrail.")
    parser.add_argument("--coverage-guardrail-min-new-settled", type=int, default=1, help="Minimum new settled singles to trigger coverage guardrail.")
    parser.add_argument("--coverage-guardrail-cooldown-hours", type=int, default=4, help="Minimum hours between coverage guardrail runs.")
    parser.add_argument("--coverage-guardrail-snapshot-limit", type=int, default=240, help="Prediction snapshot count used by coverage guardrail.")
    parser.add_argument("--coverage-guardrail-min-predictions", type=int, default=12, help="Minimum prediction snapshots needed by coverage guardrail.")
    parser.add_argument("--force-coverage-guardrail", action="store_true", help="Force coverage guardrail on current cycle.")
    parser.add_argument("--disable-market-snapshots", action="store_true", help="Disable pre-match T-120/T-30/T-5 market snapshots.")
    parser.add_argument("--market-after-kickoff-minutes", type=int, default=10, help="Allow snapshot capture up to N minutes after kickoff.")
    parser.add_argument("--run-once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument("--force-daily-report", action="store_true", help="Emit daily report on current cycle.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    project_root = Path(args.project_root).resolve()
    _bootstrap(project_root)

    from v24_app.ops.scheduler import SchedulerCycleConfig, run_scheduler_cycle

    config = SchedulerCycleConfig(
        lookback_days=args.lookback_days,
        gate_window=args.gate_window,
        report_days=args.report_days,
        report_hour=args.report_hour,
        report_minute=args.report_minute,
        force_daily_report=bool(args.force_daily_report),
        bayes_calibration_enabled=not bool(args.disable_bayes_calibration),
        bayes_min_new_settled=args.bayes_min_new_settled,
        bayes_cooldown_hours=args.bayes_cooldown_hours,
        force_bayes_calibration=bool(args.force_bayes_calibration),
        bucket_tuning_enabled=not bool(args.disable_bucket_tuning),
        bucket_tuning_min_new_settled=args.bucket_tuning_min_new_settled,
        bucket_tuning_cooldown_hours=args.bucket_tuning_cooldown_hours,
        force_bucket_tuning=bool(args.force_bucket_tuning),
        coverage_guardrail_enabled=not bool(args.disable_coverage_guardrail),
        coverage_guardrail_min_new_settled=args.coverage_guardrail_min_new_settled,
        coverage_guardrail_cooldown_hours=args.coverage_guardrail_cooldown_hours,
        coverage_guardrail_snapshot_limit=args.coverage_guardrail_snapshot_limit,
        coverage_guardrail_min_predictions=args.coverage_guardrail_min_predictions,
        force_coverage_guardrail=bool(args.force_coverage_guardrail),
        market_snapshot_enabled=not bool(args.disable_market_snapshots),
        market_snapshot_after_kickoff_minutes=args.market_after_kickoff_minutes,
    )
    interval_seconds = max(60, int(args.interval_minutes) * 60)

    while True:
        heartbeat = run_scheduler_cycle(project_root=project_root, config=config)
        print(json.dumps(heartbeat, ensure_ascii=False, indent=2))
        if args.run_once:
            return 0
        config.force_daily_report = False
        config.force_bayes_calibration = False
        config.force_bucket_tuning = False
        config.force_coverage_guardrail = False
        time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
