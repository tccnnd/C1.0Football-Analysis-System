from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .reason_codes import DecisionAction, ReasonCode, ReasonSeverity


@dataclass(slots=True)
class FeatureSnapshot:
    match_id: str
    feature_version: str
    fields: dict[str, Any]
    source: str = "unknown"
    created_at: str | None = None


@dataclass(slots=True)
class PredictionSnapshot:
    model_name: str
    raw_probabilities: dict[str, float]
    predicted_side: str
    confidence: float
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReasonRecord:
    code: ReasonCode
    severity: ReasonSeverity
    gate: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GateEvaluation:
    gate: str
    status: str
    reasons: list[ReasonRecord] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GovernanceRequest:
    match_id: str
    feature_snapshot: FeatureSnapshot
    prediction_snapshot: PredictionSnapshot
    governance_state: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GovernanceDecision:
    match_id: str
    action: DecisionAction
    allow_output: bool
    shadow_mode: bool
    reasons: list[ReasonRecord]
    gate_results: list[GateEvaluation]
    governance_version: str
    reason_codes: list[str]
    tags: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

