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

from v24_app.core import AppMatch
from v24_app.ui_modules import (
    build_settlement_status_text,
    is_settlement_score_in_range,
    parse_settlement_score_inputs,
)


class UISettleFlowModuleTests(unittest.TestCase):
    def test_parse_settlement_score_inputs(self) -> None:
        self.assertEqual(parse_settlement_score_inputs(" 2 ", "1"), (2, 1))
        with self.assertRaises(ValueError):
            parse_settlement_score_inputs("a", "1")

    def test_is_settlement_score_in_range(self) -> None:
        self.assertTrue(is_settlement_score_in_range(0, 0))
        self.assertTrue(is_settlement_score_in_range(20, 20))
        self.assertFalse(is_settlement_score_in_range(-1, 1))
        self.assertFalse(is_settlement_score_in_range(1, 21))

    def test_build_settlement_status_text(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
        )
        text = build_settlement_status_text(
            match=match,
            home_goals=2,
            away_goals=1,
            settlement={
                "result": "HOME_WIN",
                "predicted_handicap": "-0.5 主让",
                "handicap_is_correct": True,
                "predicted_total_goals": "3球",
                "total_goals": 3,
                "total_goals_is_correct": True,
                "score_is_correct": False,
            },
            mark_text_fn=lambda v: "Y" if v else "N",
        )
        self.assertIn("已结算 A 2-1 B", text)
        self.assertIn("赛果:HOME_WIN", text)
        self.assertIn("命中:Y", text)
        self.assertIn("比分命中:N", text)


if __name__ == "__main__":
    unittest.main()
