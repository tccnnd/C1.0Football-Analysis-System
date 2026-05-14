from __future__ import annotations

from typing import Mapping


STATUS_LABELS = {
    "formal_ready": "\u6b63\u5f0f\u5efa\u8bae\u53ef\u7528",
    "observe": "\u89c2\u5bdf",
    "blocked": "\u963b\u65ad",
    "needs_c1_review": "\u7b49\u5f85 C1 \u653e\u884c",
    "needs_recovery": "\u590d\u76d8\u95ed\u73af\u5f02\u5e38",
}

STATUS_TONES = {
    "formal_ready": "good",
    "observe": "warning",
    "blocked": "bad",
    "needs_c1_review": "warning",
    "needs_recovery": "warning",
}

_C1_PASS_ACTIONS = {
    "APPROVE",
    "ALLOW",
    "APPROVE_RELEASE",
    "APPROVE_RELEASE_FALLBACK",
    "\u53ef\u653e\u884c",
}
_C1_BLOCK_ACTIONS = {"BLOCK", "HOLD", "GOVERNANCE_HOLD", "\u963b\u65ad"}
_C1_PENDING_ACTIONS = {"\u8865\u9635\u5bb9", "\u63a5\u8fd1\u963b\u65ad", "\u5f85\u5904\u7406"}
_TAKEOVER_SENSITIVE_PLAYS = {"score", "scoreline", "correct_score", "total_goals", "totals", "ou"}


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _text(value: object, default: str = "-") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _bool_text(value: object) -> str:
    return "yes" if bool(value) else "no"


def _chain_item(label: str, value: str, tone: str, detail: str = "", *, passed: bool = False) -> dict[str, object]:
    return {
        "label": label,
        "value": value,
        "tone": tone,
        "detail": detail or "-",
        "passed": bool(passed),
    }


def _strategy_admission_status(prediction: Mapping[str, object]) -> tuple[dict[str, object], bool, bool]:
    admission = _as_mapping(prediction.get("strategy_admission"))
    decision = _text(admission.get("decision"), "").lower()
    release_allowed = bool(admission.get("release_allowed"))
    label = _text(admission.get("label"), decision or "-")
    top_play = _text(admission.get("top_play"), "-")
    top_pick = _text(admission.get("top_pick"), "-")
    detail = f"{label} | play={top_play} | pick={top_pick}"
    if decision == "allow" or release_allowed:
        return _chain_item("\u7b56\u7565\u51c6\u5165", decision or "allow", "good", detail, passed=True), True, False
    if decision == "block":
        return _chain_item("\u7b56\u7565\u51c6\u5165", "block", "bad", detail, passed=False), False, True
    return _chain_item("\u7b56\u7565\u51c6\u5165", decision or "missing", "warning", detail, passed=False), False, False


def _c1_status(c1_release_row: Mapping[str, object]) -> tuple[dict[str, object], bool, bool, bool]:
    if not c1_release_row:
        return (
            _chain_item(
                "C1\u6cbb\u7406",
                "missing",
                "warning",
                "\u672a\u627e\u5230 C1 \u653e\u884c\u5ba1\u67e5\u7ed3\u679c",
                passed=False,
            ),
            False,
            False,
            True,
        )
    governance_action = _text(c1_release_row.get("governance_action"), "").upper()
    suggested_action = _text(c1_release_row.get("suggested_action"), "")
    release_action = _text(c1_release_row.get("release_action"), "").upper()
    release_allowed = bool(c1_release_row.get("release_allowed"))
    reason = _text(c1_release_row.get("primary_reason_code"), "-")
    detail = f"governance={governance_action or '-'} | release={release_action or '-'} | reason={reason}"

    if release_allowed or governance_action in _C1_PASS_ACTIONS or release_action in _C1_PASS_ACTIONS or suggested_action in _C1_PASS_ACTIONS:
        return _chain_item("C1\u6cbb\u7406", "release_allowed", "good", detail, passed=True), True, False, False
    if governance_action in _C1_BLOCK_ACTIONS or release_action in _C1_BLOCK_ACTIONS or suggested_action in _C1_BLOCK_ACTIONS:
        return _chain_item("C1\u6cbb\u7406", "blocked", "bad", detail, passed=False), False, True, False
    if bool(c1_release_row.get("near_block")) or suggested_action in _C1_PENDING_ACTIONS:
        return _chain_item("C1\u6cbb\u7406", suggested_action or "pending", "warning", detail, passed=False), False, False, True
    return _chain_item("C1\u6cbb\u7406", suggested_action or "observe", "warning", detail, passed=False), False, False, True


def _selected_play(prediction: Mapping[str, object], c1_release_row: Mapping[str, object]) -> str:
    admission = _as_mapping(prediction.get("strategy_admission"))
    for value in (
        admission.get("top_play"),
        c1_release_row.get("top_play"),
        prediction.get("top_play"),
        prediction.get("play_type"),
    ):
        text = _text(value, "")
        if text:
            return text.lower()
    return ""


def _play_is_takeover_sensitive(play: str) -> bool:
    lowered = play.lower()
    return any(token in lowered for token in _TAKEOVER_SENSITIVE_PLAYS)


def _takeover_gate_status(
    prediction: Mapping[str, object],
    c1_release_row: Mapping[str, object],
    play_policy_status: Mapping[str, object],
) -> tuple[dict[str, object], bool, bool]:
    takeover_gate = _as_mapping(play_policy_status.get("takeover_gate"))
    status = _text(takeover_gate.get("status"), "").lower()
    policy_blocked = bool(play_policy_status.get("policy_blocked_by_gate"))
    recommendation = _text(takeover_gate.get("recommendation"), "-")
    selected_play = _selected_play(prediction, c1_release_row)
    sensitive = _play_is_takeover_sensitive(selected_play)
    if not status and not policy_blocked:
        return _chain_item("\u63a5\u7ba1Gate", "not_configured", "neutral", "play=-", passed=True), True, False
    detail = f"gate={status or '-'} | play={selected_play or '-'} | sensitive={_bool_text(sensitive)} | {recommendation}"
    if (policy_blocked or status == "block") and sensitive:
        return _chain_item("\u63a5\u7ba1Gate", "blocked", "bad", detail, passed=False), False, True
    if status == "watch" and sensitive:
        return _chain_item("\u63a5\u7ba1Gate", "watch", "warning", detail, passed=False), False, False
    if (policy_blocked or status in {"block", "watch"}) and not sensitive:
        return _chain_item("\u63a5\u7ba1Gate", status or "policy_blocked", "warning", detail, passed=True), True, False
    return _chain_item("\u63a5\u7ba1Gate", status or "allow", "good", detail, passed=True), True, False


def _recovery_match_row(recovery_loop: Mapping[str, object], match_id: str) -> Mapping[str, object]:
    if not match_id:
        return {}
    for item in _as_list(recovery_loop.get("rows")):
        row = _as_mapping(item)
        if _text(row.get("match_id"), "") == match_id:
            return row
    return {}


def _recovery_status(recovery_loop: Mapping[str, object], match_id: str) -> tuple[dict[str, object], bool, bool]:
    if not recovery_loop:
        return _chain_item("\u590d\u76d8\u95ed\u73af", "not_configured", "neutral", "\u6682\u65e0\u653e\u884c\u56de\u6536\u95ed\u73af\u4fe1\u606f", passed=True), True, False
    health = _text(recovery_loop.get("health"), "").lower()
    health_text = _text(recovery_loop.get("health_text"), "-")
    match_row = _recovery_match_row(recovery_loop, match_id)
    if match_row:
        status = _text(match_row.get("loop_status"), "-")
        detail = (
            f"{status} | snapshot={_bool_text(match_row.get('snapshot_saved'))} | "
            f"settled={_bool_text(match_row.get('settled'))} | pending_days={_text(match_row.get('pending_days'), '0')}"
        )
        if bool(match_row.get("stale_pending")) or (bool(match_row.get("pending")) and not bool(match_row.get("snapshot_saved"))):
            return _chain_item("\u590d\u76d8\u95ed\u73af", "needs_recovery", "warning", detail, passed=False), False, True
        return _chain_item("\u590d\u76d8\u95ed\u73af", status, "good" if bool(match_row.get("settled")) else "neutral", detail, passed=True), True, False

    stale = int(recovery_loop.get("stale_pending_count", 0) or 0)
    missing = int(recovery_loop.get("missing_snapshot_count", 0) or 0)
    pending = int(recovery_loop.get("pending_count", 0) or 0)
    detail = f"{health_text} | pending={pending} | stale={stale} | missing_snapshot={missing}"
    tone = "warning" if health == "warning" else "neutral" if health in {"watch", "collecting"} else "good"
    return _chain_item("\u590d\u76d8\u95ed\u73af", health or "unknown", tone, detail, passed=True), True, False


def _choose_status(
    *,
    admission_allowed: bool,
    admission_blocked: bool,
    c1_allowed: bool,
    c1_blocked: bool,
    c1_pending: bool,
    takeover_allowed: bool,
    takeover_blocked: bool,
    recovery_allowed: bool,
    recovery_current_blocked: bool,
) -> tuple[str, str]:
    if admission_blocked:
        return "blocked", "\u7b56\u7565\u51c6\u5165\u5df2\u963b\u65ad"
    if c1_blocked:
        return "blocked", "C1 \u6cbb\u7406\u5df2\u963b\u65ad"
    if takeover_blocked:
        return "blocked", "\u63a5\u7ba1 Gate \u963b\u65ad\u5f53\u524d\u73a9\u6cd5"
    if recovery_current_blocked:
        return "needs_recovery", "\u8be5\u573a\u653e\u884c\u8bb0\u5f55\u9700\u5148\u5b8c\u6210\u590d\u76d8\u56de\u6536"
    if not admission_allowed:
        return "observe", "\u7b56\u7565\u51c6\u5165\u5c1a\u672a\u8fbe\u5230\u6b63\u5f0f\u653e\u884c"
    if c1_pending or not c1_allowed:
        return "needs_c1_review", "\u7b49\u5f85 C1 \u653e\u884c\u5ba1\u67e5"
    if not takeover_allowed:
        return "observe", "\u63a5\u7ba1 Gate \u5904\u4e8e\u89c2\u5bdf\uff0c\u6682\u4e0d\u8fdb\u5165\u6b63\u5f0f\u5efa\u8bae"
    if not recovery_allowed:
        return "needs_recovery", "\u590d\u76d8\u95ed\u73af\u672a\u5c31\u7eea"
    return "formal_ready", "-"


def _recommendation_for_status(status: str) -> str:
    return {
        "formal_ready": "\u53ef\u8fdb\u5165\u6b63\u5f0f\u5efa\u8bae\uff0c\u540e\u7eed\u4fdd\u6301\u8d5b\u679c\u56de\u6536\u3002",
        "observe": "\u4ec5\u4f5c\u89c2\u5bdf\uff0c\u7b49\u5f85\u7b56\u7565\u6216 Gate \u8fbe\u6807\u3002",
        "blocked": "\u4e0d\u8fdb\u5165\u6b63\u5f0f\u5efa\u8bae\uff0c\u5148\u5904\u7406\u4e3b\u963b\u65ad\u56e0\u7d20\u3002",
        "needs_c1_review": "\u5148\u8fd0\u884c C1 \u653e\u884c\u5ba1\u67e5\u6216\u8865\u9f50\u9635\u5bb9/\u4fe1\u606f\u8d28\u91cf\u3002",
        "needs_recovery": "\u5148\u8865\u9f50\u653e\u884c\u5feb\u7167\u548c\u8d5b\u679c\u56de\u6536\uff0c\u518d\u8fdb\u5165\u6b63\u5f0f\u5efa\u8bae\u3002",
    }.get(status, "\u4fdd\u6301\u89c2\u5bdf\u3002")


def build_main_flow_governance_status(
    *,
    prediction: Mapping[str, object] | object,
    c1_release_row: Mapping[str, object] | object | None = None,
    play_policy_status: Mapping[str, object] | object | None = None,
    recovery_loop: Mapping[str, object] | object | None = None,
    match_id: str = "",
) -> dict[str, object]:
    resolved_prediction = _as_mapping(prediction)
    resolved_c1 = _as_mapping(c1_release_row)
    resolved_policy = _as_mapping(play_policy_status)
    resolved_recovery = _as_mapping(recovery_loop)

    admission_item, admission_allowed, admission_blocked = _strategy_admission_status(resolved_prediction)
    c1_item, c1_allowed, c1_blocked, c1_pending = _c1_status(resolved_c1)
    takeover_item, takeover_allowed, takeover_blocked = _takeover_gate_status(resolved_prediction, resolved_c1, resolved_policy)
    recovery_item, recovery_allowed, recovery_current_blocked = _recovery_status(resolved_recovery, match_id)
    status, primary_blocker = _choose_status(
        admission_allowed=admission_allowed,
        admission_blocked=admission_blocked,
        c1_allowed=c1_allowed,
        c1_blocked=c1_blocked,
        c1_pending=c1_pending,
        takeover_allowed=takeover_allowed,
        takeover_blocked=takeover_blocked,
        recovery_allowed=recovery_allowed,
        recovery_current_blocked=recovery_current_blocked,
    )
    formal_allowed = status == "formal_ready"
    return {
        "status": status,
        "label": STATUS_LABELS.get(status, status),
        "tone": STATUS_TONES.get(status, "neutral"),
        "formal_allowed": formal_allowed,
        "decision_chain": [admission_item, c1_item, takeover_item, recovery_item],
        "primary_blocker": primary_blocker,
        "recommendation": _recommendation_for_status(status),
    }


def summarize_main_flow_governance_statuses(statuses: list[Mapping[str, object]] | object) -> dict[str, int]:
    counts = {key: 0 for key in STATUS_LABELS}
    if not isinstance(statuses, list):
        return counts
    for item in statuses:
        status = _text(_as_mapping(item).get("status"), "")
        if status in counts:
            counts[status] += 1
    return counts


def build_main_flow_governance_status_text(status: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(status)
    if not resolved:
        return "Main Flow Governance\n- Status: -"
    lines = [
        "Main Flow Governance",
        f"- Status: {_text(resolved.get('label'))} ({_text(resolved.get('status'))})",
        f"- Formal allowed: {_bool_text(resolved.get('formal_allowed'))}",
        f"- Primary blocker: {_text(resolved.get('primary_blocker'))}",
        f"- Recommendation: {_text(resolved.get('recommendation'))}",
        "- Decision chain:",
    ]
    for item in _as_list(resolved.get("decision_chain")):
        row = _as_mapping(item)
        lines.append(
            f"  - {_text(row.get('label'))}: {_text(row.get('value'))} | tone={_text(row.get('tone'))} | {_text(row.get('detail'))}"
        )
    return "\n".join(lines)
