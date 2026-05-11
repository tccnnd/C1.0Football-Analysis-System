from __future__ import annotations

import sys
import tempfile
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
from v24_app.core import AppMatch


def _match(league: str = "Friendly") -> AppMatch:
    return AppMatch(
        home_team="A",
        away_team="B",
        league=league,
        match_time="19:35",
        match_date="2026-05-11",
        odds_home=2.0,
        odds_draw=3.2,
        odds_away=3.6,
    )


def _reset_ratings_cache() -> None:
    for pool in ("club", "national_team"):
        core._RATINGS_CACHE[pool] = {"signature": None, "ratings": {}}


class CoreRatingsCacheTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_ratings_cache()

    def test_match_ratings_reuse_memory_cache_and_return_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = core.StateStore(Path(tmp))
            store.save_ratings({"A": 1500.0})

            with patch("v24_app.core.STATE_STORE", store):
                _reset_ratings_cache()
                with patch.object(store, "load_ratings", wraps=store.load_ratings) as load_spy:
                    first = core._load_match_ratings(_match())
                    first["A"] = 900.0
                    second = core._load_match_ratings(_match())

        self.assertEqual(load_spy.call_count, 1)
        self.assertEqual(second["A"], 1500.0)

    def test_match_ratings_cache_reloads_when_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = core.StateStore(Path(tmp))
            store.save_ratings({"A": 1500.0})

            with patch("v24_app.core.STATE_STORE", store):
                _reset_ratings_cache()
                self.assertEqual(core._load_match_ratings(_match())["A"], 1500.0)
                store.save_ratings({"A": 1510.0})
                with patch.object(store, "load_ratings", wraps=store.load_ratings) as load_spy:
                    updated = core._load_match_ratings(_match())

        self.assertEqual(load_spy.call_count, 1)
        self.assertEqual(updated["A"], 1510.0)

    def test_save_match_ratings_refreshes_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = core.StateStore(Path(tmp))
            store.save_ratings({"A": 1500.0})

            with patch("v24_app.core.STATE_STORE", store):
                _reset_ratings_cache()
                core._save_match_ratings(_match(), {"A": 1520.0})
                with patch.object(store, "load_ratings", side_effect=AssertionError("should use refreshed ratings cache")):
                    ratings = core._load_match_ratings(_match())

        self.assertEqual(ratings["A"], 1520.0)


if __name__ == "__main__":
    unittest.main()
