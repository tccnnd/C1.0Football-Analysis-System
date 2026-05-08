from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.core.schema import PredictionSnapshot
from c1.features.governance_features import (
    build_governance_feature_fields,
    build_governance_feature_snapshot,
    compute_chaos_score,
    compute_hours_to_kickoff,
    compute_info_quality,
    compute_line_move_against_model,
    compute_lineup_freshness_hours,
    compute_missing_elo_loss,
    compute_odds_move_against_model,
)
from c1.modules.judge import load_governance_config


class GovernanceFeatureBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_governance_config(PROJECT_ROOT / "c1" / "configs" / "governance_cfg.yaml")

    def base_raw(self, **overrides):
        payload = {
            "context_completeness": 0.90,
            "odds_snapshot_quality": 0.80,
            "team_availability_quality": 0.75,
            "source_reliability": 0.85,
            "data_freshness_hours": 3,
            "lineup_known": True,
            "lineup_freshness_hours": 4,
            "home_rating": 1530,
            "away_rating": 1495,
            "market_side": "home",
            "market_divergence": 0.10,
            "injury_conflict_score": 0.15,
            "schedule_pressure": 0.20,
            "weather_risk": 0.10,
            "environment_safe": True,
            "opening_odds_home": 1.90,
            "current_odds_home": 1.98,
            "opening_odds_away": 4.20,
            "current_odds_away": 4.05,
            "opening_handicap_line": -0.50,
            "current_handicap_line": -0.25,
        }
        payload.update(overrides)
        return payload

    def prediction(self, **overrides):
        data = {
            "model_name": "stage5",
            "raw_probabilities": {"home": 0.56, "draw": 0.24, "away": 0.20},
            "predicted_side": "home",
            "confidence": 0.56,
        }
        data.update(overrides)
        return PredictionSnapshot(**data)

    def test_compute_lineup_freshness_from_timestamp(self) -> None:
        now = datetime(2026, 4, 3, 12, 0, 0)
        hours = compute_lineup_freshness_hours(
            {"lineup_known": True, "lineup_updated_at": "2026-04-03 08:30:00"},
            now=now,
        )
        self.assertAlmostEqual(hours, 3.5)

    def test_compute_hours_to_kickoff(self) -> None:
        now = datetime(2026, 4, 3, 12, 0, 0)
        hours = compute_hours_to_kickoff(
            {"match_date": "2026-04-03", "match_time": "15:30"},
            now=now,
        )
        self.assertAlmostEqual(hours or 0.0, 3.5)

    def test_compute_missing_elo_loss_from_missing_rating(self) -> None:
        loss = compute_missing_elo_loss({"home_rating": 1530, "away_rating": None})
        self.assertEqual(loss, 0.5)

    def test_compute_odds_move_against_model_uses_predicted_side(self) -> None:
        move = compute_odds_move_against_model(
            self.base_raw(),
            prediction_snapshot=self.prediction(predicted_side="home"),
        )
        self.assertAlmostEqual(move, round((1.98 - 1.90) / 1.90, 4))

    def test_compute_line_move_against_model_for_away(self) -> None:
        move = compute_line_move_against_model(
            self.base_raw(opening_handicap_line=-0.25, current_handicap_line=-0.75),
            prediction_snapshot=self.prediction(predicted_side="away"),
        )
        self.assertGreater(move, 0.0)

    def test_compute_info_quality_is_bounded(self) -> None:
        quality = compute_info_quality(self.base_raw(), self.config)
        self.assertGreaterEqual(quality, 0.0)
        self.assertLessEqual(quality, 1.0)

    def test_compute_chaos_score_increases_with_risk(self) -> None:
        low = compute_chaos_score(self.base_raw(market_divergence=0.05, injury_conflict_score=0.10), self.config)
        high = compute_chaos_score(self.base_raw(market_divergence=0.40, injury_conflict_score=0.90, lineup_known=False), self.config)
        self.assertGreater(high, low)

    def test_build_feature_fields_emits_required_governance_fields(self) -> None:
        fields = build_governance_feature_fields(
            self.base_raw(),
            prediction_snapshot=self.prediction(),
            config=self.config,
        )
        for key in (
            "info_quality",
            "lineup_known",
            "lineup_freshness_hours",
            "kickoff_hours_to_match",
            "missing_elo_loss",
            "chaos_score",
            "odds_move_against_model",
            "line_move_against_model",
        ):
            self.assertIn(key, fields)

    def test_build_feature_snapshot_wraps_fields(self) -> None:
        snapshot = build_governance_feature_snapshot(
            match_id="m-governance-1",
            raw_fields=self.base_raw(),
            prediction_snapshot=self.prediction(),
            config=self.config,
            created_at="2026-04-03 12:00:00",
        )
        self.assertEqual(snapshot.match_id, "m-governance-1")
        self.assertEqual(snapshot.feature_version, "c1.phase2")
        self.assertEqual(snapshot.created_at, "2026-04-03 12:00:00")
        self.assertIn("chaos_score", snapshot.fields)


if __name__ == "__main__":
    unittest.main()
