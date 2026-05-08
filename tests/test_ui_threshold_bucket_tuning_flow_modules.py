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
    build_threshold_bucket_tuning_apply_message,
    build_threshold_bucket_tuning_apply_status_text,
)


class UIThresholdBucketTuningFlowTests(unittest.TestCase):
    def test_build_threshold_bucket_tuning_apply_status_text(self) -> None:
        text = build_threshold_bucket_tuning_apply_status_text(
            {"calibrated": True, "reason": "ok", "validation": {"changed_play_count": 2}}
        )
        self.assertIn("弱分桶校准完成", text)
        self.assertIn("变更玩法 2", text)

    def test_build_threshold_bucket_tuning_apply_message(self) -> None:
        text = build_threshold_bucket_tuning_apply_message(
            {
                "validation": {"sample_count": 100, "changed_play_count": 1},
                "report_path": "E:/APP/ELO/reports/r.md",
            },
            "status text",
        )
        self.assertIn("结算样本: 100", text)
        self.assertIn("变更玩法: 1", text)
        self.assertIn("status text", text)


if __name__ == "__main__":
    unittest.main()
