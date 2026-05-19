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
    build_daily_parlay_empty_state,
    build_daily_parlay_export_message,
    build_daily_parlay_export_guard_text,
    build_daily_parlay_report_filename,
    build_daily_parlay_report_lines,
    build_daily_parlay_settlement_rows,
    build_daily_parlay_snapshot,
    build_daily_parlay_snapshot_settlement_closure,
    build_daily_parlay_source_health_card_rows,
    build_daily_parlay_source_health_issue_rows,
    build_daily_parlay_source_health_summary,
    build_daily_parlay_summary,
    build_daily_parlay_ticket_rows,
)


class UIDailyParlayFlowModuleTests(unittest.TestCase):
    def test_builds_summary_and_rows_for_active_tickets(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "created_at": "2026-05-18 09:00:00",
                "status": "pending",
                "mixed": True,
                "expected_hit": 0.36,
                "legs": [
                    {"play_type": "1x2", "home_team": "A", "away_team": "B", "pick": "home"},
                    {"play_type": "total_goals", "home_team": "C", "away_team": "D", "pick": "over"},
                ],
            }
        ]

        summary = build_daily_parlay_summary(active, [])
        rows = build_daily_parlay_ticket_rows(active)

        self.assertEqual(summary["active_count"], 1)
        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["mixed_count"], 1)
        self.assertAlmostEqual(summary["avg_expected_hit"], 0.36)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticket_id"], "ticket-1")
        self.assertEqual(rows[0]["status"], "pending")
        self.assertTrue(rows[0]["mixed"])
        self.assertEqual(rows[0]["expected_hit"], 0.36)
        self.assertIn("title", rows[0])
        self.assertIn("body", rows[0])
        self.assertIn("tone", rows[0])

    def test_builds_summary_and_rows_for_settled_tickets(self) -> None:
        settled = [
            {"ticket_id": "lost-1", "status": "lost", "is_hit": False, "expected_hit": 0.28, "settled_at": "2026-05-17 10:00:00"},
            {"ticket_id": "won-1", "status": "won", "is_hit": True, "expected_hit": 0.31, "settled_at": "2026-05-18 10:00:00"},
        ]

        summary = build_daily_parlay_summary([], settled)
        rows = build_daily_parlay_settlement_rows(settled)

        self.assertEqual(summary["settled_count"], 2)
        self.assertEqual(summary["won_count"], 1)
        self.assertEqual(summary["lost_count"], 1)
        self.assertEqual(summary["hit_rate"], 0.5)
        self.assertEqual([row["ticket_id"] for row in rows], ["won-1", "lost-1"])
        self.assertEqual(rows[0]["tone"], "success")
        self.assertEqual(rows[1]["tone"], "danger")

    def test_empty_state(self) -> None:
        empty_summary = build_daily_parlay_summary([], [])
        settled_summary = build_daily_parlay_summary([], [{"ticket_id": "old", "status": "won"}])
        active_summary = build_daily_parlay_summary([{"ticket_id": "active"}], [])

        self.assertTrue(build_daily_parlay_empty_state(empty_summary))
        self.assertTrue(build_daily_parlay_empty_state(settled_summary))
        self.assertEqual(build_daily_parlay_empty_state(active_summary), "")

    def test_dirty_ticket_data_is_tolerated(self) -> None:
        active = [
            None,
            "bad",
            {"ticket_id": None, "expected_hit": "bad", "legs": "bad", "mixed": "yes"},
            {"legs": [object(), {"match_id": "m-1"}], "expected_hit": None},
        ]
        settled = [
            object(),
            {"ticket_id": "settled", "status": "", "is_hit": "bad", "expected_hit": "nan"},
        ]

        summary = build_daily_parlay_summary(active, settled)
        active_rows = build_daily_parlay_ticket_rows(active)
        settled_rows = build_daily_parlay_settlement_rows(settled)

        self.assertEqual(summary["active_count"], 2)
        self.assertEqual(summary["settled_count"], 1)
        self.assertEqual(len(active_rows), 2)
        self.assertEqual(len(settled_rows), 1)
        self.assertEqual(active_rows[0]["expected_hit"], 0.0)
        self.assertIn(active_rows[0]["status"], {"pending", ""})
        self.assertEqual(settled_rows[0]["expected_hit"], 0.0)

    def test_sorting_and_limit_for_active_and_settled_rows(self) -> None:
        active = [
            {"ticket_id": "same-high", "mixed": False, "expected_hit": 0.80, "rank_score": 0.80},
            {"ticket_id": "mixed-low", "mixed": True, "expected_hit": 0.20, "rank_score": 0.20},
            {"ticket_id": "mixed-high", "mixed": True, "expected_hit": 0.50, "rank_score": 0.50},
        ]
        settled = [
            {"ticket_id": "old", "status": "won", "settled_at": "2026-05-16 10:00:00"},
            {"ticket_id": "new", "status": "lost", "settled_at": "2026-05-18 10:00:00"},
            {"ticket_id": "middle", "status": "won", "settled_at": "2026-05-17 10:00:00"},
        ]

        active_rows = build_daily_parlay_ticket_rows(active, limit=2)
        settled_rows = build_daily_parlay_settlement_rows(settled, limit=2)

        self.assertEqual([row["ticket_id"] for row in active_rows], ["mixed-high", "mixed-low"])
        self.assertEqual([row["ticket_id"] for row in settled_rows], ["new", "middle"])

    def test_report_filename_is_deterministic(self) -> None:
        self.assertEqual(
            build_daily_parlay_report_filename(datetime(2026, 5, 18, 12, 30, 5)),
            "daily_parlay_recommendations_20260518_123005.md",
        )

    def test_source_health_is_healthy_when_legs_are_traceable(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "legs": [
                    {"match_id": "m1", "source": "live:titan", "source_id": "titan-1"},
                    {"match_id": "m2", "source": "live:titan", "source_id": "titan-2"},
                ],
            }
        ]

        health = build_daily_parlay_source_health_summary(active, [])
        cards = build_daily_parlay_source_health_card_rows(health)
        issues = build_daily_parlay_source_health_issue_rows(health)

        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["tone"], "good")
        self.assertEqual(health["issue_count"], 0)
        self.assertEqual(health["metrics"]["source_id_leg_count"], 2)
        self.assertEqual(cards[0]["value"], "healthy")
        self.assertEqual(issues, [])

    def test_source_health_attention_for_missing_source_id_and_mixed_sources(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "legs": [
                    {"match_id": "m1", "source": "live:titan", "source_id": "titan-1"},
                    {"match_id": "m2", "source": "cache"},
                ],
            }
        ]

        health = build_daily_parlay_source_health_summary(active, [])
        issue_codes = {issue["code"] for issue in health["issues"]}
        issue_rows = build_daily_parlay_source_health_issue_rows(health)

        self.assertEqual(health["status"], "attention")
        self.assertEqual(health["tone"], "warning")
        self.assertIn("parlay_source_id_missing", issue_codes)
        self.assertIn("parlay_mixed_sources", issue_codes)
        self.assertEqual(health["metrics"]["mixed_ticket_count"], 1)
        self.assertTrue(any("source_id" in row["message"] for row in issue_rows))

    def test_source_health_blocked_when_no_leg_is_traceable(self) -> None:
        active = [
            {"ticket_id": "ticket-1", "legs": [{"match_id": "m1"}, {"match_id": "m2"}]},
            {"ticket_id": "ticket-2", "legs": []},
        ]

        health = build_daily_parlay_source_health_summary(active, [])
        issue_codes = {issue["code"] for issue in health["issues"]}

        self.assertEqual(health["status"], "blocked")
        self.assertEqual(health["tone"], "bad")
        self.assertIn("parlay_traceability_blocked", issue_codes)
        self.assertIn("parlay_traceability_gap", issue_codes)
        self.assertGreaterEqual(health["metrics"]["missing_traceability_leg_count"], 1)

    def test_export_guard_text_reflects_source_health(self) -> None:
        snapshot = build_daily_parlay_snapshot(
            [{"ticket_id": "ticket-1", "legs": [{"match_id": "m1"}]}],
            [],
            {},
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
        )
        guard_text = build_daily_parlay_export_guard_text(snapshot)

        self.assertIn("来源健康", guard_text)
        self.assertIn("blocked", guard_text)
        self.assertIn("source_id", guard_text)

    def test_snapshot_and_report_lines_include_export_context(self) -> None:
        active = [
            {
                "ticket_id": "ticket-1",
                "created_at": "2026-05-18 09:00:00",
                "status": "pending",
                "mixed": True,
                "expected_hit": 0.36,
                "legs": [
                    {
                        "play_type": "1x2",
                        "home_team": "A",
                        "away_team": "B",
                        "pick": "home",
                        "source": "live:titan",
                        "source_id": "titan-123",
                    },
                    {
                        "play_type": "total_goals",
                        "home_team": "C",
                        "away_team": "D",
                        "pick": "over",
                        "source": "live:titan",
                        "source_id": "titan-123",
                    },
                ],
            }
        ]
        settled = [
            {
                "ticket_id": "won-1",
                "status": "won",
                "is_hit": True,
                "expected_hit": 0.31,
                "legs": [{"source": "live:titan", "source_id": "titan-123"}],
            }
        ]
        metrics = {"ticket_count": 1, "unique_match_count": 2, "mixed_ratio": 1.0, "low_discount_count": 0}

        snapshot = build_daily_parlay_snapshot(
            active,
            settled,
            metrics,
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
            report_path=Path("reports") / "daily.md",
            source="当前分析",
        )
        lines = build_daily_parlay_report_lines(snapshot)
        payload = "\n".join(lines)

        self.assertEqual(snapshot["generated_at"], "2026-05-18 12:30:05")
        self.assertEqual(snapshot["source"], "当前分析")
        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["selector_metrics"]["unique_match_count"], 2)
        self.assertEqual(snapshot["summary"]["source"], "live:titan")
        self.assertEqual(snapshot["summary"]["source_id"], "titan-123")
        self.assertEqual(snapshot["summary"]["source_health_status"], "healthy")
        self.assertEqual(snapshot["source_health"]["status"], "healthy")
        self.assertEqual(snapshot["source_health"]["issue_count"], 0)
        self.assertEqual(snapshot["ticket_rows"][0]["ticket_id"], "ticket-1")
        self.assertEqual(snapshot["ticket_rows"][0]["source"], "live:titan")
        self.assertEqual(snapshot["ticket_rows"][0]["source_id"], "titan-123")
        self.assertEqual(snapshot["settlement_rows"][0]["source"], "live:titan")
        self.assertEqual(snapshot["settlement_rows"][0]["source_id"], "titan-123")
        self.assertIn("# 每日二串一推荐报告", payload)
        self.assertIn("## 来源健康审计", payload)
        self.assertIn("## 来源问题与建议", payload)
        self.assertIn("healthy", payload)
        self.assertIn("## 今日推荐组合", payload)
        self.assertIn("## 近期二串一结算", payload)
        self.assertIn("## 边界", payload)
        self.assertIn("票据来源", payload)
        self.assertIn("ticket-1", payload)
        self.assertIn("won-1", payload)
        self.assertIn("live:titan", payload)
        self.assertIn("titan-123", payload)
        self.assertIn("当前组合: 1", build_daily_parlay_export_message("daily.md", snapshot))

    def test_snapshot_tolerates_dirty_inputs(self) -> None:
        snapshot = build_daily_parlay_snapshot(
            [None, {"ticket_id": object(), "expected_hit": "nan", "legs": "bad"}],
            object(),
            {"ticket_count": object()},
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
        )
        lines = build_daily_parlay_report_lines(snapshot)

        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["summary"]["settled_count"], 0)
        self.assertEqual(len(snapshot["ticket_rows"]), 1)
        self.assertTrue(lines)

    def test_snapshot_settlement_closure_updates_recovery_state(self) -> None:
        snapshot = build_daily_parlay_snapshot(
            [
                {
                    "ticket_id": "ticket-1",
                    "status": "pending",
                    "expected_hit": 0.36,
                    "legs": [
                        {"match_id": "m1", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m2", "source": "live:titan", "source_id": "titan-123"},
                    ],
                },
                {
                    "ticket_id": "ticket-2",
                    "status": "pending",
                    "expected_hit": 0.24,
                    "legs": [
                        {"match_id": "m3", "source": "live:titan", "source_id": "titan-123"},
                        {"match_id": "m4", "source": "live:titan", "source_id": "titan-123"},
                    ],
                },
            ],
            [],
            {},
            generated_at=datetime(2026, 5, 18, 12, 30, 5),
        )
        closure = build_daily_parlay_snapshot_settlement_closure(
            [snapshot],
            [{"ticket_id": "ticket-1", "status": "won", "is_hit": True, "settled_at": "2026-05-18 23:00:00"}],
            generated_at=datetime(2026, 5, 18, 23, 30, 5),
        )

        summary = closure["summary"]
        updated = closure["records"][0]

        self.assertEqual(summary["status"], "partial")
        self.assertEqual(summary["snapshot_count"], 1)
        self.assertEqual(summary["checked_ticket_count"], 2)
        self.assertEqual(summary["settled_ticket_count"], 1)
        self.assertEqual(summary["newly_settled_ticket_count"], 1)
        self.assertTrue(summary["changed"])
        self.assertEqual(updated["parlay_recovery"]["status"], "partial")
        self.assertEqual(updated["parlay_recovery"]["source"], "live:titan")
        self.assertEqual(updated["parlay_recovery"]["source_id"], "titan-123")
        self.assertIn("live:titan", updated["parlay_recovery"]["source_summary_text"])
        self.assertEqual(updated["parlay_recovery"]["matched_ticket_ids"], ["ticket-1"])
        self.assertEqual(updated["parlay_recovery"]["pending_ticket_ids"], ["ticket-2"])

        second_closure = build_daily_parlay_snapshot_settlement_closure(
            closure["records"],
            [{"ticket_id": "ticket-1", "status": "won", "is_hit": True, "settled_at": "2026-05-18 23:00:00"}],
            generated_at=datetime(2026, 5, 19, 0, 0, 0),
        )
        self.assertFalse(second_closure["summary"]["changed"])
        self.assertEqual(second_closure["summary"]["newly_settled_ticket_count"], 0)


if __name__ == "__main__":
    unittest.main()
