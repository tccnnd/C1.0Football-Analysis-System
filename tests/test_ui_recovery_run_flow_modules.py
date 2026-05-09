from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    build_result_recovery_run_detail,
    build_result_recovery_run_rows,
    build_result_recovery_run_summary,
)


class UIRecoveryRunFlowModuleTests(unittest.TestCase):
    def test_summary_tracks_recent_success_and_elapsed(self) -> None:
        records = [
            {"run_id": "1", "status": "success", "elapsed_seconds": 2.0, "new_settled": 1, "started_at": "a"},
            {"run_id": "2", "status": "failed", "elapsed_seconds": 4.0, "new_settled": 0, "started_at": "b", "error": "boom"},
            {"run_id": "3", "status": "running", "started_at": "c"},
        ]
        summary = build_result_recovery_run_summary(records)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["success_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(summary["running_count"], 1)
        self.assertEqual(summary["recent_success_rate_text"], "50%")
        self.assertEqual(summary["avg_elapsed_text"], "3.00s")
        self.assertEqual(summary["latest_status_label"], "运行中")

    def test_rows_and_detail_include_recovery_metrics(self) -> None:
        records = [
            {
                "run_id": "run-1",
                "status": "success",
                "started_at": "2026-05-09 20:00:00",
                "finished_at": "2026-05-09 20:00:02",
                "elapsed_seconds": 2.1,
                "source": "live:titan",
                "lookback_days": 2,
                "fetched_finished": 6,
                "restored_snapshots": 1,
                "new_settled": 3,
                "new_parlay_settled": 1,
                "messages": ["done"],
            }
        ]
        rows = build_result_recovery_run_rows(records)
        self.assertEqual(len(rows), 1)
        self.assertIn("成功", rows[0]["title"])
        self.assertIn("新增结算 3", rows[0]["title"])
        self.assertIn("完场: 6", rows[0]["body"])

        detail = build_result_recovery_run_detail(records[0])
        self.assertIn("运行 ID: run-1", detail)
        self.assertIn("新增结算: 3", detail)
        self.assertIn("- done", detail)


if __name__ == "__main__":
    unittest.main()
