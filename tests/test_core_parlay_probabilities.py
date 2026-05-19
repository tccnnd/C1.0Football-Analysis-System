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

from v24_app.core import AppMatch, auto_settle_pending_parlays, generate_mix_parlay_recommendations, get_parlay_selector_metrics


class CoreParlayProbabilityTests(unittest.TestCase):
    class _FakeStateStore:
        def __init__(self, tickets: list[dict], settlements: list[dict]) -> None:
            self.tickets = tickets
            self.settlements = settlements
            self.saved_tickets: list[dict] | None = None

        def load_parlay_tickets(self) -> list[dict]:
            return self.tickets

        def save_parlay_tickets(self, items: list[dict], limit: int = 1000) -> None:
            self.saved_tickets = items
            self.tickets = items

        def load_settlements(self) -> list[dict]:
            return self.settlements

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

    def test_generated_parlay_legs_keep_source_metadata(self) -> None:
        match = AppMatch(
            home_team="A",
            away_team="B",
            league="L1",
            match_time="20:00",
            match_date="2026-04-05",
            odds_home=2.1,
            odds_draw=3.2,
            odds_away=3.4,
            source="live:titan",
            source_id="titan-123",
        )
        other = self._match("C", "D", "L2", "21:00")
        predictions = {
            match.match_id: {"parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.8266}]},
            other.match_id: {"parlay_eligible_plays": [{"play_type": "handicap", "pick": "+1 让胜", "confidence": 0.7973}]},
        }

        rows = generate_mix_parlay_recommendations([match, other], predictions, limit=5)
        self.assertEqual(len(rows), 1)
        legs = rows[0].get("legs", [])
        self.assertEqual(legs[0]["source"], "live:titan")
        self.assertEqual(legs[0]["source_id"], "titan-123")
        self.assertEqual(legs[1]["source"], "unknown")
        self.assertEqual(legs[1]["source_id"], "")

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

    def test_auto_settle_pending_parlays_skips_untraceable_tickets(self) -> None:
        tickets = [
            {
                "ticket_id": "ready",
                "status": "pending",
                "legs": [
                    {"match_id": "m1", "play_type": "1x2", "pick": "home", "source": "live:titan", "source_id": "s1"},
                    {
                        "match_id": "m2",
                        "play_type": "total_goals",
                        "pick": "over",
                        "source": "live:titan",
                        "source_id": "s2",
                    },
                ],
            },
            {
                "ticket_id": "missing-source",
                "status": "pending",
                "legs": [
                    {"match_id": "m1", "play_type": "1x2", "pick": "home"},
                    {"match_id": "m2", "play_type": "total_goals", "pick": "over"},
                ],
            },
            {
                "ticket_id": "mixed-source",
                "status": "pending",
                "legs": [
                    {"match_id": "m1", "play_type": "1x2", "pick": "home", "source": "live:titan", "source_id": "s1"},
                    {"match_id": "m2", "play_type": "total_goals", "pick": "over", "source": "cache", "source_id": "s2"},
                ],
            },
        ]
        settlements = [
            {"match_id": "m1", "is_correct": True},
            {"match_id": "m2", "total_goals_is_correct": True},
        ]
        store = self._FakeStateStore(tickets, settlements)

        with patch("v24_app.core.STATE_STORE", store):
            result = auto_settle_pending_parlays()

        self.assertEqual(result["new_settled"], 1)
        self.assertEqual(result["won"], 1)
        self.assertEqual(result["skipped_source_health"], 2)
        self.assertEqual(result["gate"]["status"], "attention")
        self.assertEqual(result["gate"]["ready_ticket_count"], 1)
        self.assertEqual(result["gate"]["manual_review_count"], 2)
        self.assertEqual(
            {item["code"] for item in result["manual_review_items"]},
            {"parlay_source_traceability_missing", "parlay_mixed_sources"},
        )
        saved = store.saved_tickets or []
        by_id = {item["ticket_id"]: item for item in saved}
        self.assertEqual(by_id["ready"]["status"], "won")
        self.assertEqual(by_id["ready"]["leg_results"][0]["source_id"], "s1")
        self.assertEqual(by_id["missing-source"]["status"], "pending")
        self.assertEqual(by_id["missing-source"]["settlement_recovery_gate"]["code"], "parlay_source_traceability_missing")
        self.assertEqual(by_id["mixed-source"]["settlement_recovery_gate"]["code"], "parlay_mixed_sources")

    def test_auto_settle_pending_parlays_clears_stale_gate_after_traceability_fix(self) -> None:
        tickets = [
            {
                "ticket_id": "fixed",
                "status": "pending",
                "settlement_recovery_gate": {"status": "blocked", "code": "parlay_source_traceability_missing"},
                "legs": [
                    {"match_id": "m1", "play_type": "1x2", "pick": "home", "source": "live:titan", "source_id": "s1"},
                    {"match_id": "m2", "play_type": "handicap", "pick": "+1", "source": "live:titan", "source_id": "s2"},
                ],
            }
        ]
        settlements = [
            {"match_id": "m1", "is_correct": True},
            {"match_id": "m2", "handicap_is_correct": False},
        ]
        store = self._FakeStateStore(tickets, settlements)

        with patch("v24_app.core.STATE_STORE", store):
            result = auto_settle_pending_parlays()

        self.assertEqual(result["new_settled"], 1)
        self.assertEqual(result["lost"], 1)
        self.assertEqual(result["skipped_source_health"], 0)
        saved = store.saved_tickets or []
        self.assertNotIn("settlement_recovery_gate", saved[0])


if __name__ == "__main__":
    unittest.main()
