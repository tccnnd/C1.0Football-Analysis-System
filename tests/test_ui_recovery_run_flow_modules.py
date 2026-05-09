from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    build_result_recovery_quality_alerts,
    build_result_recovery_review_summary,
    build_result_recovery_run_detail,
    build_result_recovery_run_rows,
    build_result_recovery_run_summary,
    mark_stale_result_recovery_runs,
)


class UIRecoveryRunFlowModuleTests(unittest.TestCase):
    def test_review_summary_tracks_play_and_strategy_results(self) -> None:
        summary = build_result_recovery_review_summary(
            [
                {
                    "match_id": "a",
                    "match_date": "2026-05-09",
                    "league": "Friendly League",
                    "home_team": "Alpha FC",
                    "away_team": "Bravo FC",
                    "predicted": "主胜",
                    "result": "主胜",
                    "prediction_confidence": 0.72,
                    "is_correct": True,
                    "handicap_is_correct": True,
                    "ou_is_correct": False,
                    "high_accuracy_strategy_active_count": 2,
                    "high_accuracy_strategy_hit_count": 2,
                    "strategy_allowlist_decision": "allow",
                },
                {
                    "match_id": "b",
                    "match_date": "2026-05-09",
                    "league": "Friendly League",
                    "home_team": "Charlie FC",
                    "away_team": "Delta FC",
                    "predicted": "客胜",
                    "result": "平局",
                    "prediction_confidence": 0.81,
                    "is_correct": False,
                    "handicap_is_correct": False,
                    "ou_is_correct": True,
                    "high_accuracy_strategy_active_count": 1,
                    "high_accuracy_strategy_hit_count": 0,
                },
            ]
        )

        self.assertEqual(summary["settlement_count"], 2)
        self.assertEqual(summary["plays"]["1X2"]["text"], "1/2 (50%)")
        self.assertEqual(summary["high_accuracy_strategy"]["text"], "2/3 (67%)")
        self.assertIn("Charlie FC", summary["top_misses"][0]["home_team"])

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
                "snapshot_recoverable": 2,
                "snapshot_missing_source_id": 1,
                "snapshot_checked": 4,
                "snapshot_result_hits": 3,
                "snapshot_result_misses": 1,
                "snapshot_result_miss_reasons": {"state_not_finished": 1},
                "snapshot_result_miss_items": [
                    {
                        "match_date": "2026-05-09",
                        "league": "Friendly League",
                        "home_team": "Alpha FC",
                        "away_team": "Bravo FC",
                        "schedule_id": "titan_1",
                        "reason": "state_not_finished",
                        "state_code": "1",
                        "home_goals": 0,
                        "away_goals": 0,
                    }
                ],
                "review_summary": {
                    "settlement_count": 3,
                    "summary_lines": ["本轮新增结算 3 场", "1X2 2/3 (67%)"],
                    "top_misses": [
                        {
                            "match_date": "2026-05-09",
                            "league": "Friendly League",
                            "home_team": "Alpha FC",
                            "away_team": "Bravo FC",
                            "predicted": "主胜",
                            "result": "平局",
                            "confidence": 0.71,
                        }
                    ],
                },
                "messages": ["done"],
            }
        ]
        rows = build_result_recovery_run_rows(records)
        self.assertEqual(len(rows), 1)
        self.assertIn("成功", rows[0]["title"])
        self.assertIn("新增结算 3", rows[0]["title"])
        self.assertIn("完场: 6", rows[0]["body"])
        self.assertIn("本轮新增结算", rows[0]["body"])

        detail = build_result_recovery_run_detail(records[0])
        self.assertIn("运行 ID: run-1", detail)
        self.assertIn("新增结算: 3", detail)
        self.assertIn("可自动回查: 2", detail)
        self.assertIn("缺 source_id: 1", detail)
        self.assertIn("state_not_finished=1", detail)
        self.assertIn("titan_1", detail)
        self.assertIn("1X2 2/3", detail)
        self.assertIn("Alpha FC", detail)
        self.assertIn("- done", detail)

    def test_quality_alerts_detect_failures_no_settlement_and_slow_runs(self) -> None:
        failure_alerts = build_result_recovery_quality_alerts(
            [
                {"run_id": "1", "status": "success", "new_settled": 1, "elapsed_seconds": 2.0},
                {"run_id": "2", "status": "failed", "error": "source timeout", "elapsed_seconds": 1.0},
                {"run_id": "3", "status": "failed", "error": "source timeout", "elapsed_seconds": 1.0},
            ]
        )
        self.assertEqual(failure_alerts[0]["severity"], "high")
        self.assertIn("连续回收失败", failure_alerts[0]["title"])

        no_settlement_alerts = build_result_recovery_quality_alerts(
            [
                {"run_id": "1", "status": "success", "new_settled": 0, "fetched_finished": 2, "elapsed_seconds": 1.0},
                {"run_id": "2", "status": "success", "new_settled": 0, "fetched_finished": 3, "elapsed_seconds": 1.0},
                {"run_id": "3", "status": "success", "new_settled": 0, "fetched_finished": 4, "elapsed_seconds": 1.0},
            ]
        )
        self.assertTrue(any("无新结算" in item["title"] for item in no_settlement_alerts))

        slow_alerts = build_result_recovery_quality_alerts(
            [
                {"run_id": "1", "status": "success", "new_settled": 1, "elapsed_seconds": 3.0},
                {"run_id": "2", "status": "success", "new_settled": 1, "elapsed_seconds": 4.0},
                {"run_id": "3", "status": "success", "new_settled": 1, "elapsed_seconds": 5.0},
                {"run_id": "4", "status": "success", "new_settled": 1, "elapsed_seconds": 20.0},
            ]
        )
        self.assertTrue(any("耗时异常" in item["title"] for item in slow_alerts))

    def test_mark_stale_running_records_as_interrupted(self) -> None:
        result = mark_stale_result_recovery_runs(
            [
                {
                    "run_id": "old-running",
                    "status": "running",
                    "started_at": "2026-05-09 18:00:00",
                },
                {
                    "run_id": "fresh-running",
                    "status": "running",
                    "started_at": "2026-05-09 19:45:00",
                },
            ],
            now=datetime(2026, 5, 9, 20, 0, 0),
            stale_after_minutes=60,
        )
        items = result["items"]
        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(items[0]["status"], "interrupted")
        self.assertIn("未正常完成", items[0]["error"])
        self.assertEqual(items[1]["status"], "running")

        alerts = build_result_recovery_quality_alerts(items)
        self.assertTrue(any("中断" in item["title"] for item in alerts))


if __name__ == "__main__":
    unittest.main()
