from __future__ import annotations

import json
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


def _sample(match_id: str, home_team: str, away_team: str, date: str, home_goals: int, away_goals: int) -> dict:
    return {
        "match_id": match_id,
        "features": {"market_home": 0.4},
        "label": 0,
        "meta": {
            "match_date": date,
            "match_time": "12:00",
            "league": "A",
            "home_team": home_team,
            "away_team": away_team,
            "home_goals": home_goals,
            "away_goals": away_goals,
        },
    }


def _reset_recent_form_memory_cache() -> None:
    core._RECENT_FORM_CACHE["signature"] = None
    core._RECENT_FORM_CACHE["team_histories"] = {}


class CoreRecentFormCacheTests(unittest.TestCase):
    def tearDown(self) -> None:
        _reset_recent_form_memory_cache()

    def test_recent_form_cache_reuses_persistent_histories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = core.StateStore(Path(tmp))
            store.save_xgb_samples([_sample("m1", "A", "B", "2024-01-01", 2, 1)])

            with patch("v24_app.core.STATE_STORE", store):
                _reset_recent_form_memory_cache()
                built = core._recent_form_team_histories()
                cache_path = store.state_dir / "recent_form_team_histories.json"
                cache_exists = cache_path.exists()
                _reset_recent_form_memory_cache()

                with patch.object(store, "load_xgb_samples", side_effect=AssertionError("should use recent form cache")):
                    cached = core._recent_form_team_histories()

        self.assertTrue(cache_exists)
        self.assertEqual(built["A"][0]["goals_for"], 2)
        self.assertEqual(cached["A"][0]["goals_against"], 1)

    def test_recent_form_cache_rebuilds_when_source_signature_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = core.StateStore(Path(tmp))
            store.save_xgb_samples([_sample("m1", "A", "B", "2024-01-01", 2, 1)])

            with patch("v24_app.core.STATE_STORE", store):
                _reset_recent_form_memory_cache()
                core._recent_form_team_histories()

                _reset_recent_form_memory_cache()
                store.save_xgb_samples(
                    [
                        _sample("m1", "A", "B", "2024-01-01", 2, 1),
                        _sample("m2", "C", "D", "2024-01-02", 0, 0),
                    ]
                )

                with patch.object(store, "load_xgb_samples", wraps=store.load_xgb_samples) as load_spy:
                    histories = core._recent_form_team_histories()

                payload = json.loads((store.state_dir / "recent_form_team_histories.json").read_text(encoding="utf-8"))

        self.assertTrue(load_spy.called)
        self.assertIn("C", histories)
        self.assertEqual(payload["team_count"], 4)


if __name__ == "__main__":
    unittest.main()
