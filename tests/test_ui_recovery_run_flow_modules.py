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
    build_result_recovery_strategy_adjustment,
    build_strategy_release_quality_trend,
    build_strategy_release_quality_trend_alerts,
    build_strategy_release_trend_policy_tuning,
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
        self.assertEqual(summary["strategy_adjustment"]["action"], "collect")

    def test_strategy_adjustment_tightens_on_weak_review_summary(self) -> None:
        adjustment = build_result_recovery_strategy_adjustment(
            {
                "settlement_count": 5,
                "plays": {
                    "1X2": {"rate": 0.4, "text": "2/5 (40%)"},
                    "让球": {"rate": 0.4, "text": "2/5 (40%)"},
                    "大小球": {"rate": 0.8, "text": "4/5 (80%)"},
                },
                "high_accuracy_strategy": {"rate": 0.5, "text": "2/4 (50%)"},
            }
        )

        self.assertEqual(adjustment["action"], "tighten")
        self.assertEqual(adjustment["priority"], "high")
        self.assertEqual(adjustment["policy_update"]["active_strategy_min"], 2)
        self.assertFalse(adjustment["policy_update"]["medium_risk_allowed"])
        self.assertTrue(any("1X2" in item for item in adjustment["reasons"]))

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

    def test_strategy_release_quality_trend_tracks_feedback_and_release_hit_rate(self) -> None:
        records = [
            {
                "run_id": "1",
                "status": "success",
                "started_at": "2026-05-08 20:00:00",
                "new_settled": 1,
                "strategy_release_loop_hit_rate_text": "50.0%",
                "strategy_release_loop_pending_count": 4,
                "strategy_release_loop_missing_snapshot_count": 1,
                "strategy_release_loop_stale_pending_count": 1,
                "live_feedback_validation": {
                    "status": "waiting",
                    "summary_text": "本轮暂无新增结算，高准策略实盘反馈等待后续赛果",
                    "pending_reduced": 0,
                    "feedback_known_delta": 0,
                    "hit_delta": 0,
                },
            },
            {"run_id": "failed", "status": "failed", "started_at": "2026-05-08 21:00:00", "new_settled": 0},
            {
                "run_id": "2",
                "status": "success",
                "started_at": "2026-05-09 20:00:00",
                "new_settled": 2,
                "strategy_release_loop_hit_rate_text": "60.0%",
                "strategy_release_loop_pending_count": 2,
                "strategy_release_loop_missing_snapshot_count": 0,
                "strategy_release_loop_stale_pending_count": 0,
                "live_feedback_validation": {
                    "status": "verified",
                    "summary_text": "已验证 | 待反馈减少 1 | 实盘样本 +2 | 命中 +1",
                    "pending_reduced": 1,
                    "feedback_known_delta": 2,
                    "hit_delta": 1,
                    "paused_delta": -1,
                    "recovering_delta": 0,
                },
            },
            {
                "run_id": "3",
                "status": "success",
                "started_at": "2026-05-10 20:00:00",
                "new_settled": 3,
                "strategy_release_loop_hit_rate_text": "70.0%",
                "strategy_release_loop_pending_count": 1,
                "strategy_release_loop_missing_snapshot_count": 0,
                "strategy_release_loop_stale_pending_count": 0,
                "live_feedback_validation": {
                    "status": "verified",
                    "summary_text": "已验证 | 待反馈减少 2 | 实盘样本 +3 | 命中 +2",
                    "pending_reduced": 2,
                    "feedback_known_delta": 3,
                    "hit_delta": 2,
                    "paused_delta": 0,
                    "recovering_delta": 1,
                },
            },
        ]

        trend = build_strategy_release_quality_trend(records)

        self.assertEqual(trend["status"], "improving")
        self.assertEqual(trend["sample_count"], 3)
        self.assertEqual(trend["total_new_settled"], 6)
        self.assertEqual(trend["avg_release_hit_rate_text"], "60.0%")
        self.assertEqual(trend["latest_release_hit_rate_text"], "70.0%")
        self.assertEqual(trend["release_hit_rate_delta_text"], "20.0%")
        self.assertEqual(trend["verified_count"], 2)
        self.assertEqual(trend["total_pending_reduced"], 3)
        self.assertEqual(trend["total_feedback_known_delta"], 5)
        self.assertEqual(trend["total_hit_delta"], 3)
        self.assertEqual(trend["total_paused_delta"], -1)
        self.assertEqual(trend["total_recovering_delta"], 1)
        self.assertIn("趋势改善", trend["summary_text"])
        self.assertIn("2026-05-10", trend["rows"][0]["title"])
        metric_values = {item["label"]: item["value"] for item in trend["metrics"]}
        self.assertEqual(metric_values["趋势状态"], "趋势改善")
        self.assertEqual(metric_values["实盘样本+"], "5")

    def test_strategy_release_quality_trend_alerts_flag_decline_and_backlog(self) -> None:
        trend = {
            "sample_count": 4,
            "release_hit_rate_delta": -0.12,
            "latest_release_hit_rate": 0.48,
            "avg_release_hit_rate": 0.58,
            "no_feedback_count": 2,
            "verified_count": 0,
            "total_new_settled": 5,
            "total_feedback_known_delta": 0,
            "latest_pending_count": 4,
            "latest_missing_snapshot_count": 1,
            "latest_stale_pending_count": 2,
            "total_paused_delta": 1,
        }

        alerts = build_strategy_release_quality_trend_alerts(trend, pending_threshold=3)

        titles = {item["title"] for item in alerts}
        self.assertIn("放行命中趋势走弱", titles)
        self.assertIn("最近放行命中低于观察线", titles)
        self.assertIn("实盘反馈未同步", titles)
        self.assertIn("缺少有效实盘反馈验证", titles)
        self.assertIn("放行赛果回收超期", titles)
        self.assertIn("待回收放行积压", titles)
        self.assertIn("放行快照缺失", titles)
        self.assertIn("暂停策略增加", titles)
        self.assertTrue(any(item["severity"] == "high" for item in alerts))
        self.assertEqual(build_strategy_release_quality_trend_alerts({"sample_count": 0}), [])

    def test_strategy_release_trend_policy_tuning_tightens_from_trend_alerts(self) -> None:
        trend = {
            "sample_count": 4,
            "label": "放行命中走弱",
            "release_hit_rate_delta": -0.12,
            "latest_release_hit_rate": 0.48,
            "latest_release_hit_rate_text": "48.0%",
            "avg_release_hit_rate": 0.58,
            "avg_release_hit_rate_text": "58.0%",
            "no_feedback_count": 2,
            "verified_count": 0,
            "total_new_settled": 5,
            "total_feedback_known_delta": 0,
            "latest_pending_count": 4,
            "latest_missing_snapshot_count": 1,
            "latest_stale_pending_count": 2,
            "total_paused_delta": 1,
        }
        alerts = build_strategy_release_quality_trend_alerts(trend, pending_threshold=3)

        tuning = build_strategy_release_trend_policy_tuning(
            trend,
            alerts,
            base_min_confidence=0.58,
            base_active_strategy_min=1,
            base_medium_risk_allowed=True,
        )

        self.assertEqual(tuning["action"], "tighten")
        self.assertEqual(tuning["priority"], "high")
        self.assertEqual(tuning["policy_update"]["min_confidence"], 0.70)
        self.assertEqual(tuning["policy_update"]["active_strategy_min"], 2)
        self.assertFalse(tuning["policy_update"]["medium_risk_allowed"])
        self.assertTrue(any("放行命中趋势走弱" in reason for reason in tuning["reasons"]))
        self.assertTrue(any("断路器压力" in reason for reason in tuning["reasons"]))

        hold = build_strategy_release_trend_policy_tuning(
            {"sample_count": 3, "label": "反馈稳定"},
            [],
            base_min_confidence=0.58,
        )
        self.assertEqual(hold["action"], "hold")
        self.assertEqual(hold["policy_update"], {})

        collect = build_strategy_release_trend_policy_tuning({"sample_count": 1}, alerts)
        self.assertEqual(collect["action"], "collect")
        self.assertEqual(collect["policy_update"], {})

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
                    "strategy_adjustment": {
                        "label": "建议收紧",
                        "reasons": ["1X2 命中偏低"],
                    },
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
                "strategy_release_loop_report": "E:\\APP\\ELO\\reports\\strategy_release_recovery_loop_20260509_200002.md",
                "strategy_release_loop_summary": "\u653e\u884c 4 | \u5df2\u56de\u6536 3 | \u5f85\u56de\u6536 1 | \u7f3a\u5feb\u7167 0 | \u8d85\u671f 1 | \u547d\u4e2d 66.7%",
                "strategy_release_loop_health": "\u9700\u8865\u56de\u6536",
                "strategy_release_loop_pending_count": 1,
                "strategy_release_loop_stale_pending_count": 1,
                "strategy_release_loop_missing_snapshot_count": 0,
                "strategy_release_loop_hit_rate_text": "66.7%",
                "live_feedback_validation": {
                    "status": "verified",
                    "summary_text": "\u5df2\u9a8c\u8bc1 | \u5f85\u53cd\u9988\u51cf\u5c11 2 | \u5b9e\u76d8\u6837\u672c +3 | \u547d\u4e2d +2",
                    "rows": [
                        {"title": "\u5f85\u53cd\u9988\u53d8\u5316", "body": "3 -> 1 | \u51cf\u5c11 2 | \u51c0\u53d8\u5316 -2"},
                        {"title": "\u5b9e\u76d8\u6837\u672c\u53d8\u5316", "body": "\u6837\u672c 5 -> 8 (+3) | \u547d\u4e2d 4 -> 6 (+2)"},
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
        self.assertIn("实盘反馈", rows[0]["body"])
        self.assertIn("待反馈减少 2", rows[0]["body"])

        detail = build_result_recovery_run_detail(records[0])
        self.assertIn("运行 ID: run-1", detail)
        self.assertIn("新增结算: 3", detail)
        self.assertIn("可自动回查: 2", detail)
        self.assertIn("缺 source_id: 1", detail)
        self.assertIn("state_not_finished=1", detail)
        self.assertIn("titan_1", detail)
        self.assertIn("1X2 2/3", detail)
        self.assertIn("Alpha FC", detail)
        self.assertIn("建议收紧", detail)
        self.assertIn("strategy_release_recovery_loop_20260509_200002.md", detail)
        self.assertIn("66.7%", detail)
        self.assertIn("\u653e\u884c 4", detail)
        self.assertIn("实盘反馈验证", detail)
        self.assertIn("已验证", detail)
        self.assertIn("实盘样本变化", detail)
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
