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


class CoreMarketEntropyTests(unittest.TestCase):
    def test_market_entropy_flags_odds_slope_and_kelly_conflict(self) -> None:
        match = core.AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="20:00",
            match_date="2026-05-10",
            odds_home=2.05,
            odds_draw=3.25,
            odds_away=3.90,
            opening_odds_home=1.90,
            opening_odds_draw=3.30,
            opening_odds_away=4.50,
            return_rate=0.93,
            kelly_home=0.96,
            kelly_draw=0.90,
            kelly_away=0.88,
        )

        entropy = core.build_market_entropy_signal(
            match,
            recommendation_key="home",
            recommendation_confidence=0.68,
            history_points=[
                {
                    "saved_at": "2026-05-10 19:45:00",
                    "market": {"odds_home": 1.90, "odds_draw": 3.30, "odds_away": 4.50},
                },
                {
                    "saved_at": "2026-05-10 19:55:00",
                    "market": {"odds_home": 2.02, "odds_draw": 3.25, "odds_away": 4.02},
                },
            ],
        )

        self.assertEqual(entropy["level"], "HIGH")
        self.assertGreaterEqual(entropy["score"], 0.66)
        self.assertIn("pick_odds_drifting_out", entropy["signals"])
        self.assertIn("market_steam_against_pick", entropy["signals"])
        self.assertIn("kelly_against_pick", entropy["signals"])
        self.assertIn("odds_history_step_alert", entropy["signals"])
        self.assertGreaterEqual(entropy["sequence"]["sample_count"], 3)
        self.assertGreater(abs(entropy["sequence"]["max_step_change"]), 0.07)
        self.assertLess(entropy["pick_slope"], 0)
        self.assertGreater(entropy["pick_kelly_gap"], 0)

        overlay = core._market_entropy_risk_overlay("LOW", entropy)
        self.assertTrue(overlay["applied"])
        self.assertEqual(overlay["adjusted_risk_level"], "HIGH")

    def test_market_entropy_keeps_calm_market_low(self) -> None:
        match = core.AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="20:00",
            match_date="2026-05-10",
            odds_home=1.88,
            odds_draw=3.31,
            odds_away=4.45,
            opening_odds_home=1.90,
            opening_odds_draw=3.30,
            opening_odds_away=4.50,
            return_rate=0.93,
            kelly_home=0.92,
            kelly_draw=0.93,
            kelly_away=0.91,
        )

        entropy = core.build_market_entropy_signal(
            match,
            recommendation_key="home",
            recommendation_confidence=0.68,
        )

        self.assertEqual(entropy["level"], "LOW")
        self.assertLess(entropy["score"], 0.38)
        self.assertEqual(entropy["signals"], [])

    def test_market_snapshot_history_accumulates_current_odds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = core.StateStore(Path(tmp))
            match = core.AppMatch(
                home_team="A",
                away_team="B",
                league="L1",
                match_time="20:00",
                match_date="2026-05-10",
                odds_home=1.90,
                odds_draw=3.30,
                odds_away=4.50,
                opening_odds_home=1.90,
                opening_odds_draw=3.30,
                opening_odds_away=4.50,
                kelly_home=0.92,
                kelly_draw=0.93,
                kelly_away=0.91,
            )
            key = f"unit|market_entropy|{id(self)}"
            first = {
                "saved_at": "2026-05-10 19:30:00",
                "match": {"match_id": match.match_id},
                "market": core._market_snapshot_fields_from_match(match),
            }
            second_match = core.AppMatch(
                home_team="A",
                away_team="B",
                league="L1",
                match_time="20:00",
                match_date="2026-05-10",
                odds_home=1.82,
                odds_draw=3.34,
                odds_away=4.80,
            )
            second = {
                "saved_at": "2026-05-10 19:50:00",
                "match": {"match_id": match.match_id},
                "market": core._market_snapshot_fields_from_match(second_match),
            }
            store.upsert_market_snapshot(key, first)
            store.upsert_market_snapshot(key, second)
            items = store.load_market_snapshots()
            history = items[key].get("history", [])
            self.assertGreaterEqual(len(history), 2)
            self.assertEqual(history[-1]["market"]["odds_home"], 1.82)

    def test_recent_settlements_enrich_market_entropy_from_analysis_history(self) -> None:
        class FakeStore:
            def load_settlements(self) -> list[dict]:
                return [{"match_id": "m1", "is_correct": False}]

            def load_analysis_history(self) -> dict[str, dict]:
                return {
                    "m1": {
                        "prediction": {
                            "market_entropy": {
                                "level": "HIGH",
                                "score": 0.84,
                                "signals": ["kelly_against_pick"],
                                "sequence": {"sample_count": 3, "max_step_change": 0.08, "max_abs_velocity_per_minute": 0.006},
                                "kelly_span": 0.08,
                                "pick_kelly_gap": 0.07,
                            },
                            "market_entropy_risk": {"applied": True, "reason": "market_entropy_high"},
                            "supervisor": {"status": "alert", "next_actions": ["manual_market_review"]},
                        }
                    }
                }

        with patch.object(core, "STATE_STORE", FakeStore()):
            settlements = core.get_recent_settlements(limit=10)

        self.assertEqual(settlements[0]["market_entropy_level"], "HIGH")
        self.assertEqual(settlements[0]["market_entropy_score"], 0.84)
        self.assertEqual(settlements[0]["market_entropy_signals"], ["kelly_against_pick"])
        self.assertTrue(settlements[0]["market_entropy_risk_applied"])
        self.assertEqual(settlements[0]["supervisor_status"], "alert")


if __name__ == "__main__":
    unittest.main()
