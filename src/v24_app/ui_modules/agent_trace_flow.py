from __future__ import annotations

from typing import Mapping


AGENT_STATUS_LABELS = {
    "ready": "READY",
    "completed": "READY",
    "watch": "WATCH",
    "alert": "ALERT",
    "blocked": "BLOCKED",
}


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object, default: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else default


def _format_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    if isinstance(value, Mapping):
        return ", ".join(f"{key}={_format_scalar(val)}" for key, val in value.items()) if value else "-"
    return _text(value)


def build_agent_trace_nodes(supervisor: Mapping[str, object] | object) -> list[dict[str, object]]:
    resolved = supervisor if isinstance(supervisor, Mapping) else {}
    agents = resolved.get("agents") if isinstance(resolved.get("agents"), list) else []
    nodes: list[dict[str, object]] = []
    for index, item in enumerate(agents):
        if not isinstance(item, Mapping):
            continue
        status = _text(item.get("status"), "ready").lower()
        outputs = _mapping(item.get("outputs"))
        checks = item.get("checks") if isinstance(item.get("checks"), list) else []
        actions = item.get("actions") if isinstance(item.get("actions"), list) else []
        summary = _text(item.get("trigger"))
        if item.get("rationale"):
            summary = _text(item.get("rationale"))
        elif outputs.get("signals"):
            signals = outputs.get("signals") if isinstance(outputs.get("signals"), list) else []
            summary = f"signals {len(signals)}"
        elif outputs.get("recommendation"):
            summary = f"pick {_text(outputs.get('recommendation'))}"
        elif outputs.get("admission_decision"):
            summary = f"decision {_text(outputs.get('admission_decision'))}"
        nodes.append(
            {
                "index": index,
                "name": _text(item.get("name"), f"Agent {index + 1}"),
                "status": status,
                "status_label": AGENT_STATUS_LABELS.get(status, status.upper()),
                "trigger": _text(item.get("trigger")),
                "summary": summary,
                "inputs": dict(_mapping(item.get("inputs"))),
                "outputs": dict(outputs),
                "checks": [str(value) for value in checks],
                "evidence": dict(_mapping(item.get("evidence"))),
                "rationale": _text(item.get("rationale"), summary),
                "actions": [str(value) for value in actions],
            }
        )
    return nodes


def format_agent_trace_detail(node: Mapping[str, object] | object) -> str:
    resolved = node if isinstance(node, Mapping) else {}
    lines = [
        f"{_text(resolved.get('name'))} / {_text(resolved.get('status_label'), _text(resolved.get('status')).upper())}",
        f"trigger: {_text(resolved.get('trigger'))}",
        f"summary: {_text(resolved.get('summary'))}",
    ]
    inputs = _mapping(resolved.get("inputs"))
    outputs = _mapping(resolved.get("outputs"))
    checks = resolved.get("checks") if isinstance(resolved.get("checks"), list) else []
    evidence = _mapping(resolved.get("evidence"))
    actions = resolved.get("actions") if isinstance(resolved.get("actions"), list) else []
    rationale = _text(resolved.get("rationale"), _text(resolved.get("summary")))
    if rationale:
        lines.append(f"rationale: {rationale}")
    if checks:
        lines.append("checks: " + " | ".join(str(item) for item in checks))
    if evidence:
        lines.append("evidence: " + " | ".join(f"{key}={_format_scalar(value)}" for key, value in evidence.items()))
    if inputs:
        lines.append("inputs: " + " | ".join(f"{key}={_format_scalar(value)}" for key, value in inputs.items()))
    if outputs:
        lines.append("outputs: " + " | ".join(f"{key}={_format_scalar(value)}" for key, value in outputs.items()))
    if actions:
        lines.append("actions: " + " | ".join(str(item) for item in actions))
    return "\n".join(lines)


def summarize_supervisor_trace(supervisor: Mapping[str, object] | object) -> dict[str, object]:
    resolved = supervisor if isinstance(supervisor, Mapping) else {}
    nodes = build_agent_trace_nodes(resolved)
    status_counts: dict[str, int] = {"ready": 0, "watch": 0, "alert": 0, "blocked": 0}
    for node in nodes:
        status = _text(node.get("status"), "ready").lower()
        status_counts[status] = status_counts.get(status, 0) + 1
    actions = resolved.get("next_actions") if isinstance(resolved.get("next_actions"), list) else []
    agent_actions: list[str] = []
    for node in nodes:
        node_actions = node.get("actions") if isinstance(node.get("actions"), list) else []
        for action in node_actions:
            if str(action) not in agent_actions:
                agent_actions.append(str(action))
    return {
        "status": _text(resolved.get("status"), "unknown"),
        "node_count": len(nodes),
        "status_counts": status_counts,
        "next_actions": [str(item) for item in actions],
        "agent_actions": agent_actions,
    }
