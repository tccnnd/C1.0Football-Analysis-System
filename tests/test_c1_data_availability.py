from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.data import build_match_context, build_team_availability


class C1DataAvailabilityTests(unittest.TestCase):
    def test_build_team_availability_uses_explicit_fields(self) -> None:
        payload = {
            "home_availability_known": True,
            "home_availability_updated_at": "2026-04-03 18:00:00",
            "home_availability_freshness_hours": 2,
            "home_absent_count": 2,
            "home_key_absent_count": 1,
            "home_availability_score": 0.74,
        }
        availability = build_team_availability(payload, side="home", team_name="A")
        self.assertTrue(availability.known)
        self.assertEqual(availability.team, "A")
        self.assertEqual(availability.absences, 2)
        self.assertEqual(availability.key_absences, 1)
        self.assertEqual(availability.availability_score, 0.74)

    def test_build_match_context_derives_quality_and_injury_conflict(self) -> None:
        payload = {
            "lineup_known": True,
            "lineup_updated_at": "2026-04-03 18:00:00",
            "lineup_freshness_hours": 2,
            "home_absent_count": 3,
            "away_absent_count": 0,
            "home_key_absent_count": 2,
            "away_key_absent_count": 0,
            "schedule_pressure": 0.18,
            "weather_risk": 0.12,
            "environment_safe": True,
        }
        context, home, away = build_match_context(payload, match_id="m1", home_team="A", away_team="B")
        self.assertTrue(context.lineup_known)
        self.assertGreaterEqual(context.team_availability_quality, 0.0)
        self.assertGreater(context.injury_conflict_score, 0.0)
        self.assertEqual(home.key_absences, 2)
        self.assertEqual(away.key_absences, 0)
