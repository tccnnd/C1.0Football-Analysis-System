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


class CoreHandicapMarginConsistencyTests(unittest.TestCase):
    def _match(self, line: float) -> core.AppMatch:
        return core.AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="20:00",
            match_date="2026-05-10",
            odds_home=1.90,
            odds_draw=3.30,
            odds_away=4.50,
            handicap_line=line,
        )

    def test_deep_home_line_with_flat_model_is_high_risk(self) -> None:
        signal = core.build_handicap_margin_consistency_signal(
            self._match(-1.25),
            model_margin_goals=0.10,
            probabilities={"home": 0.42, "draw": 0.30, "away": 0.28},
            handicap_probabilities={"home": 0.28, "draw": 0.22, "away": 0.50},
            recommendation_key="home",
            handicap_pick_key="away",
        )

        self.assertEqual(signal["level"], "HIGH")
        self.assertIn("line_strong_but_model_balanced", signal["signals"])
        self.assertIn("line_too_deep_for_model", signal["signals"])
        self.assertEqual(signal["market_side"], "home")
        self.assertEqual(signal["model_side"], "balanced")

    def test_model_edge_not_priced_is_medium_or_higher(self) -> None:
        signal = core.build_handicap_margin_consistency_signal(
            self._match(-0.25),
            model_margin_goals=1.05,
            probabilities={"home": 0.58, "draw": 0.24, "away": 0.18},
            handicap_probabilities={"home": 0.44, "draw": 0.28, "away": 0.28},
            recommendation_key="home",
            handicap_pick_key="home",
        )

        self.assertIn(signal["level"], {"MEDIUM", "HIGH"})
        self.assertIn("model_edge_not_priced", signal["signals"])
        self.assertIn("model_margin_stronger_than_line", signal["signals"])

    def test_aligned_line_and_margin_stays_low(self) -> None:
        signal = core.build_handicap_margin_consistency_signal(
            self._match(-0.75),
            model_margin_goals=0.85,
            probabilities={"home": 0.55, "draw": 0.25, "away": 0.20},
            handicap_probabilities={"home": 0.51, "draw": 0.24, "away": 0.25},
            recommendation_key="home",
            handicap_pick_key="home",
        )

        self.assertEqual(signal["level"], "LOW")
        self.assertEqual(signal["signals"], [])

    def test_opposite_handicap_and_model_direction_is_high_risk(self) -> None:
        signal = core.build_handicap_margin_consistency_signal(
            self._match(0.75),
            model_margin_goals=0.60,
            probabilities={"home": 0.52, "draw": 0.28, "away": 0.20},
            handicap_probabilities={"home": 0.30, "draw": 0.24, "away": 0.46},
            recommendation_key="home",
            handicap_pick_key="away",
        )

        self.assertEqual(signal["level"], "HIGH")
        self.assertIn("handicap_direction_mismatch", signal["signals"])
        self.assertIn("handicap_pick_margin_mismatch", signal["signals"])
        self.assertEqual(signal["market_side"], "away")
        self.assertEqual(signal["model_side"], "home")

    def test_recent_settlements_enrich_handicap_margin_from_analysis_history(self) -> None:
        class FakeStore:
            def load_settlements(self) -> list[dict]:
                return [{"match_id": "m1", "handicap_is_correct": False}]

            def load_analysis_history(self) -> dict[str, dict]:
                return {
                    "m1": {
                        "prediction": {
                            "handicap_margin_consistency": {
                                "level": "HIGH",
                                "score": 0.82,
                                "signals": ["handicap_direction_mismatch"],
                                "handicap_line": 0.75,
                                "model_margin_goals": 0.60,
                                "market_side": "away",
                                "model_side": "home",
                                "depth_gap": 0.15,
                                "handicap_pick_side": "away",
                            },
                            "draw_score": 0.76,
                            "draw_grade": "博平",
                            "draw_takeover": False,
                            "draw_release_guard": {
                                "blocked": True,
                                "reason": "weak_draw_odds_bucket",
                                "weak_score": True,
                                "base_takeover": True,
                                "odds_bucket": "<=3.00",
                                "odds_draw": 2.95,
                                "min_score": 0.58,
                                "evidence": {
                                    "precision": 0.222222,
                                    "draw_rate": 0.157895,
                                    "lift": -0.075439,
                                    "source": "draw_specialist_backtest_20260511_112806",
                                },
                            },
                            "supervisor": {
                                "status": "alert",
                                "next_actions": ["review_handicap_margin_consistency"],
                                "agents": [
                                    {
                                        "name": "RiskGuardian",
                                        "status": "alert",
                                        "rationale": "Risk signals require manual review before release.",
                                        "actions": ["review_handicap_margin_consistency"],
                                    }
                                ],
                            },
                        }
                    }
                }

        with patch.object(core, "STATE_STORE", FakeStore()):
            settlements = core.get_recent_settlements(limit=10)

        self.assertEqual(settlements[0]["handicap_margin_level"], "HIGH")
        self.assertEqual(settlements[0]["handicap_margin_score"], 0.82)
        self.assertEqual(settlements[0]["handicap_margin_signals"], ["handicap_direction_mismatch"])
        self.assertEqual(settlements[0]["handicap_margin_market_side"], "away")
        self.assertEqual(settlements[0]["strategy_admission_decision"], "")
        self.assertEqual(settlements[0]["draw_score"], 0.76)
        self.assertEqual(settlements[0]["draw_release_guard_status"], "blocked")
        self.assertTrue(settlements[0]["draw_release_guard_blocked"])
        self.assertEqual(settlements[0]["draw_release_guard_reason"], "weak_draw_odds_bucket")
        self.assertEqual(settlements[0]["draw_release_guard_odds_bucket"], "<=3.00")
        self.assertEqual(settlements[0]["draw_release_guard_evidence_precision"], 0.222222)
        self.assertEqual(settlements[0]["supervisor_agent_statuses"]["RiskGuardian"], "alert")
        self.assertEqual(settlements[0]["supervisor_alert_agents"], ["RiskGuardian"])
        self.assertIn("review_handicap_margin_consistency", settlements[0]["supervisor_agent_actions"])


if __name__ == "__main__":
    unittest.main()
