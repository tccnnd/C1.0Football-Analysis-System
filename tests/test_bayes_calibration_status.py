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

from v24_app.core import _current_bayes_calibration_config, get_bayes_calibration_status


class BayesCalibrationStatusTests(unittest.TestCase):
    def test_status_has_required_config_fields(self) -> None:
        status = get_bayes_calibration_status()
        self.assertIn("config", status)
        cfg = status["config"]
        for key in (
            "enabled",
            "prior_source",
            "prior_strength",
            "model_strength",
            "uncertainty_gain",
            "draw_bias_scale",
            "min_probability",
        ):
            self.assertIn(key, cfg)

    def test_current_config_prefers_enabled_league_override(self) -> None:
        mocked_status = {
            "config": {
                "enabled": True,
                "prior_source": "uniform",
                "prior_strength": 24.0,
                "model_strength": 56.0,
                "uncertainty_gain": 0.55,
                "draw_bias_scale": 0.18,
                "min_probability": 0.02,
            },
            "league_overrides": {
                "英超": {
                    "enabled": True,
                    "config": {
                        "enabled": True,
                        "prior_source": "market",
                        "prior_strength": 12.0,
                        "model_strength": 72.0,
                        "uncertainty_gain": 0.35,
                        "draw_bias_scale": 0.0,
                        "min_probability": 0.0,
                    },
                }
            },
        }
        with patch("v24_app.core.get_bayes_calibration_status", return_value=mocked_status):
            cfg = _current_bayes_calibration_config("英超")
        self.assertEqual(cfg.get("prior_source"), "market")
        self.assertEqual(float(cfg.get("model_strength", 0.0)), 72.0)


if __name__ == "__main__":
    unittest.main()
