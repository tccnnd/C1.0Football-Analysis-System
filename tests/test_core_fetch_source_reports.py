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

from v24_app import core
from v24_app.core import AppMatch, FetchDiagnostics


class _Fetcher:
    def __init__(self, matches: list[AppMatch]) -> None:
        self._matches = matches

    def get_today_matches(self) -> list[AppMatch]:
        return list(self._matches)


class CoreFetchSourceReportsTests(unittest.TestCase):
    def test_fetch_matches_exposes_per_source_reports(self) -> None:
        match = AppMatch(
            home_team="Alpha FC",
            away_team="Bravo FC",
            league="Friendly League",
            match_time="19:35",
            match_date="2026-05-10",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.2,
            source="live:titan",
        )

        with (
            patch("v24_app.core.load_cached_payload", return_value=(None, FetchDiagnostics(source="cache"))),
            patch("v24_app.core.MatchFetcherTitan", side_effect=lambda debug=False: _Fetcher([match])),
            patch("v24_app.core.MatchFetcher500", side_effect=lambda debug=False: _Fetcher([])),
            patch("v24_app.core.enrich_matches_from_market_snapshot_store", return_value=0),
            patch("v24_app.core._enrich_matches_with_market_intent", return_value=None),
            patch("v24_app.core._persist_market_snapshots_with_diagnostics", return_value=None),
        ):
            result = core.fetch_matches_v24(strict_today=True)

        self.assertEqual(len(result.matches), 1)
        self.assertEqual(result.diagnostics.source, "live:titan")
        reports = {str(item.get("source")): item for item in result.diagnostics.source_reports}
        self.assertEqual(reports["titan"]["status"], "ready")
        self.assertEqual(reports["titan"]["valid_count"], 1)
        self.assertEqual(reports["500"]["status"], "empty")
        self.assertEqual(reports["500"]["valid_count"], 0)


if __name__ == "__main__":
    unittest.main()
