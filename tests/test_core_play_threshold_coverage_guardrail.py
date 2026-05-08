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


class CorePlayThresholdCoverageGuardrailTests(unittest.TestCase):
    def test_guardrail_lowers_threshold_when_coverage_low(self) -> None:
        rows = []
        for _ in range(50):
            rows.append(
                {
                    "saved_at": "2026-04-07 10:00:00",
                    "prediction": {
                        "confidence": 0.52,
                        "handicap_confidence": 0.50,
                        "total_goals_confidence": 0.17,
                        "score_confidence": 0.09,
                        "htft_confidence": 0.16,
                    },
                }
            )

        current_thresholds = {
            "1x2": 0.56,
            "handicap": 0.56,
            "total_goals": 0.18,
            "score": 0.10,
            "htft": 0.18,
        }
        play_policy = {
            "1x2": {"single_enabled": True},
            "handicap": {"single_enabled": True},
            "total_goals": {"single_enabled": True},
            "score": {"single_enabled": False},
            "htft": {"single_enabled": True},
        }

        with (
            patch("v24_app.core._load_recent_prediction_records", return_value=rows),
            patch("v24_app.core._current_play_thresholds", return_value=current_thresholds),
            patch("v24_app.core._current_play_policy", return_value=play_policy),
            patch("v24_app.core._save_play_threshold_report") as save_mock,
            patch("v24_app.core.get_play_threshold_status", return_value={"thresholds": current_thresholds}),
        ):
            result = core.calibrate_play_thresholds_coverage_guardrail_now(write_report=False, min_predictions=12)

        self.assertTrue(save_mock.called)
        self.assertTrue(result["calibrated"])
        self.assertLess(float(result["thresholds"]["1x2"]), 0.56)
        self.assertEqual(result["validation"]["reason"], "coverage_too_low")


if __name__ == "__main__":
    unittest.main()
