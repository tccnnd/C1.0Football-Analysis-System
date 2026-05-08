from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.core.reason_codes import DecisionAction, ReasonCode
from c1.core.schema import FeatureSnapshot, PredictionSnapshot
from c1.modules.judge import GovernanceJudge, load_governance_config


class GovernanceJudgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_governance_config(PROJECT_ROOT / "c1" / "configs" / "governance_cfg.yaml")

    def make_feature_snapshot(self, **fields):
        base_fields = {
            "info_quality": 0.90,
            "lineup_known": True,
            "lineup_freshness_hours": 2,
            "kickoff_hours_to_match": 1.0,
            "missing_elo_loss": 0.01,
            "environment_safe": True,
            "market_side": "home",
            "market_divergence": 0.03,
            "injury_conflict_score": 0.0,
            "chaos_score": 0.20,
            "odds_move_against_model": 0.01,
            "line_move_against_model": 0.01,
        }
        base_fields.update(fields)
        return FeatureSnapshot(
            match_id="2026-04-03|test|A|B",
            feature_version="c1.phase1",
            fields=base_fields,
            source="unit",
        )

    def make_prediction_snapshot(self, **kwargs):
        payload = {
            "model_name": "stage5",
            "raw_probabilities": {"home": 0.58, "draw": 0.24, "away": 0.18},
            "predicted_side": "home",
            "confidence": 0.58,
        }
        payload.update(kwargs)
        return PredictionSnapshot(**payload)

    def test_clean_request_is_approved(self) -> None:
        judge = GovernanceJudge(config=self.config)
        decision = judge.evaluate(
            request=__import__("c1.core.schema", fromlist=["GovernanceRequest"]).GovernanceRequest(
                match_id="m1",
                feature_snapshot=self.make_feature_snapshot(),
                prediction_snapshot=self.make_prediction_snapshot(),
                governance_state={},
            )
        )
        self.assertEqual(decision.action, DecisionAction.APPROVE)
        self.assertTrue(decision.allow_output)
        self.assertFalse(decision.reasons)

    def test_high_confidence_low_info_goes_observe(self) -> None:
        judge = GovernanceJudge(config=self.config)
        request = __import__("c1.core.schema", fromlist=["GovernanceRequest"]).GovernanceRequest(
            match_id="m2",
            feature_snapshot=self.make_feature_snapshot(info_quality=0.42, lineup_known=False),
            prediction_snapshot=self.make_prediction_snapshot(confidence=0.74),
            governance_state={},
        )
        decision = judge.evaluate(request)
        self.assertEqual(decision.action, DecisionAction.OBSERVE)
        self.assertIn(ReasonCode.HIGH_CONFIDENCE_LOW_INFO.value, decision.reason_codes)

    def test_lineup_unknown_not_enforced_when_far_from_kickoff(self) -> None:
        judge = GovernanceJudge(config=self.config)
        request = __import__("c1.core.schema", fromlist=["GovernanceRequest"]).GovernanceRequest(
            match_id="m2b",
            feature_snapshot=self.make_feature_snapshot(
                info_quality=0.90,
                lineup_known=False,
                kickoff_hours_to_match=8.0,
            ),
            prediction_snapshot=self.make_prediction_snapshot(confidence=0.60),
            governance_state={},
        )
        decision = judge.evaluate(request)
        self.assertEqual(decision.action, DecisionAction.APPROVE)
        self.assertNotIn(ReasonCode.LINEUP_UNKNOWN.value, decision.reason_codes)

    def test_injury_conflict_blocks(self) -> None:
        judge = GovernanceJudge(config=self.config)
        request = __import__("c1.core.schema", fromlist=["GovernanceRequest"]).GovernanceRequest(
            match_id="m3",
            feature_snapshot=self.make_feature_snapshot(injury_conflict_score=0.91),
            prediction_snapshot=self.make_prediction_snapshot(predicted_side="away"),
            governance_state={},
        )
        decision = judge.evaluate(request)
        self.assertEqual(decision.action, DecisionAction.BLOCK)
        self.assertIn(ReasonCode.INJURY_CONFLICT.value, decision.reason_codes)

    def test_market_conflict_uses_predicted_side(self) -> None:
        judge = GovernanceJudge(config=self.config)
        request = __import__("c1.core.schema", fromlist=["GovernanceRequest"]).GovernanceRequest(
            match_id="m4",
            feature_snapshot=self.make_feature_snapshot(market_side="home", market_divergence=0.16),
            prediction_snapshot=self.make_prediction_snapshot(
                predicted_side="away",
                raw_probabilities={"home": 0.22, "draw": 0.24, "away": 0.54},
                confidence=0.54,
            ),
            governance_state={},
        )
        decision = judge.evaluate(request)
        self.assertEqual(decision.action, DecisionAction.DOWNGRADE)
        self.assertIn(ReasonCode.MARKET_DIVERGENCE_SOFT.value, decision.reason_codes)
        market_reason = next(reason for reason in decision.reasons if reason.code == ReasonCode.MARKET_DIVERGENCE_SOFT)
        self.assertEqual(market_reason.evidence["predicted_side"], "away")

    def test_circuit_breaker_blocks(self) -> None:
        judge = GovernanceJudge(config=self.config)
        request = __import__("c1.core.schema", fromlist=["GovernanceRequest"]).GovernanceRequest(
            match_id="m5",
            feature_snapshot=self.make_feature_snapshot(),
            prediction_snapshot=self.make_prediction_snapshot(),
            governance_state={"losing_streak": 6},
        )
        decision = judge.evaluate(request)
        self.assertEqual(decision.action, DecisionAction.BLOCK)
        self.assertIn(ReasonCode.CIRCUIT_BREAKER_ACTIVE.value, decision.reason_codes)


if __name__ == "__main__":
    unittest.main()
