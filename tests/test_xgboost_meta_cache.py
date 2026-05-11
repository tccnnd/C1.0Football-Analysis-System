from __future__ import annotations

import json
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

from v24_app.models.play_xgboost import TotalGoalsXGBoostModel
from v24_app.models.xgboost_v0 import XGBoostProbabilityModel


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class XGBoostMetaCacheTests(unittest.TestCase):
    def test_xgb_v0_meta_cache_reuses_file_read_and_returns_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = XGBoostProbabilityModel(Path(tmp))
            _write_json(
                model.meta_file,
                {
                    "updated_at": "v1",
                    "feature_order": model.FEATURE_ORDER,
                    "model": "xgb_v0_match_outcome",
                },
            )
            original_read_text = Path.read_text
            read_count = 0

            def counting_read_text(path: Path, *args, **kwargs):
                nonlocal read_count
                if path == model.meta_file:
                    read_count += 1
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", counting_read_text):
                first = model._load_meta()
                first["updated_at"] = "mutated"
                second = model._load_meta()

        self.assertEqual(read_count, 1)
        self.assertEqual(second["updated_at"], "v1")

    def test_xgb_v0_meta_cache_reloads_when_signature_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = XGBoostProbabilityModel(Path(tmp))
            _write_json(model.meta_file, {"updated_at": "v1", "feature_order": model.FEATURE_ORDER})
            self.assertEqual(model._load_meta()["updated_at"], "v1")

            _write_json(
                model.meta_file,
                {
                    "updated_at": "v2",
                    "feature_order": model.FEATURE_ORDER,
                    "model": "xgb_v0_match_outcome",
                    "extra": "signature change",
                },
            )
            updated = model._load_meta()

        self.assertEqual(updated["updated_at"], "v2")

    def test_play_model_meta_cache_reuses_file_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = TotalGoalsXGBoostModel(Path(tmp))
            _write_json(
                model.meta_file,
                {
                    "updated_at": "v1",
                    "feature_order": model.FEATURE_ORDER,
                    "class_names": ["0", "1", "2"],
                    "model": model.model_slug,
                },
            )
            original_read_text = Path.read_text
            read_count = 0

            def counting_read_text(path: Path, *args, **kwargs):
                nonlocal read_count
                if path == model.meta_file:
                    read_count += 1
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", counting_read_text):
                first = model._load_meta()
                second = model._load_meta()

        self.assertEqual(read_count, 1)
        self.assertEqual(first["class_names"], ["0", "1", "2"])
        self.assertEqual(second["model"], model.model_slug)


if __name__ == "__main__":
    unittest.main()
