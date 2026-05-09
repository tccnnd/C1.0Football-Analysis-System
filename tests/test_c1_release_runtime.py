from __future__ import annotations

import shutil
import sys
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from c1.runtime import C1ReleaseRunner


class C1ReleaseRuntimeTests(unittest.TestCase):
    def make_test_root(self) -> Path:
        base_dir = PROJECT_ROOT / "data" / "tmp_c1_release_tests"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"case_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def base_raw(self, **overrides):
        payload = {
            "league": "Friendly",
            "league_strength": 0.92,
            "odds_home": 1.72,
            "odds_draw": 3.60,
            "odds_away": 4.80,
            "opening_odds_home": 1.78,
            "opening_odds_draw": 3.55,
            "opening_odds_away": 4.60,
            "current_odds_home": 1.72,
            "current_odds_draw": 3.60,
            "current_odds_away": 4.80,
            "opening_handicap_line": -0.5,
            "current_handicap_line": -0.5,
            "handicap_line": -0.5,
            "total_goals_line": 1.5,
            "return_rate": 0.92,
            "kelly_home": 0.94,
            "kelly_draw": 0.96,
            "kelly_away": 0.99,
            "home_rating": 1560,
            "away_rating": 1480,
            "match_date": "2026-04-03",
            "match_time": "20:00",
            "context_completeness": 0.98,
            "odds_snapshot_quality": 0.95,
            "team_availability_quality": 0.92,
            "source_reliability": 0.92,
            "data_freshness_hours": 1,
            "lineup_known": True,
            "lineup_freshness_hours": 1,
            "market_side": "home",
            "market_divergence": 0.02,
            "injury_conflict_score": 0.02,
            "schedule_pressure": 0.02,
            "weather_risk": 0.01,
            "environment_safe": True,
            "home_recent_points_pg": 2.4,
            "away_recent_points_pg": 0.9,
            "recent_points_diff": 1.5,
            "home_recent_goal_diff_pg": 1.1,
            "away_recent_goal_diff_pg": -0.3,
            "recent_goal_diff_diff": 1.4,
            "home_recent_goals_for_pg": 2.0,
            "away_recent_goals_for_pg": 0.8,
            "home_recent_win_rate": 0.7,
            "away_recent_win_rate": 0.2,
        }
        payload.update(overrides)
        return payload

    def test_release_runner_produces_controlled_release_candidate(self) -> None:
        audit_dir = self.make_test_root()
        runner = C1ReleaseRunner(PROJECT_ROOT, audit_dir=audit_dir)
        shadow_result, release_decision = runner.run_match(
            match_id="2026-04-03|friendly|R|S",
            raw_fields=self.base_raw(),
            governance_state={},
            context={"source": "unit"},
            created_at="2026-04-03 22:00:00",
        )
        self.assertEqual(shadow_result.match_id, "2026-04-03|friendly|R|S")
        self.assertTrue(release_decision.release_allowed)
        self.assertEqual(release_decision.release_action, "APPROVE_RELEASE")
        self.assertGreaterEqual(len(release_decision.candidates), 1)
        self.assertEqual(runner.release.audit.read_release_decisions(limit=1)[0]["match_id"], "2026-04-03|friendly|R|S")

    def test_release_runner_holds_when_governance_blocks(self) -> None:
        audit_dir = self.make_test_root()
        runner = C1ReleaseRunner(PROJECT_ROOT, audit_dir=audit_dir)
        _, release_decision = runner.run_match(
            match_id="2026-04-03|friendly|T|U",
            raw_fields=self.base_raw(),
            governance_state={"breaker_active": True, "losing_streak": 6},
            context={"source": "unit"},
            created_at="2026-04-03 22:05:00",
        )
        self.assertFalse(release_decision.release_allowed)
        self.assertEqual(release_decision.release_action, "GOVERNANCE_HOLD")

    def test_release_runner_uses_fallback_when_translation_has_no_candidate(self) -> None:
        audit_dir = self.make_test_root()
        runner = C1ReleaseRunner(
            PROJECT_ROOT,
            audit_dir=audit_dir,
            translation_config={
                "one_x_two": {
                    "min_confidence": 0.99,
                    "min_ev": 0.99,
                    "draw_min_probability": 0.99,
                },
                "handicap": {
                    "supported_line_abs_max": 0.0,
                    "min_cover_edge": 99.0,
                    "min_side_gap": 99.0,
                    "draw_prob_max_for_side": 0.0,
                },
                "totals": {
                    "default_line": 2.5,
                    "default_expected_goals": 2.5,
                    "min_total_edge": 99.0,
                },
            },
            release_config={
                "allowed_governance_actions": ["APPROVE"],
                "allowed_plays": ["1x2", "totals"],
                "min_confidence": 0.30,
                "fallback": {
                    "enabled": True,
                    "allowed_plays": ["1x2"],
                    "min_confidence": 0.45,
                    "min_ev": -1.0,
                },
            },
        )
        _, release_decision = runner.run_match(
            match_id="2026-04-03|friendly|X|Y",
            raw_fields=self.base_raw(),
            governance_state={},
            context={"source": "unit"},
            enable_xgboost=False,
            created_at="2026-04-03 22:08:00",
        )
        self.assertTrue(release_decision.release_allowed)
        self.assertEqual(release_decision.release_action, "APPROVE_RELEASE_FALLBACK")
        self.assertGreaterEqual(len(release_decision.candidates), 1)
        self.assertEqual(release_decision.candidates[0].play, "1x2")


if __name__ == "__main__":
    unittest.main()
