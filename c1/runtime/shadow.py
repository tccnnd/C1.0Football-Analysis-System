from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from c1.audit import C1AuditStore
from c1.core.schema import FeatureSnapshot, GovernanceDecision, PredictionSnapshot
from c1.features import build_governance_feature_snapshot
from c1.inference import C1InferenceEngine, InferenceResult, build_inference_input
from c1.modules.judge import GovernanceJudge, load_governance_config
from c1.translation import C1TranslationEngine, TranslationResult, build_translation_request


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass(slots=True)
class C1ShadowRunResult:
    match_id: str
    feature_snapshot: FeatureSnapshot
    prediction_snapshot: PredictionSnapshot
    inference_result: InferenceResult
    governance_decision: GovernanceDecision
    translation_result: TranslationResult
    audit_metadata: dict[str, Any]


class C1ShadowRunner:
    def __init__(
        self,
        project_root: str | Path,
        *,
        audit_dir: str | Path | None = None,
        governance_config: dict[str, Any] | None = None,
        translation_config: dict[str, Any] | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.audit = C1AuditStore(self.project_root, audit_dir=audit_dir)
        self.governance_config = governance_config or load_governance_config(
            self.project_root / "c1" / "configs" / "governance_cfg.yaml"
        )
        self.inference = C1InferenceEngine(self.project_root)
        self.governance = GovernanceJudge(config=self.governance_config)
        self.translation = C1TranslationEngine(config=translation_config)

    def run_match(
        self,
        *,
        match_id: str,
        raw_fields: dict[str, Any],
        governance_state: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        enable_xgboost: bool = True,
        enable_lightgbm: bool = False,
        created_at: str | None = None,
    ) -> C1ShadowRunResult:
        run_time = created_at or _now_text()
        preliminary_snapshot = build_governance_feature_snapshot(
            match_id=match_id,
            raw_fields=raw_fields,
            config=self.governance_config,
            created_at=run_time,
        )
        inference_input = build_inference_input(
            match_id=match_id,
            feature_snapshot=preliminary_snapshot,
            metadata=context or {},
        )
        inference_result = self.inference.infer(
            inference_input,
            enable_xgboost=enable_xgboost,
            enable_lightgbm=enable_lightgbm,
        )
        prediction_snapshot = self._build_prediction_snapshot(inference_result, created_at=run_time)
        feature_snapshot = build_governance_feature_snapshot(
            match_id=match_id,
            raw_fields=raw_fields,
            prediction_snapshot=prediction_snapshot,
            config=self.governance_config,
            created_at=run_time,
        )
        governance_decision = self.governance.evaluate(
            request=self._build_governance_request(
                match_id=match_id,
                feature_snapshot=feature_snapshot,
                prediction_snapshot=prediction_snapshot,
                governance_state=governance_state or {},
                context=context or {},
            )
        )
        translation_result = self.translation.translate(
            build_translation_request(
                match_id=match_id,
                feature_snapshot=feature_snapshot,
                inference_result=inference_result,
                governance_decision=governance_decision,
                context=context or {},
            )
        )

        common_metadata = {
            "run_mode": "shadow",
            "pipeline": "data->features->inference->governance->translation->audit",
            "xgboost_enabled": enable_xgboost,
            "lightgbm_enabled": enable_lightgbm,
        }
        feature_record = self.audit.record_feature_vector(
            snapshot=feature_snapshot,
            attribution_tags=["shadow", "c1"],
            metadata=common_metadata,
        )
        prediction_record = self.audit.record_prediction(
            match_id=match_id,
            feature_snapshot=feature_snapshot,
            prediction_snapshot=prediction_snapshot,
            attribution_tags=["shadow", "c1"],
            metadata=common_metadata,
        )
        governance_record = self.audit.record_governance_decision(
            match_id=match_id,
            feature_snapshot=feature_snapshot,
            prediction_snapshot=prediction_snapshot,
            governance_decision=governance_decision,
            attribution_tags=["shadow", "c1"],
            metadata=common_metadata,
        )
        translation_record = self.audit.record_translation_output(
            match_id=match_id,
            feature_snapshot=feature_snapshot,
            prediction_snapshot=prediction_snapshot,
            governance_decision=governance_decision,
            translation_result=translation_result,
            attribution_tags=["shadow", "c1"],
            metadata=common_metadata,
        )
        return C1ShadowRunResult(
            match_id=match_id,
            feature_snapshot=feature_snapshot,
            prediction_snapshot=prediction_snapshot,
            inference_result=inference_result,
            governance_decision=governance_decision,
            translation_result=translation_result,
            audit_metadata={
                "feature_record_id": feature_record["record_id"],
                "prediction_record_id": prediction_record["record_id"],
                "governance_record_id": governance_record["record_id"],
                "translation_record_id": translation_record["record_id"],
            },
        )

    @staticmethod
    def _build_prediction_snapshot(inference_result: InferenceResult, *, created_at: str) -> PredictionSnapshot:
        return PredictionSnapshot(
            model_name=inference_result.model_name,
            raw_probabilities=dict(inference_result.raw_probabilities),
            predicted_side=inference_result.predicted_side,
            confidence=inference_result.confidence,
            created_at=created_at,
            metadata={
                "margin": inference_result.margin,
                "entropy": inference_result.entropy,
                "ev_by_side": dict(inference_result.ev_by_side),
                "calibration": dict(inference_result.calibration),
                "metadata": dict(inference_result.metadata),
            },
        )

    @staticmethod
    def _build_governance_request(
        *,
        match_id: str,
        feature_snapshot: FeatureSnapshot,
        prediction_snapshot: PredictionSnapshot,
        governance_state: dict[str, Any],
        context: dict[str, Any],
    ):
        request_module = __import__("c1.core.schema", fromlist=["GovernanceRequest"])
        return request_module.GovernanceRequest(
            match_id=match_id,
            feature_snapshot=feature_snapshot,
            prediction_snapshot=prediction_snapshot,
            governance_state=governance_state,
            context=context,
        )
