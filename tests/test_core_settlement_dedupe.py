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
from v24_app.core import AppMatch


class _Store:
    def __init__(self, existing: dict) -> None:
        self.existing = existing
        self.appended: list[dict] = []
        self.popped: list[str] = []

    def load_settlements(self) -> list[dict]:
        return [dict(self.existing)]

    def append_settlement(self, record: dict, limit: int = 500) -> None:
        self.appended.append(record)

    def pop_prediction_snapshot(self, match_id: str) -> dict | None:
        self.popped.append(match_id)
        return {}


class CoreSettlementDedupeTests(unittest.TestCase):
    def test_settle_match_result_skips_existing_match_id(self) -> None:
        match = AppMatch(
            home_team="Alpha FC",
            away_team="Bravo FC",
            league="Friendly League",
            match_time="19:35",
            match_date="2026-05-10",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.2,
        )
        existing = {"match_id": match.match_id, "result": "HOME_WIN", "is_correct": True}
        store = _Store(existing)

        with (
            patch("v24_app.core.STATE_STORE", store),
            patch("v24_app.core.auto_settle_pending_parlays", return_value={"new_settled": 0}) as parlay_mock,
            patch("v24_app.core.enrich_match_from_market_snapshot_store") as enrich_mock,
        ):
            result = core.settle_match_result(match, 1, 0, prediction={"recommendation": "HOME_WIN"})

        self.assertTrue(result["duplicate_skipped"])
        self.assertEqual(result["match_id"], match.match_id)
        self.assertEqual(store.appended, [])
        self.assertEqual(store.popped, [match.match_id])
        self.assertTrue(parlay_mock.called)
        self.assertFalse(enrich_mock.called)


if __name__ == "__main__":
    unittest.main()
