from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app import core


class PlayModelBacktestTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
