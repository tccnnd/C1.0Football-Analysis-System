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

from v24_app.models.bayesian_calibration import calibrate_three_way_probabilities


class BayesianCalibrationTests(unittest.TestCase):
    def test_market_prior_can_lift_draw_probability(self) -> None:
        calibrated, metadata = calibrate_three_way_probabilities(
            model_probabilities={"home": 0.52, "draw": 0.20, "away": 0.28},
            market_probabilities={"home": 0.40, "draw": 0.33, "away": 0.27},
            config={
                "enabled": True,
                "prior_source": "market",
                "prior_strength": 28.0,
                "model_strength": 50.0,
                "uncertainty_gain": 0.5,
                "draw_bias_scale": 0.3,
                "min_probability": 0.01,
            },
        )
        self.assertAlmostEqual(sum(calibrated.values()), 1.0, places=6)
        self.assertGreater(calibrated["draw"], 0.20)
        self.assertEqual(metadata.get("prior_source_used"), "market")
        self.assertGreaterEqual(float(metadata.get("draw_bias_term", 0.0)), 0.0)

    def test_disabled_keeps_distribution_shape(self) -> None:
        calibrated, metadata = calibrate_three_way_probabilities(
            model_probabilities={"home": 0.62, "draw": 0.18, "away": 0.20},
            market_probabilities={"home": 0.40, "draw": 0.35, "away": 0.25},
            config={"enabled": False, "min_probability": 0.0},
        )
        self.assertAlmostEqual(calibrated["home"], 0.62, places=2)
        self.assertAlmostEqual(calibrated["draw"], 0.18, places=2)
        self.assertAlmostEqual(calibrated["away"], 0.20, places=2)
        self.assertFalse(bool(metadata.get("enabled")))
        self.assertEqual(metadata.get("reason"), "disabled")

    def test_min_probability_floor_applies(self) -> None:
        calibrated, _ = calibrate_three_way_probabilities(
            model_probabilities={"home": 0.99, "draw": 0.005, "away": 0.005},
            market_probabilities={"home": 0.99, "draw": 0.005, "away": 0.005},
            config={"enabled": True, "min_probability": 0.03},
        )
        self.assertGreaterEqual(calibrated["draw"], 0.03 - 1e-8)
        self.assertGreaterEqual(calibrated["away"], 0.03 - 1e-8)
        self.assertAlmostEqual(sum(calibrated.values()), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
