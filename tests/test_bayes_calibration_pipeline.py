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


class BayesCalibrationPipelineTests(unittest.TestCase):
    def test_calibrate_bayes_returns_insufficient_when_split_empty(self) -> None:
        with patch.object(core, "_validation_split_samples", return_value=([], [])):
            result = core.calibrate_bayes_calibration_now()
        self.assertFalse(bool(result.get("calibrated")))
        self.assertEqual(result.get("reason"), "insufficient_validation_split")

    def test_calibrate_bayes_updates_when_candidate_improves(self) -> None:
        train_items = [{} for _ in range(120)]
        validation_items = [{} for _ in range(120)]
        rows = [
            {
                "label": 1,
                "pre_bayes_probabilities": {"home": 0.54, "draw": 0.20, "away": 0.26},
                "market_probabilities": {"home": 0.42, "draw": 0.35, "away": 0.23},
            }
        ]
        with (
            patch.object(core, "_validation_split_samples", return_value=(train_items, validation_items)),
            patch.object(core, "_collect_bayes_validation_rows", return_value=(rows, {"sample_count": 1, "date_start": "2026-01-01", "date_end": "2026-01-01"})),
            patch.object(
                core,
                "_current_bayes_calibration_config",
                return_value={**dict(core.DEFAULT_BAYES_CALIBRATION), "prior_source": "uniform"},
            ),
            patch.object(core, "get_bayes_calibration_status", return_value={"mode": "calibrated", "config": dict(core.DEFAULT_BAYES_CALIBRATION)}),
            patch.object(core, "_save_bayes_calibration_report") as mock_save,
        ):
            def fake_eval(_rows: list[dict], cfg: dict) -> dict:
                if cfg.get("prior_source") == "market":
                    return {"count": 1, "logloss": 0.48, "brier": 0.21, "accuracy": 0.72, "draw_picks": 1, "draw_hit_rate": 1.0}
                return {"count": 1, "logloss": 0.62, "brier": 0.25, "accuracy": 0.68, "draw_picks": 0, "draw_hit_rate": 0.0}

            with patch.object(core, "_evaluate_bayes_config", side_effect=fake_eval):
                result = core.calibrate_bayes_calibration_now()

        self.assertTrue(bool(result.get("calibrated")))
        self.assertEqual(result.get("reason"), "ok")
        self.assertTrue(mock_save.called)


if __name__ == "__main__":
    unittest.main()
