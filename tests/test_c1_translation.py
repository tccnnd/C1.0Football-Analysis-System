from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.core.reason_codes import DecisionAction
from c1.core.schema import FeatureSnapshot, GovernanceDecision, PredictionSnapshot
from c1.inference.schema import InferenceComponent, InferenceResult
from c1.translation import C1TranslationEngine, build_translation_request, load_translation_config


class C1TranslationTests(unittest.TestCase):
    def feature_snapshot(self, **overrides: object) -> FeatureSnapshot:
        fields = {
            "league": "Friendly",
            "odds_home": 1.86,
            "odds_draw": 3.30,
            "odds_away": 4.25,
            "home_rating": 1540,
            "away_rating": 1495,
            "handicap_line": -0.5,
            "total_goals_line": 2.5,
        }
        fields.update(overrides)
        return FeatureSnapshot(
            match_id="2026-04-03|friendly|A|B",
            feature_version="c1.phase2",
            source="unit",
            fields=fields,
        )

    def inference_result(
        self,
        *,
        probabilities: dict[str, float] | None = None,
        predicted_side: str = "home",
        confidence: float = 0.71,
        expected_goals: float = 2.9,
    ) -> InferenceResult:
        probs = probabilities or {"home": 0.54, "draw": 0.24, "away": 0.22}
        return InferenceResult(
            match_id="2026-04-03|friendly|A|B",
            model_name="c1.phase4.inference",
            raw_probabilities=probs,
            predicted_side=predicted_side,
            confidence=confidence,
            margin=0.12,
            entropy=1.4,
            ev_by_side={
                "home": round(probs["home"] * 1.86 - 1.0, 6),
                "draw": round(probs["draw"] * 3.30 - 1.0, 6),
                "away": round(probs["away"] * 4.25 - 1.0, 6),
            },
            components=[InferenceComponent(name="market", probabilities=probs)],
            calibration={"weights": {"market": 1.0}},
            metadata={"expected_goals": expected_goals},
        )

    def governance_decision(self, action: DecisionAction) -> GovernanceDecision:
        return GovernanceDecision(
            match_id="2026-04-03|friendly|A|B",
            action=action,
            allow_output=action != DecisionAction.BLOCK,
            shadow_mode=action == DecisionAction.OBSERVE,
            reasons=[],
            gate_results=[],
            governance_version="c1.phase1",
            reason_codes=[],
        )

    def test_load_translation_config(self) -> None:
        config = load_translation_config()
        self.assertIn("one_x_two", config)
        self.assertIn("handicap", config)
        self.assertIn("totals", config)

    def test_translate_one_x_two_active(self) -> None:
        engine = C1TranslationEngine()
        request = build_translation_request(
            match_id="2026-04-03|friendly|A|B",
            feature_snapshot=self.feature_snapshot(),
            inference_result=self.inference_result(),
            governance_decision=self.governance_decision(DecisionAction.APPROVE),
        )
        result = engine.translate(request)
        one_x_two = next(item for item in result.items if item.play == "1x2")
        self.assertEqual(one_x_two.status, "ACTIVE")
        self.assertEqual(one_x_two.selection, "HOME_WIN")

    def test_handicap_translation_is_not_naive_from_home_win_probability(self) -> None:
        engine = C1TranslationEngine()
        request = build_translation_request(
            match_id="2026-04-03|friendly|A|B",
            feature_snapshot=self.feature_snapshot(handicap_line=-1.5, home_rating=1510, away_rating=1498),
            inference_result=self.inference_result(
                probabilities={"home": 0.58, "draw": 0.26, "away": 0.16},
                confidence=0.74,
                expected_goals=2.15,
            ),
            governance_decision=self.governance_decision(DecisionAction.APPROVE),
        )
        result = engine.translate(request)
        handicap = next(item for item in result.items if item.play == "handicap")
        self.assertNotEqual(handicap.selection, "HOME_HANDICAP")
        self.assertIn("no_naive_1x2_mapping", handicap.tags)

    def test_totals_translation_uses_expected_goals(self) -> None:
        engine = C1TranslationEngine()
        request = build_translation_request(
            match_id="2026-04-03|friendly|A|B",
            feature_snapshot=self.feature_snapshot(total_goals_line=2.5),
            inference_result=self.inference_result(expected_goals=3.05),
            governance_decision=self.governance_decision(DecisionAction.APPROVE),
        )
        result = engine.translate(request)
        totals = next(item for item in result.items if item.play == "totals")
        self.assertEqual(totals.selection, "OVER")

    def test_governance_block_blocks_all_outputs(self) -> None:
        engine = C1TranslationEngine()
        request = build_translation_request(
            match_id="2026-04-03|friendly|A|B",
            feature_snapshot=self.feature_snapshot(),
            inference_result=self.inference_result(),
            governance_decision=self.governance_decision(DecisionAction.BLOCK),
        )
        result = engine.translate(request)
        self.assertTrue(all(item.status == "BLOCKED" for item in result.items))
        self.assertTrue(all(item.selection is None for item in result.items))

    def test_governance_observe_keeps_shadow_status(self) -> None:
        engine = C1TranslationEngine()
        request = build_translation_request(
            match_id="2026-04-03|friendly|A|B",
            feature_snapshot=self.feature_snapshot(),
            inference_result=self.inference_result(),
            governance_decision=self.governance_decision(DecisionAction.OBSERVE),
        )
        result = engine.translate(request)
        one_x_two = next(item for item in result.items if item.play == "1x2")
        self.assertEqual(one_x_two.status, "SHADOW")


if __name__ == "__main__":
    unittest.main()
