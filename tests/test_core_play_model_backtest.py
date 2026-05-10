from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app import core


class PlayModelBacktestTests(unittest.TestCase):
    def tearDown(self) -> None:
        core._PLAY_MODEL_POLICY_CACHE.clear()
        core._PLAY_MODEL_POLICY_CACHE.update({"mtime": None, "policy": None, "report": {}})

    def test_run_play_model_backtest_truncates_large_validation_set(self) -> None:
        validation_items = [
            {
                "meta": {
                    "match_date": f"2025-01-{(index % 28) + 1:02d}",
                    "home_goals": 2,
                    "away_goals": 1,
                    "handicap_line": 0.0,
                }
            }
            for index in range(12)
        ]
        prediction = {
            "handicap_recommendation": "主胜",
            "total_goals_value": 3,
            "score_recommendation": "2-1",
            "poisson": {
                "score_distribution": [{"score": "2-1", "probability": 1.0}],
                "top_total_goals": [{"goals": 3, "probability": 1.0}],
                "top_scores": [{"score": "2-1", "probability": 1.0}],
            },
            "total_goals_model": {"model_ready": True, "label": 3, "confidence": 0.9},
            "scoreline_model": {"model_ready": True, "label": "2-1", "confidence": 0.9},
            "volatile_scoreline_model": {"model_ready": True, "label": "3-2", "confidence": 0.3},
        }

        with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
            with patch("v24_app.core._sample_item_prediction", return_value=prediction):
                with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                    result = core.run_play_model_backtest(max_validation_samples=5, write_report=False)

        self.assertTrue(result["ok"])
        self.assertEqual(result["validation"]["sample_count"], 5)
        self.assertEqual(result["validation"]["original_sample_count"], 12)
        self.assertEqual(result["validation"]["max_validation_samples"], 5)
        self.assertTrue(result["validation"]["truncated"])
        self.assertAlmostEqual(result["validation"]["ratio"], 5 / 12, places=4)

    def test_total_goals_takeover_requires_material_calibration_uplift(self) -> None:
        validation_items = []
        for index in range(100):
            actual_total = 2 if index < 50 else 3
            model_total = actual_total if index < 52 else 2
            validation_items.append(
                {
                    "meta": {
                        "match_date": f"2025-02-{(index % 28) + 1:02d}",
                        "home_goals": actual_total,
                        "away_goals": 0,
                    },
                    "prediction": {
                        "recommendation": "涓昏儨",
                        "pre_play_model_total_goals_value": 2,
                        "pre_play_model_total_goals_confidence": 0.30,
                        "pre_play_model_score_recommendation": "2-0",
                        "pre_play_model_score_confidence": 0.20,
                        "poisson": {
                            "score_distribution": [{"score": f"{model_total}-0", "probability": 0.9}],
                            "top_total_goals": [{"goals": 2, "probability": 0.30}],
                        },
                        "total_goals_model": {"model_ready": True, "label": model_total, "confidence": 0.9},
                        "scoreline_model": {"model_ready": False},
                        "volatile_scoreline_model": {"model_ready": False},
                    },
                }
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_file = Path(tmp_dir) / "play_model_policy_v1.json"
            with patch.object(core, "PLAY_MODEL_POLICY_FILE", policy_file):
                with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
                    with patch("v24_app.core._sample_item_prediction", side_effect=lambda item: item["prediction"]):
                        with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                            result = core.calibrate_play_model_policy_now(max_validation_samples=None)

        total_goals_metrics = result["metrics"]["total_goals"]
        self.assertTrue(result["calibrated"])
        self.assertTrue(total_goals_metrics["best"]["takeover_enabled"])
        self.assertEqual(total_goals_metrics["current_accuracy"], 0.5)
        self.assertEqual(total_goals_metrics["best"]["accuracy"], 0.52)
        self.assertEqual(total_goals_metrics["reason"], "insufficient_calibration_uplift")
        self.assertFalse(result["policy"]["total_goals"]["takeover_enabled"])

    def test_total_goals_takeover_requires_holdout_stability(self) -> None:
        validation_items = []
        for index in range(200):
            if index < 100:
                actual_total = 2 if index < 50 else 3
                model_total = actual_total if index < 90 else 2
            else:
                actual_total = 2
                model_total = 3
            validation_items.append(
                {
                    "meta": {
                        "match_date": f"2025-03-{(index % 28) + 1:02d}",
                        "home_goals": actual_total,
                        "away_goals": 0,
                    },
                    "prediction": {
                        "pre_play_model_total_goals_value": 2,
                        "pre_play_model_total_goals_confidence": 0.30,
                        "pre_play_model_score_recommendation": "2-0",
                        "pre_play_model_score_confidence": 0.20,
                        "poisson": {
                            "score_distribution": [{"score": f"{model_total}-0", "probability": 0.9}],
                            "top_total_goals": [{"goals": 2, "probability": 0.30}],
                        },
                        "total_goals_model": {"model_ready": True, "label": model_total, "confidence": 0.9},
                        "scoreline_model": {"model_ready": False},
                        "volatile_scoreline_model": {"model_ready": False},
                    },
                }
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_file = Path(tmp_dir) / "play_model_policy_v1.json"
            with patch.object(core, "PLAY_MODEL_POLICY_FILE", policy_file):
                with patch("v24_app.core._validation_split_samples", return_value=([], validation_items)):
                    with patch("v24_app.core._sample_item_prediction", side_effect=lambda item: item["prediction"]):
                        with patch.object(core.STATE_STORE, "load_xgb_samples", return_value=validation_items):
                            result = core.calibrate_play_model_policy_now(max_validation_samples=None)

        total_goals_metrics = result["metrics"]["total_goals"]
        holdout_metrics = result["metrics"]["holdout"]
        self.assertTrue(result["calibrated"])
        self.assertEqual(result["validation"]["tuning_sample_count"], 100)
        self.assertEqual(result["validation"]["holdout_sample_count"], 100)
        self.assertTrue(total_goals_metrics["best"]["takeover_enabled"])
        self.assertGreater(total_goals_metrics["uplift"], core.PLAY_MODEL_TOTAL_GOALS_MIN_CALIBRATION_UPLIFT)
        self.assertEqual(total_goals_metrics["reason"], "holdout_regression")
        self.assertLess(holdout_metrics["total_goals_uplift"], 0)
        self.assertFalse(result["policy"]["total_goals"]["takeover_enabled"])


if __name__ == "__main__":
    unittest.main()
