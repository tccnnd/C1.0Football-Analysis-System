from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from c1.core.schema import FeatureSnapshot, GovernanceDecision
from c1.inference.schema import InferenceResult


@dataclass(slots=True)
class TranslationItem:
    play: str
    status: str
    selection: str | None = None
    line: float | None = None
    confidence: float = 0.0
    rationale: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TranslationRequest:
    match_id: str
    feature_snapshot: FeatureSnapshot
    inference_result: InferenceResult
    governance_decision: GovernanceDecision
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TranslationResult:
    match_id: str
    translator_version: str
    governance_action: str
    items: list[TranslationItem]
    metadata: dict[str, Any] = field(default_factory=dict)


def build_translation_request(
    *,
    match_id: str,
    feature_snapshot: FeatureSnapshot,
    inference_result: InferenceResult,
    governance_decision: GovernanceDecision,
    context: dict[str, Any] | None = None,
) -> TranslationRequest:
    return TranslationRequest(
        match_id=match_id,
        feature_snapshot=feature_snapshot,
        inference_result=inference_result,
        governance_decision=governance_decision,
        context=context or {},
    )
