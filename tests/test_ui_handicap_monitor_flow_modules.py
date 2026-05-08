from __future__ import annotations

import re
import sys
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_modules import (
    build_handicap_dashboard_text,
    build_handicap_shadow_report_filename,
    build_handicap_shadow_report_lines,
)


class UIHandicapMonitorFlowModuleTests(unittest.TestCase):
    def test_build_handicap_dashboard_text_empty(self) -> None:
        text = build_handicap_dashboard_text([], window=30)
        self.assertIn("暂无可用样本", text)

    def test_build_handicap_dashboard_text_has_gate_metrics(self) -> None:
        settlements = [
            {
                "timestamp": "2026-04-01 11:00:00",
                "handicap_line": -0.25,
                "handicap_confidence": 0.61,
                "handicap_is_correct": True,
            },
            {
                "timestamp": "2026-04-02 11:00:00",
                "handicap_line": 0.75,
                "handicap_confidence": 0.57,
                "handicap_is_correct": False,
            },
            {
                "timestamp": "2026-04-03 11:00:00",
                "handicap_line": -1.0,
                "handicap_confidence": 0.66,
                "handicap_is_correct": True,
            },
        ]
        text = build_handicap_dashboard_text(settlements, window=30, breaker_threshold=2)
        self.assertIn("让球专项看板", text)
        self.assertIn("命中率 66.7%", text)
        self.assertIn("分档表现", text)
        self.assertIn("|line| <= 0.25", text)

    def test_build_handicap_shadow_report_lines_daily_table(self) -> None:
        now = datetime(2026, 4, 4, 18, 0, 0)
        settlements = [
            {
                "timestamp": "2026-04-01 10:00:00",
                "handicap_line": -0.25,
                "handicap_confidence": 0.58,
                "handicap_is_correct": True,
            },
            {
                "timestamp": "2026-04-01 20:00:00",
                "handicap_line": 0.5,
                "handicap_confidence": 0.54,
                "handicap_is_correct": False,
            },
            {
                "timestamp": "2026-04-03 09:00:00",
                "handicap_line": 1.0,
                "handicap_confidence": 0.62,
                "handicap_is_correct": True,
            },
        ]
        lines = build_handicap_shadow_report_lines(
            settlements,
            days=4,
            gate_window=10,
            breaker_threshold=3,
            now=now,
        )
        payload = "\n".join(lines)
        self.assertIn("# Handicap Shadow Daily Report", payload)
        self.assertIn("## Last 14 Days Table", payload)
        self.assertIn("| 2026-04-01 | 2 | 1 | 50.0% |", payload)
        self.assertIn("| 2026-04-04 | 0 | 0 | 0.0% |", payload)

    def test_build_handicap_shadow_report_filename(self) -> None:
        now = datetime(2026, 4, 4, 18, 2, 3)
        name = build_handicap_shadow_report_filename(now=now)
        self.assertRegex(name, r"^handicap_shadow_daily_20260404_180203\.md$")
        self.assertTrue(re.match(r"^handicap_shadow_daily_\d{8}_\d{6}\.md$", name))


if __name__ == "__main__":
    unittest.main()
