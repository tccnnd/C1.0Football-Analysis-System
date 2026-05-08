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

from v24_app.data_sources.match_fetcher_titan import MatchFetcherTitan, MatchTitan


class MatchFetcherTitanTests(unittest.TestCase):
    def _match(self, *, date: str, time: str, issue: str, sid: str) -> MatchTitan:
        return MatchTitan(
            home_team=f"H{sid}",
            away_team=f"A{sid}",
            league="L1",
            match_time=time,
            match_date=date,
            odds_home=2.1,
            odds_draw=3.2,
            odds_away=3.4,
            match_id=sid,
            issue_code=issue,
            state_code="0",
        )

    def test_get_today_matches_uses_issue_window_after_11(self) -> None:
        fetcher = MatchFetcherTitan(debug=False)
        sample = [
            self._match(date="2026-04-07", time="17:00", issue="周二001", sid="1"),
            self._match(date="2026-04-08", time="01:00", issue="周二002", sid="2"),
            self._match(date="2026-04-08", time="10:30", issue="周二003", sid="3"),
            self._match(date="2026-04-08", time="12:00", issue="周三001", sid="4"),
        ]
        fetcher._load_current_matches = lambda: sample  # type: ignore[method-assign]
        rows = fetcher.get_today_matches(now=datetime(2026, 4, 7, 12, 46, 0))
        ids = {item.match_id for item in rows}
        self.assertIn("1", ids)
        self.assertIn("2", ids)
        self.assertIn("3", ids)
        self.assertNotIn("4", ids)

    def test_get_today_matches_uses_previous_issue_window_before_11(self) -> None:
        fetcher = MatchFetcherTitan(debug=False)
        sample = [
            self._match(date="2026-04-06", time="23:00", issue="周一010", sid="10"),
            self._match(date="2026-04-07", time="01:00", issue="周一011", sid="11"),
            self._match(date="2026-04-07", time="10:30", issue="周一012", sid="12"),
            self._match(date="2026-04-07", time="12:00", issue="周二001", sid="13"),
        ]
        fetcher._load_current_matches = lambda: sample  # type: ignore[method-assign]
        rows = fetcher.get_today_matches(now=datetime(2026, 4, 7, 9, 0, 0))
        ids = {item.match_id for item in rows}
        self.assertIn("10", ids)
        self.assertIn("11", ids)
        self.assertIn("12", ids)
        self.assertNotIn("13", ids)


if __name__ == "__main__":
    unittest.main()

