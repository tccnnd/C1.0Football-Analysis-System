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
from v24_app.ui_modules import build_parlay_detail_lines, refresh_parlay_recommendations


class UIParlayFlowModuleTests(unittest.TestCase):
    def test_refresh_parlay_recommendations(self) -> None:
        match_a = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="19:35",
            match_date="2026-04-04",
            odds_home=1.9,
            odds_draw=3.2,
            odds_away=4.1,
        )
        match_b = AppMatch(
            home_team="C",
            away_team="D",
            league="L2",
            match_time="20:00",
            match_date="2026-04-04",
            odds_home=2.1,
            odds_draw=3.1,
            odds_away=3.7,
        )
        predictions = {
            match_a.match_id: {"confidence": 0.6},
            match_b.match_id: {"confidence": 0.55},
        }

        def fake_generator(matches, candidate_predictions, limit):
            self.assertEqual(len(matches), 2)
            self.assertEqual(len(candidate_predictions), 2)
            self.assertEqual(limit, 5)
            return [{"legs": [{"play_type": "1x2", "home_team": "A", "away_team": "B", "pick": "主胜"}, {"play_type": "totals", "home_team": "C", "away_team": "D", "pick": "2球"}], "expected_hit": 0.33}]

        rows = refresh_parlay_recommendations(
            matches=[match_a, match_b],
            predictions=predictions,
            active_release_allowed_ids=set(),
            generator_fn=fake_generator,
            limit=5,
        )
        self.assertEqual(len(rows), 1)

    def test_build_parlay_detail_lines(self) -> None:
        lines = build_parlay_detail_lines(
            [
                {
                    "legs": [
                        {"play_type": "1x2", "home_team": "A", "away_team": "B", "pick": "主胜"},
                        {"play_type": "totals", "home_team": "C", "away_team": "D", "pick": "2球"},
                    ],
                    "expected_hit": 0.33,
                    "expected_hit_raw": 0.41,
                    "correlation_discount": 0.88,
                }
            ]
        )
        self.assertEqual(lines[0], "二串一推荐")
        self.assertIn("[1x2] A vs B 主胜", lines[1])
        self.assertIn("33.0%", lines[1])
        self.assertIn("raw=41.0%", lines[2])
        self.assertEqual(build_parlay_detail_lines([]), [])


if __name__ == "__main__":
    unittest.main()
