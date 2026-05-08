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
    build_coverage_monitor_text,
    build_coverage_status_suffix,
    summarize_prediction_coverage,
)


class UICoverageMonitorFlowTests(unittest.TestCase):
    def test_summarize_prediction_coverage(self) -> None:
        predictions = {
            "m1": {
                "single_play_recommendations": [{"play_type": "1x2"}, {"play_type": "handicap"}],
                "parlay_eligible_plays": [{"play_type": "handicap"}],
            },
            "m2": {
                "single_play_recommendations": [],
                "parlay_eligible_plays": [],
            },
            "m3": {
                "single_play_recommendations": [{"play_type": "total_goals"}],
                "parlay_eligible_plays": [{"play_type": "total_goals"}],
            },
        }
        summary = summarize_prediction_coverage(predictions=predictions, formal_count=1)
        self.assertEqual(summary["analyzed_count"], 3)
        self.assertEqual(summary["single_match_count"], 2)
        self.assertEqual(summary["parlay_match_count"], 2)
        self.assertEqual(summary["by_play_match_count"]["1x2"], 1)
        self.assertEqual(summary["by_play_match_count"]["total_goals"], 1)

    def test_build_coverage_text_and_suffix(self) -> None:
        summary = {
            "analyzed_count": 10,
            "single_match_count": 2,
            "single_coverage": 0.2,
            "single_pick_count": 4,
            "parlay_match_count": 1,
            "parlay_coverage": 0.1,
            "formal_count": 0,
            "formal_coverage": 0.0,
            "by_play_match_count": {"1x2": 2, "handicap": 1},
            "risk_level": "warn",
            "risk_reasons": ["single_coverage_low"],
        }
        text = build_coverage_monitor_text(summary)
        self.assertIn("推荐覆盖率监控", text)
        self.assertIn("状态: 预警", text)
        suffix = build_coverage_status_suffix(summary)
        self.assertIn("覆盖率 20%", suffix)
        self.assertIn("预警", suffix)


if __name__ == "__main__":
    unittest.main()
