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

from v24_app.data_sources.match_fetcher_500 import Match500, MatchFetcher500


class MatchFetcher500WindowTests(unittest.TestCase):
    def test_issue_window_definition(self) -> None:
        fetcher = MatchFetcher500(debug=False)
        start, end = fetcher._current_issue_window(datetime(2026, 4, 7, 12, 0, 0))
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2026-04-07 11:00")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2026-04-08 11:00")

    def test_parse_match_datetime(self) -> None:
        fetcher = MatchFetcher500(debug=False)
        match = Match500(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="01:00",
            match_date="2026-04-08",
        )
        dt = fetcher._parse_match_datetime(match)
        self.assertIsNotNone(dt)
        self.assertEqual(dt.strftime("%Y-%m-%d %H:%M"), "2026-04-08 01:00")


if __name__ == "__main__":
    unittest.main()

