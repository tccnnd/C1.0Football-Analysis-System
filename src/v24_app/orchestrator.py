from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


AGENT_ORDER = (
    "DataHunter",
    "ConflictResolver",
    "MarketEntropy",
    "Simulation",
    "RiskGuardian",
    "StrategyComposer",
)


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _num(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _risk_bucket(value: object) -> str:
    text = _text(value).upper()
    if "HIGH" in text or "高" in text:
        return "high"
    if "MEDIUM" in text or "MID" in text or "中" in text:
        return "medium"
    return "low"


def _agent(
    name: str,
    status: str,
    trigger: str,
    inputs: Mapping[str, object],
    outputs: Mapping[str, object],
    *,
    checks: list[str] | None = None,
    evidence: Mapping[str, object] | None = None,
    rationale: str = "",
    actions: list[str] | None = None,
) -> dict:
    return {
        "name": name,
        "status": status,
        "trigger": trigger,
        "inputs": dict(inputs),
        "outputs": dict(outputs),
        "checks": list(checks or []),
        "evidence": dict(evidence or {}),
        "rationale": _text(rationale, "-"),
        "actions": list(actions or []),
    }


def _overall_status(agent_rows: list[dict]) -> str:
    statuses = {str(item.get("status") or "") for item in agent_rows}
    if "blocked" in statuses:
        return "blocked"
    if "alert" in statuses:
        return "alert"
    if "watch" in statuses:
        return "watch"
    return "completed"


def build_supervisor_orchestration(
    *,
    match: Any,
    prediction_context: Mapping[str, object] | None = None,
    diagnostics: Any | None = None,
) -> dict:
    context = prediction_context if isinstance(prediction_context, Mapping) else {}
    market_entropy = _mapping(context.get("market_entropy"))
    sequence = _mapping(market_entropy.get("sequence"))
    handicap_margin = _mapping(context.get("handicap_margin_consistency"))
    strategy_admission = _mapping(context.get("strategy_admission"))
    market_entropy_risk = _mapping(context.get("market_entropy_risk"))
    probabilities = _mapping(context.get("probabilities"))

    odds_values = [
        _num(getattr(match, "odds_home", 0.0)),
        _num(getattr(match, "odds_draw", 0.0)),
        _num(getattr(match, "odds_away", 0.0)),
    ]
    odds_ready = all(value > 1.0 for value in odds_values)
    source = _text(getattr(match, "source", ""), "unknown")
    source_reports = getattr(diagnostics, "source_reports", None) if diagnostics is not None else None
    source_failures = 0
    if isinstance(source_reports, list):
        source_failures = sum(1 for item in source_reports if isinstance(item, Mapping) and str(item.get("status")) not in {"ready", "ok"})

    data_status = "ready" if odds_ready else "blocked"
    if data_status == "ready" and source_failures > 0:
        data_status = "watch"
    data_actions: list[str] = []
    if not odds_ready:
        data_actions.append("refresh_data")
    if source_failures > 0:
        data_actions.append("inspect_source_failures")

    conflict_status = "ready"
    conflict_score = 1.0
    if not odds_ready:
        conflict_status = "blocked"
        conflict_score = 0.0
    elif source_failures > 0:
        conflict_status = "watch"
        conflict_score = 0.72
    conflict_actions = ["refresh_data"] if conflict_status == "blocked" else (["cross_check_sources"] if conflict_status == "watch" else [])

    entropy_level = _text(market_entropy.get("level"), "LOW").upper()
    entropy_score = _num(market_entropy.get("score"))
    handicap_margin_level = _text(handicap_margin.get("level"), "LOW").upper()
    handicap_margin_score = _num(handicap_margin.get("score"))
    entropy_status = "ready"
    if entropy_level == "HIGH":
        entropy_status = "alert"
    elif entropy_level == "MEDIUM":
        entropy_status = "watch"
    entropy_actions: list[str] = []
    if entropy_level == "HIGH":
        entropy_actions.extend(["manual_market_review", "capture_next_market_snapshot"])
    elif entropy_level == "MEDIUM":
        entropy_actions.append("watch_market_movement")

    confidence = _num(context.get("confidence"))
    simulation_status = "ready" if probabilities and confidence > 0 else "blocked"
    risk_bucket = _risk_bucket(context.get("risk_level"))
    risk_status = "ready"
    if risk_bucket == "high":
        risk_status = "alert"
    elif handicap_margin_level == "HIGH":
        risk_status = "alert"
    elif risk_bucket == "medium" or bool(market_entropy_risk.get("applied")):
        risk_status = "watch"
    elif handicap_margin_level == "MEDIUM":
        risk_status = "watch"
    risk_actions: list[str] = []
    if risk_status == "alert":
        risk_actions.append("keep_observation")
    if handicap_margin_level == "HIGH":
        risk_actions.append("review_handicap_margin_consistency")
    elif handicap_margin_level == "MEDIUM":
        risk_actions.append("downgrade_handicap_watch")

    release_allowed = bool(strategy_admission.get("release_allowed"))
    strategy_status = "ready" if _text(context.get("recommendation")) else "blocked"
    if strategy_status == "ready" and not release_allowed:
        strategy_status = "watch"
    strategy_actions = ["ready_for_report"] if strategy_status == "ready" else (["keep_observation"] if strategy_status == "watch" else ["wait_for_recommendation"])

    agents = [
        _agent(
            "DataHunter",
            data_status,
            "match_loaded",
            {"source": source, "source_failures": source_failures},
            {
                "odds_ready": odds_ready,
                "history_samples": int(_num(sequence.get("sample_count"))),
            },
            checks=["odds_home/draw/away > 1.0", "source diagnostics available", "market history snapshot count"],
            evidence={"odds": odds_values, "source": source, "source_failures": source_failures},
            rationale="Core market data is ready." if data_status == "ready" else "Core market data is incomplete or source quality needs attention.",
            actions=data_actions,
        ),
        _agent(
            "ConflictResolver",
            conflict_status,
            "data_quality_check",
            {"source": source, "source_failures": source_failures},
            {"confidence": round(conflict_score, 3)},
            checks=["source failure count", "odds availability", "data confidence score"],
            evidence={"confidence": round(conflict_score, 3), "odds_ready": odds_ready},
            rationale="No obvious data conflict." if conflict_status == "ready" else "Data quality is not strong enough for automatic release.",
            actions=conflict_actions,
        ),
        _agent(
            "MarketEntropy",
            entropy_status,
            "market_signal_check",
            {
                "level": entropy_level,
                "score": round(entropy_score, 4),
            },
            {
                "signals": list(market_entropy.get("signals")) if isinstance(market_entropy.get("signals"), list) else [],
                "max_step_change": _num(sequence.get("max_step_change")),
                "max_velocity": _num(sequence.get("max_abs_velocity_per_minute")),
            },
            checks=["entropy level", "odds slope", "odds velocity", "Kelly span", "market signals"],
            evidence={
                "level": entropy_level,
                "score": round(entropy_score, 4),
                "signals": list(market_entropy.get("signals")) if isinstance(market_entropy.get("signals"), list) else [],
                "history_samples": int(_num(sequence.get("sample_count"))),
            },
            rationale=(
                "Market pressure is abnormal and requires review."
                if entropy_status == "alert"
                else "Market signal is elevated; keep watching."
                if entropy_status == "watch"
                else "Market signal stays inside normal range."
            ),
            actions=entropy_actions,
        ),
        _agent(
            "Simulation",
            simulation_status,
            "probability_fusion",
            {"model": _text(context.get("model"), "-")},
            {
                "recommendation": _text(context.get("recommendation"), "-"),
                "confidence": round(confidence, 4),
                "expected_goals": round(_num(context.get("expected_goals")), 3),
            },
            checks=["probability distribution exists", "recommendation confidence", "expected goals"],
            evidence={"probabilities": dict(probabilities), "confidence": round(confidence, 4)},
            rationale="Model simulation produced a usable recommendation." if simulation_status == "ready" else "Model simulation output is missing.",
            actions=[] if simulation_status == "ready" else ["rerun_prediction"],
        ),
        _agent(
            "RiskGuardian",
            risk_status,
            "risk_overlay",
            {
                "risk_level": _text(context.get("risk_level"), "-"),
                "base_risk_level": _text(context.get("risk_level_base"), "-"),
            },
            {
                "market_entropy_overlay": bool(market_entropy_risk.get("applied")),
                "handicap_margin_level": handicap_margin_level,
                "handicap_margin_score": round(handicap_margin_score, 4),
                "handicap_margin_signals": (
                    list(handicap_margin.get("signals"))
                    if isinstance(handicap_margin.get("signals"), list)
                    else []
                ),
                "admission_decision": _text(strategy_admission.get("decision"), "-"),
            },
            checks=["risk bucket", "market entropy overlay", "handicap margin consistency", "strategy admission"],
            evidence={
                "risk_bucket": risk_bucket,
                "market_entropy_level": entropy_level,
                "handicap_margin_level": handicap_margin_level,
                "handicap_margin_score": round(handicap_margin_score, 4),
                "release_allowed": release_allowed,
            },
            rationale=(
                "Risk signals require manual review before release."
                if risk_status == "alert"
                else "Risk is elevated; keep the match in watch mode."
                if risk_status == "watch"
                else "No blocking risk overlay is active."
            ),
            actions=risk_actions,
        ),
        _agent(
            "StrategyComposer",
            strategy_status,
            "report_ready_check",
            {
                "release_allowed": release_allowed,
                "recommendation": _text(context.get("recommendation"), "-"),
            },
            {
                "single_play_count": int(_num(strategy_admission.get("single_play_count"))),
                "top_play": _text(strategy_admission.get("top_play"), "-"),
                "top_pick": _text(strategy_admission.get("top_pick"), "-"),
            },
            checks=["recommendation exists", "strategy admission", "single play availability", "report readiness"],
            evidence={
                "release_allowed": release_allowed,
                "admission_decision": _text(strategy_admission.get("decision"), "-"),
                "single_play_count": int(_num(strategy_admission.get("single_play_count"))),
            },
            rationale="Report can be generated with release status." if strategy_status != "blocked" else "Report is waiting for a valid recommendation.",
            actions=strategy_actions,
        ),
    ]

    next_actions: list[str] = []
    if not odds_ready:
        next_actions.append("refresh_data")
    if entropy_level == "HIGH":
        next_actions.extend(["manual_market_review", "capture_next_market_snapshot"])
    if handicap_margin_level == "HIGH":
        next_actions.append("review_handicap_margin_consistency")
    if risk_bucket == "high" or not release_allowed:
        next_actions.append("keep_observation")
    if not next_actions:
        next_actions.append("ready_for_report")

    status = _overall_status(agents)
    return {
        "name": "Supervisor",
        "version": "orchestrator_v1",
        "status": status,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "match_id": _text(getattr(match, "match_id", ""), "-"),
        "agents": agents,
        "decision": {
            "release_allowed": bool(release_allowed and status not in {"blocked", "alert"}),
            "requires_human_review": status in {"blocked", "alert"},
            "risk_bucket": risk_bucket,
            "market_entropy_level": entropy_level,
            "handicap_margin_level": handicap_margin_level,
        },
        "next_actions": next_actions,
    }
