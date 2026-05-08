from __future__ import annotations

import json
import shutil
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ops.scheduler import SchedulerCycleConfig, run_scheduler_cycle, should_emit_daily_report
from v24_app.ops.scheduler import should_run_bayes_calibration, should_run_bucket_tuning, should_run_coverage_guardrail


class OpsSchedulerTests(unittest.TestCase):
    def test_should_emit_daily_report(self) -> None:
        now = datetime(2026, 4, 5, 8, 6, 0)
        self.assertTrue(
            should_emit_daily_report(
                now=now,
                last_report_date="2026-04-04",
                report_hour=8,
                report_minute=5,
                force=False,
            )
        )
        self.assertFalse(
            should_emit_daily_report(
                now=now,
                last_report_date="2026-04-05",
                report_hour=8,
                report_minute=5,
                force=False,
            )
        )
        self.assertTrue(
            should_emit_daily_report(
                now=datetime(2026, 4, 5, 6, 0, 0),
                last_report_date="2026-04-05",
                report_hour=8,
                report_minute=5,
                force=True,
            )
        )

    def test_run_scheduler_cycle_writes_state_and_report(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_ops_scheduler_{uuid4().hex}"
        try:
            (root / "data" / "state").mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 4, 5, 8, 10, 0)

            with patch("v24_app.ops.scheduler.auto_settle_finished_matches", return_value={"new_settled": 1, "new_parlay_settled": 0}), patch(
                "v24_app.ops.scheduler.get_recent_settlements",
                return_value=[
                    {
                        "timestamp": "2026-04-05 01:00:00",
                        "handicap_line": -0.5,
                        "handicap_is_correct": True,
                        "handicap_confidence": 0.6,
                    }
                ],
            ), patch("v24_app.ops.scheduler.get_gate_metrics", return_value={"overall": {"hit_rate": 0.5}}), patch(
                "v24_app.ops.scheduler.get_parlay_selector_metrics",
                return_value={"ticket_count": 3, "max_match_exposure": 2},
            ), patch(
                "v24_app.ops.scheduler.calibrate_bayes_calibration_now",
                return_value={"calibrated": True, "reason": "ok"},
            ) as mock_bayes, patch(
                "v24_app.ops.scheduler.calibrate_play_thresholds_by_settlement_now",
                return_value={"calibrated": True, "reason": "ok_bucket"},
            ) as mock_bucket, patch(
                "v24_app.ops.scheduler.calibrate_play_thresholds_coverage_guardrail_now",
                return_value={"calibrated": True, "reason": "ok_guardrail"},
            ) as mock_guardrail, patch(
                "v24_app.ops.scheduler.fetch_matches_v24",
                return_value=SimpleNamespace(matches=[]),
            ):
                heartbeat = run_scheduler_cycle(
                    project_root=root,
                    config=SchedulerCycleConfig(report_hour=8, report_minute=5),
                    now=now,
                )

            self.assertTrue(heartbeat["daily_report_emitted"])
            self.assertTrue((root / "data" / "state" / "ops_scheduler_state.json").exists())
            self.assertTrue((root / "reports" / "ops_scheduler_heartbeat.json").exists())
            report_path = Path(heartbeat["daily_report_path"])
            self.assertTrue(report_path.exists())
            ops_report_path = Path(heartbeat["ops_daily_report_path"])
            self.assertTrue(ops_report_path.exists())
            ops_report_text = ops_report_path.read_text(encoding="utf-8")
            self.assertIn("Parlay Selector Health", ops_report_text)
            self.assertTrue(mock_bayes.called)
            self.assertTrue(mock_bucket.called)
            self.assertTrue(mock_guardrail.called)
            self.assertIn("bayes_calibration", heartbeat)
            self.assertIn("bucket_tuning", heartbeat)
            self.assertEqual((heartbeat.get("bucket_tuning") or {}).get("reason"), "ok_bucket")
            self.assertIn("coverage_guardrail", heartbeat)
            self.assertEqual((heartbeat.get("coverage_guardrail") or {}).get("reason"), "ok_guardrail")
            self.assertEqual(heartbeat.get("new_settled"), 1)
            self.assertIn("market_snapshots", heartbeat)
            self.assertEqual((heartbeat.get("market_snapshots") or {}).get("reason"), "no_matches")
            self.assertIn("parlay_selector", heartbeat)
            self.assertEqual((heartbeat.get("parlay_selector") or {}).get("ticket_count"), 3)

            state_payload = json.loads((root / "data" / "state" / "ops_scheduler_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state_payload.get("last_daily_report_date"), "2026-04-05")
            self.assertEqual(state_payload.get("last_bayes_calibration_reason"), "ok")
            self.assertEqual(state_payload.get("last_bucket_tuning_reason"), "ok_bucket")
            self.assertEqual(state_payload.get("last_coverage_guardrail_reason"), "ok_guardrail")
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def test_run_scheduler_cycle_skips_report_before_time(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_ops_scheduler_{uuid4().hex}"
        try:
            (root / "data" / "state").mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 4, 5, 7, 0, 0)

            with patch("v24_app.ops.scheduler.auto_settle_finished_matches", return_value={"new_settled": 0}), patch(
                "v24_app.ops.scheduler.get_recent_settlements",
                return_value=[],
            ), patch("v24_app.ops.scheduler.get_gate_metrics", return_value={}), patch(
                "v24_app.ops.scheduler.get_parlay_selector_metrics",
                return_value={},
            ), patch(
                "v24_app.ops.scheduler.calibrate_bayes_calibration_now",
                return_value={"calibrated": False, "reason": "should_not_run"},
            ) as mock_bayes, patch(
                "v24_app.ops.scheduler.calibrate_play_thresholds_by_settlement_now",
                return_value={"calibrated": False, "reason": "should_not_run_bucket"},
            ) as mock_bucket, patch(
                "v24_app.ops.scheduler.calibrate_play_thresholds_coverage_guardrail_now",
                return_value={"calibrated": False, "reason": "should_not_run_guardrail"},
            ) as mock_guardrail, patch(
                "v24_app.ops.scheduler.fetch_matches_v24",
                return_value=SimpleNamespace(matches=[]),
            ):
                heartbeat = run_scheduler_cycle(
                    project_root=root,
                    config=SchedulerCycleConfig(report_hour=8, report_minute=5),
                    now=now,
                )

            self.assertFalse(heartbeat["daily_report_emitted"])
            self.assertEqual(heartbeat["daily_report_path"], "")
            self.assertFalse(mock_bayes.called)
            self.assertFalse(mock_bucket.called)
            self.assertFalse(mock_guardrail.called)
            self.assertEqual((heartbeat.get("bayes_calibration") or {}).get("trigger"), "insufficient_new_settled")
            self.assertEqual((heartbeat.get("bucket_tuning") or {}).get("trigger"), "insufficient_new_settled")
            self.assertEqual((heartbeat.get("coverage_guardrail") or {}).get("trigger"), "insufficient_new_settled")
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def test_run_scheduler_cycle_can_disable_market_snapshots(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_ops_scheduler_{uuid4().hex}"
        try:
            (root / "data" / "state").mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 4, 5, 9, 0, 0)
            with patch("v24_app.ops.scheduler.auto_settle_finished_matches", return_value={"new_settled": 0}), patch(
                "v24_app.ops.scheduler.get_recent_settlements",
                return_value=[],
            ), patch("v24_app.ops.scheduler.get_gate_metrics", return_value={}), patch(
                "v24_app.ops.scheduler.get_parlay_selector_metrics",
                return_value={},
            ), patch(
                "v24_app.ops.scheduler.fetch_matches_v24",
                return_value=SimpleNamespace(matches=[]),
            ):
                heartbeat = run_scheduler_cycle(
                    project_root=root,
                    config=SchedulerCycleConfig(
                        report_hour=8,
                        report_minute=5,
                        bayes_calibration_enabled=False,
                        bucket_tuning_enabled=False,
                        coverage_guardrail_enabled=False,
                        market_snapshot_enabled=False,
                    ),
                    now=now,
                )
            self.assertEqual((heartbeat.get("market_snapshots") or {}).get("reason"), "disabled")
            self.assertEqual((heartbeat.get("bucket_tuning") or {}).get("trigger"), "disabled")
            self.assertEqual((heartbeat.get("coverage_guardrail") or {}).get("trigger"), "disabled")
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def test_should_run_bayes_calibration(self) -> None:
        now = datetime(2026, 4, 5, 10, 0, 0)
        should_run, reason = should_run_bayes_calibration(
            now=now,
            last_run_at="",
            new_settled=2,
            min_new_settled=1,
            cooldown_hours=6,
            enabled=True,
            force=False,
        )
        self.assertTrue(should_run)
        self.assertEqual(reason, "never_run")

        should_run, reason = should_run_bayes_calibration(
            now=now,
            last_run_at="2026-04-05 08:30:00",
            new_settled=2,
            min_new_settled=1,
            cooldown_hours=6,
            enabled=True,
            force=False,
        )
        self.assertFalse(should_run)
        self.assertEqual(reason, "cooldown_active")

    def test_should_run_coverage_guardrail(self) -> None:
        now = datetime(2026, 4, 5, 10, 0, 0)
        should_run, reason = should_run_coverage_guardrail(
            now=now,
            last_run_at="",
            new_settled=2,
            min_new_settled=1,
            cooldown_hours=4,
            enabled=True,
            force=False,
        )
        self.assertTrue(should_run)
        self.assertEqual(reason, "never_run")

        should_run, reason = should_run_coverage_guardrail(
            now=now,
            last_run_at="2026-04-05 08:30:00",
            new_settled=2,
            min_new_settled=1,
            cooldown_hours=4,
            enabled=True,
            force=False,
        )
        self.assertFalse(should_run)
        self.assertEqual(reason, "cooldown_active")

    def test_should_run_bucket_tuning(self) -> None:
        now = datetime(2026, 4, 5, 10, 0, 0)
        should_run, reason = should_run_bucket_tuning(
            now=now,
            last_run_at="",
            new_settled=2,
            min_new_settled=1,
            cooldown_hours=6,
            enabled=True,
            force=False,
        )
        self.assertTrue(should_run)
        self.assertEqual(reason, "never_run")

        should_run, reason = should_run_bucket_tuning(
            now=now,
            last_run_at="2026-04-05 08:30:00",
            new_settled=2,
            min_new_settled=1,
            cooldown_hours=6,
            enabled=True,
            force=False,
        )
        self.assertFalse(should_run)
        self.assertEqual(reason, "cooldown_active")


if __name__ == "__main__":
    unittest.main()
