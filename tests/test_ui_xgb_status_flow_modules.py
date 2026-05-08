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

from v24_app.ui_modules import (
    build_train_xgb_apply_message,
    build_train_xgb_apply_status_text,
    build_xgb_status_text,
)


class UIXGBStatusFlowModuleTests(unittest.TestCase):
    def test_build_xgb_status_text(self) -> None:
        text = build_xgb_status_text(
            {
                "xgboost_available": True,
                "sample_count": 120,
                "valid_feature_count": 110,
                "label_counts": {0: 40, 1: 30, 2: 50},
                "min_train_samples": 80,
                "model_exists": True,
                "model_ready": True,
                "model_compatible": True,
                "model_updated_at": "2026-04-04 12:00:00",
                "last_train_attempt": "2026-04-04 12:10:00",
            }
        )
        self.assertIn("XGBoost v0 状态", text)
        self.assertIn("样本总数: 120", text)
        self.assertIn("标签分布(主/平/客): 40 / 30 / 50", text)
        self.assertIn("模型已就绪: True", text)

    def test_build_train_xgb_apply_texts(self) -> None:
        result = {"trained": True, "reason": "ok", "sample_count": 128, "updated_at": "2026-04-04 12:30:00"}
        status = build_train_xgb_apply_status_text(result)
        self.assertIn("XGB训练成功", status)
        self.assertIn("样本 128", status)
        message = build_train_xgb_apply_message(result, "XGB-STATUS")
        self.assertIn("训练结果: 成功", message)
        self.assertIn("原因: ok", message)
        self.assertIn("XGB-STATUS", message)


if __name__ == "__main__":
    unittest.main()
