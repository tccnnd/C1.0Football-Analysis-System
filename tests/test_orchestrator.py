from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.core import AppMatch
from v24_app.orchestrator import build_supervisor_orchestration


class OrchestratorTests(unittest.TestCase):
    def test_supervisor_flags_high_market_entropy_for_review(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="20:00",
            match_date="2026-05-10",
            odds_home=2.05,
            odds_draw=3.25,
            odds_away=3.90,
            source="live:titan",
        )

        trace = build_supervisor_orchestration(
            match=match,
            prediction_context={
                "recommendation": "home",
                "confidence": 0.68,
                "risk_level": "HIGH",
                "risk_level_base": "LOW",
                "probabilities": {"home": 0.50, "draw": 0.28, "away": 0.22},
                "expected_goals": 2.3,
                "market_entropy": {
                    "level": "HIGH",
                    "score": 0.84,
                    "signals": ["market_steam_against_pick"],
                    "sequence": {"sample_count": 3, "max_step_change": 0.08, "max_abs_velocity_per_minute": 0.006},
                },
                "market_entropy_risk": {"applied": True},
                "strategy_admission": {"release_allowed": False, "decision": "observe"},
            },
        )

        self.assertEqual(trace["status"], "alert")
        self.assertTrue(trace["decision"]["requires_human_review"])
        self.assertFalse(trace["decision"]["release_allowed"])
        self.assertIn("manual_market_review", trace["next_actions"])
        statuses = {item["name"]: item["status"] for item in trace["agents"]}
        self.assertEqual(statuses["MarketEntropy"], "alert")
        self.assertEqual(statuses["RiskGuardian"], "alert")
        entropy_agent = next(item for item in trace["agents"] if item["name"] == "MarketEntropy")
        self.assertIn("market signals", entropy_agent["checks"])
        self.assertIn("manual_market_review", entropy_agent["actions"])
        self.assertIn("abnormal", entropy_agent["rationale"])

    def test_supervisor_blocks_when_core_market_data_missing(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="20:00",
            match_date="2026-05-10",
            odds_home=0.0,
            odds_draw=0.0,
            odds_away=0.0,
        )

        trace = build_supervisor_orchestration(match=match, prediction_context={})

        self.assertEqual(trace["status"], "blocked")
        self.assertIn("refresh_data", trace["next_actions"])
        statuses = {item["name"]: item["status"] for item in trace["agents"]}
        self.assertEqual(statuses["DataHunter"], "blocked")
        self.assertEqual(statuses["Simulation"], "blocked")
        data_agent = next(item for item in trace["agents"] if item["name"] == "DataHunter")
        self.assertIn("refresh_data", data_agent["actions"])
        self.assertIn("odds", data_agent["evidence"])

    def test_supervisor_flags_handicap_margin_conflict_for_review(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="20:00",
            match_date="2026-05-10",
            odds_home=1.90,
            odds_draw=3.30,
            odds_away=4.50,
            handicap_line=0.75,
        )

        trace = build_supervisor_orchestration(
            match=match,
            prediction_context={
                "recommendation": "home",
                "confidence": 0.66,
                "risk_level": "LOW",
                "risk_level_base": "LOW",
                "probabilities": {"home": 0.52, "draw": 0.28, "away": 0.20},
                "expected_goals": 2.4,
                "market_entropy": {"level": "LOW", "score": 0.10, "signals": []},
                "handicap_margin_consistency": {
                    "level": "HIGH",
                    "score": 0.82,
                    "signals": ["handicap_direction_mismatch"],
                },
                "strategy_admission": {"release_allowed": True, "decision": "allow"},
            },
        )

        self.assertEqual(trace["status"], "alert")
        self.assertIn("review_handicap_margin_consistency", trace["next_actions"])
        self.assertEqual(trace["decision"]["handicap_margin_level"], "HIGH")
        statuses = {item["name"]: item["status"] for item in trace["agents"]}
        self.assertEqual(statuses["RiskGuardian"], "alert")
        risk_agent = next(item for item in trace["agents"] if item["name"] == "RiskGuardian")
        self.assertIn("review_handicap_margin_consistency", risk_agent["actions"])
        self.assertEqual(risk_agent["evidence"]["handicap_margin_level"], "HIGH")


if __name__ == "__main__":
    unittest.main()
