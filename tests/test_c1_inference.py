from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from c1.core.schema import FeatureSnapshot
from c1.inference import (
    BaselineInferenceEngine,
    C1InferenceEngine,
    C1XGBoostAdapter,
    build_inference_input,
    load_ensemble_calibration,
)


class C1InferenceTests(unittest.TestCase):
    def feature_snapshot(self) -> FeatureSnapshot:
        return FeatureSnapshot(
            match_id="2026-04-03|friendly|A|B",
            feature_version="c1.phase2",
            source="unit",
            fields={
                "league": "Friendly",
                "league_strength": 0.92,
                "odds_home": 1.88,
                "odds_draw": 3.35,
                "odds_away": 4.10,
                "home_rating": 1530,
                "away_rating": 1488,
                "opening_odds_home": 1.82,
                "opening_odds_draw": 3.40,
                "opening_odds_away": 4.30,
                "return_rate": 0.92,
                "kelly_home": 0.95,
                "kelly_draw": 0.93,
                "kelly_away": 0.98,
                "match_date": "2026-04-03",
                "match_time": "19:35",
                "home_recent_points_pg": 2.2,
                "away_recent_points_pg": 1.1,
                "recent_points_diff": 1.1,
                "home_recent_goal_diff_pg": 0.9,
                "away_recent_goal_diff_pg": -0.2,
                "recent_goal_diff_diff": 1.1,
                "home_recent_goals_for_pg": 1.8,
                "away_recent_goals_for_pg": 0.9,
                "home_recent_win_rate": 0.6,
                "away_recent_win_rate": 0.2,
            },
        )

    def test_load_ensemble_calibration(self) -> None:
        calibration = load_ensemble_calibration(PROJECT_ROOT)
        self.assertIn("market", calibration.weights)
        self.assertIn("elo", calibration.weights)
        self.assertIn("poisson", calibration.weights)
        self.assertIn("xgboost", calibration.weights)

    def test_build_inference_input(self) -> None:
        snapshot = self.feature_snapshot()
        inference_input = build_inference_input(match_id=snapshot.match_id, feature_snapshot=snapshot)
        self.assertEqual(inference_input.match_id, snapshot.match_id)
        self.assertEqual(inference_input.home_rating, 1530)
        self.assertEqual(inference_input.away_rating, 1488)

    def test_baseline_inference_returns_normalized_probabilities(self) -> None:
        snapshot = self.feature_snapshot()
        inference_input = build_inference_input(match_id=snapshot.match_id, feature_snapshot=snapshot)
        engine = BaselineInferenceEngine()
        output = engine.infer(inference_input, {"market": 0.35, "elo": 0.30, "poisson": 0.20})
        total = sum(output.fused_probabilities.values())
        self.assertAlmostEqual(total, 1.0, places=5)
        self.assertEqual({component.name for component in output.components}, {"market", "elo", "poisson"})

    def test_xgb_adapter_returns_component_shape(self) -> None:
        snapshot = self.feature_snapshot()
        inference_input = build_inference_input(match_id=snapshot.match_id, feature_snapshot=snapshot)
        adapter = C1XGBoostAdapter(PROJECT_ROOT)
        component = adapter.infer(inference_input)
        self.assertEqual(component.name, "xgboost")
        self.assertIn("home", component.probabilities)
        self.assertIn("xgb_features", component.metadata)

    def test_runtime_inference_returns_raw_only_result(self) -> None:
        snapshot = self.feature_snapshot()
        inference_input = build_inference_input(match_id=snapshot.match_id, feature_snapshot=snapshot)
        engine = C1InferenceEngine(PROJECT_ROOT)
        result = engine.infer(inference_input, enable_xgboost=True, enable_lightgbm=False)
        self.assertEqual(result.match_id, snapshot.match_id)
        self.assertIn(result.predicted_side, {"home", "draw", "away"})
        self.assertIn("home", result.raw_probabilities)
        self.assertIn("draw", result.raw_probabilities)
        self.assertIn("away", result.raw_probabilities)
        self.assertIn("home", result.ev_by_side)
        self.assertIn("weights", result.calibration)
        self.assertFalse(hasattr(result, "handicap_recommendation"))


if __name__ == "__main__":
    unittest.main()
