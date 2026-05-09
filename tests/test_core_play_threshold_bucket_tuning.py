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


class CorePlayThresholdBucketTuningTests(unittest.TestCase):
    def test_calibrate_play_thresholds_by_settlement_now(self) -> None:
        settlements: list[dict] = []
        for _ in range(20):
            settlements.append(
                {
                    "is_correct": False,
                    "prediction_confidence": 0.70,
                    "handicap_is_correct": True,
                    "handicap_confidence": 0.55,
                    "total_goals_is_correct": True,
                    "total_goals_confidence": 0.20,
                    "score_is_correct": False,
                    "score_confidence": 0.12,
                }
            )
        for _ in range(8):
            settlements[_]["is_correct"] = True

        current_thresholds = {
            "1x2": 0.56,
            "handicap": 0.56,
            "total_goals": 0.18,
            "score": 0.10,
            "htft": 0.18,
        }

        with (
            patch("v24_app.core.get_recent_settlements", return_value=settlements),
            patch("v24_app.core._current_play_thresholds", return_value=current_thresholds),
            patch("v24_app.core.get_play_threshold_status", return_value={"thresholds": current_thresholds}),
            patch("v24_app.core._save_play_threshold_report") as save_mock,
        ):
            result = core.calibrate_play_thresholds_by_settlement_now(
                write_report=False,
                min_samples=10,
                weak_ev_bias=-0.08,
                strong_ev_bias=0.08,
                step=0.02,
            )

        self.assertTrue(save_mock.called)
        self.assertTrue(result["calibrated"])
        self.assertGreater(float(result["thresholds"]["1x2"]), 0.56)
        self.assertLess(float(result["thresholds"]["handicap"]), 0.56)
        self.assertEqual(result["metrics"]["htft"]["reason"], "insufficient_samples")

    def test_calibrate_layered_filter_thresholds_now(self) -> None:
        settlements: list[dict] = []
        for _ in range(12):
            settlements.append(
                {
                    "league": "弱联赛",
                    "is_correct": False,
                    "prediction_confidence": 0.62,
                    "handicap_is_correct": True,
                    "handicap_confidence": 0.72,
                }
            )
        current_thresholds = {
            "1x2": 0.56,
            "handicap": 0.56,
            "total_goals": 0.18,
            "score": 0.10,
            "htft": 0.18,
        }

        with (
            patch("v24_app.core.get_recent_settlements", return_value=settlements),
            patch("v24_app.core._current_play_thresholds", return_value=current_thresholds),
            patch(
                "v24_app.core.get_play_threshold_status",
                return_value={
                    "updated_at": "now",
                    "mode": "bucket_tuned",
                    "thresholds": current_thresholds,
                    "metrics": {},
                    "validation": {},
                },
            ),
            patch("v24_app.core._save_play_threshold_report") as save_mock,
        ):
            result = core.calibrate_layered_filter_thresholds_now(min_samples=8)

        self.assertTrue(result["calibrated"])
        self.assertGreaterEqual(result["league_rule_count"], 1)
        weak_rule = result["layered_filter"]["league_play"]["弱联赛"]["1x2"]
        self.assertTrue(weak_rule["blocked"])
        self.assertGreater(float(weak_rule["min_threshold"]), 0.56)
        self.assertTrue(save_mock.called)


if __name__ == "__main__":
    unittest.main()
