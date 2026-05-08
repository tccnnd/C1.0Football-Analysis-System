from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.core import AppMatch, generate_mix_parlay_recommendations, get_parlay_selector_metrics


class CoreParlayProbabilityTests(unittest.TestCase):
    def _match(self, home: str, away: str, league: str, kick: str) -> AppMatch:
        return AppMatch(
            home_team=home,
            away_team=away,
            league=league,
            match_time=kick,
            match_date="2026-04-05",
            odds_home=2.1,
            odds_draw=3.2,
            odds_away=3.4,
        )

    def test_expected_hit_uses_calibrated_probability(self) -> None:
        m1 = self._match("A", "B", "L1", "20:00")
        m2 = self._match("C", "D", "L2", "21:00")
        predictions = {
            m1.match_id: {"parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.8266}]},
            m2.match_id: {"parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.7973}]},
        }
        rows = generate_mix_parlay_recommendations([m1, m2], predictions, limit=5)
        self.assertEqual(len(rows), 1)
        ticket = rows[0]
        raw = float(ticket.get("expected_hit_raw", 0.0))
        calibrated = float(ticket.get("expected_hit", 0.0))
        self.assertAlmostEqual(raw, 0.6590, places=4)
        self.assertLess(calibrated, raw)
        self.assertLess(float(ticket.get("correlation_discount", 1.0)), 1.0)
        self.assertIn("play_reliability_factor", ticket)
        legs = ticket.get("legs", [])
        self.assertTrue(isinstance(legs, list) and len(legs) == 2)
        self.assertIn("calibrated_confidence", legs[0])
        self.assertIn("calibrated_confidence", legs[1])

    def test_same_play_type_has_stronger_discount_than_mixed(self) -> None:
        m1 = self._match("A", "B", "L1", "20:00")
        m2 = self._match("C", "D", "L2", "21:00")
        m3 = self._match("E", "F", "L3", "22:00")
        predictions = {
            m1.match_id: {"parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.8266}]},
            m2.match_id: {"parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.7973}]},
            m3.match_id: {"parlay_eligible_plays": [{"play_type": "total_goals", "pick": "3球", "confidence": 0.3581}]},
        }
        rows = generate_mix_parlay_recommendations([m1, m2, m3], predictions, limit=10)
        same_discounts = []
        mixed_discounts = []
        for item in rows:
            legs = item.get("legs") or []
            if not isinstance(legs, list) or len(legs) != 2:
                continue
            a = str(legs[0].get("play_type", ""))
            b = str(legs[1].get("play_type", ""))
            discount = float(item.get("correlation_discount", 1.0) or 1.0)
            if a == b:
                same_discounts.append(discount)
            else:
                mixed_discounts.append(discount)
        self.assertTrue(same_discounts)
        self.assertTrue(mixed_discounts)
        self.assertLess(max(same_discounts), min(mixed_discounts))

    def test_selection_diversifies_match_exposure(self) -> None:
        matches = [
            self._match("A", "B", "L1", "19:00"),
            self._match("C", "D", "L2", "20:00"),
            self._match("E", "F", "L3", "21:00"),
            self._match("G", "H", "L4", "22:00"),
        ]
        predictions = {
            matches[0].match_id: {
                "indices": {"upset_index": 0.20, "stability_index": 0.78, "confidence_index": 0.76},
                "parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.84}],
            },
            matches[1].match_id: {
                "indices": {"upset_index": 0.25, "stability_index": 0.74, "confidence_index": 0.72},
                "parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.82}],
            },
            matches[2].match_id: {
                "indices": {"upset_index": 0.34, "stability_index": 0.67, "confidence_index": 0.68},
                "parlay_eligible_plays": [{"play_type": "1x2", "pick": "主胜", "confidence": 0.79}],
            },
            matches[3].match_id: {
                "indices": {"upset_index": 0.30, "stability_index": 0.70, "confidence_index": 0.69},
                "parlay_eligible_plays": [{"play_type": "total_goals", "pick": "2球", "confidence": 0.77}],
            },
        }
        rows = generate_mix_parlay_recommendations(matches, predictions, limit=4)
        self.assertEqual(len(rows), 4)
        exposure: dict[str, int] = {}
        for ticket in rows:
            legs = ticket.get("legs") or []
            self.assertEqual(len(legs), 2)
            self.assertIn("pair_quality_factor", ticket)
            for leg in legs:
                match_id = str(leg.get("match_id", ""))
                exposure[match_id] = int(exposure.get(match_id, 0)) + 1
        self.assertTrue(exposure)
        self.assertLessEqual(max(exposure.values()), 2)

    def test_get_parlay_selector_metrics(self) -> None:
        tickets = [
            {
                "ticket_id": "t1",
                "mixed": True,
                "expected_hit": 0.31,
                "correlation_discount": 0.86,
                "max_leg_upset": 0.52,
                "pair_quality_factor": 1.02,
                "play_reliability_factor": 0.98,
                "legs": [{"match_id": "m1"}, {"match_id": "m2"}],
            },
            {
                "ticket_id": "t2",
                "mixed": False,
                "expected_hit": 0.42,
                "correlation_discount": 0.79,
                "max_leg_upset": 0.69,
                "pair_quality_factor": 0.93,
                "play_reliability_factor": 0.95,
                "legs": [{"match_id": "m1"}, {"match_id": "m3"}],
            },
        ]
        with patch("v24_app.core.get_active_parlay_recommendations", return_value=tickets):
            metrics = get_parlay_selector_metrics(limit=20)
        self.assertEqual(metrics.get("ticket_count"), 2)
        self.assertEqual(metrics.get("unique_match_count"), 3)
        self.assertEqual(metrics.get("max_match_exposure"), 2)
        self.assertEqual(metrics.get("high_expected_hit_count"), 1)
        self.assertEqual(metrics.get("low_discount_count"), 1)
        self.assertEqual(metrics.get("high_upset_leg_count"), 1)


if __name__ == "__main__":
    unittest.main()
