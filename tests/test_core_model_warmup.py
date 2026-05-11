from __future__ import annotations

import sys
import tempfile
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


class _WarmupModel:
    def __init__(self, model_file: Path, *, fail: bool = False) -> None:
        self.model_file = model_file
        self.fail = fail
        self.calls = 0
        self._model_ready = False

    def _load_model(self) -> None:
        self.calls += 1
        if self.fail:
            raise RuntimeError("load failed")
        self._model_ready = True


class CoreModelWarmupTests(unittest.TestCase):
    def test_warmup_prediction_models_loads_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "model.json"
            model_file.write_text("{}", encoding="utf-8")
            first = _WarmupModel(model_file)
            second = _WarmupModel(model_file)

            with patch("v24_app.core._prediction_model_warmup_targets", return_value=[("first", first), ("second", second)]):
                report = core.warmup_prediction_models()

        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["ready_count"], 2)
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)
        self.assertTrue(all(item["ready"] for item in report["items"]))

    def test_warmup_prediction_models_reports_errors_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_file = Path(tmp) / "model.json"
            model_file.write_text("{}", encoding="utf-8")
            ok = _WarmupModel(model_file)
            failed = _WarmupModel(model_file, fail=True)

            with patch("v24_app.core._prediction_model_warmup_targets", return_value=[("ok", ok), ("failed", failed)]):
                report = core.warmup_prediction_models()

        self.assertEqual(report["status"], "error")
        self.assertEqual(report["ready_count"], 1)
        failed_item = next(item for item in report["items"] if item["model"] == "failed")
        self.assertEqual(failed_item["status"], "error")
        self.assertIn("load failed", failed_item["error"])


if __name__ == "__main__":
    unittest.main()
