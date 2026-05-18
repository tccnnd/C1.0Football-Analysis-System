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
    build_daily_parlay_empty_state,
    build_daily_parlay_settlement_rows,
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


if __name__ == "__main__":
    unittest.main()
