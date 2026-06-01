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

from c1.audit import C1AuditStore
from c1.core.reason_codes import DecisionAction
from c1.runtime import C1ShadowRunner


class C1ShadowRuntimeTests(unittest.TestCase):
    def make_test_root(self) -> Path:
        base_dir = PROJECT_ROOT / "data" / "tmp_c1_shadow_tests"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"case_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def base_raw(self, **overrides):
        payload = {
            "league": "Friendly",
            "league_strength": 0.92,
            "odds_home": 1.88,
            "odds_draw": 3.30,
            "odds_away": 4.10,
            "opening_odds_home": 1.82,
            "opening_odds_draw": 3.36,
            "opening_odds_away": 4.25,
            "current_odds_home": 1.88,
            "current_odds_draw": 3.30,
            "current_odds_away": 4.10,
            "opening_handicap_line": -0.5,
            "current_handicap_line": -0.5,
            "handicap_line": -0.5,
            "total_goals_line": 2.5,
            "return_rate": 0.92,
            "kelly_home": 0.95,
            "kelly_draw": 0.94,
            "kelly_away": 0.98,
            "home_rating": 1532,
            "away_rating": 1491,
            "match_date": "2026-04-03",
            "match_time": "19:35",
            "context_completeness": 0.94,
            "odds_snapshot_quality": 0.88,
            "team_availability_quality": 0.74,
            "source_reliability": 0.91,
            "data_freshness_hours": 2,
            "lineup_known": True,
            "lineup_freshness_hours": 2,
            "market_side": "home",
            "market_divergence": 0.04,
            "injury_conflict_score": 0.06,
            "schedule_pressure": 0.10,
            "weather_risk": 0.08,
            "environment_safe": True,
            "home_recent_points_pg": 2.3,
            "away_recent_points_pg": 1.1,
            "recent_points_diff": 1.2,
            "home_recent_goal_diff_pg": 1.0,
            "away_recent_goal_diff_pg": -0.2,
            "recent_goal_diff_diff": 1.2,
            "home_recent_goals_for_pg": 1.9,
            "away_recent_goals_for_pg": 0.9,
            "home_recent_win_rate": 0.6,
            "away_recent_win_rate": 0.2,
        }
        payload.update(overrides)
        return payload

    def test_shadow_runner_executes_full_pipeline_and_records_audit(self) -> None:
        audit_dir = self.make_test_root()
        runner = C1ShadowRunner(PROJECT_ROOT, audit_dir=audit_dir)
        result = runner.run_match(
            match_id="2026-04-03|friendly|A|B",
            raw_fields=self.base_raw(),
            governance_state={},
            context={"source": "unit"},
            created_at="2026-04-03 20:00:00",
        )
        self.assertEqual(result.match_id, "2026-04-03|friendly|A|B")
        self.assertIn(result.inference_result.predicted_side, {"home", "draw", "away"})
        self.assertIn(result.governance_decision.action, {DecisionAction.APPROVE, DecisionAction.DOWNGRADE, DecisionAction.OBSERVE, DecisionAction.BLOCK})
        # Translation layer now emits 5 plays: 1x2 / handicap / totals / htft / scoreline
        self.assertEqual(len(result.translation_result.items), 5)
        self.assertEqual(
            {item.play for item in result.translation_result.items},
            {"1x2", "handicap", "totals", "htft", "scoreline"},
        )
        self.assertIn("translation_record_id", result.audit_metadata)

        store = C1AuditStore(PROJECT_ROOT, audit_dir=audit_dir)
        self.assertEqual(len(store.read_feature_vectors()), 1)
        self.assertEqual(len(store.read_predictions()), 1)
        self.assertEqual(len(store.read_governance_decisions()), 1)
        self.assertEqual(len(store.read_translation_outputs()), 1)

    def test_shadow_runner_propagates_block_to_translation_outputs(self) -> None:
        audit_dir = self.make_test_root()
        runner = C1ShadowRunner(PROJECT_ROOT, audit_dir=audit_dir)
        result = runner.run_match(
            match_id="2026-04-03|friendly|C|D",
            raw_fields=self.base_raw(),
            governance_state={"breaker_active": True, "losing_streak": 6},
            context={"source": "unit"},
            created_at="2026-04-03 20:05:00",
        )
        self.assertEqual(result.governance_decision.action, DecisionAction.BLOCK)
        self.assertTrue(all(item.status == "BLOCKED" for item in result.translation_result.items))


if __name__ == "__main__":
    unittest.main()
