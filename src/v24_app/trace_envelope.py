from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Mapping


TRACE_VERSION = "trace_v1"
DEFAULT_PROMPT_VERSION = "strategy_report_v1"


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _text(value: object, default: str = "-") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _match_attr(match: Any, name: str, default: object = "") -> object:
    return getattr(match, name, default)


def _trace_id_for(*, match_id: str, generated_at: str, status: str, recommendation: str) -> str:
    seed = "|".join([match_id, generated_at, status, recommendation])
    return "trc_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _trace_nodes(supervisor: Mapping[str, object]) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    for index, item in enumerate(_as_list(supervisor.get("agents"))):
        if not isinstance(item, Mapping):
            continue
        name = _text(item.get("name"), f"Agent {index + 1}")
        nodes.append(
            {
                "span_id": f"agent-{index + 1:02d}",
                "parent_id": "supervisor",
                "index": index,
                "name": name,
                "status": _text(item.get("status"), "ready").lower(),
                "trigger": _text(item.get("trigger")),
                "inputs": dict(_as_mapping(item.get("inputs"))),
                "outputs": dict(_as_mapping(item.get("outputs"))),
                "checks": [str(value) for value in _as_list(item.get("checks"))],
                "evidence": dict(_as_mapping(item.get("evidence"))),
                "rationale": _text(item.get("rationale")),
                "actions": [str(value) for value in _as_list(item.get("actions"))],
            }
        )
    return nodes


def _tool_calls_from_nodes(trace_id: str, nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    tool_calls: list[dict[str, object]] = []
    for node in nodes:
        agent = _text(node.get("name"))
        for action in _as_list(node.get("actions")):
            action_text = _text(action, "")
            if not action_text:
                continue
            tool_calls.append(
                {
                    "tool_call_id": f"{trace_id}:tool:{len(tool_calls) + 1:02d}",
                    "agent": agent,
                    "name": action_text,
                    "status": "suggested",
                    "source": "agent_action",
                }
            )
    return tool_calls


def _evidence_refs(match: Any, prediction: Mapping[str, object], nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    source = _text(_match_attr(match, "source", ""), "")
    source_id = _text(_match_attr(match, "source_id", ""), "")
    match_id = _text(_match_attr(match, "match_id", ""), "")
    if source or source_id:
        refs.append(
            {
                "ref_id": "match_source",
                "kind": "source",
                "source": source or "-",
                "source_id": source_id or "-",
                "match_id": match_id or "-",
            }
        )
    refs.append(
        {
            "ref_id": "market_odds",
            "kind": "market",
            "source": source or "-",
            "odds_home": _match_attr(match, "odds_home", None),
            "odds_draw": _match_attr(match, "odds_draw", None),
            "odds_away": _match_attr(match, "odds_away", None),
        }
    )
    if isinstance(prediction.get("market_entropy"), Mapping):
        refs.append(
            {
                "ref_id": "market_entropy",
                "kind": "risk_signal",
                "level": _as_mapping(prediction.get("market_entropy")).get("level"),
                "score": _as_mapping(prediction.get("market_entropy")).get("score"),
            }
        )
    for node in nodes:
        evidence = _as_mapping(node.get("evidence"))
        if not evidence:
            continue
        refs.append(
            {
                "ref_id": f"agent:{_text(node.get('name'))}:evidence",
                "kind": "agent_evidence",
                "agent": _text(node.get("name")),
                "keys": [str(key) for key in list(evidence.keys())[:8]],
            }
        )
    return refs


def build_prediction_trace_envelope(
    *,
    match: Any,
    prediction: Mapping[str, object] | object,
    started_at: datetime | None = None,
    generated_at: datetime | None = None,
    latency_ms: float | int | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> dict[str, object]:
    resolved = prediction if isinstance(prediction, Mapping) else {}
    existing = _as_mapping(resolved.get("trace"))
    supervisor = _as_mapping(resolved.get("supervisor"))
    decision = _as_mapping(supervisor.get("decision"))
    generated = generated_at or datetime.now()
    generated_text = generated.strftime("%Y-%m-%d %H:%M:%S.%f")
    started_text = started_at.strftime("%Y-%m-%d %H:%M:%S.%f") if isinstance(started_at, datetime) else ""
    status = _text(supervisor.get("status"), _text(resolved.get("risk_level"), "unknown"))
    recommendation = _text(resolved.get("recommendation"), "")
    match_id = _text(_match_attr(match, "match_id", ""), _text(resolved.get("match_id"), "-"))
    trace_id = _text(
        existing.get("trace_id"),
        _trace_id_for(
            match_id=match_id,
            generated_at=generated_text,
            status=status,
            recommendation=recommendation,
        ),
    )
    nodes = _trace_nodes(supervisor)
    envelope = {
        "trace_id": trace_id,
        "trace_version": TRACE_VERSION,
        "prompt_version": _text(existing.get("prompt_version"), prompt_version),
        "generated_at": generated_text,
        "started_at": started_text or generated_text,
        "latency_ms": round(float(latency_ms), 3) if latency_ms is not None else None,
        "status": status,
        "decision": {
            "recommendation": recommendation or "-",
            "confidence": resolved.get("confidence"),
            "risk_level": resolved.get("risk_level"),
            "release_allowed": bool(decision.get("release_allowed")),
            "requires_human_review": bool(decision.get("requires_human_review")),
        },
        "nodes": nodes,
        "tool_calls": _tool_calls_from_nodes(trace_id, nodes),
        "evidence_refs": _evidence_refs(match, resolved, nodes),
    }
    return envelope
