from __future__ import annotations

import sys
import unittest
from dataclasses import asdict
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
    def _match(self, home: str, source: str = "live:titan") -> AppMatch:
        return AppMatch(
            home_team=home,
            away_team="Bravo FC",
            league="Friendly League",
            match_time="19:35",
            match_date="2026-05-10",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.2,
            source=source,
        )

    def _cache_diagnostics(self, *, fresh: bool = True) -> FetchDiagnostics:
        diagnostics = FetchDiagnostics(source="cache")
        diagnostics.cache_exists = True
        diagnostics.cache_fresh = fresh
        diagnostics.cache_date = "2026-05-10" if fresh else "2026-05-08"
        diagnostics.cache_match_count = 1
        diagnostics.cache_age_days = 0 if fresh else 2
        return diagnostics

    def test_fetch_matches_exposes_per_source_reports(self) -> None:
        match = self._match("Alpha FC")

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

    def test_force_live_bypasses_fresh_cache(self) -> None:
        cached_match = self._match("Cached FC", source="cache")
        live_match = self._match("Live FC")
        payload = {"date": "2026-05-10", "matches": [asdict(cached_match)]}

        with (
            patch("v24_app.core.load_cached_payload", return_value=(payload, self._cache_diagnostics(fresh=True))),
            patch("v24_app.core.MatchFetcherTitan", side_effect=lambda debug=False: _Fetcher([live_match])),
            patch("v24_app.core.MatchFetcher500", side_effect=lambda debug=False: _Fetcher([])),
            patch("v24_app.core.enrich_matches_from_market_snapshot_store", return_value=0),
            patch("v24_app.core._enrich_matches_with_market_intent", return_value=None),
            patch("v24_app.core._persist_market_snapshots_with_diagnostics", return_value=None),
        ):
            result = core.fetch_matches_v24(strict_today=True, force_live=True)

        self.assertEqual(result.diagnostics.source, "live:titan")
        self.assertEqual(result.matches[0].home_team, "Live FC")
        self.assertTrue(result.diagnostics.cache_fresh)
        self.assertTrue(any("手动重试在线源" in item for item in result.diagnostics.messages))

    def test_force_live_falls_back_to_fresh_cache_when_online_sources_empty(self) -> None:
        cached_match = self._match("Cached FC", source="cache")
        payload = {"date": "2026-05-10", "matches": [asdict(cached_match)]}

        with (
            patch("v24_app.core.load_cached_payload", return_value=(payload, self._cache_diagnostics(fresh=True))),
            patch("v24_app.core.MatchFetcherTitan", side_effect=lambda debug=False: _Fetcher([])),
            patch("v24_app.core.MatchFetcher500", side_effect=lambda debug=False: _Fetcher([])),
            patch("v24_app.core.enrich_matches_from_market_snapshot_store", return_value=0),
            patch("v24_app.core._enrich_matches_with_market_intent", return_value=None),
            patch("v24_app.core._persist_market_snapshots_with_diagnostics", return_value=None),
        ):
            result = core.fetch_matches_v24(strict_today=True, force_live=True)

        self.assertEqual(result.diagnostics.source, "cache")
        self.assertEqual(result.matches[0].home_team, "Cached FC")
        reports = {str(item.get("source")): item for item in result.diagnostics.source_reports}
        self.assertEqual(reports["titan"]["status"], "empty")
        self.assertEqual(reports["500"]["status"], "empty")


if __name__ == "__main__":
    unittest.main()
