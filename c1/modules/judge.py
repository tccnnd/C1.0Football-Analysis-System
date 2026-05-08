from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from c1.core.reason_codes import DecisionAction, ReasonCode, ReasonSeverity
from c1.core.schema import (
    FeatureSnapshot,
    GateEvaluation,
    GovernanceDecision,
    GovernanceRequest,
    PredictionSnapshot,
    ReasonRecord,
)


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "governance_cfg.yaml"
GOVERNANCE_VERSION = "c1.phase1"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "home": "home",
        "draw": "draw",
        "away": "away",
        "主": "home",
        "平": "draw",
        "客": "away",
        "主胜": "home",
        "平局": "draw",
        "客胜": "away",
    }
    return mapping.get(text, text)


def load_governance_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid governance config: {config_path}")
    return payload


def _make_reason(
    *,
    gate: str,
    code: ReasonCode,
    severity: ReasonSeverity,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> ReasonRecord:
    return ReasonRecord(
        code=code,
        severity=severity,
        gate=gate,
        message=message,
        evidence=evidence or {},
    )


@dataclass(slots=True)
class BaseGate:
    name: str

    def evaluate(self, request: GovernanceRequest, config: dict[str, Any]) -> GateEvaluation:
        raise NotImplementedError


class InfoGate(BaseGate):
    def __init__(self) -> None:
        super().__init__(name="InfoGate")

    def evaluate(self, request: GovernanceRequest, config: dict[str, Any]) -> GateEvaluation:
        thresholds = config.get("thresholds", {})
        fields = request.feature_snapshot.fields
        reasons: list[ReasonRecord] = []

        info_quality = _safe_float(fields.get("info_quality"), default=1.0)
        lineup_known = _safe_bool(fields.get("lineup_known"), default=True)
        lineup_freshness_hours = _safe_float(fields.get("lineup_freshness_hours"), default=0.0)
        kickoff_hours_to_match = fields.get("kickoff_hours_to_match")
        if kickoff_hours_to_match in (None, ""):
            kickoff_hours_to_match = None
        else:
            kickoff_hours_to_match = _safe_float(kickoff_hours_to_match, default=0.0)
        lineup_required_within_hours = _safe_float(thresholds.get("lineup_required_within_hours"), 2.0)
        missing_elo_loss = _safe_float(fields.get("missing_elo_loss"), default=0.0)
        confidence = _safe_float(request.prediction_snapshot.confidence, default=0.0)

        if info_quality < _safe_float(thresholds.get("info_quality_critical"), 0.35):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.INFO_QUALITY_CRITICAL,
                    severity=ReasonSeverity.HARD,
                    message="Feature information quality is critically low.",
                    evidence={"info_quality": info_quality},
                )
            )
        elif info_quality < _safe_float(thresholds.get("info_quality_warning"), 0.55):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.INFO_QUALITY_LOW,
                    severity=ReasonSeverity.SOFT,
                    message="Feature information quality is below governance threshold.",
                    evidence={"info_quality": info_quality},
                )
            )

        lineup_required_now = kickoff_hours_to_match is None or kickoff_hours_to_match <= lineup_required_within_hours
        if not lineup_known and lineup_required_now:
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.LINEUP_UNKNOWN,
                    severity=ReasonSeverity.SOFT,
                    message="Lineup information is not confirmed.",
                    evidence={
                        "lineup_known": lineup_known,
                        "kickoff_hours_to_match": kickoff_hours_to_match,
                        "lineup_required_within_hours": lineup_required_within_hours,
                    },
                )
            )

        if lineup_known and lineup_freshness_hours > _safe_float(thresholds.get("lineup_freshness_warning_hours"), 12.0):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.LINEUP_STALE,
                    severity=ReasonSeverity.SOFT,
                    message="Lineup information is stale.",
                    evidence={
                        "lineup_freshness_hours": lineup_freshness_hours,
                        "kickoff_hours_to_match": kickoff_hours_to_match,
                    },
                )
            )

        if missing_elo_loss > _safe_float(thresholds.get("missing_elo_loss_warning"), 0.08):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.MISSING_ELO_LOSS,
                    severity=ReasonSeverity.SOFT,
                    message="Missing Elo signal causes material information loss.",
                    evidence={"missing_elo_loss": missing_elo_loss},
                )
            )

        low_info_trigger = info_quality <= _safe_float(thresholds.get("low_info_high_confidence_quality_max"), 0.50) or (
            (not lineup_known) and lineup_required_now
        )
        if confidence >= _safe_float(thresholds.get("high_confidence_min"), 0.68) and low_info_trigger:
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.HIGH_CONFIDENCE_LOW_INFO,
                    severity=ReasonSeverity.SOFT,
                    message="High-confidence prediction is not supported by enough information quality.",
                    evidence={
                        "confidence": confidence,
                        "info_quality": info_quality,
                        "lineup_known": lineup_known,
                    },
                )
            )

        status = "PASS"
        if any(reason.severity == ReasonSeverity.HARD for reason in reasons):
            status = "FAIL"
        elif reasons:
            status = "WARN"
        return GateEvaluation(
            gate=self.name,
            status=status,
            reasons=reasons,
            metrics={
                "info_quality": info_quality,
                "lineup_known": lineup_known,
                "lineup_freshness_hours": lineup_freshness_hours,
                "kickoff_hours_to_match": kickoff_hours_to_match,
                "missing_elo_loss": missing_elo_loss,
            },
        )


class EnvironmentGate(BaseGate):
    def __init__(self) -> None:
        super().__init__(name="EnvironmentGate")

    def evaluate(self, request: GovernanceRequest, config: dict[str, Any]) -> GateEvaluation:
        thresholds = config.get("thresholds", {})
        fields = request.feature_snapshot.fields
        reasons: list[ReasonRecord] = []

        environment_safe = _safe_bool(fields.get("environment_safe"), default=True)
        odds_move_against_model = _safe_float(fields.get("odds_move_against_model"), default=0.0)
        line_move_against_model = _safe_float(fields.get("line_move_against_model"), default=0.0)

        if not environment_safe:
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.ENVIRONMENT_UNSAFE,
                    severity=ReasonSeverity.HARD,
                    message="Environment gate marked the match context as unsafe.",
                    evidence={"environment_safe": environment_safe},
                )
            )

        if odds_move_against_model >= _safe_float(thresholds.get("odds_move_against_model_warning"), 0.08):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.ODDS_MOVE_AGAINST_MODEL,
                    severity=ReasonSeverity.SOFT,
                    message="Odds moved materially against the model view.",
                    evidence={"odds_move_against_model": odds_move_against_model},
                )
            )

        if line_move_against_model >= _safe_float(thresholds.get("line_move_against_model_warning"), 0.08):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.LINE_MOVE_AGAINST_MODEL,
                    severity=ReasonSeverity.SOFT,
                    message="Line movement diverged against the model view.",
                    evidence={"line_move_against_model": line_move_against_model},
                )
            )

        status = "PASS"
        if any(reason.severity == ReasonSeverity.HARD for reason in reasons):
            status = "FAIL"
        elif reasons:
            status = "WARN"
        return GateEvaluation(
            gate=self.name,
            status=status,
            reasons=reasons,
            metrics={
                "environment_safe": environment_safe,
                "odds_move_against_model": odds_move_against_model,
                "line_move_against_model": line_move_against_model,
            },
        )


class ConflictDetector(BaseGate):
    def __init__(self) -> None:
        super().__init__(name="ConflictDetector")

    def evaluate(self, request: GovernanceRequest, config: dict[str, Any]) -> GateEvaluation:
        thresholds = config.get("thresholds", {})
        fields = request.feature_snapshot.fields
        reasons: list[ReasonRecord] = []

        predicted_side = _normalize_side(request.prediction_snapshot.predicted_side)
        market_side = _normalize_side(fields.get("market_side"))
        market_divergence = _safe_float(fields.get("market_divergence"), default=0.0)
        injury_conflict_score = _safe_float(fields.get("injury_conflict_score"), default=0.0)

        if predicted_side and market_side and predicted_side != market_side:
            hard_threshold = _safe_float(thresholds.get("market_divergence_hard"), 0.22)
            soft_threshold = _safe_float(thresholds.get("market_divergence_soft"), 0.12)
            if market_divergence >= hard_threshold:
                reasons.append(
                    _make_reason(
                        gate=self.name,
                        code=ReasonCode.MARKET_DIVERGENCE_HARD,
                        severity=ReasonSeverity.HARD,
                        message="Predicted side materially conflicts with market direction.",
                        evidence={
                            "predicted_side": predicted_side,
                            "market_side": market_side,
                            "market_divergence": market_divergence,
                        },
                    )
                )
            elif market_divergence >= soft_threshold:
                reasons.append(
                    _make_reason(
                        gate=self.name,
                        code=ReasonCode.MARKET_DIVERGENCE_SOFT,
                        severity=ReasonSeverity.SOFT,
                        message="Predicted side conflicts with market direction.",
                        evidence={
                            "predicted_side": predicted_side,
                            "market_side": market_side,
                            "market_divergence": market_divergence,
                        },
                    )
                )

        hard_injury = _safe_float(thresholds.get("injury_conflict_hard"), 0.70)
        if injury_conflict_score >= hard_injury:
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.INJURY_CONFLICT,
                    severity=ReasonSeverity.HARD,
                    message="Injury conflict exceeds hard governance threshold.",
                    evidence={
                        "predicted_side": predicted_side,
                        "injury_conflict_score": injury_conflict_score,
                    },
                )
            )

        status = "PASS"
        if any(reason.severity == ReasonSeverity.HARD for reason in reasons):
            status = "FAIL"
        elif reasons:
            status = "WARN"
        return GateEvaluation(
            gate=self.name,
            status=status,
            reasons=reasons,
            metrics={
                "predicted_side": predicted_side,
                "market_side": market_side,
                "market_divergence": market_divergence,
                "injury_conflict_score": injury_conflict_score,
            },
        )


class RiskGovernor(BaseGate):
    def __init__(self) -> None:
        super().__init__(name="RiskGovernor")

    def evaluate(self, request: GovernanceRequest, config: dict[str, Any]) -> GateEvaluation:
        thresholds = config.get("thresholds", {})
        chaos_score = _safe_float(request.feature_snapshot.fields.get("chaos_score"), default=0.0)
        reasons: list[ReasonRecord] = []

        if chaos_score >= _safe_float(thresholds.get("chaos_score_block"), 0.82):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.CHAOS_RISK_CRITICAL,
                    severity=ReasonSeverity.HARD,
                    message="Chaos score exceeds the block threshold.",
                    evidence={"chaos_score": chaos_score},
                )
            )
        elif chaos_score >= _safe_float(thresholds.get("chaos_score_observe"), 0.55):
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.CHAOS_RISK_ELEVATED,
                    severity=ReasonSeverity.SOFT,
                    message="Chaos score exceeds the observe threshold.",
                    evidence={"chaos_score": chaos_score},
                )
            )

        status = "PASS"
        if any(reason.severity == ReasonSeverity.HARD for reason in reasons):
            status = "FAIL"
        elif reasons:
            status = "WARN"
        return GateEvaluation(
            gate=self.name,
            status=status,
            reasons=reasons,
            metrics={"chaos_score": chaos_score},
        )


class CircuitBreaker(BaseGate):
    def __init__(self) -> None:
        super().__init__(name="CircuitBreaker")

    def evaluate(self, request: GovernanceRequest, config: dict[str, Any]) -> GateEvaluation:
        thresholds = config.get("thresholds", {})
        state = request.governance_state or {}
        breaker_active = _safe_bool(state.get("breaker_active"), default=False)
        losing_streak = _safe_float(state.get("losing_streak"), default=0.0)
        threshold = _safe_float(thresholds.get("circuit_breaker_losing_streak"), 5.0)
        reasons: list[ReasonRecord] = []

        if breaker_active or losing_streak >= threshold:
            reasons.append(
                _make_reason(
                    gate=self.name,
                    code=ReasonCode.CIRCUIT_BREAKER_ACTIVE,
                    severity=ReasonSeverity.HARD,
                    message="Circuit breaker is active.",
                    evidence={
                        "breaker_active": breaker_active,
                        "losing_streak": losing_streak,
                        "threshold": threshold,
                    },
                )
            )

        status = "FAIL" if reasons else "PASS"
        return GateEvaluation(
            gate=self.name,
            status=status,
            reasons=reasons,
            metrics={
                "breaker_active": breaker_active,
                "losing_streak": losing_streak,
                "threshold": threshold,
            },
        )


class GovernanceJudge:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_governance_config()
        self.gates: list[BaseGate] = [
            InfoGate(),
            EnvironmentGate(),
            ConflictDetector(),
            RiskGovernor(),
            CircuitBreaker(),
        ]

    def evaluate(self, request: GovernanceRequest) -> GovernanceDecision:
        gate_results = [gate.evaluate(request, self.config) for gate in self.gates]
        reasons = [reason for result in gate_results for reason in result.reasons]
        hard_reasons = [reason for reason in reasons if reason.severity == ReasonSeverity.HARD]
        soft_reasons = [reason for reason in reasons if reason.severity == ReasonSeverity.SOFT]
        soft_codes = {reason.code for reason in soft_reasons}
        decision_rules = self.config.get("decision_rules", {})
        observe_soft_count = int(decision_rules.get("observe_min_soft_conflicts", 3))

        if hard_reasons:
            action = DecisionAction.BLOCK
        elif ReasonCode.HIGH_CONFIDENCE_LOW_INFO in soft_codes:
            action = DecisionAction.OBSERVE
        elif len(soft_reasons) >= observe_soft_count:
            action = DecisionAction.OBSERVE
        elif soft_reasons:
            action = DecisionAction.DOWNGRADE
        else:
            action = DecisionAction.APPROVE

        tags: list[str] = []
        if action == DecisionAction.OBSERVE:
            tags.append("shadow_run")
        if soft_reasons:
            tags.append("risk_flagged")
        if hard_reasons:
            tags.append("blocked")

        return GovernanceDecision(
            match_id=request.match_id,
            action=action,
            allow_output=action != DecisionAction.BLOCK,
            shadow_mode=action == DecisionAction.OBSERVE,
            reasons=reasons,
            gate_results=gate_results,
            governance_version=GOVERNANCE_VERSION,
            reason_codes=[reason.code.value for reason in reasons],
            tags=tags,
            trace={
                "hard_reason_count": len(hard_reasons),
                "soft_reason_count": len(soft_reasons),
                "gate_statuses": {result.gate: result.status for result in gate_results},
                "predicted_side": request.prediction_snapshot.predicted_side,
            },
        )


def evaluate_governance(
    *,
    match_id: str,
    feature_snapshot: FeatureSnapshot,
    prediction_snapshot: PredictionSnapshot,
    governance_state: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> GovernanceDecision:
    judge = GovernanceJudge(config=config)
    request = GovernanceRequest(
        match_id=match_id,
        feature_snapshot=feature_snapshot,
        prediction_snapshot=prediction_snapshot,
        governance_state=governance_state or {},
        context=context or {},
    )
    return judge.evaluate(request)
