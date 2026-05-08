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
    build_coverage_guardrail_apply_message,
    build_coverage_guardrail_apply_status_text,
)


class UICoverageGuardrailFlowTests(unittest.TestCase):
    def test_build_coverage_guardrail_apply_status_text(self) -> None:
        text = build_coverage_guardrail_apply_status_text(
            {"calibrated": True, "reason": "ok", "validation": {"final_single_coverage": 0.42}}
        )
        self.assertIn("覆盖率保护完成", text)
        self.assertIn("覆盖率 42%", text)

    def test_build_coverage_guardrail_apply_message(self) -> None:
        text = build_coverage_guardrail_apply_message(
            {
                "validation": {
                    "prediction_count": 80,
                    "base_single_coverage": 0.22,
                    "final_single_coverage": 0.36,
                },
                "report_path": "E:/APP/ELO/reports/x.md",
            },
            "threshold status",
        )
        self.assertIn("预测样本: 80", text)
        self.assertIn("基线覆盖率: 22.0%", text)
        self.assertIn("调整后覆盖率: 36.0%", text)
        self.assertIn("threshold status", text)


if __name__ == "__main__":
    unittest.main()
