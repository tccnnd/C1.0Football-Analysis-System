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
    build_gate_summary_text,
    build_parlay_settlement_row,
    build_single_settlement_row,
)


class UISettlementViewModuleTests(unittest.TestCase):
    def test_build_gate_summary_text(self) -> None:
        text = build_gate_summary_text(
            {
                "overall": {"hit_rate": 0.55, "ev_bias": -0.02, "losing_streak": 2, "breaker_on": False},
                "singles": {"hit_rate": 0.57, "ev_bias": -0.01, "sample_count": 20},
                "parlays": {"hit_rate": 0.50, "ev_bias": 0.03, "sample_count": 10},
            }
        )
        self.assertIn("Gate-Overall: 命中率 55.0%", text)
        self.assertIn("Singles: 命中率 57.0%", text)
        self.assertIn("Parlays: 命中率 50.0%", text)

    def test_build_single_settlement_row(self) -> None:
        row = build_single_settlement_row(
            {
                "timestamp": "2026-04-04 20:00:00",
                "league": "L1",
                "home_team": "A",
                "away_team": "B",
                "home_goals": 2,
                "away_goals": 1,
                "predicted": "主胜",
                "is_correct": True,
                "predicted_handicap": "-0.5 主让",
                "handicap_is_correct": False,
                "predicted_total_goals": "3球",
                "total_goals": 3,
                "predicted_score": "2-1",
                "score_is_correct": True,
            },
            mark_text_fn=lambda v: "Y" if v else "N",
        )
        self.assertEqual(row[2], "A vs B")
        self.assertEqual(row[3], "2:1")
        self.assertEqual(row[5], "Y")
        self.assertEqual(row[6], "-")
        self.assertIn("/ N", row[7])

    def test_build_parlay_settlement_row(self) -> None:
        row = build_parlay_settlement_row(
            {
                "settled_at": "2026-04-04 21:00:00",
                "mixed": True,
                "expected_hit": 0.33,
                "is_hit": True,
                "legs": [
                    {"play_type": "1x2", "home_team": "A", "away_team": "B", "pick": "主胜"},
                    {"play_type": "totals", "home_team": "C", "away_team": "D", "pick": "2球"},
                ],
            }
        )
        self.assertEqual(row[1], "Y")
        self.assertIn("[1x2] A vs B 主胜", row[2])
        self.assertEqual(row[3], "33.0%")
        self.assertEqual(row[4], "命中")


if __name__ == "__main__":
    unittest.main()
