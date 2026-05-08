from __future__ import annotations

import json
import shutil
import sys
import unittest
from datetime import datetime
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    build_ops_heartbeat_summary_text,
    build_ops_trend_rows,
    build_ops_trend_text,
    build_threshold_change_table_text,
    export_ops_trend_csv,
    export_threshold_trend_csv,
    load_ops_heartbeat,
    read_latest_ops_daily_report,
)


class UIOpsReportFlowModuleTests(unittest.TestCase):
    def test_read_latest_ops_daily_report_and_heartbeat(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_ops_report_{uuid4().hex}"
        try:
            report_dir = root / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "ops_daily_summary_20260406.md").write_text("# old", encoding="utf-8")
            latest_path = report_dir / "ops_daily_summary_20260407.md"
            latest_path.write_text("# new report", encoding="utf-8")
            heartbeat_payload = {
                "updated_at": "2026-04-07 18:00:00",
                "new_settled": 2,
                "bayes_calibration": {"reason": "ok"},
                "bucket_tuning": {"reason": "ok"},
                "coverage_guardrail": {"reason": "no_guardrail_change_needed"},
            }
            (report_dir / "ops_scheduler_heartbeat.json").write_text(
                json.dumps(heartbeat_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            payload = read_latest_ops_daily_report(report_dir)
            self.assertTrue(payload.get("ok"))
            self.assertEqual(str(payload.get("path")), str(latest_path))
            hb = load_ops_heartbeat(report_dir)
            self.assertEqual(hb.get("new_settled"), 2)
            summary_text = build_ops_heartbeat_summary_text(hb)
            self.assertIn("2", summary_text)
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def test_build_ops_trend_text_includes_threshold_table(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_ops_report_{uuid4().hex}"
        try:
            report_dir = root / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "ops_daily_summary_20260406.md").write_text(
                "\n".join(
                    [
                        "# V24 Ops Daily Summary",
                        "- Overall: hit 30.0% | expected 35.0% | ev_bias -5.0% | losing_streak 1 | breaker False",
                        "- Bayes: trigger=cooldown_elapsed | calibrated=True | reason=ok",
                        "- Bucket Tuning: trigger=cooldown_elapsed | calibrated=False | reason=no_significant_bucket_gap",
                        "- Coverage Guardrail: trigger=cooldown_elapsed | calibrated=False | reason=no_guardrail_change_needed",
                        "- mode: coverage_guardrail",
                        "- updated_at: 2026-04-06 18:00:00",
                        "- 1x2=0.76, handicap=0.72, total_goals=0.20, score=0.11, htft=0.36",
                        "- tickets=5 | unique_matches=4 | max_exposure=2 | avg_exposure=1.25",
                        "- mixed_ratio=60.0% | avg_expected_hit=24.0% | max_expected_hit=31.0%",
                        "- risk_flags: high_expected_hit=0, low_discount=1, high_upset_leg=0",
                        "- factors: pair_quality=1.03, play_reliability=0.96",
                    ]
                ),
                encoding="utf-8",
            )
            (report_dir / "ops_daily_summary_20260407.md").write_text(
                "\n".join(
                    [
                        "# V24 Ops Daily Summary",
                        "- Overall: hit 40.0% | expected 30.0% | ev_bias +10.0% | losing_streak 0 | breaker True",
                        "- Bayes: trigger=cooldown_elapsed | calibrated=True | reason=ok",
                        "- Bucket Tuning: trigger=cooldown_elapsed | calibrated=True | reason=ok",
                        "- Coverage Guardrail: trigger=cooldown_elapsed | calibrated=True | reason=ok",
                        "- mode: coverage_guardrail",
                        "- updated_at: 2026-04-07 18:00:00",
                        "- 1x2=0.78, handicap=0.75, total_goals=0.21, score=0.12, htft=0.37",
                        "- tickets=6 | unique_matches=3 | max_exposure=3 | avg_exposure=2.00",
                        "- mixed_ratio=50.0% | avg_expected_hit=36.0% | max_expected_hit=45.0%",
                        "- risk_flags: high_expected_hit=2, low_discount=2, high_upset_leg=2",
                        "- factors: pair_quality=0.91, play_reliability=0.88",
                    ]
                ),
                encoding="utf-8",
            )
            text = build_ops_trend_text(report_dir, days=7)
            self.assertIn("20260406", text)
            self.assertIn("20260407", text)
            self.assertIn("[ALERT] breaker_on", text)
            self.assertIn("Threshold Change Table", text)
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def test_build_ops_trend_rows_and_export_csv(self) -> None:
        root = PROJECT_ROOT / "data" / f"tmp_test_ops_report_{uuid4().hex}"
        try:
            report_dir = root / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "ops_daily_summary_20260406.md").write_text(
                "\n".join(
                    [
                        "# V24 Ops Daily Summary",
                        "- Overall: hit 33.0% | expected 40.0% | ev_bias -9.0% | losing_streak 2 | breaker false",
                        "- Bayes: trigger=cooldown_elapsed | calibrated=False | reason=skipped",
                        "- Bucket Tuning: trigger=cooldown_elapsed | calibrated=False | reason=skipped",
                        "- Coverage Guardrail: trigger=cooldown_elapsed | calibrated=False | reason=skipped",
                        "- mode: coverage_guardrail",
                        "- updated_at: 2026-04-06 18:00:00",
                        "- 1x2=0.76, handicap=0.72, total_goals=0.20, score=0.11, htft=0.36",
                        "- tickets=5 | unique_matches=4 | max_exposure=2 | avg_exposure=1.25",
                        "- mixed_ratio=60.0% | avg_expected_hit=22.0% | max_expected_hit=31.0%",
                        "- risk_flags: high_expected_hit=0, low_discount=1, high_upset_leg=0",
                        "- factors: pair_quality=1.03, play_reliability=0.96",
                    ]
                ),
                encoding="utf-8",
            )
            (report_dir / "ops_daily_summary_20260407.md").write_text(
                "\n".join(
                    [
                        "# V24 Ops Daily Summary",
                        "- Overall: hit 40.0% | expected 30.0% | ev_bias +10.0% | losing_streak 0 | breaker true",
                        "- Bayes: trigger=cooldown_elapsed | calibrated=True | reason=ok",
                        "- Bucket Tuning: trigger=cooldown_elapsed | calibrated=True | reason=ok",
                        "- Coverage Guardrail: trigger=cooldown_elapsed | calibrated=True | reason=ok",
                        "- mode: coverage_guardrail",
                        "- updated_at: 2026-04-07 18:00:00",
                        "- 1x2=0.78, handicap=0.75, total_goals=0.21, score=0.12, htft=0.37",
                        "- tickets=6 | unique_matches=3 | max_exposure=3 | avg_exposure=2.00",
                        "- mixed_ratio=50.0% | avg_expected_hit=36.0% | max_expected_hit=45.0%",
                        "- risk_flags: high_expected_hit=2, low_discount=2, high_upset_leg=2",
                        "- factors: pair_quality=0.91, play_reliability=0.88",
                    ]
                ),
                encoding="utf-8",
            )
            rows = build_ops_trend_rows(report_dir, days=7)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].get("date"), "20260406")
            self.assertEqual(rows[1].get("date"), "20260407")
            self.assertAlmostEqual(float(rows[0].get("threshold_1x2") or 0.0), 0.76, places=4)
            self.assertAlmostEqual(float(rows[1].get("threshold_1x2") or 0.0), 0.78, places=4)

            threshold_table = build_threshold_change_table_text(rows)
            self.assertIn("Threshold Change Table", threshold_table)
            self.assertIn("20260407", threshold_table)
            self.assertIn("+0.02", threshold_table)

            csv_path = export_ops_trend_csv(
                report_dir,
                rows=rows,
                days=7,
                now=datetime(2026, 4, 7, 18, 30, 0),
            )
            self.assertIsNotNone(csv_path)
            assert csv_path is not None
            self.assertTrue(csv_path.exists())
            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("date,overall_hit_rate,overall_ev_bias", csv_text)
            self.assertIn("threshold_1x2", csv_text)
            self.assertIn("delta_threshold_1x2", csv_text)

            threshold_csv_path = export_threshold_trend_csv(
                report_dir,
                rows=rows,
                days=7,
                now=datetime(2026, 4, 7, 18, 30, 0),
            )
            self.assertIsNotNone(threshold_csv_path)
            assert threshold_csv_path is not None
            self.assertTrue(threshold_csv_path.exists())
            threshold_csv_text = threshold_csv_path.read_text(encoding="utf-8")
            self.assertIn("date,threshold_mode,threshold_updated_at", threshold_csv_text)
            self.assertIn("delta_threshold_handicap", threshold_csv_text)
            self.assertIn("20260407", threshold_csv_text)
        finally:
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

