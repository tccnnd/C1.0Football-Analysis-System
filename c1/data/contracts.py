from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CanonicalMatch:
    match_id: str
    source: str
    source_id: str
    home_team: str
    away_team: str
    league: str
    match_date: str
    match_time: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OddsSnapshot:
    match_id: str
    source: str
    recorded_at: str | None
    odds_home: float
    odds_draw: float
    odds_away: float
    opening_odds_home: float = 0.0
    opening_odds_draw: float = 0.0
    opening_odds_away: float = 0.0
    handicap_line: float = 0.0
    total_goals_line: float = 2.5
    return_rate: float = 0.0
    kelly_home: float = 0.0
    kelly_draw: float = 0.0
    kelly_away: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TeamAvailability:
    team: str
    known: bool
    updated_at: str | None = None
    freshness_hours: float | None = None
    absences: int = 0
    key_absences: int = 0
    availability_score: float = 0.0
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MatchContext:
    match_id: str
    lineup_known: bool
    lineup_updated_at: str | None = None
    lineup_freshness_hours: float | None = None
    team_availability_quality: float = 0.0
    injury_conflict_score: float = 0.0
    schedule_pressure: float = 0.0
    weather_risk: float = 0.0
    environment_safe: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    text = _as_text(value).lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


@dataclass(slots=True)
class PlayModelTakeoverGateAuditEntry:
    version_id: str
    updated_at: str
    source: str = "backtest"
    previous_status: str | None = None
    status: str = "-"
    transition: str = "-"
    reason: str = "-"
    recommendation: str = "-"
    policy_impact: str = "-"
    blocking_count: int = 0
    warning_count: int = 0
    issue_codes: list[str] = field(default_factory=list)
    validation_sample_count: int = 0
    total_goals_model_delta: float = 0.0
    score_model_delta: float = 0.0
    backtest_ok: bool = False
    backtest_reason: str = "-"
    report_path: str = "-"
    metrics: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlayModelTakeoverGateAuditSummary:
    history_count: int = 0
    latest_status: str | None = None
    latest_previous_status: str | None = None
    latest_transition: str | None = None
    latest_reason: str | None = None
    latest_updated_at: str | None = None
    latest_policy_impact: str | None = None
    latest_backtest_ok: bool = False
    latest_validation_sample_count: int = 0
    latest_total_goals_model_delta: float = 0.0
    latest_score_model_delta: float = 0.0
    latest_report_path: str | None = None


@dataclass(slots=True)
class PlayModelTakeoverGateAuditReport:
    updated_at: str
    history_count: int
    latest_transition: str | None = None
    latest_reason: str | None = None
    markdown_path: str = "-"
    csv_path: str = "-"


def build_play_model_takeover_gate_audit_entry(payload: dict[str, Any] | object) -> PlayModelTakeoverGateAuditEntry:
    item = _as_mapping(payload)
    metrics = _as_mapping(item.get("metrics"))
    validation = _as_mapping(item.get("validation"))
    validation_sample_count = _as_int(metrics.get("validation_sample_count"), _as_int(validation.get("sample_count"), 0))
    issue_codes = [
        _as_text(code)
        for code in (item.get("issue_codes") if isinstance(item.get("issue_codes"), list) else [])
        if _as_text(code)
    ]
    return PlayModelTakeoverGateAuditEntry(
        version_id=_as_text(item.get("version_id"), "-"),
        updated_at=_as_text(item.get("updated_at"), "-"),
        source=_as_text(item.get("source"), "backtest"),
        previous_status=_as_text(item.get("previous_status")) or None,
        status=_as_text(item.get("status"), "-"),
        transition=_as_text(item.get("transition"), "-"),
        reason=_as_text(item.get("reason"), "-"),
        recommendation=_as_text(item.get("recommendation"), "-"),
        policy_impact=_as_text(item.get("policy_impact"), "-"),
        blocking_count=_as_int(item.get("blocking_count"), 0),
        warning_count=_as_int(item.get("warning_count"), 0),
        issue_codes=issue_codes,
        validation_sample_count=validation_sample_count,
        total_goals_model_delta=_as_float(metrics.get("total_goals_model_delta"), 0.0),
        score_model_delta=_as_float(metrics.get("score_model_delta"), 0.0),
        backtest_ok=_as_bool(item.get("backtest_ok"), False),
        backtest_reason=_as_text(item.get("backtest_reason"), "-"),
        report_path=_as_text(item.get("report_path"), "-"),
        metrics=metrics,
        validation=validation,
    )


def build_play_model_takeover_gate_audit_summary(
    payload: dict[str, Any] | object,
) -> PlayModelTakeoverGateAuditSummary:
    item = _as_mapping(payload)
    return PlayModelTakeoverGateAuditSummary(
        history_count=_as_int(item.get("history_count"), 0),
        latest_status=_as_text(item.get("latest_status")) or None,
        latest_previous_status=_as_text(item.get("latest_previous_status")) or None,
        latest_transition=_as_text(item.get("latest_transition")) or None,
        latest_reason=_as_text(item.get("latest_reason")) or None,
        latest_updated_at=_as_text(item.get("latest_updated_at")) or None,
        latest_policy_impact=_as_text(item.get("latest_policy_impact")) or None,
        latest_backtest_ok=_as_bool(item.get("latest_backtest_ok"), False),
        latest_validation_sample_count=_as_int(item.get("latest_validation_sample_count"), 0),
        latest_total_goals_model_delta=_as_float(item.get("latest_total_goals_model_delta"), 0.0),
        latest_score_model_delta=_as_float(item.get("latest_score_model_delta"), 0.0),
        latest_report_path=_as_text(item.get("latest_report_path")) or None,
    )


def build_play_model_takeover_gate_audit_report(
    payload: dict[str, Any] | object,
) -> PlayModelTakeoverGateAuditReport:
    item = _as_mapping(payload)
    return PlayModelTakeoverGateAuditReport(
        updated_at=_as_text(item.get("updated_at"), "-"),
        history_count=_as_int(item.get("history_count"), 0),
        latest_transition=_as_text(item.get("latest_transition")) or None,
        latest_reason=_as_text(item.get("latest_reason")) or None,
        markdown_path=_as_text(item.get("markdown_path"), "-"),
        csv_path=_as_text(item.get("csv_path"), "-"),
    )
