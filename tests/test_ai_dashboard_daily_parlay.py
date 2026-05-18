from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ai_dashboard import DashboardRow, SmartMatchDashboard
from v24_app.core import AppMatch


class AIDashboardDailyParlayTests(unittest.TestCase):
    def _match(self, home: str, away: str) -> AppMatch:
        return AppMatch(
            home_team=home,
            away_team=away,
            league="L1",
            match_time="20:00",
            match_date="2026-05-18",
            odds_home=2.1,
            odds_draw=3.2,
            odds_away=3.4,
        )

    def test_daily_parlay_snapshot_refreshes_from_current_rows(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard._log_event = lambda *args, **kwargs: None
        first = self._match("A", "B")
        second = self._match("C", "D")
        dashboard.rows = [
            DashboardRow(first, {"parlay_eligible_plays": [{"play_type": "1x2", "pick": "home", "confidence": 0.72}]}),
            DashboardRow(second, {"parlay_eligible_plays": [{"play_type": "total_goals", "pick": "over", "confidence": 0.70}]}),
        ]
        active = [
            {
                "ticket_id": "ticket-1",
                "status": "pending",
                "expected_hit": 0.35,
                "mixed": True,
                "legs": [{"match_id": first.match_id}, {"match_id": second.match_id}],
            }
        ]

        with patch("v24_app.ai_dashboard.refresh_parlay_recommendations", return_value=active) as refresh, patch(
            "v24_app.ai_dashboard.get_recent_parlay_settlements",
            return_value=[{"ticket_id": "settled", "status": "won", "is_hit": True}],
        ), patch(
            "v24_app.ai_dashboard.get_parlay_selector_metrics",
            return_value={"ticket_count": 1, "unique_match_count": 2},
        ):
            snapshot = dashboard._daily_parlay_snapshot()

        refresh.assert_called_once()
        self.assertTrue(snapshot["refreshed_from_current"])
        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["summary"]["settled_count"], 1)
        self.assertEqual(snapshot["ticket_rows"][0]["ticket_id"], "ticket-1")

    def test_daily_parlay_snapshot_falls_back_to_saved_active_tickets(self) -> None:
        dashboard = object.__new__(SmartMatchDashboard)
        dashboard._log_event = lambda *args, **kwargs: None
        dashboard.rows = []
        active = [{"ticket_id": "saved", "status": "pending", "expected_hit": 0.31, "legs": []}]

        with patch("v24_app.ai_dashboard.refresh_parlay_recommendations") as refresh, patch(
            "v24_app.ai_dashboard.get_active_parlay_recommendations",
            return_value=active,
        ) as load_active, patch(
            "v24_app.ai_dashboard.get_recent_parlay_settlements",
            return_value=[],
        ), patch(
            "v24_app.ai_dashboard.get_parlay_selector_metrics",
            return_value={"ticket_count": 1},
        ):
            snapshot = dashboard._daily_parlay_snapshot()

        refresh.assert_not_called()
        load_active.assert_called_once()
        self.assertFalse(snapshot["refreshed_from_current"])
        self.assertEqual(snapshot["summary"]["active_count"], 1)
        self.assertEqual(snapshot["ticket_rows"][0]["ticket_id"], "saved")


if __name__ == "__main__":
    unittest.main()
