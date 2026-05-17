from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Mapping

from c1.data.fact_contracts import (
    ACTION_FACT_SCHEMA_VERSION,
    MATCH_FACT_SCHEMA_VERSION,
    SOURCE_PROVENANCE_SCHEMA_VERSION,
)


TRACE_VERSION = "trace_v1"
DEFAULT_PROMPT_VERSION = "strategy_report_v1"
DEFAULT_PROMPT_NAME = "strategy_report"
DEFAULT_WORKFLOW_NAME = "match-analysis-v1"
DEFAULT_WORKFLOW_VERSION = "match_analysis_v1"
DEFAULT_EVAL_SUITE_VERSION = "strategy_eval_v1"
DEFAULT_THREAD_ID = "app:local"
DEFAULT_USER_ID = "local-user"
FACT_REF_VERSION = "fact_ref_v1"


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _text(value: object, default: str = "-") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _match_attr(match: Any, name: str, default: object = "") -> object:
    return getattr(match, name, default)


def _trace_id_for(*, match_id: str, generated_at: str, status: str, recommendation: str) -> str:
    seed = "|".join([match_id, generated_at, status, recommendation])
    return "trc_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _hash_id(prefix: str, *parts: object, length: int = 16) -> str:
    seed = "|".join(str(part if part is not None else "") for part in parts)
    return f"{prefix}_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:length]


def _first_text(*values: object, default: str = "-") -> str:
    for value in values:
        text = _text(value, "")
        if text:
            return text
    return default


def _dedupe_texts(values: list[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _text(value, "")
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _get_value(source: object, key: str, default: object = "") -> object:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _fact_schema_for_kind(kind: str, source: object | None = None) -> str:
    explicit = _text(_get_value(source or {}, "schema_version", ""), "")
    if explicit:
        return explicit
    if kind == "match_fact":
        return MATCH_FACT_SCHEMA_VERSION
    if kind == "action_fact":
        return ACTION_FACT_SCHEMA_VERSION
    if kind == "source_provenance":
        return SOURCE_PROVENANCE_SCHEMA_VERSION
    return ""


def build_fact_ref(kind: str, source: object, *, fallback_match_id: str = "") -> dict[str, object]:
    resolved_kind = _text(kind, "fact")
    match_id = _first_text(_get_value(source, "match_id", ""), fallback_match_id, default="")
    provider = _first_text(_get_value(source, "provider", ""), _get_value(source, "source", ""), _get_value(source, "source_vendor", ""), default="")
    source_id = _first_text(_get_value(source, "source_id", ""), _get_value(source, "provider_match_id", ""), _get_value(source, "source_event_id", ""), default="")
    action_id = _first_text(_get_value(source, "action_id", ""), _get_value(source, "event_id", ""), default="")
    if resolved_kind == "match_fact":
        identity = match_id or source_id
    elif resolved_kind == "action_fact":
        identity = action_id or source_id
    elif resolved_kind == "source_provenance":
        identity = f"{provider}:{source_id}" if provider or source_id else match_id
    else:
        identity = action_id or match_id or source_id
    ref = {
        "ref_id": _hash_id("fact", resolved_kind, identity, length=16),
        "kind": resolved_kind,
        "fact_ref_version": FACT_REF_VERSION,
        "schema_version": _fact_schema_for_kind(resolved_kind, source),
        "match_id": match_id,
        "provider": provider,
        "source_id": source_id,
    }
    if action_id:
        ref["action_id"] = action_id
    source_version = _text(_get_value(source, "source_version", ""), "")
    if source_version:
        ref["source_version"] = source_version
    raw_payload_ref = _text(_get_value(source, "raw_payload_ref", ""), "")
    if raw_payload_ref:
        ref["raw_payload_ref"] = raw_payload_ref
    return ref


def _dedupe_fact_refs(refs: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    for item in refs:
        ref_id = _text(item.get("ref_id"), "")
        if not ref_id or ref_id in seen:
            continue
        seen.add(ref_id)
        result.append(item)
    return result


def _source_ref_from_match(match: Any, match_id: str) -> dict[str, object]:
    return {
        "match_id": match_id,
        "provider": _text(_match_attr(match, "source", ""), ""),
        "source_id": _text(_match_attr(match, "source_id", ""), ""),
        "source_vendor": _text(_match_attr(match, "source", ""), ""),
    }


def _match_fact_ref(match: Any, match_id: str) -> dict[str, object]:
    provider = _text(_match_attr(match, "source", ""), "")
    source_id = _text(_match_attr(match, "source_id", ""), "")
    return build_fact_ref(
        "match_fact",
        {
            "match_id": match_id,
            "provider": provider,
            "source_id": source_id,
            "schema_version": MATCH_FACT_SCHEMA_VERSION,
        },
    )


def _fact_refs_from_prediction(match: Any, prediction: Mapping[str, object], match_id: str, existing: Mapping[str, object]) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = [_match_fact_ref(match, match_id)]
    source_ref = build_fact_ref("source_provenance", _source_ref_from_match(match, match_id), fallback_match_id=match_id)
    if _text(source_ref.get("provider"), "") or _text(source_ref.get("source_id"), ""):
        refs.append(source_ref)

    for key, kind in (
        ("fact_refs", ""),
        ("match_fact_refs", "match_fact"),
        ("action_fact_refs", "action_fact"),
        ("source_provenance_refs", "source_provenance"),
    ):
        for item in _as_list(existing.get(key)) + _as_list(prediction.get(key)):
            if not isinstance(item, Mapping):
                continue
            item_kind = _text(item.get("kind"), kind or "fact")
            if item.get("ref_id") and item.get("schema_version"):
                refs.append(dict(item))
                continue
            refs.append(build_fact_ref(item_kind, item, fallback_match_id=match_id))
    return _dedupe_fact_refs(refs)


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


def _compact_fact_refs(fact_refs: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "ref_id": item.get("ref_id"),
            "kind": item.get("kind"),
            "schema_version": item.get("schema_version"),
            "match_id": item.get("match_id"),
        }
        for item in fact_refs
    ]


def _input_ref(match: Any, match_id: str, fact_refs: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "ref_id": _hash_id("input", match_id, _match_attr(match, "source_id", "")),
        "kind": "match_prediction_input",
        "match_id": match_id,
        "source": _text(_match_attr(match, "source", ""), "-"),
        "source_id": _text(_match_attr(match, "source_id", ""), "-"),
        "odds": {
            "home": _match_attr(match, "odds_home", None),
            "draw": _match_attr(match, "odds_draw", None),
            "away": _match_attr(match, "odds_away", None),
        },
        "fact_refs": _compact_fact_refs(fact_refs or []),
    }


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


def _retrieval_refs_from_evidence(evidence_refs: list[dict[str, object]]) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for item in evidence_refs:
        ref_id = _text(item.get("ref_id"), "")
        if not ref_id:
            continue
        refs.append(
            {
                "ref_id": f"retrieval:{ref_id}",
                "kind": "evidence_ref",
                "source_ref_id": ref_id,
                "source_kind": _text(item.get("kind"), "-"),
            }
        )
    return refs


def _fact_evidence_refs(fact_refs: list[dict[str, object]]) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for item in fact_refs:
        ref_id = _text(item.get("ref_id"), "")
        if not ref_id:
            continue
        refs.append(
            {
                "ref_id": f"fact:{ref_id}",
                "kind": "fact_ref",
                "fact_ref_id": ref_id,
                "fact_kind": _text(item.get("kind"), "-"),
                "schema_version": _text(item.get("schema_version"), "-"),
                "match_id": _text(item.get("match_id"), "-"),
            }
        )
    return refs


def _tool_failure_rate(tool_calls: list[dict[str, object]]) -> float:
    if not tool_calls:
        return 0.0
    failed = 0
    for item in tool_calls:
        status = _text(item.get("status"), "").lower()
        if status in {"failed", "error", "timeout"}:
            failed += 1
    return round(failed / len(tool_calls), 4)


def _evidence_coverage_ratio(evidence_refs: list[dict[str, object]]) -> float:
    if not evidence_refs:
        return 0.0
    covered = 0
    if any(item.get("kind") == "source" for item in evidence_refs):
        covered += 1
    if any(item.get("ref_id") == "market_odds" for item in evidence_refs):
        covered += 1
    if any(item.get("kind") == "risk_signal" for item in evidence_refs):
        covered += 1
    if any(item.get("kind") == "agent_evidence" for item in evidence_refs):
        covered += 1
    return round(_clamp(covered / 4.0), 4)


def _observations(
    trace_id: str,
    nodes: list[dict[str, object]],
    tool_calls: list[dict[str, object]],
    retrieval_refs: list[dict[str, object]],
) -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []
    for node in nodes:
        observations.append(
            {
                "observation_id": f"{trace_id}:obs:{_text(node.get('span_id'), 'agent')}",
                "type": "agent",
                "name": _text(node.get("name"), "-"),
                "status": _text(node.get("status"), "ready"),
                "parent_id": _text(node.get("parent_id"), "supervisor"),
            }
        )
    for index, tool in enumerate(tool_calls):
        observations.append(
            {
                "observation_id": f"{trace_id}:obs:tool-{index + 1:02d}",
                "type": "tool",
                "name": _text(tool.get("name"), "-"),
                "status": _text(tool.get("status"), "suggested"),
                "parent_id": _text(tool.get("agent"), "agent"),
            }
        )
    for index, ref in enumerate(retrieval_refs):
        observations.append(
            {
                "observation_id": f"{trace_id}:obs:retrieval-{index + 1:02d}",
                "type": "retrieval",
                "name": _text(ref.get("source_ref_id"), "-"),
                "status": "success",
                "parent_id": "retrieval",
            }
        )
    return observations


def build_prediction_trace_envelope(
    *,
    match: Any,
    prediction: Mapping[str, object] | object,
    started_at: datetime | None = None,
    generated_at: datetime | None = None,
    latency_ms: float | int | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    prompt_name: str = DEFAULT_PROMPT_NAME,
    workflow_name: str = DEFAULT_WORKFLOW_NAME,
    workflow_version: str = DEFAULT_WORKFLOW_VERSION,
    eval_suite_version: str = DEFAULT_EVAL_SUITE_VERSION,
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
    normalized_fact_refs = _fact_refs_from_prediction(match, resolved, match_id, existing)
    tool_calls = _as_list(existing.get("tool_calls"))
    if not all(isinstance(item, Mapping) for item in tool_calls):
        tool_calls = []
    normalized_tool_calls = [dict(item) for item in tool_calls if isinstance(item, Mapping)] or _tool_calls_from_nodes(trace_id, nodes)
    evidence_refs = _as_list(existing.get("evidence_refs"))
    if not all(isinstance(item, Mapping) for item in evidence_refs):
        evidence_refs = []
    normalized_evidence_refs = [dict(item) for item in evidence_refs if isinstance(item, Mapping)] or _evidence_refs(match, resolved, nodes)
    normalized_evidence_refs = _dedupe_fact_refs([*normalized_evidence_refs, *_fact_evidence_refs(normalized_fact_refs)])
    retrieval_refs = _as_list(existing.get("retrieval_refs"))
    if not all(isinstance(item, Mapping) for item in retrieval_refs):
        retrieval_refs = []
    normalized_retrieval_refs = [dict(item) for item in retrieval_refs if isinstance(item, Mapping)] or _retrieval_refs_from_evidence(normalized_evidence_refs)
    latency_value = _float_or_none(latency_ms if latency_ms is not None else existing.get("latency_ms"))
    evidence_coverage_ratio = _evidence_coverage_ratio(normalized_evidence_refs)
    retrieval_hit_rate = round(
        _clamp(len(normalized_retrieval_refs) / max(len(normalized_evidence_refs), 1)),
        4,
    )
    tool_failure_rate = _tool_failure_rate(normalized_tool_calls)
    report_grounded_flag = bool(normalized_evidence_refs)
    model_name = _first_text(existing.get("model_name"), resolved.get("model"), default="-")
    workflow_name_value = _first_text(existing.get("workflow_name"), resolved.get("workflow_name"), workflow_name)
    workflow_version_value = _first_text(existing.get("workflow_version"), resolved.get("workflow_version"), workflow_version)
    prompt_name_value = _first_text(existing.get("prompt_name"), resolved.get("prompt_name"), prompt_name)
    prompt_version_value = _first_text(existing.get("prompt_version"), resolved.get("prompt_version"), prompt_version)
    session_id = _first_text(
        existing.get("session_id"),
        resolved.get("session_id"),
        _hash_id("ses", _match_attr(match, "match_date", ""), _match_attr(match, "league", ""), length=12),
    )
    request_id = _first_text(existing.get("request_id"), resolved.get("request_id"), _hash_id("req", trace_id, match_id, length=12))
    analysis_id = _first_text(existing.get("analysis_id"), resolved.get("analysis_id"), _hash_id("ana", trace_id, match_id, length=12))
    thread_id = _first_text(existing.get("thread_id"), resolved.get("thread_id"), DEFAULT_THREAD_ID)
    user_id = _first_text(existing.get("user_id"), resolved.get("user_id"), DEFAULT_USER_ID)
    input_ref = dict(existing.get("input_ref")) if isinstance(existing.get("input_ref"), Mapping) else _input_ref(match, match_id, normalized_fact_refs)
    if "fact_refs" not in input_ref:
        input_ref["fact_refs"] = _compact_fact_refs(normalized_fact_refs)
    state_snapshot_ref = _first_text(
        existing.get("state_snapshot_ref"),
        resolved.get("state_snapshot_ref"),
        f"prediction_snapshot:{_hash_id('snap', match_id, _match_attr(match, 'source_id', ''), length=12)}",
    )
    output_ref = _first_text(existing.get("output_ref"), resolved.get("output_ref"), f"prediction_output:{trace_id}")
    replay_input_ref = (
        dict(existing.get("replay_input_ref"))
        if isinstance(existing.get("replay_input_ref"), Mapping)
        else {
            "ref_id": input_ref.get("ref_id"),
            "kind": "prediction_replay_input",
            "state_snapshot_ref": state_snapshot_ref,
            "fact_refs": _compact_fact_refs(normalized_fact_refs),
        }
    )
    if "fact_refs" not in replay_input_ref:
        replay_input_ref["fact_refs"] = _compact_fact_refs(normalized_fact_refs)
    model_params = dict(existing.get("model_params")) if isinstance(existing.get("model_params"), Mapping) else {}
    if not model_params and isinstance(resolved.get("ensemble_weights"), Mapping):
        model_params["ensemble_weights"] = dict(_as_mapping(resolved.get("ensemble_weights")))
    token_usage = (
        dict(existing.get("token_usage"))
        if isinstance(existing.get("token_usage"), Mapping)
        else {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "source": "local"}
    )
    cost = (
        dict(existing.get("cost"))
        if isinstance(existing.get("cost"), Mapping)
        else {"amount": 0.0, "currency": "USD", "estimated": False, "source": "local"}
    )
    metadata = dict(existing.get("metadata")) if isinstance(existing.get("metadata"), Mapping) else {}
    metadata.update(
        {
            key: value
            for key, value in {
                "league": _match_attr(match, "league", ""),
                "match_date": _match_attr(match, "match_date", ""),
                "match_time": _match_attr(match, "match_time", ""),
                "source": _match_attr(match, "source", ""),
                "source_id": _match_attr(match, "source_id", ""),
                "framework_independent": True,
                "fact_ref_count": len(normalized_fact_refs),
            }.items()
            if key not in metadata
        }
    )
    tags = _dedupe_texts(
        [
            *(_as_list(existing.get("tags")) if isinstance(existing.get("tags"), list) else []),
            "prediction_trace",
            workflow_name_value,
            status.lower(),
            _text(resolved.get("risk_level"), "").lower(),
        ]
    )
    scores = dict(existing.get("scores")) if isinstance(existing.get("scores"), Mapping) else {}
    if not scores:
        scores = {
            "prediction_confidence": {
                "value": _float_or_none(resolved.get("confidence")),
                "source": "prediction",
            },
            "evidence_coverage_ratio": {
                "value": evidence_coverage_ratio,
                "source": "trace_envelope",
            },
            "tool_failure_rate": {
                "value": tool_failure_rate,
                "source": "trace_envelope",
            },
        }
    envelope = {
        "trace_id": trace_id,
        "trace_version": TRACE_VERSION,
        "session_id": session_id,
        "parent_trace_id": _first_text(existing.get("parent_trace_id"), resolved.get("parent_trace_id"), default=""),
        "request_id": request_id,
        "thread_id": thread_id,
        "user_id": user_id,
        "workflow_name": workflow_name_value,
        "workflow_version": workflow_version_value,
        "match_id": match_id,
        "analysis_id": analysis_id,
        "fact_refs": normalized_fact_refs,
        "input_ref": input_ref,
        "retrieval_refs": normalized_retrieval_refs,
        "prompt_name": prompt_name_value,
        "prompt_version": prompt_version_value,
        "model_name": model_name,
        "model_params": model_params,
        "state_snapshot_ref": state_snapshot_ref,
        "output_ref": output_ref,
        "scores": scores,
        "generated_at": generated_text,
        "started_at": started_text or generated_text,
        "ended_at": _first_text(existing.get("ended_at"), generated_text),
        "latency_ms": round(latency_value, 3) if latency_value is not None else None,
        "token_usage": token_usage,
        "cost": cost,
        "tags": tags,
        "metadata": metadata,
        "replayable": bool(existing.get("replayable", True)),
        "replay_input_ref": replay_input_ref,
        "replay_seed": _first_text(existing.get("replay_seed"), resolved.get("replay_seed"), _hash_id("seed", match_id, trace_id, length=12)),
        "eval_suite_version": _first_text(existing.get("eval_suite_version"), resolved.get("eval_suite_version"), eval_suite_version),
        "evidence_coverage_ratio": evidence_coverage_ratio,
        "retrieval_hit_rate": retrieval_hit_rate,
        "tool_failure_rate": tool_failure_rate,
        "hallucination_flag": not report_grounded_flag,
        "report_grounded_flag": report_grounded_flag,
        "status": status,
        "decision": {
            "recommendation": recommendation or "-",
            "confidence": resolved.get("confidence"),
            "risk_level": resolved.get("risk_level"),
            "release_allowed": bool(decision.get("release_allowed")),
            "requires_human_review": bool(decision.get("requires_human_review")),
        },
        "nodes": nodes,
        "observations": _observations(trace_id, nodes, normalized_tool_calls, normalized_retrieval_refs),
        "tool_calls": normalized_tool_calls,
        "evidence_refs": normalized_evidence_refs,
    }
    return envelope
