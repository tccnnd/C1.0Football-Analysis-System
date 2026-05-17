from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.data import (
    ACTION_FACT_SCHEMA_VERSION,
    MATCH_FACT_SCHEMA_VERSION,
    SOURCE_PROVENANCE_SCHEMA_VERSION,
    ActionFact,
    MatchFact,
    SourceProvenance,
    build_action_fact,
    build_match_fact,
    build_source_provenance,
)


class C1FactContractTests(unittest.TestCase):
    def test_build_match_fact_keeps_match_grain_and_provenance(self) -> None:
        fact = build_match_fact(
            {
                "match_id": "2026-06-01|wc|ARG|FRA",
                "provider": "statsbomb",
                "source_id": "m1",
                "competition_id": "wc",
                "season_id": "2026",
                "stage": "final",
                "kickoff_at_utc": "2026-06-01T18:00:00Z",
                "status": "finished",
                "home_team_id": "ARG",
                "away_team_id": "FRA",
                "home_score_ft": "2",
                "away_score_ft": "1",
                "winning_team_id": "ARG",
                "home_lineup": [{"player_id": "p1"}],
                "away_lineup": [{"player_id": "p2"}],
                "referees": [{"name": "R"}],
                "odds_open_home": "2.10",
                "odds_close_home": "1.95",
                "data_freshness_minutes": "12.5",
            }
        )

        self.assertIsInstance(fact, MatchFact)
        self.assertEqual(fact.schema_version, MATCH_FACT_SCHEMA_VERSION)
        self.assertEqual(fact.match_id, "2026-06-01|wc|ARG|FRA")
        self.assertEqual(fact.provider_match_ids, {"statsbomb": "m1"})
        self.assertEqual(fact.source.provider, "statsbomb")
        self.assertEqual(fact.home_score_ft, 2)
        self.assertEqual(fact.away_score_ft, 1)
        self.assertEqual(fact.odds_open_home, 2.1)
        self.assertEqual(fact.data_freshness_minutes, 12.5)
        self.assertEqual(fact.validate(), [])
        self.assertEqual(fact.to_dict()["source"]["schema_version"], SOURCE_PROVENANCE_SCHEMA_VERSION)

    def test_match_fact_rejects_event_level_payload(self) -> None:
        with self.assertRaisesRegex(ValueError, "MatchFact cannot contain event/action arrays"):
            build_match_fact(
                {
                    "match_id": "m1",
                    "home_team_id": "h",
                    "away_team_id": "a",
                    "events": [{"id": "e1"}],
                }
            )

    def test_match_fact_validates_conditional_scores_and_winner(self) -> None:
        fact = build_match_fact(
            {
                "match_id": "m1",
                "home_team_id": "h",
                "away_team_id": "a",
                "status": "finished",
                "has_extratime": True,
                "has_shootout": True,
                "home_score_ft": 2,
                "away_score_ft": 1,
                "winning_team_id": "a",
                "provider_match_ids": {"manual": "m1"},
            }
        )

        self.assertIn("missing_extratime_score", fact.validate())
        self.assertIn("missing_shootout_score", fact.validate())
        self.assertIn("winning_team_mismatch", fact.validate())

    def test_build_action_fact_maps_spadl_like_fields(self) -> None:
        action = build_action_fact(
            {
                "action_id": "a1",
                "game_id": "m1",
                "original_event_id": "e1",
                "provider": "statsbomb",
                "seq_no": 7,
                "period_id": "1",
                "time_seconds": "123.4",
                "team_id": "h",
                "player_id": "p1",
                "action_family": "pass",
                "type_name": "cross",
                "result_name": "success",
                "bodypart_name": "foot",
                "start_x": 30,
                "start_y": 44,
                "end_x": 92,
                "end_y": 28,
                "possession_id": "pos1",
                "phase_id": "phase1",
                "score_for": 1,
                "score_against": 0,
            }
        )

        self.assertIsInstance(action, ActionFact)
        self.assertEqual(action.schema_version, ACTION_FACT_SCHEMA_VERSION)
        self.assertEqual(action.match_id, "m1")
        self.assertEqual(action.source_event_id, "e1")
        self.assertEqual(action.action_type, "cross")
        self.assertEqual(action.result, "success")
        self.assertEqual(action.bodypart, "foot")
        self.assertEqual(action.validate(), [])

    def test_action_fact_validates_coordinate_and_traceability_rules(self) -> None:
        action = build_action_fact(
            {
                "action_id": "a1",
                "match_id": "m1",
                "seq_no": -1,
                "period": "1",
                "time_seconds": -5,
                "team_id": "h",
                "player_id": "p1",
                "action_family": "shot",
                "action_type": "shot",
                "result": "success",
                "start_x": 121,
                "start_y": 81,
            }
        )

        issues = action.validate()
        self.assertIn("negative_seq_no", issues)
        self.assertIn("negative_time_seconds", issues)
        self.assertIn("start_x_out_of_range", issues)
        self.assertIn("start_y_out_of_range", issues)
        self.assertIn("missing_source_event_id", issues)

    def test_synthetic_action_allows_missing_source_event_id(self) -> None:
        action = build_action_fact(
            {
                "action_id": "synthetic-1",
                "match_id": "m1",
                "seq_no": 3,
                "period": "1",
                "time_seconds": 44,
                "team_id": "h",
                "player_id": "p1",
                "action_family": "carry",
                "action_type": "dribble",
                "result": "success",
                "is_synthetic": True,
            }
        )

        self.assertNotIn("missing_source_event_id", action.validate())

    def test_build_source_provenance_accepts_source_aliases(self) -> None:
        source = build_source_provenance(
            {
                "source": "football-data",
                "provider_match_id": "fd-1",
                "version": "2026-05-18",
                "url": "https://example.test/matches/fd-1",
            }
        )

        self.assertIsInstance(source, SourceProvenance)
        self.assertEqual(source.provider, "football-data")
        self.assertEqual(source.source_id, "fd-1")
        self.assertEqual(source.source_version, "2026-05-18")
        self.assertEqual(source.source_vendor, "football-data")


if __name__ == "__main__":
    unittest.main()
