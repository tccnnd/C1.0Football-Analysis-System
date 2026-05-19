from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import date, datetime
from typing import Mapping, Sequence


ROLE_LABELS = {
    "primary": "\u4e3b\u7b56\u7565",
    "backup": "\u5907\u9009",
    "observe": "\u89c2\u5bdf",
}
PLAY_LABELS = {
    "market_1x2": "\u5e02\u573a\u80dc\u5e73\u8d1f",
    "1x2": "\u80dc\u5e73\u8d1f",
    "handicap": "\u8ba9\u7403",
    "ou": "\u5927\u5c0f\u7403",
    "total_goals": "\u603b\u8fdb\u7403",
    "score": "\u6bd4\u5206",
}
DATA_LAYER_LABELS = {
    "historical_market": "\u5386\u53f2\u5e02\u573a",
    "app_settlement": "APP \u7ed3\u7b97",
    "jc_stratified_market": "\u7ade\u5f69\u5206\u5c42",
}
SCOPE_LABELS = {
    "global": "\u5168\u5c40",
    "league": "\u8054\u8d5b",
    "jc_bucket": "\u7ade\u5f69\u7a33\u5b9a\u6876",
}
ADMISSION_DECISION_LABELS = {
    "allow": "\u6b63\u5f0f\u653e\u884c",
    "observe": "\u89c2\u5bdf",
    "block": "\u963b\u65ad",
}
ADMISSION_FILTER_LABELS = {
    "all": "\u5168\u90e8",
    "allow": "\u6b63\u5f0f\u653e\u884c",
    "observe": "\u89c2\u5bdf",
    "block": "\u963b\u65ad",
}
ADMISSION_ACTION_LABELS = {
    "FORMAL_ALLOW": "\u6b63\u5f0f\u653e\u884c",
    "OBSERVE_ONLY": "\u4ec5\u89c2\u5bdf",
    "BLOCK": "\u963b\u65ad",
    "allow": "\u6b63\u5f0f\u653e\u884c",
    "release": "\u6b63\u5f0f\u653e\u884c",
    "observe": "\u4ec5\u89c2\u5bdf",
    "block": "\u963b\u65ad",
}
ADMISSION_REASON_LABELS = {
    "strategy_not_calibrated": "\u9ad8\u51c6\u7b56\u7565\u5c1a\u672a\u6821\u51c6",
    "high_accuracy_strategy_active": "\u547d\u4e2d\u6b63\u5f0f\u9ad8\u51c6\u7b56\u7565",
    "high_accuracy_strategy_count_below_policy": "\u9ad8\u51c6\u7b56\u7565\u6570\u91cf\u4f4e\u4e8e\u5f53\u524d\u51c6\u5165\u95e8\u69db",
    "no_official_high_accuracy_strategy": "\u672a\u547d\u4e2d\u6b63\u5f0f\u9ad8\u51c6\u7b56\u7565",
    "breaker_shadow_observation": "\u65ad\u8def\u89c2\u5bdf\u7b56\u7565\u547d\u4e2d\uff0c\u4ecd\u9700\u590d\u6838",
    "risk_high": "\u98ce\u9669\u7b49\u7ea7\u4e3a\u9ad8\u98ce\u9669",
    "risk_medium": "\u98ce\u9669\u7b49\u7ea7\u4e3a\u4e2d\u98ce\u9669",
    "risk_medium_policy_watch": "\u5f53\u524d\u95e8\u69db\u5c06\u4e2d\u98ce\u9669\u964d\u4e3a\u89c2\u5bdf",
    "risk_low": "\u98ce\u9669\u7b49\u7ea7\u4e3a\u4f4e\u98ce\u9669",
    "confidence_block": "\u7f6e\u4fe1\u5ea6\u4f4e\u4e8e\u963b\u65ad\u7ebf",
    "confidence_watch": "\u7f6e\u4fe1\u5ea6\u4f4e\u4e8e\u6b63\u5f0f\u653e\u884c\u7ebf",
    "no_single_play_passed": "\u6682\u65e0\u5355\u73a9\u6cd5\u901a\u8fc7\u95e8\u69db",
    "agent_replay_policy_watch": "Agent Replay \u663e\u793a\u5f53\u524d\u98ce\u9669\u4fe1\u53f7\u4e0e\u5386\u53f2\u5931\u8bef\u5f3a\u76f8\u5173",
}
PRE_MATCH_REVIEW_CHECKLIST = (
    "\u786e\u8ba4\u9996\u53d1\u3001\u4f24\u505c\u3001\u8f6e\u6362\u4e0e\u4e34\u573a\u540d\u5355\u6ca1\u6709\u53cd\u5411\u53d8\u5316\u3002",
    "\u786e\u8ba4\u76d8\u53e3/\u8d54\u7387\u4e34\u573a\u65b9\u5411\u6ca1\u6709\u6301\u7eed\u80cc\u79bb\u6a21\u578b\u65b9\u5411\u3002",
    "\u786e\u8ba4\u98ce\u9669\u7b49\u7ea7\u3001\u7f6e\u4fe1\u5ea6\u3001\u7b56\u7565\u51c6\u5165\u4ecd\u7ef4\u6301\u6b63\u5f0f\u653e\u884c\u3002",
    "\u786e\u8ba4\u9ad8\u51c6\u7b56\u7565\u672a\u88ab\u65ad\u8def\u5668\u6682\u505c\uff0c\u5f71\u5b50\u6062\u590d\u672a\u88ab\u8bef\u5f53\u6b63\u5f0f\u653e\u884c\u3002",
    "\u786e\u8ba4\u8d5b\u524d\u9884\u6d4b\u5feb\u7167\u5df2\u7ecf\u4fdd\u5b58\uff0c\u8d5b\u540e\u53ef\u56de\u6536\u8d5b\u679c\u3002",
    "\u8d5b\u540e\u5f55\u5165\u6bd4\u5206\u5e76\u8fdb\u5165\u590d\u76d8\uff0c\u66f4\u65b0\u771f\u5b9e\u547d\u4e2d\u53cd\u9988\u3002",
)


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _pct(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except (TypeError, ValueError):
        return "-"


def _label(labels: Mapping[str, str], value: object) -> str:
    key = str(value or "").strip()
    return labels.get(key, key or "-")


def _field(value: object, name: str, default: object = "-") -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _row_match(row: object) -> object:
    return _field(row, "match", {})


def _row_prediction(row: object) -> Mapping[str, object]:
    return _as_mapping(_field(row, "prediction", {}))


def _strategy_admission(prediction: Mapping[str, object]) -> Mapping[str, object]:
    return _as_mapping(prediction.get("strategy_admission"))


def _row_match_id(match: object) -> str:
    direct = _text(_field(match, "match_id", ""), "")
    if direct:
        return direct
    return "|".join(
        [
            _text(_field(match, "match_date"), ""),
            _text(_field(match, "league"), ""),
            _text(_field(match, "home_team"), ""),
            _text(_field(match, "away_team"), ""),
        ]
    ).strip("|")


def _settlement_match_id(item: Mapping[str, object]) -> str:
    direct = _text(item.get("match_id"), "")
    if direct:
        return direct
    return "|".join(
        [
            _text(item.get("match_date"), ""),
            _text(item.get("league"), ""),
            _text(item.get("home_team"), ""),
            _text(item.get("away_team"), ""),
        ]
    ).strip("|")


def _allowlist_marker(prediction: Mapping[str, object], snapshot: Mapping[str, object]) -> Mapping[str, object]:
    marker = _as_mapping(prediction.get("strategy_allowlist"))
    if marker:
        return marker
    marker = _as_mapping(snapshot.get("strategy_allowlist"))
    if marker:
        return marker
    snapshot_prediction = _as_mapping(snapshot.get("prediction"))
    return _as_mapping(snapshot_prediction.get("strategy_allowlist"))


def _admission_decision(admission: Mapping[str, object]) -> str:
    decision = str(admission.get("decision") or "").strip()
    return decision if decision in {"allow", "observe", "block"} else "observe"


def _text(value: object, default: str = "-") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _parse_date_value(value: object) -> date | None:
    text = _text(value, "")
    if not text:
        return None
    text = text.replace("/", "-")
    if len(text) >= 10:
        text = text[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _md_cell(value: object) -> str:
    return _text(value).replace("|", "/").replace("\n", " ")


def _risk_text(value: object) -> str:
    text = _text(value, "")
    upper = text.upper()
    if "HIGH" in upper or "\u9ad8" in text:
        return "\u9ad8\u98ce\u9669"
    if "MEDIUM" in upper or "\u4e2d" in text:
        return "\u4e2d\u98ce\u9669"
    if "LOW" in upper or "\u4f4e" in text:
        return "\u4f4e\u98ce\u9669"
    return text or "-"


def _admission_label(admission: Mapping[str, object]) -> str:
    decision = str(admission.get("decision") or "").strip()
    return _text(admission.get("label") or ADMISSION_DECISION_LABELS.get(decision))


def _admission_reason_label(value: object) -> str:
    key = _text(value, "")
    return ADMISSION_REASON_LABELS.get(key, key)


def _admission_reasons(admission: Mapping[str, object], *, limit: int = 6) -> str:
    reasons = admission.get("reasons", [])
    if not isinstance(reasons, list) or not reasons:
        return "-"
    try:
        count = max(0, int(limit))
    except (TypeError, ValueError):
        count = 6
    items = [_admission_reason_label(item) for item in reasons[:count]]
    return "\uff1b".join(item for item in items if item) or "-"


def format_strategy_admission_label(admission: Mapping[str, object] | object) -> str:
    return _admission_label(_as_mapping(admission))


def format_strategy_admission_action(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    action = _text(resolved.get("action"), "")
    return ADMISSION_ACTION_LABELS.get(action, action or "-")


def format_strategy_admission_reasons(admission: Mapping[str, object] | object, *, limit: int = 6) -> str:
    return _admission_reasons(_as_mapping(admission), limit=limit)


def format_strategy_admission_pick(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    play = _label(PLAY_LABELS, resolved.get("top_play"))
    pick = _text(resolved.get("top_pick"))
    confidence = _pct(resolved.get("top_confidence"))
    if play == "-" and pick == "-":
        return "-"
    return f"{play} {pick} / {confidence}"


def format_strategy_admission_thresholds(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    if not resolved:
        return "-"
    active_count = _safe_int(resolved.get("active_count"))
    active_min = max(1, _safe_int(resolved.get("active_strategy_min"), 1))
    medium_policy = "\u5141\u8bb8" if _safe_bool(resolved.get("medium_risk_allowed"), True) else "\u89c2\u5bdf"
    high_policy = "\u5141\u8bb8" if _safe_bool(resolved.get("high_risk_allowed"), False) else "\u963b\u65ad"
    return (
        f"\u7f6e\u4fe1 {_pct(resolved.get('confidence'))} / "
        f"\u653e\u884c\u7ebf {_pct(resolved.get('min_confidence'))} / "
        f"\u963b\u65ad\u7ebf {_pct(resolved.get('block_confidence'))}\uff1b"
        f"\u9ad8\u51c6 {active_count}/{active_min}\uff1b"
        f"\u4e2d\u98ce\u9669{medium_policy}\uff1b\u9ad8\u98ce\u9669{high_policy}"
    )


def format_strategy_admission_replay_guard(admission: Mapping[str, object] | object) -> str:
    resolved = _as_mapping(admission)
    guard = _as_mapping(resolved.get("agent_replay_guard"))
    if not guard:
        return "-"
    if not _safe_bool(guard.get("applied")):
        agent_names = guard.get("agent_names") if isinstance(guard.get("agent_names"), list) else []
        if not agent_names:
            return "-"
        return f"未触发降级 | 当前Agent: {', '.join(str(item) for item in agent_names)}"
    top_agent = _text(guard.get("top_agent"))
    prediction_rate = guard.get("top_prediction_miss_rate")
    handicap_rate = guard.get("top_handicap_miss_rate")
    parts = [f"触发观察降级 | Agent {top_agent}"]
    if prediction_rate is not None:
        parts.append(f"胜平负历史失误 {_pct(prediction_rate)}")
    if handicap_rate is not None:
        parts.append(f"让球历史失误 {_pct(handicap_rate)}")
    actions = guard.get("actions") if isinstance(guard.get("actions"), list) else []
    if actions:
        parts.append(f"动作 {', '.join(str(item) for item in actions[:3])}")
    return "；".join(parts)


def _high_strategy_count(high_strategy: Mapping[str, object], field: str, items: list[object]) -> int:
    if items:
        return len(items)
    return _safe_int(high_strategy.get(field))


def _high_strategy_feedback_text(item: Mapping[str, object]) -> str:
    feedback = _as_mapping(item.get("jc_live_feedback"))
    if feedback:
        live_count = _safe_int(feedback.get("live_count"))
        hit_count = _safe_int(feedback.get("live_hit_count"))
        rate = feedback.get("live_hit_rate")
        status = _text(feedback.get("status"))
        recovery = _text(feedback.get("recovery_status"), "")
        suffix = f" | 恢复 {recovery}" if recovery else ""
        if live_count:
            return f"实盘 {status} {hit_count}/{live_count} ({_pct(rate)}){suffix}"
        return f"实盘 {status}{suffix}"

    breaker = _as_mapping(item.get("breaker"))
    known_count = _safe_int(breaker.get("known_count"))
    if known_count:
        hit_count = _safe_int(breaker.get("hit_count"))
        return f"实盘反馈 {hit_count}/{known_count} ({_pct(breaker.get('recent_hit_rate'))})"
    return "实盘待反馈"


def _high_strategy_breaker_text(item: Mapping[str, object]) -> str:
    breaker = _as_mapping(item.get("breaker"))
    if not breaker:
        return "断路 -"
    status = _text(breaker.get("status"))
    miss = _safe_int(breaker.get("miss_streak"))
    threshold = _safe_int(breaker.get("threshold"), 3)
    recovery = _safe_int(breaker.get("recovery_streak"))
    recovery_required = _safe_int(breaker.get("recovery_hits_required"), 2)
    return f"断路 {status} | 连错 {miss}/{threshold} | 恢复 {recovery}/{recovery_required}"


def _format_high_strategy_item(item: Mapping[str, object], *, label: str, index: int) -> str:
    play = _label(PLAY_LABELS, item.get("play_type"))
    pick = _text(item.get("pick"))
    confidence = _pct(item.get("confidence"))
    min_confidence = _pct(item.get("min_confidence"))
    accuracy = item.get("backtest_accuracy", item.get("accuracy"))
    hit_count = _safe_int(item.get("backtest_hits", item.get("hit_count")))
    sample_count = _safe_int(item.get("backtest_samples", item.get("sample_count")))
    layer = _as_mapping(item.get("layer"))
    data_layer = _label(DATA_LAYER_LABELS, item.get("data_layer") or layer.get("data_layer"))
    role = _label(ROLE_LABELS, item.get("effective_role") or item.get("role"))
    return (
        f"{index}. {label}/{role} {play} {pick} | "
        f"置信 {confidence}/{min_confidence} | "
        f"回测 {_pct(accuracy)} ({hit_count}/{sample_count}) | "
        f"{data_layer} | {_high_strategy_breaker_text(item)} | {_high_strategy_feedback_text(item)}"
    )


def format_high_accuracy_strategy_release_explanation(
    high_strategy: Mapping[str, object] | object,
    admission: Mapping[str, object] | object = None,
    *,
    limit: int = 3,
) -> str:
    resolved = _as_mapping(high_strategy)
    if not resolved or not _safe_bool(resolved.get("enabled")):
        return "-"

    admission_payload = _as_mapping(admission)
    active_items = [item for item in _as_list(resolved.get("active_matches")) if isinstance(item, Mapping)]
    shadow_items = [item for item in _as_list(resolved.get("shadow_matches")) if isinstance(item, Mapping)]
    active_count = _high_strategy_count(resolved, "active_count", active_items)
    shadow_count = _high_strategy_count(resolved, "shadow_count", shadow_items)
    summary = _text(resolved.get("summary"))
    decision = _admission_label(admission_payload) if admission_payload else ("正式放行" if active_count else "观察")
    release_state = "可放行" if _safe_bool(admission_payload.get("release_allowed")) else "不可放行" if admission_payload else ("可放行" if active_count else "不可放行")

    lines = [
        f"状态: {decision} / {release_state} | 正式 {active_count} / 观察 {shadow_count} | {summary}",
    ]
    if admission_payload:
        lines.append(f"候选: {format_strategy_admission_pick(admission_payload)}")

    evidence: list[tuple[str, Mapping[str, object]]] = [("正式", item) for item in active_items]
    evidence.extend(("观察", item) for item in shadow_items)
    if not evidence and resolved.get("play_type"):
        evidence.append(("候选", resolved))

    try:
        item_limit = max(0, int(limit))
    except (TypeError, ValueError):
        item_limit = 3
    for index, (label, item) in enumerate(evidence[:item_limit], start=1):
        lines.append(_format_high_strategy_item(item, label=label, index=index))
    if len(evidence) > item_limit:
        lines.append(f"... 另有 {len(evidence) - item_limit} 条策略证据")
    return "\n".join(lines)


def compute_strategy_admission_counts(rows: Sequence[object] | object) -> dict[str, int]:
    counts = {"all": 0, "allow": 0, "observe": 0, "block": 0}
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return counts
    for row in rows:
        prediction = _row_prediction(row)
        if not prediction:
            continue
        counts["all"] += 1
        counts[_admission_decision(_strategy_admission(prediction))] += 1
    return counts


def filter_strategy_admission_rows(rows: Sequence[object] | object, selected_filter: object = "all") -> list[object]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    selected = str(selected_filter or "all").strip()
    if selected not in ADMISSION_FILTER_LABELS:
        selected = next((key for key, label in ADMISSION_FILTER_LABELS.items() if label == selected), "all")
    if selected == "all":
        return list(rows)
    return [
        row
        for row in rows
        if _admission_decision(_strategy_admission(_row_prediction(row))) == selected
    ]


def build_strategy_release_pool_rows(
    rows: Sequence[object] | object,
    *,
    snapshots: Mapping[str, object] | object = None,
    settlements: Sequence[Mapping[str, object]] | object = None,
) -> list[dict[str, object]]:
    snapshot_map = snapshots if isinstance(snapshots, Mapping) else {}
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    settled_ids = {_settlement_match_id(item) for item in settlement_items if _settlement_match_id(item)}
    pool: list[dict[str, object]] = []
    for row in select_strategy_allowlist_rows(rows):
        match = _row_match(row)
        prediction = _row_prediction(row)
        admission = _strategy_admission(prediction)
        match_id = _row_match_id(match)
        snapshot = _as_mapping(snapshot_map.get(match_id)) if match_id else {}
        marker = _allowlist_marker(prediction, snapshot)
        exported = bool(_text(marker.get("file"), ""))
        snapshot_saved = bool(snapshot)
        settled = bool(match_id and match_id in settled_ids)
        pool.append(
            {
                "match_id": match_id,
                "match": match,
                "prediction": prediction,
                "admission": admission,
                "title": f"{_text(_field(match, 'league'))} | {_text(_field(match, 'home_team'))} vs {_text(_field(match, 'away_team'))}",
                "kickoff": f"{_text(_field(match, 'match_date'))} {_text(_field(match, 'match_time'))}",
                "recommendation": _text(prediction.get("recommendation")),
                "confidence_text": _pct(prediction.get("confidence")),
                "risk_text": _risk_text(prediction.get("risk_level")),
                "candidate_text": format_strategy_admission_pick(marker if marker else admission),
                "reason_text": format_strategy_admission_reasons(marker if marker else admission, limit=4),
                "export_status": "\u5df2\u5bfc\u51fa" if exported else "\u672a\u5bfc\u51fa",
                "allowlist_file": _text(marker.get("file")),
                "exported_at": _text(marker.get("exported_at")),
                "snapshot_status": "\u5df2\u4fdd\u5b58" if snapshot_saved else "\u7f3a\u5feb\u7167",
                "settlement_status": "\u5df2\u56de\u6536" if settled else "\u5f85\u56de\u6536",
                "ready_for_recovery": bool(snapshot_saved and not settled),
            }
        )
    return pool


def build_strategy_release_recovery_alerts(snapshot_rows: Sequence[Mapping[str, object]] | object, *, limit: int = 5) -> dict[str, object]:
    if not isinstance(snapshot_rows, Sequence) or isinstance(snapshot_rows, (str, bytes)):
        return {"count": 0, "rows": [], "summary": "\u6682\u65e0\u6b63\u5f0f\u653e\u884c\u5f85\u56de\u6536\u63d0\u9192"}
    alerts: list[dict[str, str]] = []
    for item in snapshot_rows:
        if not isinstance(item, Mapping):
            continue
        allowlist = _as_mapping(item.get("strategy_allowlist"))
        if not allowlist:
            continue
        if _text(item.get("status")) != "\u5f85\u56de\u6536":
            continue
        match = _as_mapping(item.get("match"))
        prediction = _as_mapping(item.get("prediction"))
        title = (
            f"\u5f85\u56de\u6536 | {_text(match.get('league'))} | "
            f"{_text(match.get('home_team'))} vs {_text(match.get('away_team'))}"
        )
        body = (
            f"\u5f00\u8d5b: {_text(match.get('match_date'))} {_text(match.get('match_time'))}\n"
            f"\u63a8\u8350: {_text(prediction.get('recommendation'))} | \u7f6e\u4fe1 {_pct(prediction.get('confidence'))} | \u98ce\u9669 {_risk_text(prediction.get('risk_level'))}\n"
            f"\u6e05\u5355: {_text(allowlist.get('file'))} | \u5bfc\u51fa\u65f6\u95f4: {_text(allowlist.get('exported_at'))}\n"
            f"\u5019\u9009: {format_strategy_admission_pick(allowlist)}"
        )
        alerts.append({"title": title, "body": body})
    try:
        max_rows = max(0, int(limit))
    except (TypeError, ValueError):
        max_rows = 5
    count = len(alerts)
    return {
        "count": count,
        "rows": alerts[:max_rows],
        "summary": f"\u6709 {count} \u573a\u6b63\u5f0f\u653e\u884c\u5df2\u8fdb\u5165\u5f85\u56de\u6536" if count else "\u6682\u65e0\u6b63\u5f0f\u653e\u884c\u5f85\u56de\u6536\u63d0\u9192",
    }


def _allowlist_sort_key(row: object) -> tuple[str, str, str, str, float]:
    match = _row_match(row)
    prediction = _row_prediction(row)
    return (
        _text(_field(match, "match_date")),
        _text(_field(match, "match_time")),
        _text(_field(match, "league")),
        _text(_field(match, "home_team")),
        -_safe_float(prediction.get("confidence")),
    )


def _strategy_pool(status: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [item for item in _as_list(status.get("strategy_pool")) if isinstance(item, Mapping)]


def _strategy_layer(item: Mapping[str, object]) -> Mapping[str, object]:
    return _as_mapping(item.get("layer"))


def _strategy_stability(item: Mapping[str, object]) -> Mapping[str, object]:
    return _as_mapping(item.get("stability"))


def _known_strategy_settlement_items(settlements: Sequence[Mapping[str, object]]) -> list[tuple[Mapping[str, object], Mapping[str, object]]]:
    rows: list[tuple[Mapping[str, object], Mapping[str, object]]] = []
    for settlement in settlements:
        if not isinstance(settlement, Mapping):
            continue
        for item in _as_list(settlement.get("high_accuracy_strategy_items")):
            if isinstance(item, Mapping):
                rows.append((settlement, item))
    return rows


def build_high_accuracy_strategy_settlement_summary(settlements: Sequence[Mapping[str, object]]) -> dict[str, object]:
    rows = _known_strategy_settlement_items(settlements)
    known = [item for _settlement, item in rows if item.get("is_hit") is not None]
    official = [item for item in known if not bool(item.get("is_shadow"))]
    shadow = [item for item in known if bool(item.get("is_shadow"))]
    hits = sum(1 for item in known if item.get("is_hit") is True)
    misses = sum(1 for item in known if item.get("is_hit") is False)
    unknown = len(rows) - len(known)
    hit_rate = hits / len(known) if known else None
    official_hits = sum(1 for item in official if item.get("is_hit") is True)
    shadow_hits = sum(1 for item in shadow if item.get("is_hit") is True)
    return {
        "active_count": len(rows),
        "official_count": len(official),
        "official_hit_count": official_hits,
        "shadow_count": len(shadow),
        "shadow_hit_count": shadow_hits,
        "known_count": len(known),
        "hit_count": hits,
        "miss_count": misses,
        "unknown_count": unknown,
        "hit_rate": hit_rate,
        "hit_rate_text": _pct(hit_rate) if hit_rate is not None else "-",
        "summary_text": f"{hits}/{len(known)}" if known else "-",
        "official_summary_text": f"{official_hits}/{len(official)}" if official else "-",
        "shadow_summary_text": f"{shadow_hits}/{len(shadow)}" if shadow else "-",
    }


ERROR_ATTRIBUTION_LABELS = {
    "data_missing": "\u6570\u636e\u7f3a\u5931",
    "high_confidence_miss": "\u9ad8\u7f6e\u4fe1\u5931\u8bef",
    "historical_gap": "\u5386\u53f2\u56de\u6d4b\u4e0e\u5b9e\u76d8\u80cc\u79bb",
    "jc_wilson_breach": "JC\u8dcc\u7834Wilson",
    "jc_odds_drift": "JC\u8d54\u7387\u6f02\u79fb",
    "jc_confidence_drift": "JC\u7f6e\u4fe1\u6f02\u79fb",
    "jc_live_downgraded": "JC\u7a33\u5b9a\u6876\u964d\u7ea7",
    "statsbomb_xg_against_pick": "StatsBomb xG\u53cd\u5411",
    "statsbomb_finishing_variance": "StatsBomb\u7ec8\u7ed3\u504f\u5dee",
    "statsbomb_event_control_gap": "StatsBomb\u573a\u9762\u52a3\u52bf",
    "video_tempo_shift": "AI Video\u8282\u594f\u53d8\u5316",
    "video_finishing_variance": "AI Video\u7ec8\u7ed3\u6ce2\u52a8",
    "video_margin_risk": "AI Video\u8ba9\u7403/\u80dc\u5dee\u98ce\u9669",
    "video_low_quality_evidence": "AI Video\u8bc1\u636e\u4e0d\u8db3",
    "video_manual_review_needed": "AI Video\u9700\u4eba\u5de5\u590d\u6838",
    "small_sample": "\u6837\u672c\u4e0d\u8db3",
    "shadow_observation": "\u89c2\u5bdf\u7b56\u7565\u5931\u8bef",
    "unknown": "\u672a\u5b9a\u4e49\u9519\u56e0",
}
ERROR_ATTRIBUTION_WEIGHTS = {
    "small_sample": 0.25,
    "statsbomb_xg_against_pick": 1.15,
    "statsbomb_finishing_variance": 1.12,
    "statsbomb_event_control_gap": 1.1,
    "video_low_quality_evidence": 0.35,
    "video_manual_review_needed": 0.5,
}
STATSBOMB_EVENT_ATTRIBUTION_CODES = (
    "statsbomb_xg_against_pick",
    "statsbomb_finishing_variance",
    "statsbomb_event_control_gap",
)

VIDEO_REVIEW_HYPOTHESIS_TO_ERROR_CODE = {
    "tempo_shift": "video_tempo_shift",
    "finishing_variance": "video_finishing_variance",
    "set_piece_or_transition_risk": "video_margin_risk",
    "low_quality_video_evidence": "video_low_quality_evidence",
    "manual_tactical_review_needed": "video_manual_review_needed",
}


def _error_attribution_rank_key(
    item: tuple[str, int],
    weights: Mapping[str, object] | None = None,
) -> tuple[float, int, str]:
    code, count = item
    resolved_weights = _as_mapping(weights) or ERROR_ATTRIBUTION_WEIGHTS
    weight = _safe_float(resolved_weights.get(code, ERROR_ATTRIBUTION_WEIGHTS.get(code, 1.0)), 1.0)
    priority = 1 if code == "small_sample" else 0
    return (-count * weight, priority, ERROR_ATTRIBUTION_LABELS.get(code, code))


def _label_count_pair(label_counts: Mapping[str, object], label: str) -> tuple[int, int]:
    bucket = _as_mapping(label_counts.get(label))
    negative = _safe_int(bucket.get("0", bucket.get(0)))
    positive = _safe_int(bucket.get("1", bucket.get(1)))
    return negative, positive


def build_statsbomb_review_training_weight_signal(
    payload: Mapping[str, object] | object | None,
) -> dict[str, object]:
    resolved = _as_mapping(payload)
    items = _as_list(resolved.get("items"))
    summary = _as_mapping(resolved.get("summary"))
    sample_count = _safe_int(summary.get("sample_count"), len(items))
    feature_order = _as_list(summary.get("feature_order"))
    label_counts = _as_mapping(summary.get("label_counts"))
    prediction_hit_count, prediction_miss_count = _label_count_pair(label_counts, "prediction_miss")
    prediction_known_count = prediction_hit_count + prediction_miss_count
    prediction_miss_rate = prediction_miss_count / prediction_known_count if prediction_known_count else None

    status = "missing"
    if sample_count > 0:
        status = "weak"
    if sample_count >= 20 and prediction_known_count >= 10:
        status = "ready"

    weight = 1.0
    if sample_count > 0:
        weight = 1.05
    if sample_count >= 20 and prediction_known_count >= 10:
        weight = 1.15
    if sample_count >= 50:
        weight = 1.25
    if sample_count >= 100:
        weight = 1.35
    if prediction_miss_rate is not None and prediction_miss_rate >= 0.55:
        weight += 0.05
    weight = round(min(1.45, max(1.0, weight)), 2)

    attribution_weights = dict(ERROR_ATTRIBUTION_WEIGHTS)
    if sample_count > 0:
        attribution_weights.update(
            {
                "statsbomb_xg_against_pick": round(min(1.50, weight + 0.05), 2),
                "statsbomb_finishing_variance": weight,
                "statsbomb_event_control_gap": round(min(1.45, weight), 2),
            }
        )

    return {
        "status": status,
        "sample_count": sample_count,
        "feature_count": len(feature_order),
        "prediction_known_count": prediction_known_count,
        "prediction_miss_count": prediction_miss_count,
        "prediction_miss_rate": prediction_miss_rate,
        "prediction_miss_rate_text": _pct(prediction_miss_rate) if prediction_miss_rate is not None else "-",
        "attribution_weights": attribution_weights,
        "active_codes": list(STATSBOMB_EVENT_ATTRIBUTION_CODES) if sample_count > 0 else [],
        "memory_tags": ["statsbomb_review_training_weighted"] if sample_count > 0 else [],
        "summary_text": (
            f"StatsBomb review samples {sample_count} | "
            f"prediction miss {(_pct(prediction_miss_rate) if prediction_miss_rate is not None else '-')} | "
            f"weight {weight:.2f}"
        ),
        "leakage_note": resolved.get("leakage_note")
        or "StatsBomb review training samples use post-match event evidence and must not be used as pre-match prediction features.",
    }


def _statsbomb_review_neutral_attribution_weights() -> dict[str, float]:
    weights = dict(ERROR_ATTRIBUTION_WEIGHTS)
    for code in STATSBOMB_EVENT_ATTRIBUTION_CODES:
        weights[code] = 1.0
    return weights


def _gate_statsbomb_review_training_weight_signal(
    signal: Mapping[str, object] | object,
    quality_status: object,
) -> dict[str, object]:
    resolved = dict(_as_mapping(signal))
    raw_weights = dict(_as_mapping(resolved.get("attribution_weights")))
    status = str(quality_status or "").strip().lower()
    enabled = status == "healthy" and _safe_int(resolved.get("sample_count")) > 0
    if enabled:
        resolved["weight_gate"] = {
            "enabled": True,
            "mode": "active",
            "quality_status": status,
            "reason": "statsbomb_review_quality_healthy",
        }
        resolved["raw_attribution_weights"] = raw_weights
        return resolved

    mode = "disabled" if status == "blocked" else "report_only" if status == "attention" else "disabled"
    resolved["status"] = mode
    resolved["attribution_weights"] = _statsbomb_review_neutral_attribution_weights()
    resolved["raw_attribution_weights"] = raw_weights
    resolved["active_codes"] = []
    resolved["memory_tags"] = ["statsbomb_review_training_report_only"] if mode == "report_only" and _safe_int(resolved.get("sample_count")) > 0 else []
    resolved["weight_gate"] = {
        "enabled": False,
        "mode": mode,
        "quality_status": status or "-",
        "reason": "statsbomb_review_quality_not_healthy",
    }
    resolved["summary_text"] = f"{resolved.get('summary_text') or '-'} | gate={mode}"
    return resolved


def build_statsbomb_review_training_quality_summary(
    payload: Mapping[str, object] | object | None,
) -> dict[str, object]:
    resolved = _as_mapping(payload)
    summary = _as_mapping(resolved.get("summary"))
    raw_signal = build_statsbomb_review_training_weight_signal(resolved)
    label_counts = _as_mapping(summary.get("label_counts"))
    sample_count = _safe_int(raw_signal.get("sample_count"))
    feature_count = _safe_int(raw_signal.get("feature_count"))
    issues: list[dict[str, object]] = []
    label_rows: list[dict[str, object]] = []
    label_specs = [
        ("prediction_miss", "1X2错因标签"),
        ("handicap_miss", "让球错因标签"),
        ("ou_miss", "大小球错因标签"),
    ]
    for key, label in label_specs:
        hit_count, miss_count = _label_count_pair(label_counts, key)
        known_count = hit_count + miss_count
        miss_rate = miss_count / known_count if known_count else None
        tone = "neutral"
        if known_count:
            tone = "warning" if miss_rate is not None and (miss_rate >= 0.80 or miss_rate <= 0.20) else "good"
        label_rows.append(
            {
                "code": key,
                "label": label,
                "known_count": known_count,
                "hit_count": hit_count,
                "miss_count": miss_count,
                "miss_rate": miss_rate,
                "value": f"{miss_count}/{known_count}" if known_count else "-",
                "tone": tone,
                "detail": f"hit={hit_count} | miss={miss_count} | miss_rate={_pct(miss_rate) if miss_rate is not None else '-'}",
            }
        )
        if sample_count > 0 and known_count <= 0:
            issues.append(
                {
                    "code": f"{key}_missing",
                    "severity": "warning",
                    "message": f"{label}缺少可用标签",
                    "recommendation": "补齐赛果回收标签，否则事件代理训练样本无法稳定参与该玩法归因。",
                }
            )
        elif known_count > 0 and miss_rate is not None and (miss_rate >= 0.85 or miss_rate <= 0.15):
            issues.append(
                {
                    "code": f"{key}_skewed",
                    "severity": "warning",
                    "message": f"{label}类别分布偏斜",
                    "recommendation": "补充命中和未命中两类样本，避免 Evaluation Agent 过度偏向单一解释。",
                }
            )

    if sample_count <= 0:
        issues.insert(
            0,
            {
                "code": "statsbomb_review_samples_missing",
                "severity": "blocking",
                "message": "StatsBomb事件代理复盘样本为空",
                "recommendation": "先在复盘中心生成事件代理复盘样本，再观察归因权重变化。",
            },
        )
    elif sample_count < 20:
        issues.append(
            {
                "code": "statsbomb_review_sample_count_low",
                "severity": "warning",
                "message": f"StatsBomb事件代理样本偏少: {sample_count}/20",
                "recommendation": "继续回收带StatsBomb事件摘要的已结算比赛，优先补近期主流赛事。",
            }
        )
    if sample_count > 0 and feature_count <= 0:
        issues.append(
            {
                "code": "statsbomb_review_features_missing",
                "severity": "warning",
                "message": "事件代理样本缺少特征顺序",
                "recommendation": "重新生成复盘训练样本，确保xG、射门、事件数等特征完整。",
            }
        )

    has_blocking = any(str(issue.get("severity") or "") == "blocking" for issue in issues)
    status = "blocked" if has_blocking else "attention" if issues else "healthy"
    tone = "bad" if status == "blocked" else "warning" if status == "attention" else "good"
    signal = _gate_statsbomb_review_training_weight_signal(raw_signal, status)
    active_weights = _as_mapping(signal.get("attribution_weights"))
    weight_gate = _as_mapping(signal.get("weight_gate"))
    gate_mode = str(weight_gate.get("mode") or "")
    weight_rows = [
        {
            "code": code,
            "label": ERROR_ATTRIBUTION_LABELS.get(code, code),
            "value": f"{_safe_float(active_weights.get(code), 1.0):.2f}",
            "tone": "good" if bool(weight_gate.get("enabled")) and _safe_float(active_weights.get(code), 1.0) > 1.0 else "neutral",
            "detail": "赛后事件代理权重，仅在质量 healthy 时用于 Evaluation Agent 错因排序。",
        }
        for code in STATSBOMB_EVENT_ATTRIBUTION_CODES
    ]
    card_rows = [
        {
            "label": "整体状态",
            "value": status,
            "tone": tone,
            "detail": f"issues={len(issues)} | signal={signal.get('status') or '-'}",
        },
        {
            "label": "样本数",
            "value": str(sample_count),
            "tone": "good" if sample_count >= 20 else "warning" if sample_count > 0 else "bad",
            "detail": f"features={feature_count}",
        },
        {
            "label": "1X2标签",
            "value": label_rows[0]["value"] if label_rows else "-",
            "tone": str(label_rows[0]["tone"]) if label_rows else "neutral",
            "detail": str(label_rows[0]["detail"]) if label_rows else "-",
        },
        {
            "label": "权重Gate",
            "value": gate_mode or "-",
            "tone": "good" if bool(weight_gate.get("enabled")) else "warning" if gate_mode == "report_only" else "bad" if gate_mode == "disabled" else "neutral",
            "detail": (
                f"enabled={bool(weight_gate.get('enabled'))} | "
                f"quality={weight_gate.get('quality_status') or '-'} | "
                f"reason={weight_gate.get('reason') or '-'}"
            ),
        },
        {
            "label": "当前权重",
            "value": f"{_safe_float(active_weights.get('statsbomb_finishing_variance'), 1.0):.2f}",
            "tone": "good" if bool(weight_gate.get("enabled")) else "warning" if status == "attention" else "neutral",
            "detail": str(signal.get("summary_text") or "-"),
        },
    ]
    return {
        "status": status,
        "tone": tone,
        "issue_count": len(issues),
        "issues": issues,
        "sample_count": sample_count,
        "feature_count": feature_count,
        "label_rows": label_rows,
        "weight_rows": weight_rows,
        "card_rows": card_rows,
        "signal": signal,
        "raw_signal": raw_signal,
        "weight_gate": dict(weight_gate),
        "summary_text": f"事件代理样本 {sample_count} | 标签 {label_rows[0]['value'] if label_rows else '-'} | 状态 {status}",
        "leakage_note": signal.get("leakage_note"),
    }


def build_statsbomb_review_training_quality_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_review_training_quality_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_review_training_quality_report_lines(
    quality: Mapping[str, object] | object,
    repair_feedback_records: Sequence[Mapping[str, object] | object] | None = None,
    gate_audit_records: Sequence[Mapping[str, object] | object] | None = None,
    gate_alert_action_rows: Sequence[Mapping[str, object] | object] | None = None,
    gate_followup_records: Sequence[Mapping[str, object] | object] | None = None,
) -> list[str]:
    resolved = _as_mapping(quality)
    label_rows = [row for row in _as_list(resolved.get("label_rows")) if isinstance(row, Mapping)]
    weight_rows = [row for row in _as_list(resolved.get("weight_rows")) if isinstance(row, Mapping)]
    issues = [row for row in _as_list(resolved.get("issues")) if isinstance(row, Mapping)]
    feedback_rows = [row for row in _as_list(repair_feedback_records) if isinstance(row, Mapping)]
    audit_rows = [row for row in _as_list(gate_audit_records) if isinstance(row, Mapping)]
    alert_action_rows = [row for row in _as_list(gate_alert_action_rows) if isinstance(row, Mapping)]
    followup_rows = [row for row in _as_list(gate_followup_records) if isinstance(row, Mapping)]
    signal = _as_mapping(resolved.get("signal"))
    weight_gate = _as_mapping(resolved.get("weight_gate") or signal.get("weight_gate"))
    active_codes = ", ".join(str(code) for code in _as_list(signal.get("active_codes"))) or "-"
    memory_tags = ", ".join(str(tag) for tag in _as_list(signal.get("memory_tags"))) or "-"
    audit_modes = [str(row.get("gate_mode") or "-") for row in audit_rows[:8]]
    chronological_modes = list(reversed(audit_modes))
    gate_trend_text = " -> ".join(chronological_modes) or "-"
    gate_transition_count = sum(
        1 for index in range(1, len(chronological_modes)) if chronological_modes[index] != chronological_modes[index - 1]
    )
    gate_mode_counts = Counter(str(row.get("gate_mode") or "-") for row in audit_rows)
    lines = [
        "# StatsBomb/Event Proxy 样本质量报告",
        "",
        f"- 总体质量状态: {resolved.get('status') or '-'}",
        f"- 样本数: {_safe_int(resolved.get('sample_count'))}",
        f"- 特征数: {_safe_int(resolved.get('feature_count'))}",
        f"- issue_count: {_safe_int(resolved.get('issue_count'))}",
        f"- 摘要: {resolved.get('summary_text') or '-'}",
        "- 约束: StatsBomb/Event Proxy 仅用于赛后复盘，不进入赛前预测特征。",
        "",
        "## 权重Gate（weight_gate）",
        "",
        f"- enabled: {bool(weight_gate.get('enabled'))}",
        f"- mode: {weight_gate.get('mode') or '-'}",
        f"- quality_status: {weight_gate.get('quality_status') or '-'}",
        f"- reason: {weight_gate.get('reason') or '-'}",
        f"- active_codes: {active_codes}",
        f"- memory_tags: {memory_tags}",
        "",
        "## 权重Gate趋势（gate_audit_records）",
        "",
        f"- audit_count: {len(audit_rows)}",
        f"- recent_modes_old_to_new: {gate_trend_text}",
        f"- transition_count: {gate_transition_count}",
        f"- active/report_only/disabled: {gate_mode_counts.get('active', 0)}/{gate_mode_counts.get('report_only', 0)}/{gate_mode_counts.get('disabled', 0)}",
        "",
        "| occurred_at | trigger | mode | enabled | quality | reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if not audit_rows:
        lines.append("| - | - | - | - | - | - |")
    for row in audit_rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("occurred_at")),
                    _md_cell(row.get("trigger")),
                    _md_cell(row.get("gate_mode")),
                    _md_cell(bool(row.get("gate_enabled"))),
                    _md_cell(row.get("quality_status")),
                    _md_cell(row.get("gate_reason")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 权重Gate处置动作（gate_alert_actions）",
            "",
            "| action_key | 标题 | 说明 | tone |",
            "| --- | --- | --- | --- |",
        ]
    )
    if not alert_action_rows:
        lines.append("| - | - | - | - |")
    for row in alert_action_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("action_key")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("body")),
                    _md_cell(row.get("tone")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 权重Gate复检（gate_followup_records）",
            "",
            "| title | body | tone |",
            "| --- | --- | --- |",
        ]
    )
    if not followup_rows:
        lines.append("| - | - | - |")
    for row in followup_rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("title")),
                    _md_cell(row.get("body")),
                    _md_cell(row.get("tone")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 标签分布（label_rows）",
            "",
            "| 标签 | 值 | 已知样本 | hit | miss | miss_rate |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    if not label_rows:
        lines.append("| - | - | 0 | 0 | 0 | - |")
    for row in label_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("label") or row.get("code")),
                    _md_cell(row.get("value")),
                    str(_safe_int(row.get("known_count"))),
                    str(_safe_int(row.get("hit_count"))),
                    str(_safe_int(row.get("miss_count"))),
                    _md_cell(_pct(row.get("miss_rate")) if row.get("miss_rate") is not None else "-"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 错因权重（weight_rows）",
            "",
            "| 代码 | 权重 | 说明 |",
            "| --- | ---: | --- |",
        ]
    )
    if not weight_rows:
        lines.append("| - | 1.00 | - |")
    for row in weight_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("code")),
                    _md_cell(row.get("value")),
                    _md_cell(row.get("detail")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 质量问题与建议（issues）",
            "",
            "| 问题代码 | 严重级别 | 说明 | 建议 |",
            "| --- | --- | --- | --- |",
        ]
    )
    if not issues:
        lines.append("| - | - | - | - |")
    for issue in issues:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(issue.get("code")),
                    _md_cell(issue.get("severity")),
                    _md_cell(issue.get("message")),
                    _md_cell(issue.get("recommendation")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 最近修复反馈（repair_feedback_records）",
            "",
            "| action_key | outcome | 样本变化 | 问题变化 | 下一步建议 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if not feedback_rows:
        lines.append("| - | - | - | - | - |")
    for row in feedback_rows[:20]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("action_key")),
                    _md_cell(row.get("outcome")),
                    _md_cell(row.get("sample_change") or row.get("sample_delta")),
                    _md_cell(row.get("issue_change") or row.get("issue_delta")),
                    _md_cell(row.get("next_step") or row.get("next_recommendation")),
                ]
            )
            + " |"
        )
    return lines


def _pick_side(value: object) -> str:
    text = _text(value, "").upper()
    if text in {"HOME", "HOME_WIN", "H", "1"} or "HOME" in text:
        return "home"
    if text in {"AWAY", "AWAY_WIN", "A", "2"} or "AWAY" in text:
        return "away"
    if "\u4e3b" in text:
        return "home"
    if "\u5ba2" in text:
        return "away"
    return ""


def _actual_side(value: object) -> str:
    text = _text(value, "").upper()
    if text in {"HOME", "HOME_WIN", "H", "1"} or "HOME" in text:
        return "home"
    if text in {"AWAY", "AWAY_WIN", "A", "2"} or "AWAY" in text:
        return "away"
    if text in {"DRAW", "D", "X"} or "DRAW" in text:
        return "draw"
    if "\u4e3b" in text:
        return "home"
    if "\u5ba2" in text:
        return "away"
    if "\u5e73" in text:
        return "draw"
    return ""


def _statsbomb_team_stats(settlement: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object], str, str]:
    summary = _as_mapping(settlement.get("statsbomb_event_summary"))
    team_stats = _as_mapping(summary.get("team_stats"))
    home = _text(settlement.get("home_team"), "")
    away = _text(settlement.get("away_team"), "")
    home_stats = _as_mapping(team_stats.get(home))
    away_stats = _as_mapping(team_stats.get(away))
    if (not home_stats or not away_stats) and len(team_stats) >= 2:
        names = list(team_stats.keys())
        if not home_stats:
            home = _text(names[0], home)
            home_stats = _as_mapping(team_stats.get(names[0]))
        if not away_stats:
            away = _text(names[1], away)
            away_stats = _as_mapping(team_stats.get(names[1]))
    return home_stats, away_stats, home, away


def _statsbomb_event_evidence(settlement: Mapping[str, object], item: Mapping[str, object]) -> dict[str, object]:
    home_stats, away_stats, home, away = _statsbomb_team_stats(settlement)
    if not home_stats or not away_stats:
        return {"codes": [], "body": "", "available": False}
    home_xg = _safe_float(home_stats.get("xg"))
    away_xg = _safe_float(away_stats.get("xg"))
    home_shots = _safe_int(home_stats.get("shots"))
    away_shots = _safe_int(away_stats.get("shots"))
    home_goals = _safe_int(home_stats.get("goals"), _safe_int(settlement.get("home_goals")))
    away_goals = _safe_int(away_stats.get("goals"), _safe_int(settlement.get("away_goals")))
    pick_side = _pick_side(item.get("pick"))
    actual_side = _actual_side(item.get("actual"))
    codes: list[str] = []
    if item.get("is_hit") is False and pick_side in {"home", "away"}:
        picked_xg = home_xg if pick_side == "home" else away_xg
        opponent_xg = away_xg if pick_side == "home" else home_xg
        picked_shots = home_shots if pick_side == "home" else away_shots
        opponent_shots = away_shots if pick_side == "home" else home_shots
        if picked_xg + 0.25 < opponent_xg:
            codes.append("statsbomb_xg_against_pick")
        if picked_xg >= opponent_xg + 0.35 and actual_side and actual_side != pick_side:
            codes.append("statsbomb_finishing_variance")
        if picked_xg + 0.15 < opponent_xg and picked_shots + 4 <= opponent_shots:
            codes.append("statsbomb_event_control_gap")
    body = (
        f"StatsBomb: xG {home} {home_xg:.2f} - {away_xg:.2f} {away} | "
        f"\u5c04\u95e8 {home_shots}-{away_shots} | \u8fdb\u7403 {home_goals}-{away_goals}"
    )
    return {"codes": codes, "body": body, "available": True}


def _video_review_agent(settlement: Mapping[str, object]) -> Mapping[str, object]:
    video_review = _as_mapping(settlement.get("video_review"))
    return _as_mapping(video_review.get("agent_review"))


def _video_review_hypothesis_rows(agent_review: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [row for row in _as_list(agent_review.get("event_hypotheses")) if isinstance(row, Mapping)]


def _video_review_evidence(settlement: Mapping[str, object]) -> dict[str, object]:
    agent_review = _video_review_agent(settlement)
    if not agent_review:
        return {"codes": [], "body": "", "available": False}
    hypotheses = _video_review_hypothesis_rows(agent_review)
    evidence_level = _text(agent_review.get("evidence_level"), "unknown")
    evidence_score = _safe_float(agent_review.get("evidence_score"), 0.0)
    followup = _as_mapping(agent_review.get("recommended_followup"))
    codes: list[str] = []
    for item in hypotheses:
        hypothesis_code = _text(item.get("code"), "")
        mapped = VIDEO_REVIEW_HYPOTHESIS_TO_ERROR_CODE.get(hypothesis_code)
        confidence = _safe_float(item.get("confidence"), 0.0)
        if mapped and (confidence >= 0.35 or mapped == "video_low_quality_evidence"):
            codes.append(mapped)
    if evidence_level == "low" and "video_low_quality_evidence" not in codes:
        codes.append("video_low_quality_evidence")
    top = hypotheses[0] if hypotheses else {}
    top_code = _text(top.get("code"), "-") if isinstance(top, Mapping) else "-"
    top_confidence = _safe_float(top.get("confidence"), 0.0) if isinstance(top, Mapping) else 0.0
    body = (
        f"AI Video: evidence {evidence_level}/{_pct(evidence_score)} | "
        f"top {top_code} {_pct(top_confidence)} | followup {followup.get('code') or '-'}"
    )
    deduped: list[str] = []
    for code in codes:
        if code not in deduped:
            deduped.append(code)
    return {
        "codes": deduped,
        "body": body,
        "available": True,
        "evidence_level": evidence_level,
        "evidence_score": evidence_score,
        "hypotheses": hypotheses,
        "recommended_followup": followup,
    }


def build_video_review_memory_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    review_count = 0
    visual_ready_count = 0
    low_evidence_count = 0
    actionable_count = 0
    hypothesis_counts: dict[str, int] = {}
    followup_counts: dict[str, int] = {}
    rows: list[dict[str, object]] = []
    memory_tags: list[str] = []
    for settlement in settlement_items:
        agent_review = _video_review_agent(settlement)
        if not agent_review:
            continue
        review_count += 1
        if str(agent_review.get("vision_model_status") or "") == "offline_visual_evidence_ready":
            visual_ready_count += 1
        evidence_level = _text(agent_review.get("evidence_level"), "unknown")
        evidence_score = _safe_float(agent_review.get("evidence_score"), 0.0)
        if evidence_level == "low":
            low_evidence_count += 1
        hypotheses = _video_review_hypothesis_rows(agent_review)
        followup = _as_mapping(agent_review.get("recommended_followup"))
        followup_code = _text(followup.get("code"), "")
        if followup_code:
            followup_counts[followup_code] = _safe_int(followup_counts.get(followup_code)) + 1
        for hypothesis in hypotheses:
            code = _text(hypothesis.get("code"), "")
            if not code:
                continue
            hypothesis_counts[code] = _safe_int(hypothesis_counts.get(code)) + 1
            mapped = VIDEO_REVIEW_HYPOTHESIS_TO_ERROR_CODE.get(code)
            if mapped and mapped not in memory_tags:
                memory_tags.append(mapped)
            if mapped and mapped not in {"video_low_quality_evidence", "video_manual_review_needed"}:
                actionable_count += 1
        top = hypotheses[0] if hypotheses else {}
        rows.append(
            {
                "title": f"{settlement.get('match_date') or '-'} | {settlement.get('league') or '-'} | {settlement.get('home_team') or '-'} vs {settlement.get('away_team') or '-'}",
                "body": (
                    f"evidence {evidence_level}/{_pct(evidence_score)} | "
                    f"top {_text(top.get('code'), '-') if isinstance(top, Mapping) else '-'} "
                    f"{_pct(top.get('confidence')) if isinstance(top, Mapping) else '-'} | "
                    f"followup {followup_code or '-'}"
                ),
                "evidence_level": evidence_level,
                "evidence_score": evidence_score,
                "top_hypothesis": _text(top.get("code"), "-") if isinstance(top, Mapping) else "-",
                "top_confidence": _safe_float(top.get("confidence"), 0.0) if isinstance(top, Mapping) else 0.0,
                "recommended_followup": followup_code or "-",
            }
        )
    ranked_hypotheses = sorted(hypothesis_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    top_hypothesis = ranked_hypotheses[0][0] if ranked_hypotheses else "-"
    status = "missing"
    if review_count:
        status = "needs_more_evidence" if low_evidence_count and not actionable_count else "ready"
    if review_count and "video_post_match_review" not in memory_tags:
        memory_tags.insert(0, "video_post_match_review")
    return {
        "status": status,
        "review_count": review_count,
        "visual_ready_count": visual_ready_count,
        "low_evidence_count": low_evidence_count,
        "actionable_count": actionable_count,
        "hypothesis_counts": dict(ranked_hypotheses),
        "followup_counts": dict(sorted(followup_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))),
        "top_hypothesis": top_hypothesis,
        "memory_tags": memory_tags,
        "rows": rows[: max(0, int(limit))],
        "summary_text": f"AI Video {review_count} | ready {visual_ready_count} | actionable {actionable_count} | top {top_hypothesis}",
        "leakage_note": "AI video review uses post-match visual evidence and must not be used as pre-match prediction features.",
    }


def build_video_review_source_coverage_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    statsbomb_samples: Sequence[Mapping[str, object]] | Mapping[str, object] | object | None = None,
    video_memory: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    def _list_items(value: Sequence[Mapping[str, object]] | Mapping[str, object] | object | None) -> list[Mapping[str, object]]:
        if isinstance(value, Mapping):
            for key in ("items", "rows", "settlements"):
                resolved = value.get(key)
                if isinstance(resolved, Sequence) and not isinstance(resolved, (str, bytes)):
                    return [item for item in resolved if isinstance(item, Mapping)]
            return []
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [item for item in value if isinstance(item, Mapping)]
        return []

    def _match_id(item: Mapping[str, object]) -> str:
        direct = _text(item.get("match_id"), "")
        if direct:
            return direct
        match = _as_mapping(item.get("match"))
        direct = _text(match.get("match_id"), "")
        if direct:
            return direct
        return _text(item.get("source_match_id"), "")

    def _video_kind(settlement: Mapping[str, object]) -> str:
        review = _as_mapping(settlement.get("video_review"))
        video = _as_mapping(review.get("video"))
        if not video:
            video = _as_mapping(settlement.get("video"))
        source_policy = _as_mapping(review.get("source_policy"))
        source_type = _text(video.get("source_type"), "").strip().lower()
        path = _text(video.get("path"), "").strip()
        url = _text(video.get("url"), "").strip()
        probe_status = _text(video.get("probe_status"), "").strip().lower()
        if source_type in {"local_file", "local_video", "file"}:
            return "local_video"
        if path and source_policy.get("mode") != "reference_only" and probe_status != "external_reference":
            return "local_video"
        if source_type == "external_reference" or source_policy.get("mode") == "reference_only" or url or probe_status == "external_reference":
            return "external_reference"
        return ""

    settlement_items = _list_items(settlements)
    sample_items = _list_items(statsbomb_samples)
    memory_items = _list_items(video_memory)
    memory_summary = _as_mapping(_as_mapping(video_memory or {}).get("summary"))

    statsbomb_proxy_match_ids: set[str] = set()
    for sample in sample_items:
        meta = _as_mapping(sample.get("meta"))
        source_text = " ".join(
            [
                _text(sample.get("source"), ""),
                _text(meta.get("source"), ""),
            ]
        ).strip().lower()
        if not source_text:
            continue
        if "statsbomb" not in source_text and "event_proxy" not in source_text and "event-sandbox" not in source_text:
            continue
        match_id = _match_id(sample) or _text(meta.get("match_id"), "") or _text(meta.get("source_match_id"), "")
        if match_id:
            statsbomb_proxy_match_ids.add(match_id)

    total_settled_count = len(settlement_items)
    local_video_count = 0
    external_reference_count = 0
    statsbomb_event_proxy_count = 0
    no_review_evidence_count = 0
    rows: list[dict[str, object]] = []

    for settlement in settlement_items:
        video_kind = _video_kind(settlement)
        summary = _as_mapping(settlement.get("statsbomb_event_summary"))
        match_id = _match_id(settlement)
        if video_kind == "local_video":
            local_video_count += 1
        elif video_kind == "external_reference":
            external_reference_count += 1
        elif summary or (match_id and match_id in statsbomb_proxy_match_ids):
            statsbomb_event_proxy_count += 1
        else:
            no_review_evidence_count += 1

    def _ratio_text(count: int) -> str:
        return _pct(count / total_settled_count) if total_settled_count else "-"

    local_ratio = local_video_count / total_settled_count if total_settled_count else 0.0
    external_ratio = external_reference_count / total_settled_count if total_settled_count else 0.0
    proxy_ratio = statsbomb_event_proxy_count / total_settled_count if total_settled_count else 0.0
    missing_ratio = no_review_evidence_count / total_settled_count if total_settled_count else 1.0

    if total_settled_count <= 0:
        coverage_status = "blocked"
    elif no_review_evidence_count == total_settled_count:
        coverage_status = "blocked"
    elif missing_ratio >= 0.5:
        coverage_status = "blocked"
    elif no_review_evidence_count > 0:
        coverage_status = "attention"
    else:
        coverage_status = "healthy"

    rows.extend(
        [
            {
                "code": "local_video",
                "label": "本地视频",
                "title": f"本地视频 | {local_video_count}",
                "count": local_video_count,
                "ratio": local_ratio,
                "ratio_text": _ratio_text(local_video_count),
                "coverage_kind": "video_ready",
                "tone": "good" if local_video_count else "neutral",
                "suggestion": "可直接导入所选视频复盘并标注事件。",
                "body": f"数量 {local_video_count} | 占比 {_ratio_text(local_video_count)}\n建议: 可直接导入所选视频复盘并标注事件。",
            },
            {
                "code": "external_reference",
                "label": "外部回放链接",
                "title": f"外部回放链接 | {external_reference_count}",
                "count": external_reference_count,
                "ratio": external_ratio,
                "ratio_text": _ratio_text(external_reference_count),
                "coverage_kind": "video_ready",
                "tone": "good" if external_reference_count else "neutral",
                "suggestion": "FIFA+ Archive 当前主要适合世界杯回放；联赛/杯赛如没有合法本地视频文件，APP 会降级使用 StatsBomb/Event Proxy。",
                "body": (
                    f"数量 {external_reference_count} | 占比 {_ratio_text(external_reference_count)}\n"
                    "建议: FIFA+ Archive 当前主要适合世界杯回放；联赛/杯赛如没有合法本地视频文件，APP 会降级使用 StatsBomb/Event Proxy。"
                ),
            },
            {
                "code": "statsbomb_event_proxy",
                "label": "StatsBomb/Event Proxy",
                "title": f"StatsBomb/Event Proxy | {statsbomb_event_proxy_count}",
                "count": statsbomb_event_proxy_count,
                "ratio": proxy_ratio,
                "ratio_text": _ratio_text(statsbomb_event_proxy_count),
                "coverage_kind": "event_proxy_ready",
                "tone": "warning" if statsbomb_event_proxy_count else "neutral",
                "suggestion": "没有视频但有 StatsBomb 事件摘要时，降级使用事件代理做赛后归因。",
                "body": (
                    f"数量 {statsbomb_event_proxy_count} | 占比 {_ratio_text(statsbomb_event_proxy_count)}\n"
                    "建议: 没有视频但有 StatsBomb 事件摘要时，降级使用事件代理做赛后归因。"
                ),
            },
            {
                "code": "no_review_evidence",
                "label": "缺少复盘证据",
                "title": f"缺少复盘证据 | {no_review_evidence_count}",
                "count": no_review_evidence_count,
                "ratio": missing_ratio if total_settled_count else 1.0,
                "ratio_text": _ratio_text(no_review_evidence_count),
                "coverage_kind": "missing_evidence",
                "tone": "bad" if no_review_evidence_count else "good",
                "suggestion": "补齐合法视频、外链或事件代理；否则只能保留低置信复盘。",
                "body": (
                    f"数量 {no_review_evidence_count} | 占比 {_ratio_text(no_review_evidence_count)}\n"
                    "建议: 补齐合法视频、外链或事件代理；否则只能保留低置信复盘。"
                ),
            },
        ]
    )

    video_memory_sample_count = _safe_int(memory_summary.get("sample_count"), len(memory_items))
    video_memory_note = (
        f"现有视频记忆样本 {video_memory_sample_count} 条，仅用于赛后复盘归因，不进入赛前预测特征。"
        if video_memory_sample_count > 0
        else "视频记忆仅用于赛后复盘归因，不进入赛前预测特征。"
    )
    fallback_policy_text = "\n".join(
        [
            "FIFA+ Archive 当前主要适合世界杯回放。",
            "联赛/杯赛如果没有合法视频文件，APP 会降级使用 StatsBomb/Event Proxy 作为赛后归因来源。",
            "赛后事件证据只用于复盘归因，不进入赛前预测特征。",
            video_memory_note,
        ]
    )

    return {
        "total_settled_count": total_settled_count,
        "local_video_count": local_video_count,
        "external_reference_count": external_reference_count,
        "statsbomb_event_proxy_count": statsbomb_event_proxy_count,
        "no_review_evidence_count": no_review_evidence_count,
        "coverage_status": coverage_status,
        "rows": rows,
        "fallback_policy_text": fallback_policy_text,
    }


def build_video_review_resource_closure_summary(
    video_source_coverage: Mapping[str, object] | object,
    video_memory_health: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    coverage = _as_mapping(video_source_coverage)
    memory = _as_mapping(video_memory_health)
    memory_health = _as_mapping(memory.get("health"))
    memory_status = _text(memory_health.get("status") or memory.get("status"), "blocked")
    coverage_status = _text(coverage.get("coverage_status"), "blocked")

    local_count = _safe_int(coverage.get("local_video_count"))
    external_count = _safe_int(coverage.get("external_reference_count"))
    proxy_count = _safe_int(coverage.get("statsbomb_event_proxy_count"))
    missing_count = _safe_int(coverage.get("no_review_evidence_count"))
    settled_count = _safe_int(coverage.get("total_settled_count"))
    closure_count = local_count + external_count + proxy_count
    closure_rate = closure_count / settled_count if settled_count else 0.0

    statuses = {coverage_status, memory_status}
    if "blocked" in statuses:
        status = "blocked"
    elif "attention" in statuses or missing_count > 0:
        status = "attention"
    else:
        status = "healthy"

    tone = {"healthy": "good", "attention": "warning", "blocked": "bad"}.get(status, "neutral")
    status_label = {"healthy": "资源闭环可用", "attention": "需要补证据", "blocked": "资源闭环受阻"}.get(status, status)
    if missing_count > 0:
        next_step = "补本地视频 / 合法回放后回到缺口中心复核"
        action_key = "open_video_review_evidence_gap_center_window"
    elif proxy_count > 0:
        next_step = "进入 StatsBomb 闭环复核，确认事件代理样本是否已回写"
        action_key = "open_statsbomb_review_training_closure_window"
    else:
        next_step = "维持当前资源闭环"
        action_key = "open_ai_video_review_center_window"

    boundary_text = _text(
        coverage.get("fallback_policy_text"),
        "StatsBomb/Event Proxy 仅用于赛后复盘，不进入赛前预测特征。",
    )
    rows = [
        {
            "label": "闭环状态",
            "value": status,
            "tone": tone,
            "detail": f"coverage={coverage_status} | memory={memory_status}",
        },
        {
            "label": "闭环率",
            "value": f"{closure_rate:.0%}",
            "tone": "good" if status == "healthy" else "warning" if closure_rate > 0 else "bad",
            "detail": f"已闭环 {closure_count} / 已结算 {settled_count}",
        },
        {
            "label": "来源分布",
            "value": f"本地 {local_count} / 外部 {external_count} / 事件代理 {proxy_count}",
            "tone": "good" if closure_count else "neutral",
            "detail": f"缺证据 {missing_count}",
        },
        {
            "label": "使用边界",
            "value": "赛后复盘",
            "tone": "neutral",
            "detail": boundary_text,
        },
    ]
    body = (
        f"来源 {coverage_status} | 记忆 {memory_status} | 已结算 {settled_count}\n"
        f"闭环 {closure_count}/{settled_count} | 本地 {local_count} | 外部 {external_count} | "
        f"事件代理 {proxy_count} | 缺证据 {missing_count}\n"
        f"下一步 {next_step}\n"
        f"{boundary_text}"
    )
    return {
        "status": status,
        "tone": tone,
        "status_label": status_label,
        "summary_text": f"closed {closure_count}/{settled_count} | missing {missing_count} | memory {memory_status}",
        "title": f"视频资源闭环 | {status_label}",
        "body": body,
        "coverage_status": coverage_status,
        "memory_status": memory_status,
        "settled_count": settled_count,
        "local_video_count": local_count,
        "external_reference_count": external_count,
        "statsbomb_event_proxy_count": proxy_count,
        "no_review_evidence_count": missing_count,
        "closure_count": closure_count,
        "closure_rate": round(closure_rate, 4),
        "next_step": next_step,
        "action_key": action_key,
        "boundary_text": boundary_text,
        "card_rows": rows,
        "rows": rows,
    }


def _side_from_margin(value: float, *, threshold: float = 0.0) -> str:
    if value > threshold:
        return "home"
    if value < -threshold:
        return "away"
    return "draw"


def _pct_text_to_float(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text == "-":
        return None
    if text.endswith("%"):
        text = text[:-1]
        try:
            return float(text) / 100.0
        except (TypeError, ValueError):
            return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number


def _statsbomb_baseline_summary(baseline: Mapping[str, object] | object) -> Mapping[str, object]:
    resolved = _as_mapping(baseline)
    return _as_mapping(resolved.get("summary"))


def build_statsbomb_event_review_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    baseline: Mapping[str, object] | object | None = None,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    rows: list[dict[str, object]] = []
    xg_aligned = 0
    shot_aligned = 0
    finishing_variance = 0
    control_gap = 0
    xg_totals: list[float] = []
    event_counts: list[int] = []

    for settlement in settlement_items:
        home_stats, away_stats, home, away = _statsbomb_team_stats(settlement)
        if not home_stats or not away_stats:
            continue
        home_goals = _safe_int(home_stats.get("goals"), _safe_int(settlement.get("home_goals")))
        away_goals = _safe_int(away_stats.get("goals"), _safe_int(settlement.get("away_goals")))
        home_xg = _safe_float(home_stats.get("xg"))
        away_xg = _safe_float(away_stats.get("xg"))
        home_shots = _safe_int(home_stats.get("shots"))
        away_shots = _safe_int(away_stats.get("shots"))
        summary = _as_mapping(settlement.get("statsbomb_event_summary"))
        event_count = _safe_int(summary.get("event_count"))
        score_winner = _side_from_margin(float(home_goals - away_goals))
        xg_winner = _side_from_margin(home_xg - away_xg, threshold=0.25)
        shot_winner = _side_from_margin(float(home_shots - away_shots), threshold=2.0)
        xg_ok = xg_winner == score_winner
        shot_ok = shot_winner == score_winner
        variance = xg_winner != "draw" and xg_winner != score_winner
        gap = abs(home_xg - away_xg) >= 0.35 and abs(home_shots - away_shots) >= 4
        xg_aligned += 1 if xg_ok else 0
        shot_aligned += 1 if shot_ok else 0
        finishing_variance += 1 if variance else 0
        control_gap += 1 if gap else 0
        xg_totals.append(home_xg + away_xg)
        event_counts.append(event_count)
        diagnosis: list[str] = []
        if variance:
            diagnosis.append("\u7ec8\u7ed3\u6ce2\u52a8")
        if gap and not xg_ok:
            diagnosis.append("\u573a\u9762\u4e0e\u8d5b\u679c\u80cc\u79bb")
        if xg_ok and shot_ok:
            diagnosis.append("\u4e8b\u4ef6\u652f\u6301\u8d5b\u679c")
        if not diagnosis:
            diagnosis.append("\u5747\u52bf\u6216\u4f4e\u5dee\u5f02")
        diagnosis_text = "\u3001".join(diagnosis)
        rows.append(
            {
                "title": f"{settlement.get('league') or '-'} | {home or '-'} vs {away or '-'}",
                "body": (
                    f"xG {home or '-'} {home_xg:.2f} - {away_xg:.2f} {away or '-'} | "
                    f"\u5c04\u95e8 {home_shots}-{away_shots} | \u6bd4\u5206 {home_goals}-{away_goals}\n"
                    f"\u5224\u5b9a: {diagnosis_text} | \u4e8b\u4ef6 {event_count}"
                ),
                "xg_aligned": xg_ok,
                "shot_aligned": shot_ok,
                "finishing_variance": variance,
                "control_gap": gap,
                "xg_margin": round(home_xg - away_xg, 4),
                "event_count": event_count,
            }
        )

    sample_count = len(rows)
    baseline_summary = _statsbomb_baseline_summary(baseline or {})
    baseline_match_count = _safe_int(baseline_summary.get("match_count"))
    baseline_xg_alignment = baseline_summary.get("xg_alignment_rate") or "-"
    baseline_variance = baseline_summary.get("finishing_variance_rate") or "-"
    xg_alignment_rate = xg_aligned / sample_count if sample_count else None
    variance_rate = finishing_variance / sample_count if sample_count else None
    baseline_variance_value = _pct_text_to_float(baseline_variance)
    status = "no_event_data"
    if sample_count:
        status = "review_ready"
        if baseline_variance_value is not None and variance_rate is not None and variance_rate > baseline_variance_value + 0.08:
            status = "variance_watch"
        elif control_gap:
            status = "control_gap_watch"
    rows.sort(
        key=lambda row: (
            not bool(row.get("finishing_variance")),
            not bool(row.get("control_gap")),
            -abs(_safe_float(row.get("xg_margin"))),
            str(row.get("title") or ""),
        )
    )
    return {
        "status": status,
        "sample_count": sample_count,
        "xg_aligned": xg_aligned,
        "xg_alignment_rate": xg_alignment_rate,
        "xg_alignment_rate_text": _pct(xg_alignment_rate) if xg_alignment_rate is not None else "-",
        "shot_aligned": shot_aligned,
        "shot_alignment_rate_text": _pct(shot_aligned / sample_count) if sample_count else "-",
        "finishing_variance_count": finishing_variance,
        "finishing_variance_rate": variance_rate,
        "finishing_variance_rate_text": _pct(variance_rate) if variance_rate is not None else "-",
        "control_gap_count": control_gap,
        "avg_xg_total": round(sum(xg_totals) / sample_count, 4) if sample_count else 0.0,
        "avg_event_count": round(sum(event_counts) / sample_count, 2) if sample_count else 0.0,
        "baseline_match_count": baseline_match_count,
        "baseline_xg_alignment_rate": baseline_xg_alignment,
        "baseline_finishing_variance_rate": baseline_variance,
        "leakage_note": "\u8be5\u6a21\u5757\u4ec5\u7528\u4e8e\u8d5b\u540e\u590d\u76d8\uff0c\u4e0d\u53c2\u4e0e\u8d5b\u524d\u9884\u6d4b\u8f93\u5165\u3002",
        "rows": rows[: max(0, int(limit))],
        "summary_text": (
            f"\u6837\u672c {sample_count} | xG\u5bf9\u9f50 {(_pct(xg_alignment_rate) if xg_alignment_rate is not None else '-')} | "
            f"\u7ec8\u7ed3\u6ce2\u52a8 {finishing_variance} | \u57fa\u7ebf {baseline_match_count}\u573a"
        ),
    }


def _statsbomb_memory_items(memory: Mapping[str, object] | object) -> list[Mapping[str, object]]:
    payload = _as_mapping(memory)
    items = _as_list(payload.get("items"))
    return [item for item in items if isinstance(item, Mapping)]


def _statsbomb_memory_query_tags(
    error_attribution: Mapping[str, object] | object,
    event_review: Mapping[str, object] | object,
) -> list[str]:
    attribution = _as_mapping(error_attribution)
    reason_counts = _as_mapping(attribution.get("reason_counts"))
    review = _as_mapping(event_review)
    has_statsbomb_signal = (
        _safe_int(review.get("sample_count")) > 0
        or _safe_int(reason_counts.get("statsbomb_finishing_variance")) > 0
        or _safe_int(reason_counts.get("statsbomb_event_control_gap")) > 0
        or _safe_int(reason_counts.get("statsbomb_xg_against_pick")) > 0
    )
    if not has_statsbomb_signal:
        return []
    tags: list[str] = ["statsbomb_post_match_review"]
    if _safe_int(reason_counts.get("statsbomb_finishing_variance")) or _safe_int(review.get("finishing_variance_count")):
        tags.extend(["statsbomb_finishing_variance", "xg_result_divergence"])
    if _safe_int(reason_counts.get("statsbomb_event_control_gap")) or _safe_int(review.get("control_gap_count")):
        tags.append("event_control_gap")
    if _safe_int(reason_counts.get("statsbomb_xg_against_pick")):
        tags.append("xg_direction_failed")
    if _safe_int(attribution.get("miss_count")):
        tags.append("strategy_miss")
    deduped: list[str] = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def build_statsbomb_fewshot_memory_summary(
    error_attribution: Mapping[str, object] | object,
    event_review: Mapping[str, object] | object,
    memory: Mapping[str, object] | object | None = None,
    *,
    limit: int = 3,
) -> dict[str, object]:
    items = _statsbomb_memory_items(memory or {})
    query_tags = _statsbomb_memory_query_tags(error_attribution, event_review)
    rows: list[dict[str, object]] = []
    for item in items:
        labels = _as_mapping(item.get("labels"))
        tags = [str(tag) for tag in _as_list(labels.get("tags"))]
        matched = [tag for tag in query_tags if tag in tags]
        if not matched:
            continue
        features = _as_mapping(item.get("features"))
        meta = _as_mapping(item.get("meta"))
        score = len(matched) * 10
        if labels.get("is_hit") is False and "strategy_miss" in query_tags:
            score += 4
        if "statsbomb_finishing_variance" in matched:
            score += 3
        if "event_control_gap" in matched:
            score += 2
        rows.append(
            {
                "id": item.get("id") or "-",
                "score": score,
                "matched_tags": matched,
                "title": f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}",
                "body": (
                    f"{labels.get('simulated_pick') or '-'} -> {labels.get('actual') or '-'} | "
                    f"{'命中' if labels.get('is_hit') is True else '未命中'} | "
                    f"{labels.get('root_cause') or '-'} | xG差 {float(_safe_float(features.get('xg_margin'), 0.0) or 0.0):+.2f}"
                ),
                "completion": item.get("completion") or "-",
                "tags": tags,
            }
        )
    rows.sort(key=lambda row: (-_safe_int(row.get("score")), str(row.get("title") or "")))
    limited = rows[: max(0, int(limit))]
    memory_summary = _as_mapping(_as_mapping(memory or {}).get("summary"))
    return {
        "status": "ready" if items else "missing",
        "sample_count": len(items),
        "matched_count": len(rows),
        "query_tags": query_tags,
        "baseline_match_count": _safe_int(memory_summary.get("baseline_match_count")),
        "rows": limited,
        "summary_text": f"记忆库 {len(items)} | 命中 {len(rows)} | 标签 {', '.join(query_tags[:4])}",
        "leakage_note": _as_mapping(memory or {}).get("leakage_note")
        or "These few-shot samples use post-match event data and must not be used as pre-match prediction features.",
    }


def _video_review_fewshot_query_tags(
    error_attribution: Mapping[str, object] | object,
    video_review_memory: Mapping[str, object] | object,
) -> list[str]:
    attribution = _as_mapping(error_attribution)
    reason_counts = _as_mapping(attribution.get("reason_counts"))
    review = _as_mapping(video_review_memory)
    review_tags = [str(tag) for tag in _as_list(review.get("memory_tags")) if str(tag)]
    video_codes = (
        "video_tempo_shift",
        "video_finishing_variance",
        "video_margin_risk",
        "video_low_quality_evidence",
        "video_manual_review_needed",
    )
    has_video_signal = any(_safe_int(reason_counts.get(code)) > 0 for code in video_codes) or bool(review_tags)
    if not has_video_signal:
        return []
    tags: list[str] = ["video_post_match_review"]
    for code in video_codes:
        if _safe_int(reason_counts.get(code)) > 0 or code in review_tags:
            tags.append(code)
    if _safe_int(attribution.get("miss_count")):
        tags.append("strategy_miss")
    deduped: list[str] = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def build_video_review_fewshot_memory_summary(
    error_attribution: Mapping[str, object] | object,
    video_review_memory: Mapping[str, object] | object,
    memory: Mapping[str, object] | object | None = None,
    *,
    limit: int = 3,
) -> dict[str, object]:
    items = _statsbomb_memory_items(memory or {})
    query_tags = _video_review_fewshot_query_tags(error_attribution, video_review_memory)
    rows: list[dict[str, object]] = []
    for item in items:
        labels = _as_mapping(item.get("labels"))
        tags = [str(tag) for tag in _as_list(labels.get("tags")) if str(tag)]
        matched = [tag for tag in query_tags if tag in tags]
        if not matched:
            continue
        features = _as_mapping(item.get("features"))
        meta = _as_mapping(item.get("meta"))
        source = str(meta.get("source") or "-")
        score = len(matched) * 10
        if source == "video_manual_annotation":
            score += 4
        if labels.get("is_hit") is False and "strategy_miss" in query_tags:
            score += 4
        if labels.get("root_cause") in matched:
            score += 3
        rows.append(
            {
                "id": item.get("id") or "-",
                "score": score,
                "matched_tags": matched,
                "title": f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}",
                "body": (
                    f"{labels.get('simulated_pick') or '-'} -> {labels.get('actual') or '-'} | "
                    f"{'hit' if labels.get('is_hit') is True else 'miss'} | "
                    f"{labels.get('root_cause') or '-'} | source {source} | "
                    f"evidence {float(_safe_float(features.get('evidence_score'), 0.0) or 0.0):.2f}"
                ),
                "completion": item.get("completion") or "-",
                "tags": tags,
                "source": source,
            }
        )
    rows.sort(key=lambda row: (-_safe_int(row.get("score")), str(row.get("title") or "")))
    limited = rows[: max(0, int(limit))]
    memory_summary = _as_mapping(_as_mapping(memory or {}).get("summary"))
    return {
        "status": "ready" if items else "missing",
        "sample_count": len(items),
        "matched_count": len(rows),
        "query_tags": query_tags,
        "manual_annotation_sample_count": _safe_int(memory_summary.get("manual_annotation_sample_count")),
        "auto_hypothesis_sample_count": _safe_int(memory_summary.get("auto_hypothesis_sample_count")),
        "rows": limited,
        "summary_text": f"Video memory {len(items)} | matched {len(rows)} | tags {', '.join(query_tags[:4]) or '-'}",
        "leakage_note": _as_mapping(memory or {}).get("leakage_note")
        or "These few-shot samples use post-match video evidence and must not be used as pre-match prediction features.",
    }


def build_statsbomb_fewshot_memory_monitor(
    memory: Mapping[str, object] | object | None = None,
    current_memory_summary: Mapping[str, object] | object | None = None,
    *,
    required_tags: Sequence[str] | None = None,
    limit: int = 8,
) -> dict[str, object]:
    items = _statsbomb_memory_items(memory or {})
    current = _as_mapping(current_memory_summary)
    required = list(
        required_tags
        or (
            "statsbomb_finishing_variance",
            "event_control_gap",
            "xg_result_divergence",
            "shot_result_divergence",
            "xg_direction_failed",
            "strategy_miss",
            "strategy_hit",
        )
    )
    tag_counts: dict[str, int] = {}
    root_counts: dict[str, int] = {}
    miss_count = 0
    hit_count = 0
    for item in items:
        labels = _as_mapping(item.get("labels"))
        if labels.get("is_hit") is False:
            miss_count += 1
        elif labels.get("is_hit") is True:
            hit_count += 1
        root = str(labels.get("root_cause") or "").strip()
        if root:
            root_counts[root] = root_counts.get(root, 0) + 1
        for tag in [str(tag) for tag in _as_list(labels.get("tags"))]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    covered_tags = [tag for tag in required if _safe_int(tag_counts.get(tag)) > 0]
    missing_tags = [tag for tag in required if _safe_int(tag_counts.get(tag)) <= 0]
    coverage_rate = len(covered_tags) / len(required) if required else None
    tag_rows = [
        {
            "title": f"{tag} | {_safe_int(count)}",
            "body": f"标签 {tag} 覆盖 {_safe_int(count)} 个历史复盘样本。",
            "tag": tag,
            "count": _safe_int(count),
        }
        for tag, count in sorted(tag_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    ]
    root_rows = [
        {
            "title": f"{root} | {_safe_int(count)}",
            "body": f"根因 {root} 覆盖 {_safe_int(count)} 个历史复盘样本。",
            "root_cause": root,
            "count": _safe_int(count),
        }
        for root, count in sorted(root_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    ]
    matched_count = _safe_int(current.get("matched_count"))
    query_tags = [str(tag) for tag in _as_list(current.get("query_tags"))]
    status = "missing"
    if items:
        status = "active_match" if matched_count else "ready"
        if not query_tags:
            status = "standby"
    return {
        "status": status,
        "sample_count": len(items),
        "hit_count": hit_count,
        "miss_count": miss_count,
        "tag_count": len(tag_counts),
        "root_cause_count": len(root_counts),
        "covered_tags": covered_tags,
        "missing_tags": missing_tags,
        "coverage_rate": coverage_rate,
        "coverage_rate_text": _pct(coverage_rate) if coverage_rate is not None else "-",
        "current_matched_count": matched_count,
        "current_query_tags": query_tags,
        "tag_rows": tag_rows[: max(0, int(limit))],
        "root_rows": root_rows[: max(0, int(limit))],
        "summary_text": (
            f"样本 {len(items)} | 标签覆盖 {(_pct(coverage_rate) if coverage_rate is not None else '-')} | "
            f"当前命中 {matched_count} | 缺口 {len(missing_tags)}"
        ),
        "leakage_note": _as_mapping(memory or {}).get("leakage_note")
        or "These few-shot samples use post-match event data and must not be used as pre-match prediction features.",
    }


def build_statsbomb_fewshot_memory_quality_alerts(
    monitor: Mapping[str, object] | object | None = None,
    *,
    min_samples: int = 20,
    concentration_threshold: float = 0.65,
) -> dict[str, object]:
    data = _as_mapping(monitor)
    sample_count = _safe_int(data.get("sample_count"))
    current_matched_count = _safe_int(data.get("current_matched_count"))
    current_query_tags = [str(tag) for tag in _as_list(data.get("current_query_tags"))]
    missing_tags = [str(tag) for tag in _as_list(data.get("missing_tags"))]
    tag_rows = [_as_mapping(row) for row in _as_list(data.get("tag_rows"))]
    root_rows = [_as_mapping(row) for row in _as_list(data.get("root_rows"))]
    alerts: list[dict[str, str]] = []
    memory_tags: list[str] = []
    score_delta = 0

    if sample_count <= 0:
        alerts.append(
            {
                "title": "建立StatsBomb复盘记忆库",
                "body": "当前没有可用的赛后事件 few-shot 样本，Evaluation Agent 只能依赖规则归因，建议先沉淀已结束比赛的复盘样本。",
                "tag": "statsbomb_memory_missing",
            }
        )
        memory_tags.append("statsbomb_memory_missing")
        score_delta -= 4
    elif sample_count < max(1, int(min_samples)):
        alerts.append(
            {
                "title": "补充StatsBomb复盘样本",
                "body": f"当前 few-shot 记忆样本 {sample_count} 条，低于 {max(1, int(min_samples))} 条观察线，建议优先补充高置信失误和冷门场次。",
                "tag": "statsbomb_memory_low_sample",
            }
        )
        memory_tags.append("statsbomb_memory_low_sample")
        score_delta -= 3

    if sample_count > 0 and missing_tags:
        alerts.append(
            {
                "title": "补齐复盘标签缺口",
                "body": f"缺少 {', '.join(missing_tags[:5])} 等标签样本，后续复盘需要覆盖这些根因，避免 few-shot 记忆偏科。",
                "tag": "statsbomb_memory_tag_gap",
            }
        )
        memory_tags.append("statsbomb_memory_tag_gap")
        score_delta -= 2

    if sample_count > 0 and current_query_tags and current_matched_count <= 0:
        alerts.append(
            {
                "title": "补充当前错因相似样本",
                "body": f"当前复盘查询标签为 {', '.join(current_query_tags[:5])}，但历史记忆没有命中相似案例，建议赛后优先导出这一类 few-shot 样本。",
                "tag": "statsbomb_memory_no_current_match",
            }
        )
        memory_tags.append("statsbomb_memory_no_current_match")
        score_delta -= 3

    root_total = sum(_safe_int(row.get("count")) for row in root_rows)
    if sample_count >= 5 and root_total > 0 and root_rows:
        top_root = root_rows[0]
        top_root_count = _safe_int(top_root.get("count"))
        root_share = top_root_count / root_total if root_total else 0.0
        if root_share >= max(0.0, min(1.0, float(concentration_threshold))):
            alerts.append(
                {
                    "title": "降低复盘根因集中度",
                    "body": f"根因 {top_root.get('root_cause') or '-'} 占 few-shot 记忆 {root_share:.1%}，建议补充其他错因类型，避免 Evaluation Agent 过度套用单一解释。",
                    "tag": "statsbomb_memory_concentrated",
                }
            )
            memory_tags.append("statsbomb_memory_concentrated")
            score_delta -= 2

    diagnostic_tag_rows = [
        row
        for row in tag_rows
        if str(row.get("tag") or "") not in {"statsbomb_post_match_review", "strategy_miss", "strategy_hit"}
    ]
    tag_total = sum(_safe_int(row.get("count")) for row in diagnostic_tag_rows)
    if sample_count >= 5 and tag_total > 0 and diagnostic_tag_rows:
        top_tag = diagnostic_tag_rows[0]
        top_tag_count = _safe_int(top_tag.get("count"))
        tag_share = top_tag_count / tag_total if tag_total else 0.0
        if tag_share >= max(0.0, min(1.0, float(concentration_threshold))):
            alerts.append(
                {
                    "title": "降低复盘标签集中度",
                    "body": f"诊断标签 {top_tag.get('tag') or '-'} 占 few-shot 记忆 {tag_share:.1%}，建议补充场面劣势、xG 背离、命中案例等不同标签。",
                    "tag": "statsbomb_memory_tag_concentrated",
                }
            )
            memory_tags.append("statsbomb_memory_tag_concentrated")
            score_delta -= 2

    status = "watch" if alerts else "healthy"
    return {
        "status": status,
        "alert_count": len(alerts),
        "alerts": alerts[:5],
        "memory_tags": memory_tags,
        "score_delta": score_delta,
        "summary_text": f"记忆告警 {len(alerts)} | 样本 {sample_count} | 当前命中 {current_matched_count}",
    }


def _statsbomb_required_backfill_tags(monitor: Mapping[str, object]) -> list[str]:
    tags: list[str] = []
    for source in (monitor.get("current_query_tags"), monitor.get("missing_tags")):
        for tag in _as_list(source):
            tag_text = str(tag).strip()
            if tag_text and tag_text not in tags:
                tags.append(tag_text)
    if not tags:
        tags.extend(
            [
                "strategy_miss",
                "strategy_hit",
                "statsbomb_finishing_variance",
                "event_control_gap",
                "xg_direction_failed",
            ]
        )
    return tags


def _statsbomb_backfill_task_title(tag: str) -> str:
    labels = {
        "strategy_miss": "补充未命中复盘样本",
        "strategy_hit": "补充命中对照样本",
        "statsbomb_finishing_variance": "补充终结波动样本",
        "event_control_gap": "补充场面劣势样本",
        "xg_result_divergence": "补充xG与赛果背离样本",
        "shot_result_divergence": "补充射门与赛果背离样本",
        "xg_direction_failed": "补充xG方向失效样本",
    }
    return labels.get(tag, f"补充 {tag} 样本")


def _statsbomb_baseline_backfill_tags(row: Mapping[str, object]) -> list[str]:
    precomputed = [str(tag) for tag in _as_list(row.get("backfill_tags")) if str(tag)]
    if precomputed:
        deduped_precomputed: list[str] = []
        for tag in precomputed:
            if tag not in deduped_precomputed:
                deduped_precomputed.append(tag)
        return deduped_precomputed
    tags = ["statsbomb_post_match_review"]
    if bool(row.get("finishing_variance")):
        tags.extend(["statsbomb_finishing_variance", "xg_result_divergence"])
    if "xg_aligned_with_score" in row and not bool(row.get("xg_aligned_with_score")):
        tags.extend(["xg_result_divergence", "xg_direction_failed"])
    if "shot_aligned_with_score" in row and not bool(row.get("shot_aligned_with_score")):
        tags.append("shot_result_divergence")
    home_shots = _safe_int(row.get("home_shots"))
    away_shots = _safe_int(row.get("away_shots"))
    goal_margin = _safe_float(row.get("goal_margin"))
    shot_margin = home_shots - away_shots
    if (goal_margin > 0 and shot_margin < -3) or (goal_margin < 0 and shot_margin > 3):
        tags.append("event_control_gap")
    if "xg_aligned_with_score" in row and bool(row.get("xg_aligned_with_score")):
        tags.append("strategy_hit")
    else:
        tags.append("strategy_miss")
    deduped: list[str] = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def _statsbomb_baseline_backfill_items(
    baseline: Mapping[str, object] | object,
    target_tags: set[str],
) -> list[Mapping[str, object]]:
    resolved = _as_mapping(baseline)
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    tag_index = _as_mapping(resolved.get("backfill_tag_index"))
    if not tag_index or not target_tags:
        return items
    selected: list[Mapping[str, object]] = []
    seen_indexes: set[int] = set()
    for tag in sorted(target_tags):
        for value in _as_list(tag_index.get(tag)):
            index = _safe_int(value, -1)
            if index < 0 or index >= len(items) or index in seen_indexes:
                continue
            seen_indexes.add(index)
            selected.append(items[index])
    return selected


def _statsbomb_settlement_backfill_row(
    settlement: Mapping[str, object],
    tags: Sequence[str],
    *,
    source: str,
    priority_base: int = 0,
) -> dict[str, object]:
    home_stats, away_stats, home_team, away_team = _statsbomb_team_stats(settlement)
    home_team = home_team or str(settlement.get("home_team") or "-")
    away_team = away_team or str(settlement.get("away_team") or "-")
    title = f"{settlement.get('match_date') or '-'} | {settlement.get('league') or '-'} | {home_team} vs {away_team}"
    tag_list = [str(tag) for tag in tags if str(tag)]
    row: dict[str, object] = {
        "source": source,
        "match_id": settlement.get("match_id") or "-",
        "match_date": settlement.get("match_date") or "-",
        "league": settlement.get("league") or "-",
        "home_team": home_team,
        "away_team": away_team,
        "title": title,
        "tags": tag_list,
        "priority_score": priority_base,
        "body": f"{title}\n标签: {', '.join(tag_list[:6]) if tag_list else '-'}",
    }
    if home_stats and away_stats:
        summary = _as_mapping(settlement.get("statsbomb_event_summary"))
        home_goals = _safe_int(home_stats.get("goals"), _safe_int(settlement.get("home_goals")))
        away_goals = _safe_int(away_stats.get("goals"), _safe_int(settlement.get("away_goals")))
        home_xg = _safe_float(home_stats.get("xg"))
        away_xg = _safe_float(away_stats.get("xg"))
        home_shots = _safe_int(home_stats.get("shots"))
        away_shots = _safe_int(away_stats.get("shots"))
        goal_margin = home_goals - away_goals
        xg_margin = home_xg - away_xg
        shot_margin = home_shots - away_shots
        score_winner = _side_from_margin(float(goal_margin))
        xg_winner = _side_from_margin(xg_margin, threshold=0.25)
        shot_winner = _side_from_margin(float(shot_margin), threshold=2.0)
        row.update(
            {
                "score": f"{home_goals}-{away_goals}",
                "home_xg": home_xg,
                "away_xg": away_xg,
                "home_shots": home_shots,
                "away_shots": away_shots,
                "goal_margin": goal_margin,
                "xg_margin": round(xg_margin, 4),
                "shot_margin": shot_margin,
                "event_count": _safe_int(summary.get("event_count")),
                "score_winner": score_winner,
                "xg_winner": xg_winner,
                "xg_aligned_with_score": xg_winner == score_winner,
                "shot_aligned_with_score": shot_winner == score_winner,
                "finishing_variance": xg_winner != "draw" and xg_winner != score_winner,
            }
        )
    return row


def build_statsbomb_fewshot_backfill_queue(
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    settlements: Sequence[Mapping[str, object]] | object | None = None,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    *,
    limit: int = 8,
    include_candidates: bool = True,
) -> dict[str, object]:
    monitor_data = _as_mapping(monitor)
    quality_data = _as_mapping(quality)
    alert_rows = [_as_mapping(alert) for alert in _as_list(quality_data.get("alerts"))]
    health = build_statsbomb_fewshot_memory_health_summary(monitor_data, quality_data)
    health_issues = [_as_mapping(issue) for issue in _as_list(health.get("issues"))]
    required_tags = _statsbomb_required_backfill_tags(monitor_data)
    sample_count = _safe_int(monitor_data.get("sample_count"))
    missing_tags = [str(tag) for tag in _as_list(monitor_data.get("missing_tags"))]
    current_query_tags = [str(tag) for tag in _as_list(monitor_data.get("current_query_tags"))]
    missing_tag_set = set(missing_tags)
    current_query_tag_set = set(current_query_tags)
    tasks: list[dict[str, object]] = []

    if sample_count <= 0 or any(str(alert.get("tag") or "") == "statsbomb_memory_missing" for alert in alert_rows):
        tasks.append(
            {
                "task": "seed_memory",
                "priority": 100,
                "title": "建立StatsBomb few-shot种子库",
                "target_tags": required_tags,
                "body": "优先从已结束且带 StatsBomb 事件数据的比赛生成基础 few-shot 样本，命中和未命中样本都要覆盖。",
            }
        )
    if any(str(alert.get("tag") or "") == "statsbomb_memory_low_sample" for alert in alert_rows):
        tasks.append(
            {
                "task": "increase_sample_size",
                "priority": 90,
                "title": "扩大StatsBomb few-shot样本数",
                "target_tags": required_tags,
                "body": f"当前样本 {sample_count} 条，优先补充高置信失误、冷门和命中对照样本。",
            }
        )
    if missing_tags:
        for tag in missing_tags[:6]:
            tasks.append(
                {
                    "task": "cover_missing_tag",
                    "priority": 85,
                    "title": _statsbomb_backfill_task_title(tag),
                    "target_tags": [tag],
                    "body": f"记忆库缺少 {tag}，需要从赛后事件复盘中补齐这一类 few-shot 样本。",
                }
            )
    if current_query_tags and _safe_int(monitor_data.get("current_matched_count")) <= 0:
        tasks.append(
            {
                "task": "cover_current_context",
                "priority": 95,
                "title": "补充当前错因相似样本",
                "target_tags": current_query_tags,
                "body": f"当前查询标签 {', '.join(current_query_tags[:6])} 没有命中历史记忆，需要优先补充同类赛后案例。",
            }
        )
    if any(str(alert.get("tag") or "") in {"statsbomb_memory_concentrated", "statsbomb_memory_tag_concentrated"} for alert in alert_rows):
        tasks.append(
            {
                "task": "diversify_memory",
                "priority": 70,
                "title": "分散复盘记忆分布",
                "target_tags": required_tags,
                "body": "当前 few-shot 记忆集中在少数根因或标签，建议补充不同联赛、不同比分结构、不同事件形态的样本。",
            }
        )

    target_tag_set = {tag for task in tasks for tag in _as_list(task.get("target_tags"))}
    if not target_tag_set:
        target_tag_set = set(required_tags)
    scored_rows: list[dict[str, object]] = []
    scored_count = 0
    if include_candidates:
        row_limit = max(0, int(limit))

        def score_candidate(row: Mapping[str, object]) -> None:
            nonlocal scored_count
            row_tags = {str(tag) for tag in _as_list(row.get("tags"))}
            overlap = sorted(row_tags & target_tag_set)
            if tasks and not overlap:
                return
            matched_health_issues: list[str] = []
            if overlap and missing_tags and set(overlap) & set(missing_tags):
                matched_health_issues.append("required_tag_gap")
            if sample_count < 20 and overlap:
                matched_health_issues.append("sample_count_low")
            if _safe_int(quality_data.get("alert_count")) and overlap:
                matched_health_issues.append("quality_alerts_present")
            for issue in health_issues:
                issue_code = str(issue.get("code") or "")
                if issue_code in {"memory_missing", "sample_count_low", "required_tag_gap", "quality_alerts_present"} and issue_code not in matched_health_issues:
                    if issue_code == "memory_missing" or overlap:
                        matched_health_issues.append(issue_code)
            repair_score = _safe_int(row.get("priority_score"))
            repair_reasons: list[str] = []
            priority_why: list[str] = []
            missing_hits = sorted(set(overlap) & missing_tag_set)
            current_hits = sorted(set(overlap) & current_query_tag_set)
            if missing_hits:
                value = 35 * len(missing_hits)
                repair_score += value
                repair_reasons.append(f"missing_tags +{value}: {', '.join(missing_hits[:4])}")
                priority_why.append(f"覆盖缺口标签: {', '.join(missing_hits[:4])}")
            if current_hits:
                value = 25 * len(current_hits)
                repair_score += value
                repair_reasons.append(f"current_query +{value}: {', '.join(current_hits[:4])}")
                priority_why.append(f"命中当前比赛错因上下文: {', '.join(current_hits[:4])}")
            for issue in matched_health_issues:
                if issue == "memory_missing":
                    repair_score += 40
                    repair_reasons.append("memory_missing +40")
                    priority_why.append("few-shot 记忆为空，优先补种子样本")
                elif issue == "required_tag_gap":
                    repair_score += 25
                    repair_reasons.append("required_tag_gap +25")
                    priority_why.append("当前必需标签缺口，需优先补齐")
                elif issue == "sample_count_low":
                    repair_score += 12
                    repair_reasons.append("sample_count_low +12")
                    priority_why.append("样本总量不足，需扩大样本池")
                elif issue == "quality_alerts_present":
                    repair_score += 10
                    repair_reasons.append("quality_alerts_present +10")
                    priority_why.append("存在质量告警，优先补高价值样本")
            if str(row.get("source") or "") == "recent_settlement":
                repair_score += 15
                repair_reasons.append("recent_settlement +15")
                priority_why.append("近期实盘样本，复盘价值更高")
            if not repair_reasons and overlap:
                value = 8 * len(overlap)
                repair_score += value
                repair_reasons.append(f"target_overlap +{value}")
                priority_why.append("覆盖目标标签")
            scored_count += 1
            if row_limit <= 0:
                return
            scored = dict(row)
            scored["matched_tags"] = overlap
            scored["matched_health_issues"] = matched_health_issues
            scored["repair_score"] = repair_score
            scored["repair_reasons"] = repair_reasons
            scored["priority_why"] = priority_why[:6]
            scored["missing_labels_hit"] = missing_hits
            scored["current_context_hit"] = current_hits
            scored["flow_status"] = {
                "draft": "pending",
                "merge": "pending",
                "apply": "pending",
                "summary": "backfill_queued_only",
            }
            scored["priority_score"] = repair_score
            scored["body"] = (
                f"{row.get('body', '-')}\n"
                f"命中补样目标: {', '.join(overlap[:6]) if overlap else '-'}\n"
                f"健康问题: {', '.join(matched_health_issues[:4]) if matched_health_issues else '-'}\n"
                f"修复评分: {repair_score} | {', '.join(repair_reasons[:4]) if repair_reasons else '-'}"
            )
            scored_rows.append(scored)
            scored_rows.sort(
                key=lambda row: (
                    -_safe_int(row.get("repair_score", row.get("priority_score"))),
                    str(row.get("match_date") or ""),
                    str(row.get("title") or ""),
                )
            )
            del scored_rows[row_limit:]

        for item in settlements if isinstance(settlements, Sequence) else []:
            if not isinstance(item, Mapping) or not _as_mapping(item.get("statsbomb_event_summary")):
                continue
            attribution = build_strategy_error_attribution_summary([item])
            event_review = build_statsbomb_event_review_summary([item], statsbomb_event_baseline or {})
            tags = _statsbomb_memory_query_tags(attribution, event_review)
            if tags:
                score_candidate(_statsbomb_settlement_backfill_row(item, tags, source="recent_settlement", priority_base=20))

        baseline_items = _statsbomb_baseline_backfill_items(statsbomb_event_baseline or {}, target_tag_set)
        for item in baseline_items:
            tags = _statsbomb_baseline_backfill_tags(item)
            settlement = {
                "match_id": item.get("match_id"),
                "match_date": item.get("match_date"),
                "league": item.get("league"),
                "home_team": item.get("home_team"),
                "away_team": item.get("away_team"),
            }
            score_candidate(_statsbomb_settlement_backfill_row(settlement, tags, source="statsbomb_baseline", priority_base=5))
    tasks.sort(key=lambda row: (-_safe_int(row.get("priority")), str(row.get("title") or "")))
    status = "ready" if tasks else "healthy"
    return {
        "status": status,
        "task_count": len(tasks),
        "candidate_count": scored_count,
        "health_status": health.get("status") or "-",
        "health_summary": health.get("summary_text") or "-",
        "health_issues": [dict(issue) for issue in health_issues],
        "health_issue_codes": [str(issue.get("code") or "-") for issue in health_issues],
        "target_tags": sorted(str(tag) for tag in target_tag_set),
        "missing_labels": missing_tags,
        "current_query_labels": current_query_tags,
        "current_match_unmatched": _safe_int(monitor_data.get("current_matched_count")) <= 0,
        "workflow_status": {
            "draft": "pending",
            "merge": "pending",
            "apply": "pending",
            "summary": "backfill_queue_only",
        },
        "candidate_generation": "full" if include_candidates else "deferred",
        "tasks": tasks[: max(0, int(limit))],
        "candidate_rows": scored_rows[: max(0, int(limit))],
        "summary_text": f"补样任务 {len(tasks)} | 候选 {scored_count} | 目标标签 {len(target_tag_set)}",
        "leakage_note": "Backfill queue uses post-match StatsBomb event evidence for review memory only; never feed it into pre-match prediction features.",
    }


def build_statsbomb_fewshot_backfill_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_backfill_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_backfill_report_lines(
    queue: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
) -> list[str]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(queue)
    tasks = [row for row in _as_list(resolved.get("tasks")) if isinstance(row, Mapping)]
    candidates = [row for row in _as_list(resolved.get("candidate_rows")) if isinstance(row, Mapping)]
    health_issues = [row for row in _as_list(resolved.get("health_issues")) if isinstance(row, Mapping)]
    workflow = _as_mapping(resolved.get("workflow_status"))
    lines = [
        "# StatsBomb Few-shot 补样队列",
        "",
        f"- 生成时间: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 摘要: {resolved.get('summary_text') or '-'}",
        f"- 状态: {resolved.get('status') or '-'}",
        f"- 缺口标签: {', '.join(str(tag) for tag in _as_list(resolved.get('missing_labels'))[:12]) or '-'}",
        f"- 当前比赛标签: {', '.join(str(tag) for tag in _as_list(resolved.get('current_query_labels'))[:12]) or '-'}",
        f"- 当前比赛是否命中历史样本: {'否' if bool(resolved.get('current_match_unmatched')) else '是'}",
        f"- 流程状态: draft={workflow.get('draft') or '-'} | merge={workflow.get('merge') or '-'} | apply={workflow.get('apply') or '-'}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        "",
        "## 补样任务",
        "",
        "| 优先级 | 任务 | 目标标签 | 说明 |",
        "| ---: | --- | --- | --- |",
    ]
    lines.extend(["", "## 缺口与健康驱动", "", "| Issue | Severity | Recommendation |", "| --- | --- | --- |"])
    if not health_issues:
        lines.append("| - | - | - |")
    for issue in health_issues:
        lines.append(
            "| "
            + " | ".join([_md_cell(issue.get("code")), _md_cell(issue.get("severity")), _md_cell(issue.get("recommendation"))])
            + " |"
        )
    lines.extend(["", "## 补样任务", "", "| Priority | Task | Target tags | Description |", "| ---: | --- | --- | --- |"])
    if not tasks:
        lines.append("| 0 | 暂无补样任务 | - | 当前 StatsBomb few-shot 记忆覆盖健康。 |")
    for task in tasks:
        target_tags = ", ".join(str(tag) for tag in _as_list(task.get("target_tags"))) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(_safe_int(task.get("priority"))),
                    _md_cell(task.get("title")),
                    _md_cell(target_tags),
                    _md_cell(task.get("body")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 候选比赛",
            "",
            "| 修复评分 | 来源 | 日期 | 赛事 | 比赛 | 命中目标 | 健康驱动 | 优先原因 | 流程状态 | 标签 |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if not candidates:
        lines.append("| 0 | - | - | - | 暂无候选 | - | - | - | - |")
    for row in candidates:
        matched_tags = ", ".join(str(tag) for tag in _as_list(row.get("matched_tags"))) or "-"
        health_issues = ", ".join(str(issue) for issue in _as_list(row.get("matched_health_issues"))) or "-"
        repair_reasons = ", ".join(str(reason) for reason in _as_list(row.get("priority_why"))) or ", ".join(str(reason) for reason in _as_list(row.get("repair_reasons"))) or "-"
        flow_status = _as_mapping(row.get("flow_status"))
        flow_text = f"draft={flow_status.get('draft') or '-'} | merge={flow_status.get('merge') or '-'} | apply={flow_status.get('apply') or '-'}"
        tags = ", ".join(str(tag) for tag in _as_list(row.get("tags"))) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(_safe_int(row.get("repair_score", row.get("priority_score")))),
                    _md_cell(row.get("source")),
                    _md_cell(row.get("match_date")),
                    _md_cell(row.get("league")),
                    _md_cell(row.get("title")),
                    _md_cell(matched_tags),
                    _md_cell(health_issues),
                    _md_cell(repair_reasons),
                    _md_cell(flow_text),
                    _md_cell(tags),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 复盘执行原则",
            "",
            "- 只从已经完场且具备 StatsBomb 事件证据的比赛生成 few-shot 样本。",
            "- 样本用于 Evaluation Agent 赛后归因和报告增强，不得作为赛前预测特征。",
            "- 每次补样后重新检查标签覆盖率、当前错因命中数和根因集中度。",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_draft_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_draft_{current.strftime('%Y%m%d_%H%M%S')}.json"


def build_statsbomb_fewshot_draft_review_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_draft_review_{current.strftime('%Y%m%d_%H%M%S')}.md"


def _statsbomb_baseline_row_key(row: Mapping[str, object]) -> list[str]:
    keys: list[str] = []
    for value in (row.get("match_id"), row.get("source_match_id")):
        text = str(value or "").strip()
        if text and text not in keys:
            keys.append(text)
    title = f"{row.get('match_date') or '-'} | {row.get('league') or '-'} | {row.get('home_team') or '-'} vs {row.get('away_team') or '-'}"
    if title not in keys:
        keys.append(title)
    return keys


def _statsbomb_backfill_candidate_has_draft_fields(candidate: Mapping[str, object]) -> bool:
    required_fields = ("home_team", "away_team", "home_xg", "away_xg", "home_shots", "away_shots", "score")
    return all(candidate.get(field) not in {None, ""} for field in required_fields)


def _statsbomb_fewshot_draft_from_baseline_row(
    row: Mapping[str, object],
    candidate: Mapping[str, object],
) -> dict[str, object]:
    score_winner = str(row.get("score_winner") or "").strip().lower()
    if score_winner not in {"home", "away", "draw"}:
        score_winner = _side_from_margin(_safe_float(row.get("goal_margin")))
    xg_winner = str(row.get("xg_winner") or "").strip().lower()
    if xg_winner not in {"home", "away", "draw"}:
        xg_winner = _side_from_margin(_safe_float(row.get("xg_margin")), threshold=0.25)
    simulated_pick = xg_winner if xg_winner in {"home", "away", "draw"} else score_winner
    actual = score_winner if score_winner in {"home", "away", "draw"} else "draw"
    is_hit = simulated_pick == actual
    tags = _statsbomb_baseline_backfill_tags(row)
    root_cause = "event_evidence_aligned" if is_hit else "statsbomb_finishing_variance" if bool(row.get("finishing_variance")) else "event_result_divergence"
    home_xg = _safe_float(row.get("home_xg"))
    away_xg = _safe_float(row.get("away_xg"))
    home_shots = _safe_int(row.get("home_shots"))
    away_shots = _safe_int(row.get("away_shots"))
    shot_margin = _safe_float(row.get("shot_margin"), float(home_shots - away_shots))
    match_title = f"{row.get('home_team') or '-'} vs {row.get('away_team') or '-'}"
    matched_health_issues = [str(issue) for issue in _as_list(candidate.get("matched_health_issues"))]
    repair_score = _safe_int(candidate.get("repair_score", candidate.get("priority_score")))
    repair_reasons = [str(reason) for reason in _as_list(candidate.get("repair_reasons")) if str(reason)]
    prompt = (
        "请作为 Evaluation Agent 复盘一场使用 StatsBomb 赛后事件的历史案例。\n"
        f"比赛: {row.get('match_date') or '-'} | {row.get('league') or '-'} | {match_title}\n"
        f"比分: {row.get('score') or '-'} | 模拟策略: 按 xG 方向选择 {_statsbomb_side_to_pick(simulated_pick)} | 实际: {_statsbomb_side_to_pick(actual)}\n"
        f"xG: {home_xg:.2f}-{away_xg:.2f} | 射门: {home_shots}-{away_shots} | 草稿目标标签: {', '.join(_as_list(candidate.get('matched_tags'))[:6]) or '-'}"
    )
    if matched_health_issues:
        prompt += f"\n健康驱动: {', '.join(matched_health_issues[:6])}"
    if repair_score > 0 or repair_reasons:
        prompt += f"\n补样优先级: 修复评分 {repair_score} | 排序原因: {', '.join(repair_reasons[:6]) if repair_reasons else '-'}"
    if is_hit:
        completion = "结论: 模拟策略命中。StatsBomb 事件方向与赛果一致，可作为 Evaluation Agent 的正向对照复盘样本。"
    else:
        completion = (
            "结论: 模拟策略未命中。StatsBomb 事件显示 xG 或射门质量支持模拟方向但赛果相反，"
            "应优先归因为终结波动、事件与结果背离或 xG 方向失效，不应回灌为赛前预测特征。"
        )
    return {
        "id": f"statsbomb_backfill_draft:{row.get('source_match_id') or row.get('match_id') or candidate.get('match_id') or '-'}",
        "review_status": "draft",
        "draft_note": "Generated from StatsBomb backfill queue. Review manually before merging into official few-shot memory.",
        "prompt": prompt,
        "completion": completion,
        "labels": {
            "simulated_pick": _statsbomb_side_to_pick(simulated_pick),
            "actual": _statsbomb_side_to_pick(actual),
            "is_hit": bool(is_hit),
            "root_cause": root_cause,
            "tags": tags,
        },
        "features": {
            "home_xg": home_xg,
            "away_xg": away_xg,
            "xg_margin": _safe_float(row.get("xg_margin")),
            "home_shots": float(home_shots),
            "away_shots": float(away_shots),
            "shot_margin": shot_margin,
            "event_count": float(_safe_float(row.get("event_count"))),
        },
        "meta": {
            "source": "statsbomb_fewshot_backfill_draft",
            "candidate_source": candidate.get("source") or "-",
            "match_id": row.get("match_id"),
            "source_match_id": row.get("source_match_id"),
            "match_date": row.get("match_date"),
            "league": row.get("league"),
            "season": row.get("season"),
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "score": row.get("score"),
            "matched_backfill_tags": [str(tag) for tag in _as_list(candidate.get("matched_tags"))],
            "matched_health_issues": matched_health_issues,
            "repair_score": repair_score,
            "repair_reasons": repair_reasons,
        },
    }


def build_statsbomb_fewshot_draft_payload(
    queue: Mapping[str, object] | object,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
    limit: int = 20,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved_queue = _as_mapping(queue)
    baseline_items = [item for item in _as_list(_as_mapping(statsbomb_event_baseline).get("items")) if isinstance(item, Mapping)]
    baseline_index: dict[str, Mapping[str, object]] = {}
    for row in baseline_items:
        for key in _statsbomb_baseline_row_key(row):
            baseline_index[key] = row
    items: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    candidates = [row for row in _as_list(resolved_queue.get("candidate_rows")) if isinstance(row, Mapping)]
    for candidate in candidates:
        lookup_keys = [str(candidate.get("match_id") or "").strip(), str(candidate.get("title") or "").strip()]
        baseline_row = next((baseline_index[key] for key in lookup_keys if key and key in baseline_index), None)
        if not baseline_row:
            if _statsbomb_backfill_candidate_has_draft_fields(candidate):
                baseline_row = candidate
            else:
                skipped.append(
                    {
                        "match_id": candidate.get("match_id") or "-",
                        "title": candidate.get("title") or "-",
                        "reason": "missing_baseline_row",
                        "repair_score": _safe_int(candidate.get("repair_score", candidate.get("priority_score"))),
                        "repair_reasons": [str(reason) for reason in _as_list(candidate.get("repair_reasons")) if str(reason)],
                    }
                )
                continue
        draft = _statsbomb_fewshot_draft_from_baseline_row(baseline_row, candidate)
        draft_id = str(draft.get("id") or "")
        if draft_id in seen_ids:
            continue
        seen_ids.add(draft_id)
        items.append(draft)
        if len(items) >= max(0, int(limit)):
            break
    tag_counts: dict[str, int] = {}
    health_issue_counts: dict[str, int] = {}
    repair_reason_counts: dict[str, int] = {}
    top_repair_score = 0
    for item in items:
        labels = _as_mapping(item.get("labels"))
        for tag in _as_list(labels.get("tags")):
            tag_text = str(tag)
            tag_counts[tag_text] = tag_counts.get(tag_text, 0) + 1
        meta = _as_mapping(item.get("meta"))
        top_repair_score = max(top_repair_score, _safe_int(meta.get("repair_score")))
        for issue in _as_list(meta.get("matched_health_issues")):
            issue_text = str(issue)
            if issue_text:
                health_issue_counts[issue_text] = health_issue_counts.get(issue_text, 0) + 1
        for reason in _as_list(meta.get("repair_reasons")):
            reason_text = str(reason)
            if reason_text:
                repair_reason_counts[reason_text] = repair_reason_counts.get(reason_text, 0) + 1
    leakage_note = "Draft samples use post-match StatsBomb event data for Evaluation Agent review only; do not use as pre-match prediction features."
    payload = {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot backfill queue",
        "purpose": "draft_only_manual_review_required",
        "review_status": "draft",
        "leakage_note": leakage_note,
        "summary": {
            "draft_count": len(items),
            "candidate_count": len(candidates),
            "skipped_count": len(skipped),
            "tag_counts": dict(sorted(tag_counts.items())),
            "health_issue_counts": dict(sorted(health_issue_counts.items())),
            "repair_reason_counts": dict(sorted(repair_reason_counts.items())),
            "top_repair_score": top_repair_score,
        },
        "backfill_summary": resolved_queue.get("summary_text") or "-",
        "backfill_health_summary": resolved_queue.get("health_summary") or "-",
        "items": items,
        "skipped": skipped,
    }
    payload["validation"] = validate_statsbomb_fewshot_draft_payload(payload)
    return payload


def validate_statsbomb_fewshot_draft_payload(payload: Mapping[str, object] | object) -> dict[str, object]:
    resolved = _as_mapping(payload)
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    issues: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    required_top_fields = ("id", "prompt", "completion", "labels", "features", "meta", "review_status")
    required_labels = ("simulated_pick", "actual", "is_hit", "root_cause", "tags")
    required_features = ("home_xg", "away_xg", "xg_margin", "home_shots", "away_shots", "shot_margin", "event_count")
    required_meta = ("match_date", "league", "home_team", "away_team", "score")
    leakage_terms = (
        "pre-match prediction feature",
        "赛前预测特征",
        "用于赛前预测",
        "feed into pre-match",
    )
    tag_counts: dict[str, int] = {}

    for index, item in enumerate(items):
        item_id = str(item.get("id") or f"index:{index}")
        if item_id in seen_ids:
            duplicate_ids.add(item_id)
        seen_ids.add(item_id)
        for field in required_top_fields:
            value = item.get(field)
            if field not in item or value is None or value == "":
                issues.append({"severity": "high", "item_id": item_id, "code": "missing_field", "field": field})
        if str(item.get("review_status") or "") != "draft":
            issues.append({"severity": "medium", "item_id": item_id, "code": "unexpected_review_status", "field": "review_status"})
        labels = _as_mapping(item.get("labels"))
        for field in required_labels:
            value = labels.get(field)
            if field not in labels or value is None or value == "":
                issues.append({"severity": "high", "item_id": item_id, "code": "missing_label", "field": field})
        tags = [str(tag) for tag in _as_list(labels.get("tags")) if str(tag)]
        if not tags:
            issues.append({"severity": "high", "item_id": item_id, "code": "missing_tags", "field": "labels.tags"})
        if "statsbomb_post_match_review" not in tags:
            issues.append({"severity": "high", "item_id": item_id, "code": "missing_post_match_tag", "field": "labels.tags"})
        if "strategy_hit" not in tags and "strategy_miss" not in tags:
            issues.append({"severity": "medium", "item_id": item_id, "code": "missing_hit_miss_tag", "field": "labels.tags"})
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        features = _as_mapping(item.get("features"))
        for field in required_features:
            if field not in features:
                issues.append({"severity": "medium", "item_id": item_id, "code": "missing_feature", "field": field})
        meta = _as_mapping(item.get("meta"))
        for field in required_meta:
            if field not in meta or meta.get(field) in {None, ""}:
                issues.append({"severity": "medium", "item_id": item_id, "code": "missing_meta", "field": field})
        combined_text = "\n".join(
            [
                str(item.get("prompt") or ""),
                str(item.get("completion") or ""),
                str(item.get("draft_note") or ""),
            ]
        ).lower()
        for term in leakage_terms:
            if term.lower() in combined_text:
                issues.append({"severity": "medium", "item_id": item_id, "code": "leakage_boundary_mention", "field": "prompt/completion"})
                break

    for item_id in sorted(duplicate_ids):
        issues.append({"severity": "high", "item_id": item_id, "code": "duplicate_id", "field": "id"})
    if not items:
        issues.append({"severity": "medium", "item_id": "-", "code": "empty_draft", "field": "items"})

    high_count = sum(1 for issue in issues if issue.get("severity") == "high")
    medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
    status = "blocked" if high_count else "review" if medium_count else "ready"
    return {
        "status": status,
        "issue_count": len(issues),
        "high_count": high_count,
        "medium_count": medium_count,
        "tag_counts": dict(sorted(tag_counts.items())),
        "issues": issues[:50],
        "summary_text": f"草稿校验 {status} | 问题 {len(issues)} | high {high_count} | medium {medium_count}",
    }


def _statsbomb_fewshot_item_keys(item: Mapping[str, object]) -> list[str]:
    keys: list[str] = []
    item_id = str(item.get("id") or "").strip()
    if item_id:
        keys.append(f"id:{item_id}")
    meta = _as_mapping(item.get("meta"))
    for field in ("match_id", "source_match_id"):
        value = str(meta.get(field) or "").strip()
        if value:
            keys.append(f"{field}:{value}")
    title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
    if title.strip():
        keys.append(f"title:{title}")
    deduped: list[str] = []
    for key in keys:
        if key not in deduped:
            deduped.append(key)
    return deduped


def build_statsbomb_fewshot_merge_plan(
    draft_payload: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    draft = _as_mapping(draft_payload)
    validation = _as_mapping(draft.get("validation")) or validate_statsbomb_fewshot_draft_payload(draft)
    existing_items = [item for item in _statsbomb_memory_items(existing_memory or {}) if isinstance(item, Mapping)]
    existing_keys: set[str] = set()
    for item in existing_items:
        existing_keys.update(_statsbomb_fewshot_item_keys(item))
    mergeable: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    seen_draft_keys: set[str] = set()
    if _safe_int(validation.get("high_count")) > 0:
        return {
            "status": "blocked",
            "mergeable_count": 0,
            "skipped_count": len(_as_list(draft.get("items"))),
            "existing_count": len(existing_items),
            "mergeable_items": [],
            "skipped_rows": [
                {
                    "id": _as_mapping(item).get("id") or "-",
                    "title": (
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('match_date') or '-'} | "
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('league') or '-'} | "
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('home_team') or '-'} vs "
                        f"{_as_mapping(_as_mapping(item).get('meta')).get('away_team') or '-'}"
                    ),
                    "reason": "validation_high_issues",
                }
                for item in _as_list(draft.get("items"))
                if isinstance(item, Mapping)
            ],
            "validation": validation,
            "summary_text": f"合并计划 blocked | 可合并 0 | 跳过 {len(_as_list(draft.get('items')))} | high {_safe_int(validation.get('high_count'))}",
            "leakage_note": "Merge plan is read-only and does not write to official few-shot memory.",
        }
    for item in [row for row in _as_list(draft.get("items")) if isinstance(row, Mapping)]:
        item_id = str(item.get("id") or "-")
        item_keys = _statsbomb_fewshot_item_keys(item)
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        overlap_existing = sorted(set(item_keys) & existing_keys)
        overlap_draft = sorted(set(item_keys) & seen_draft_keys)
        if overlap_existing:
            skipped.append({"id": item_id, "title": title, "reason": "already_in_memory", "matched_keys": overlap_existing[:3]})
            continue
        if overlap_draft:
            skipped.append({"id": item_id, "title": title, "reason": "duplicate_in_draft", "matched_keys": overlap_draft[:3]})
            continue
        seen_draft_keys.update(item_keys)
        labels = _as_mapping(item.get("labels"))
        health_issues = [str(issue) for issue in _as_list(meta.get("matched_health_issues"))]
        mergeable.append(
            {
                "id": item_id,
                "title": title,
                "root_cause": labels.get("root_cause") or "-",
                "tags": [str(tag) for tag in _as_list(labels.get("tags"))],
                "health_issues": health_issues,
                "item": item,
            }
        )
    status = "ready" if mergeable and _safe_int(validation.get("medium_count")) == 0 else "review" if mergeable else "empty"
    return {
        "status": status,
        "mergeable_count": len(mergeable),
        "skipped_count": len(skipped),
        "existing_count": len(existing_items),
        "mergeable_items": mergeable,
        "skipped_rows": skipped,
        "validation": validation,
        "summary_text": f"合并计划 {status} | 可合并 {len(mergeable)} | 跳过 {len(skipped)} | 现有 {len(existing_items)}",
        "leakage_note": "Merge plan is read-only and does not write to official few-shot memory.",
    }


def build_statsbomb_fewshot_merge_plan_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_plan_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_plan_lines(plan: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(plan)
    validation = _as_mapping(resolved.get("validation"))
    mergeable = [item for item in _as_list(resolved.get("mergeable_items")) if isinstance(item, Mapping)]
    skipped = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot 合并计划",
        "",
        f"- 摘要: {resolved.get('summary_text') or '-'}",
        f"- 状态: {resolved.get('status') or '-'}",
        f"- 校验: {validation.get('summary_text') or '-'}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        "",
        "## 可合并样本",
        "",
        "| ID | 比赛 | 根因 | 健康驱动 | 标签 |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not mergeable:
        lines.append("| - | 暂无可合并样本 | - | - | - |")
    for row in mergeable:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("id")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("root_cause")),
                    _md_cell(", ".join(str(issue) for issue in _as_list(row.get("health_issues")))),
                    _md_cell(", ".join(str(tag) for tag in _as_list(row.get("tags")))),
                ]
            )
            + " |"
        )
    lines.extend(["", "## 跳过样本", "", "| ID | 比赛 | 原因 | 匹配键 |", "| --- | --- | --- | --- |"])
    if not skipped:
        lines.append("| - | 暂无跳过样本 | - | - |")
    for row in skipped:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("id")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("reason")),
                    _md_cell(", ".join(str(key) for key in _as_list(row.get("matched_keys")))),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 后续原则",
            "",
            "- 该计划只读，不会写入正式 few-shot 记忆库。",
            "- blocked 状态必须先修复草稿 high 问题。",
            "- review 状态需要人工确认 medium 问题后再合并。",
            "- 合并后必须重新运行记忆覆盖监控和补样队列。",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_merge_bundle_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_bundle_{current.strftime('%Y%m%d_%H%M%S')}.json"


def build_statsbomb_fewshot_merge_bundle_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_bundle_review_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_bundle(
    plan: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(plan)
    validation = _as_mapping(resolved.get("validation"))
    mergeable = [item for item in _as_list(resolved.get("mergeable_items")) if isinstance(item, Mapping)]
    bundle_items = [_as_mapping(item.get("item")) for item in mergeable if _as_mapping(item.get("item"))]
    health_issue_counts: dict[str, int] = {}
    for item in bundle_items:
        meta = _as_mapping(item.get("meta"))
        for issue in _as_list(meta.get("matched_health_issues")):
            issue_text = str(issue)
            if issue_text:
                health_issue_counts[issue_text] = health_issue_counts.get(issue_text, 0) + 1
    status = "blocked"
    if str(resolved.get("status") or "") in {"ready", "review"} and bundle_items:
        status = "pending_manual_apply"
    elif str(resolved.get("status") or "") == "empty":
        status = "empty"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot merge plan",
        "purpose": "manual_apply_bundle",
        "status": status,
        "approval_required": True,
        "write_policy": "read_only_export_no_state_write",
        "leakage_note": "Bundle contains post-match StatsBomb review samples only; applying it must not feed samples into pre-match prediction features.",
        "plan_summary": resolved.get("summary_text") or "-",
        "validation_summary": validation.get("summary_text") or "-",
        "summary": {
            "bundle_count": len(bundle_items),
            "merge_plan_status": resolved.get("status") or "-",
            "skipped_count": _safe_int(resolved.get("skipped_count")),
            "existing_count": _safe_int(resolved.get("existing_count")),
            "health_issue_counts": dict(sorted(health_issue_counts.items())),
        },
        "items": bundle_items,
        "skipped_rows": [dict(row) for row in _as_list(resolved.get("skipped_rows")) if isinstance(row, Mapping)],
    }


def build_statsbomb_fewshot_merge_bundle_report_lines(bundle: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(bundle)
    summary = _as_mapping(resolved.get("summary"))
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    skipped = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot 合并可应用包",
        "",
        f"- 生成时间: {resolved.get('updated_at') or '-'}",
        f"- 状态: {resolved.get('status') or '-'}",
        f"- 审批要求: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- 写入策略: {resolved.get('write_policy') or '-'}",
        f"- 计划摘要: {resolved.get('plan_summary') or '-'}",
        f"- 校验摘要: {resolved.get('validation_summary') or '-'}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        "",
        "## Bundle 摘要",
        "",
        f"- 可应用样本: {_safe_int(summary.get('bundle_count'))}",
        f"- 合并计划状态: {summary.get('merge_plan_status') or '-'}",
        f"- 跳过样本: {_safe_int(summary.get('skipped_count'))}",
        f"- 现有记忆样本: {_safe_int(summary.get('existing_count'))}",
        f"- 健康驱动: {', '.join(f'{key}:{value}' for key, value in _as_mapping(summary.get('health_issue_counts')).items()) or '-'}",
        "",
        "## 可应用样本",
        "",
        "| ID | 比赛 | 根因 | 健康驱动 | 标签 |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not items:
        lines.append("| - | 暂无可应用样本 | - | - | - |")
    for item in items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        health_issues = ", ".join(str(issue) for issue in _as_list(meta.get("matched_health_issues"))) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(title),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(health_issues),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if skipped:
        lines.extend(["", "## 跳过记录", "", "| ID | 比赛 | 原因 |", "| --- | --- | --- |"])
        for row in skipped[:20]:
            lines.append(
                "| "
                + " | ".join([_md_cell(row.get("id")), _md_cell(row.get("title")), _md_cell(row.get("reason"))])
                + " |"
            )
    lines.extend(
        [
            "",
            "## 应用前检查",
            "",
            "- [ ] 人工确认 bundle 中每条样本都来自赛后事件证据。",
            "- [ ] 人工确认没有 high 级草稿校验问题。",
            "- [ ] 应用前备份正式 few-shot 记忆库。",
            "- [ ] 应用后重新运行记忆监控、补样队列和 Evaluation Agent 相关测试。",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_merge_apply_preview_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_apply_preview_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_apply_preview(
    bundle: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(bundle)
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    validation = validate_statsbomb_fewshot_draft_payload({"items": items})
    existing_items = [item for item in _statsbomb_memory_items(existing_memory or {}) if isinstance(item, Mapping)]
    existing_keys: set[str] = set()
    for item in existing_items:
        existing_keys.update(_statsbomb_fewshot_item_keys(item))
    append_items: list[Mapping[str, object]] = []
    skipped_rows: list[dict[str, object]] = []
    seen_bundle_keys: set[str] = set()
    for item in items:
        item_id = str(item.get("id") or "-")
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        item_keys = _statsbomb_fewshot_item_keys(item)
        overlap_existing = sorted(set(item_keys) & existing_keys)
        overlap_bundle = sorted(set(item_keys) & seen_bundle_keys)
        if overlap_existing:
            skipped_rows.append({"id": item_id, "title": title, "reason": "already_in_memory", "matched_keys": overlap_existing[:3]})
            continue
        if overlap_bundle:
            skipped_rows.append({"id": item_id, "title": title, "reason": "duplicate_in_bundle", "matched_keys": overlap_bundle[:3]})
            continue
        seen_bundle_keys.update(item_keys)
        append_items.append(item)

    bundle_status = str(resolved.get("status") or "")
    bundle_purpose = str(resolved.get("purpose") or "")
    structural_issues: list[dict[str, object]] = []
    if bundle_purpose != "manual_apply_bundle":
        structural_issues.append({"severity": "high", "code": "unexpected_purpose", "field": "purpose"})
    if bundle_status not in {"pending_manual_apply", "empty"}:
        structural_issues.append({"severity": "high", "code": "unexpected_bundle_status", "field": "status"})
    if resolved.get("approval_required") is not True:
        structural_issues.append({"severity": "high", "code": "approval_not_required", "field": "approval_required"})
    if _safe_int(validation.get("high_count")):
        structural_issues.append({"severity": "high", "code": "sample_validation_high", "field": "items"})

    high_count = _safe_int(validation.get("high_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "high")
    medium_count = _safe_int(validation.get("medium_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "medium")
    if high_count:
        status = "blocked"
    elif append_items:
        status = "ready_for_manual_apply" if medium_count == 0 else "review_required"
    else:
        status = "empty"
    backup_filename = f"statsbomb_sandbox_fewshot_samples.backup_{current.strftime('%Y%m%d_%H%M%S')}.json"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot merge bundle",
        "purpose": "manual_apply_preview",
        "status": status,
        "dry_run": True,
        "approval_required": True,
        "no_state_write": True,
        "leakage_note": resolved.get("leakage_note")
        or "StatsBomb post-match review samples must stay inside Evaluation Agent memory.",
        "backup_filename": backup_filename,
        "summary": {
            "append_count": len(append_items) if not high_count else 0,
            "skipped_count": len(skipped_rows),
            "existing_count": len(existing_items),
            "bundle_count": len(items),
            "high_count": high_count,
            "medium_count": medium_count,
        },
        "validation": validation,
        "structural_issues": structural_issues,
        "append_items": [] if high_count else [dict(item) for item in append_items],
        "skipped_rows": skipped_rows,
    }


def build_statsbomb_fewshot_merge_apply_preview_lines(preview: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(preview)
    summary = _as_mapping(resolved.get("summary"))
    validation = _as_mapping(resolved.get("validation"))
    append_items = [item for item in _as_list(resolved.get("append_items")) if isinstance(item, Mapping)]
    skipped_rows = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    structural_issues = [item for item in _as_list(resolved.get("structural_issues")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot Merge Apply Preview",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Dry run: {'YES' if resolved.get('dry_run') else 'NO'}",
        f"- Approval required: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- No state write: {'YES' if resolved.get('no_state_write') else 'NO'}",
        f"- Backup filename before real apply: {resolved.get('backup_filename') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Would append: {_safe_int(summary.get('append_count'))}",
        f"- Skipped: {_safe_int(summary.get('skipped_count'))}",
        f"- Existing memory samples: {_safe_int(summary.get('existing_count'))}",
        f"- Bundle samples: {_safe_int(summary.get('bundle_count'))}",
        f"- Validation high/medium: {_safe_int(summary.get('high_count'))} / {_safe_int(summary.get('medium_count'))}",
        f"- Draft validation: {validation.get('summary_text') or '-'}",
        "",
        "## Would Append",
        "",
        "| ID | Match | Root cause | Tags |",
        "| --- | --- | --- | --- |",
    ]
    if not append_items:
        lines.append("| - | No appendable sample | - | - |")
    for item in append_items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(title),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if skipped_rows:
        lines.extend(["", "## Skipped", "", "| ID | Match | Reason | Matched keys |", "| --- | --- | --- | --- |"])
        for row in skipped_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(row.get("id")),
                        _md_cell(row.get("title")),
                        _md_cell(row.get("reason")),
                        _md_cell(", ".join(str(key) for key in _as_list(row.get("matched_keys")))),
                    ]
                )
                + " |"
            )
    if structural_issues:
        lines.extend(["", "## Blocking Issues", "", "| Severity | Code | Field |", "| --- | --- | --- |"])
        for issue in structural_issues:
            lines.append(
                "| "
                + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("code")), _md_cell(issue.get("field"))])
                + " |"
            )
    lines.extend(
        [
            "",
            "## Next Manual Checks",
            "",
            "- Confirm every sample is post-match evidence for Evaluation Agent only.",
            "- Confirm the preview status is ready_for_manual_apply or review_required.",
            "- Back up the official few-shot memory before any future real apply operation.",
            "- Re-run memory monitor and Evaluation Agent tests after any future real apply operation.",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_merge_apply_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_merge_applied_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_merge_apply_result(
    bundle: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    preview = build_statsbomb_fewshot_merge_apply_preview(bundle, existing_memory or {}, generated_at=current)
    preview_summary = _as_mapping(preview.get("summary"))
    preview_status = str(preview.get("status") or "")
    append_items = [item for item in _as_list(preview.get("append_items")) if isinstance(item, Mapping)]
    if preview_status not in {"ready_for_manual_apply", "review_required"} or not append_items:
        return {
            "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "StatsBomb few-shot merge bundle",
            "purpose": "manual_apply_result",
            "status": "blocked" if preview_status == "blocked" else "empty",
            "preview": preview,
            "summary": {
                "applied_count": 0,
                "existing_count": _safe_int(preview_summary.get("existing_count")),
                "final_count": _safe_int(preview_summary.get("existing_count")),
                "skipped_count": _safe_int(preview_summary.get("skipped_count")),
            },
            "updated_memory": None,
        }

    existing = _as_mapping(existing_memory or {})
    existing_items = [dict(item) for item in _statsbomb_memory_items(existing)]
    approved_items: list[dict[str, object]] = []
    health_issue_counts: dict[str, int] = {}
    for item in append_items:
        approved = dict(item)
        approved["review_status"] = "approved"
        approved["applied_at"] = current.strftime("%Y-%m-%d %H:%M:%S")
        approved_items.append(approved)
        meta = _as_mapping(approved.get("meta"))
        for issue in _as_list(meta.get("matched_health_issues")):
            issue_text = str(issue)
            if issue_text:
                health_issue_counts[issue_text] = health_issue_counts.get(issue_text, 0) + 1
    health_issue_counts = dict(sorted(health_issue_counts.items()))
    merged_items = existing_items + approved_items
    tag_counts: dict[str, int] = {}
    hit_count = 0
    miss_count = 0
    for item in merged_items:
        labels = _as_mapping(item.get("labels"))
        if labels.get("is_hit") is True:
            hit_count += 1
        elif labels.get("is_hit") is False:
            miss_count += 1
        for tag in _as_list(labels.get("tags")):
            tag_text = str(tag)
            if tag_text:
                tag_counts[tag_text] = tag_counts.get(tag_text, 0) + 1
    existing_summary = dict(_as_mapping(existing.get("summary")))
    existing_summary.update(
        {
            "sample_count": len(merged_items),
            "tag_counts": dict(sorted(tag_counts.items())),
            "hit_count": hit_count,
            "miss_count": miss_count,
            "last_manual_apply_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "last_manual_apply_count": len(approved_items),
            "last_manual_apply_health_issue_counts": health_issue_counts,
        }
    )
    leakage_note = (
        str(existing.get("leakage_note") or "")
        or str(_as_mapping(bundle).get("leakage_note") or "")
        or "These few-shot samples use post-match event data and must not be used as pre-match prediction features."
    )
    updated_memory = dict(existing)
    updated_memory.update(
        {
            "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "source": existing.get("source") or "StatsBomb few-shot memory with manual merge",
            "purpose": existing.get("purpose") or "evaluation_agent_fewshot_post_match_review",
            "leakage_note": leakage_note,
            "summary": existing_summary,
            "items": merged_items,
            "last_manual_apply": {
                "applied_at": current.strftime("%Y-%m-%d %H:%M:%S"),
                "applied_count": len(approved_items),
                "skipped_count": _safe_int(preview_summary.get("skipped_count")),
                "backup_filename": preview.get("backup_filename") or "-",
                "health_issue_counts": health_issue_counts,
            },
        }
    )
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot merge bundle",
        "purpose": "manual_apply_result",
        "status": "ready_to_write",
        "preview": preview,
        "summary": {
            "applied_count": len(approved_items),
            "existing_count": len(existing_items),
            "final_count": len(merged_items),
            "skipped_count": _safe_int(preview_summary.get("skipped_count")),
            "health_issue_counts": health_issue_counts,
        },
        "updated_memory": updated_memory,
    }


def build_statsbomb_fewshot_merge_apply_report_lines(result: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(result)
    summary = _as_mapping(resolved.get("summary"))
    preview = _as_mapping(resolved.get("preview"))
    health_issue_counts = _as_mapping(summary.get("health_issue_counts"))
    health_issue_text = ", ".join(f"{key}:{value}" for key, value in health_issue_counts.items()) or "-"
    lines = [
        "# StatsBomb Few-shot Merge Apply",
        "",
        f"- Applied at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Preview status: {preview.get('status') or '-'}",
        f"- Applied samples: {_safe_int(summary.get('applied_count'))}",
        f"- Skipped samples: {_safe_int(summary.get('skipped_count'))}",
        f"- Existing samples before apply: {_safe_int(summary.get('existing_count'))}",
        f"- Final memory samples: {_safe_int(summary.get('final_count'))}",
        f"- Health issues: {health_issue_text}",
        f"- Backup filename: {preview.get('backup_filename') or '-'}",
        f"- Leakage boundary: {preview.get('leakage_note') or '-'}",
        "",
        "## Applied Items",
        "",
        "| ID | Match | Root cause | Health issues | Tags |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in [item for item in _as_list(preview.get("append_items")) if isinstance(item, Mapping)]:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        title = f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"
        health_issues = ", ".join(str(issue) for issue in _as_list(meta.get("matched_health_issues"))) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(title),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(health_issues),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if _safe_int(summary.get("applied_count")) == 0:
        lines.append("| - | No sample was applied | - | - | - |")
    lines.extend(
        [
            "",
            "## Required Follow-up",
            "",
            "- Re-open the strategy dashboard and confirm the few-shot monitor sample count increased.",
            "- Export the backfill queue again to verify coverage gaps changed as expected.",
            "- Keep this report with the backup file for rollback reference.",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_memory_rollback_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_memory_rollback_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_memory_rollback_preview(
    backup_memory: Mapping[str, object] | object,
    current_memory: Mapping[str, object] | object | None = None,
    *,
    backup_name: str = "-",
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    backup = _as_mapping(backup_memory)
    current_payload = _as_mapping(current_memory or {})
    backup_items = [item for item in _statsbomb_memory_items(backup) if isinstance(item, Mapping)]
    current_items = [item for item in _statsbomb_memory_items(current_payload) if isinstance(item, Mapping)]
    validation = validate_statsbomb_fewshot_draft_payload({"items": backup_items})
    structural_issues: list[dict[str, object]] = []
    if not backup:
        structural_issues.append({"severity": "high", "code": "empty_backup_payload", "field": "backup"})
    if "items" not in backup or not isinstance(backup.get("items"), list):
        structural_issues.append({"severity": "high", "code": "missing_backup_items", "field": "items"})
    purpose = str(backup.get("purpose") or "")
    if purpose and purpose != "evaluation_agent_fewshot_post_match_review":
        structural_issues.append({"severity": "medium", "code": "unexpected_purpose", "field": "purpose"})
    high_count = _safe_int(validation.get("high_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "high")
    medium_count = _safe_int(validation.get("medium_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "medium")
    status = "ready_to_restore" if high_count == 0 else "blocked"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot memory backup",
        "purpose": "manual_rollback_preview",
        "status": status,
        "approval_required": True,
        "no_state_write": True,
        "backup_name": backup_name,
        "summary": {
            "backup_count": len(backup_items),
            "current_count": len(current_items),
            "delta": len(backup_items) - len(current_items),
            "high_count": high_count,
            "medium_count": medium_count,
        },
        "backup_updated_at": backup.get("updated_at") or "-",
        "current_updated_at": current_payload.get("updated_at") or "-",
        "validation": validation,
        "structural_issues": structural_issues,
        "leakage_note": backup.get("leakage_note")
        or "Restored few-shot memory remains post-match review evidence for Evaluation Agent only.",
    }


def build_statsbomb_fewshot_memory_rollback_report_lines(preview: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(preview)
    summary = _as_mapping(resolved.get("summary"))
    validation = _as_mapping(resolved.get("validation"))
    structural_issues = [item for item in _as_list(resolved.get("structural_issues")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot Memory Rollback",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Backup file: {resolved.get('backup_name') or '-'}",
        f"- Approval required: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- No state write in preview: {'YES' if resolved.get('no_state_write') else 'NO'}",
        f"- Backup updated at: {resolved.get('backup_updated_at') or '-'}",
        f"- Current updated at: {resolved.get('current_updated_at') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Backup samples: {_safe_int(summary.get('backup_count'))}",
        f"- Current samples: {_safe_int(summary.get('current_count'))}",
        f"- Restore delta: {_safe_int(summary.get('delta'))}",
        f"- Validation high/medium: {_safe_int(summary.get('high_count'))} / {_safe_int(summary.get('medium_count'))}",
        f"- Backup validation: {validation.get('summary_text') or '-'}",
        "",
    ]
    if structural_issues:
        lines.extend(["## Structural Issues", "", "| Severity | Code | Field |", "| --- | --- | --- |"])
        for issue in structural_issues:
            lines.append(
                "| "
                + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("code")), _md_cell(issue.get("field"))])
                + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## Required Manual Checks",
            "",
            "- Confirm the selected backup is the intended rollback target.",
            "- Confirm restore delta is expected.",
            "- Keep the pre-rollback safety backup generated by the APP.",
            "- Re-open the strategy dashboard and verify the few-shot monitor after rollback.",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_memory_audit_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_fewshot_memory_audit_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_fewshot_memory_health_summary(
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    *,
    backup_count: int | None = None,
) -> dict[str, object]:
    resolved_monitor = _as_mapping(monitor)
    resolved_quality = _as_mapping(quality)
    sample_count = _safe_int(resolved_monitor.get("sample_count"))
    missing_tags = [str(tag) for tag in _as_list(resolved_monitor.get("missing_tags"))]
    alert_count = _safe_int(resolved_quality.get("alert_count"))
    health_issues: list[dict[str, object]] = []
    if sample_count <= 0:
        health_issues.append(
            {
                "severity": "high",
                "code": "memory_missing",
                "title": "No few-shot memory samples",
                "recommendation": "Generate and review StatsBomb few-shot drafts before relying on memory-assisted evaluation.",
            }
        )
    elif sample_count < 20:
        health_issues.append(
            {
                "severity": "medium",
                "code": "sample_count_low",
                "title": "Few-shot sample count is below observation target",
                "recommendation": "Prioritize high-confidence misses, cold results, and different leagues in the backfill queue.",
            }
        )
    if backup_count is not None and sample_count > 0 and backup_count <= 0:
        health_issues.append(
            {
                "severity": "medium",
                "code": "backup_missing",
                "title": "No memory backup found",
                "recommendation": "Create a backup before the next manual apply or rollback operation.",
            }
        )
    if missing_tags:
        health_issues.append(
            {
                "severity": "medium",
                "code": "required_tag_gap",
                "title": f"Missing required tags: {', '.join(missing_tags[:5])}",
                "recommendation": "Use the StatsBomb backfill queue to add cases covering the missing tags.",
            }
        )
    if alert_count:
        health_issues.append(
            {
                "severity": "medium",
                "code": "quality_alerts_present",
                "title": f"Quality alerts present: {alert_count}",
                "recommendation": "Resolve memory quality alerts before changing Evaluation Agent behavior.",
            }
        )
    status = "missing" if sample_count <= 0 else "attention" if health_issues else "healthy"
    tone = "bad" if status == "missing" else "warning" if status == "attention" else "good"
    return {
        "status": status,
        "tone": tone,
        "issue_count": len(health_issues),
        "high_count": sum(1 for issue in health_issues if issue.get("severity") == "high"),
        "medium_count": sum(1 for issue in health_issues if issue.get("severity") == "medium"),
        "summary_text": f"{status} | issues {len(health_issues)} | samples {sample_count}",
        "issues": health_issues,
    }


def build_statsbomb_fewshot_health_driver_summary(
    health: Mapping[str, object] | object | None = None,
    backfill_queue: Mapping[str, object] | object | None = None,
    memory: Mapping[str, object] | object | None = None,
    *,
    limit: int = 6,
) -> dict[str, object]:
    resolved_health = _as_mapping(health)
    resolved_queue = _as_mapping(backfill_queue)
    resolved_memory = _as_mapping(memory)
    issue_rows = [_as_mapping(issue) for issue in _as_list(resolved_health.get("issues"))]
    candidate_rows = [_as_mapping(row) for row in _as_list(resolved_queue.get("candidate_rows"))]
    last_apply = _as_mapping(resolved_memory.get("last_manual_apply"))
    memory_summary = _as_mapping(resolved_memory.get("summary"))
    last_apply_counts = _as_mapping(last_apply.get("health_issue_counts")) or _as_mapping(
        memory_summary.get("last_manual_apply_health_issue_counts")
    )

    active_driver_counts: dict[str, int] = {}
    for issue in issue_rows:
        code = str(issue.get("code") or "").strip()
        if code:
            active_driver_counts[code] = active_driver_counts.get(code, 0) + 1

    backfill_driver_counts: dict[str, int] = {}
    for row in candidate_rows:
        for issue in _as_list(row.get("matched_health_issues")):
            issue_text = str(issue).strip()
            if issue_text:
                backfill_driver_counts[issue_text] = backfill_driver_counts.get(issue_text, 0) + 1

    resolved_last_apply_counts: dict[str, int] = {}
    for key, value in last_apply_counts.items():
        key_text = str(key).strip()
        if key_text:
            resolved_last_apply_counts[key_text] = _safe_int(value)

    rows: list[dict[str, object]] = []
    for issue in issue_rows:
        code = str(issue.get("code") or "-")
        rows.append(
            {
                "kind": "active_issue",
                "title": f"{code} | {issue.get('severity') or '-'}",
                "body": str(issue.get("recommendation") or issue.get("title") or "-"),
                "driver": code,
                "count": 1,
                "tone": "bad" if str(issue.get("severity") or "") == "high" else "warning",
            }
        )
    for driver, count in sorted(backfill_driver_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0]))):
        rows.append(
            {
                "kind": "backfill_candidate",
                "title": f"补样候选 | {driver}",
                "body": f"当前补样队列有 {_safe_int(count)} 场候选可覆盖该健康驱动。",
                "driver": driver,
                "count": _safe_int(count),
                "tone": "info",
            }
        )
    for driver, count in sorted(resolved_last_apply_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0]))):
        rows.append(
            {
                "kind": "last_apply",
                "title": f"最近应用 | {driver}",
                "body": f"最近一次 few-shot 应用已补入 {_safe_int(count)} 条该健康驱动样本。",
                "driver": driver,
                "count": _safe_int(count),
                "tone": "good",
            }
        )

    status = "healthy"
    if active_driver_counts:
        status = "attention"
    elif backfill_driver_counts:
        status = "queued"
    elif resolved_last_apply_counts:
        status = "recently_applied"
    tone = "warning" if status == "attention" else "info" if status == "queued" else "good" if status == "recently_applied" else "neutral"
    active_text = ", ".join(f"{key}:{value}" for key, value in sorted(active_driver_counts.items())) or "-"
    queued_text = ", ".join(f"{key}:{value}" for key, value in sorted(backfill_driver_counts.items())) or "-"
    applied_text = ", ".join(f"{key}:{value}" for key, value in sorted(resolved_last_apply_counts.items())) or "-"
    return {
        "status": status,
        "tone": tone,
        "active_driver_counts": dict(sorted(active_driver_counts.items())),
        "backfill_driver_counts": dict(sorted(backfill_driver_counts.items())),
        "last_apply_driver_counts": dict(sorted(resolved_last_apply_counts.items())),
        "summary_text": f"active {active_text} | queued {queued_text} | applied {applied_text}",
        "rows": rows[: max(0, int(limit))],
    }


def build_statsbomb_fewshot_memory_audit_report(
    memory: Mapping[str, object] | object | None = None,
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    *,
    backup_rows: Sequence[Mapping[str, object]] | None = None,
    operation_rows: Sequence[Mapping[str, object]] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    payload = _as_mapping(memory or {})
    resolved_monitor = _as_mapping(monitor)
    resolved_quality = _as_mapping(quality)
    items = _statsbomb_memory_items(payload)
    backups = [dict(row) for row in list(backup_rows or []) if isinstance(row, Mapping)]
    operations = [dict(row) for row in list(operation_rows or []) if isinstance(row, Mapping)]
    alerts = [_as_mapping(row) for row in _as_list(resolved_quality.get("alerts"))]
    last_apply = _as_mapping(payload.get("last_manual_apply"))
    missing_tags = [str(tag) for tag in _as_list(resolved_monitor.get("missing_tags"))]
    sample_count = len(items)
    alert_count = _safe_int(resolved_quality.get("alert_count"))
    health = build_statsbomb_fewshot_memory_health_summary(resolved_monitor, resolved_quality, backup_count=len(backups))
    health_issues = [dict(issue) for issue in _as_list(health.get("issues")) if isinstance(issue, Mapping)]
    status = str(health.get("status") or "missing")
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb few-shot memory",
        "purpose": "memory_audit_report",
        "status": status,
        "memory_updated_at": payload.get("updated_at") or "-",
        "leakage_note": payload.get("leakage_note")
        or "These few-shot samples use post-match event data and must not be used as pre-match prediction features.",
        "summary": {
            "sample_count": sample_count,
            "hit_count": _safe_int(resolved_monitor.get("hit_count")),
            "miss_count": _safe_int(resolved_monitor.get("miss_count")),
            "tag_count": _safe_int(resolved_monitor.get("tag_count")),
            "root_cause_count": _safe_int(resolved_monitor.get("root_cause_count")),
            "coverage_rate_text": resolved_monitor.get("coverage_rate_text") or "-",
            "missing_tag_count": len(missing_tags),
            "alert_count": alert_count,
            "backup_count": len(backups),
            "operation_count": len(operations),
            "health_issue_count": len(health_issues),
            "last_manual_apply_count": _safe_int(last_apply.get("applied_count")),
            "last_manual_apply_at": last_apply.get("applied_at") or "-",
        },
        "tag_rows": [dict(row) for row in _as_list(resolved_monitor.get("tag_rows")) if isinstance(row, Mapping)],
        "root_rows": [dict(row) for row in _as_list(resolved_monitor.get("root_rows")) if isinstance(row, Mapping)],
        "missing_tags": missing_tags,
        "quality_alerts": [dict(row) for row in alerts],
        "health_issues": health_issues,
        "backup_rows": backups,
        "operation_rows": operations,
    }


def build_statsbomb_fewshot_memory_audit_report_lines(audit: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(audit)
    summary = _as_mapping(resolved.get("summary"))
    tag_rows = [row for row in _as_list(resolved.get("tag_rows")) if isinstance(row, Mapping)]
    root_rows = [row for row in _as_list(resolved.get("root_rows")) if isinstance(row, Mapping)]
    alerts = [row for row in _as_list(resolved.get("quality_alerts")) if isinstance(row, Mapping)]
    health_issues = [row for row in _as_list(resolved.get("health_issues")) if isinstance(row, Mapping)]
    backup_rows = [row for row in _as_list(resolved.get("backup_rows")) if isinstance(row, Mapping)]
    operation_rows = [row for row in _as_list(resolved.get("operation_rows")) if isinstance(row, Mapping)]
    lines = [
        "# StatsBomb Few-shot Memory Audit",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Memory updated at: {resolved.get('memory_updated_at') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Samples: {_safe_int(summary.get('sample_count'))}",
        f"- Hit / miss: {_safe_int(summary.get('hit_count'))} / {_safe_int(summary.get('miss_count'))}",
        f"- Tags / root causes: {_safe_int(summary.get('tag_count'))} / {_safe_int(summary.get('root_cause_count'))}",
        f"- Required tag coverage: {summary.get('coverage_rate_text') or '-'}",
        f"- Missing required tags: {_safe_int(summary.get('missing_tag_count'))}",
        f"- Quality alerts: {_safe_int(summary.get('alert_count'))}",
        f"- Health issues: {_safe_int(summary.get('health_issue_count'))}",
        f"- Backups: {_safe_int(summary.get('backup_count'))}",
        f"- Recent apply/rollback reports: {_safe_int(summary.get('operation_count'))}",
        f"- Last manual apply: {summary.get('last_manual_apply_at') or '-'} | {_safe_int(summary.get('last_manual_apply_count'))} samples",
        "",
        "## Tag Coverage",
        "",
        "| Tag | Count |",
        "| --- | --- |",
    ]
    if not tag_rows:
        lines.append("| - | 0 |")
    for row in tag_rows:
        lines.append("| " + " | ".join([_md_cell(row.get("tag")), _md_cell(row.get("count"))]) + " |")
    lines.extend(["", "## Root Causes", "", "| Root cause | Count |", "| --- | --- |"])
    if not root_rows:
        lines.append("| - | 0 |")
    for row in root_rows:
        lines.append("| " + " | ".join([_md_cell(row.get("root_cause")), _md_cell(row.get("count"))]) + " |")
    missing_tags = [str(tag) for tag in _as_list(resolved.get("missing_tags"))]
    lines.extend(["", "## Missing Required Tags", ""])
    lines.append(", ".join(missing_tags) if missing_tags else "-")
    lines.extend(["", "## Health Issues", "", "| Severity | Code | Recommendation |", "| --- | --- | --- |"])
    if not health_issues:
        lines.append("| - | - | - |")
    for issue in health_issues:
        lines.append(
            "| "
            + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("code")), _md_cell(issue.get("recommendation"))])
            + " |"
        )
    lines.extend(["", "## Quality Alerts", "", "| Title | Tag |", "| --- | --- |"])
    if not alerts:
        lines.append("| - | - |")
    for alert in alerts:
        lines.append("| " + " | ".join([_md_cell(alert.get("title")), _md_cell(alert.get("tag"))]) + " |")
    lines.extend(["", "## Backups", "", "| File | Size | Modified |", "| --- | --- | --- |"])
    if not backup_rows:
        lines.append("| - | - | - |")
    for row in backup_rows[:20]:
        lines.append(
            "| "
            + " | ".join([_md_cell(row.get("name")), _md_cell(row.get("size")), _md_cell(row.get("modified_at"))])
            + " |"
        )
    lines.extend(["", "## Recent Operations", "", "| File | Type | Modified |", "| --- | --- | --- |"])
    if not operation_rows:
        lines.append("| - | - | - |")
    for row in operation_rows[:20]:
        lines.append(
            "| "
            + " | ".join([_md_cell(row.get("name")), _md_cell(row.get("type")), _md_cell(row.get("modified_at"))])
            + " |"
        )
    lines.extend(
        [
            "",
            "## Next Checks",
            "",
            "- If quality alerts exist, prioritize backfill queue generation before adding new model behavior.",
            "- Keep at least one recent backup after every manual apply or rollback.",
            "- Do not use StatsBomb post-match few-shot samples as pre-match prediction features.",
            "",
        ]
    )
    return lines


def build_statsbomb_fewshot_draft_review_lines(payload: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(payload)
    summary = _as_mapping(resolved.get("summary"))
    validation = _as_mapping(resolved.get("validation")) or validate_statsbomb_fewshot_draft_payload(resolved)
    items = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    skipped = [item for item in _as_list(resolved.get("skipped")) if isinstance(item, Mapping)]
    lines = [
        "# StatsBomb Few-shot 草稿审查",
        "",
        f"- 生成时间: {resolved.get('updated_at') or '-'}",
        f"- 草稿数量: {_safe_int(summary.get('draft_count'))}",
        f"- 候选数量: {_safe_int(summary.get('candidate_count'))}",
        f"- 最高修复评分: {_safe_int(summary.get('top_repair_score'))}",
        f"- 跳过数量: {_safe_int(summary.get('skipped_count'))}",
        f"- 防泄漏边界: {resolved.get('leakage_note') or '-'}",
        f"- 校验摘要: {validation.get('summary_text') or '-'}",
        "",
        "## 质量校验",
        "",
        f"- 状态: {validation.get('status') or '-'}",
        f"- High: {_safe_int(validation.get('high_count'))}",
        f"- Medium: {_safe_int(validation.get('medium_count'))}",
        "",
    ]
    lines.insert(19, f"- 健康驱动: {resolved.get('backfill_health_summary') or '-'}")
    validation_issues = [item for item in _as_list(validation.get("issues")) if isinstance(item, Mapping)]
    if validation_issues:
        lines.extend(["| 严重度 | 样本 | 代码 | 字段 |", "| --- | --- | --- | --- |"])
        for issue in validation_issues[:12]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(issue.get("severity")),
                        _md_cell(issue.get("item_id")),
                        _md_cell(issue.get("code")),
                        _md_cell(issue.get("field")),
                    ]
                )
                + " |"
            )
        lines.append("")
    else:
        lines.extend(["未发现结构性问题。", ""])
    lines.extend(
        [
            "## 草稿样本",
            "",
        ]
    )
    if not items:
        lines.extend(["暂无可审查草稿。", ""])
    for item in items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        lines.extend(
            [
                f"### {meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}",
                "",
                f"- ID: {item.get('id') or '-'}",
                f"- Health issues: {', '.join(str(issue) for issue in _as_list(meta.get('matched_health_issues'))) or '-'}",
                f"- 修复评分: {_safe_int(meta.get('repair_score'))}",
                f"- 排序原因: {', '.join(str(reason) for reason in _as_list(meta.get('repair_reasons'))) or '-'}",
                f"- 状态: {item.get('review_status') or '-'}",
                f"- 模拟/实际: {labels.get('simulated_pick') or '-'} / {labels.get('actual') or '-'}",
                f"- 命中: {labels.get('is_hit')}",
                f"- 根因: {labels.get('root_cause') or '-'}",
                f"- 标签: {', '.join(str(tag) for tag in _as_list(labels.get('tags'))) or '-'}",
                f"- 补样命中标签: {', '.join(str(tag) for tag in _as_list(meta.get('matched_backfill_tags'))) or '-'}",
                "",
                str(item.get("completion") or "-"),
                "",
            ]
        )
    if skipped:
        lines.extend(["## 跳过候选", "", "| Match ID | 比赛 | 原因 |", "| --- | --- | --- |"])
        for item in skipped:
            lines.append(
                "| "
                + " | ".join([_md_cell(item.get("match_id")), _md_cell(item.get("title")), _md_cell(item.get("reason"))])
                + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## 合并前检查",
            "",
            "- [ ] 确认样本来自完场后的 StatsBomb 事件证据。",
            "- [ ] 确认标签、根因和 completion 没有把赛后信息写入赛前预测特征。",
            "- [ ] 确认样本覆盖的是当前缺口标签或当前错因相似案例。",
            "",
        ]
    )
    return lines


def _statsbomb_sandbox_row(row: Mapping[str, object], baseline: Mapping[str, object] | object | None = None) -> dict[str, object]:
    xg_margin = _safe_float(row.get("xg_margin"))
    goal_margin = _safe_int(row.get("goal_margin"))
    diagnosis: list[str] = []
    if bool(row.get("finishing_variance")):
        diagnosis.append("\u7ec8\u7ed3\u6ce2\u52a8")
    if not bool(row.get("xg_aligned_with_score")):
        diagnosis.append("xG\u4e0e\u8d5b\u679c\u80cc\u79bb")
    if not bool(row.get("shot_aligned_with_score")):
        diagnosis.append("\u5c04\u95e8\u4e0e\u8d5b\u679c\u80cc\u79bb")
    if not diagnosis:
        diagnosis.append("\u4e8b\u4ef6\u652f\u6301\u8d5b\u679c")
    diagnosis_text = "\u3001".join(diagnosis)
    return {
        "match_id": row.get("match_id") or "-",
        "match_date": row.get("match_date") or "-",
        "league": row.get("league") or "-",
        "season": row.get("season") or "-",
        "title": f"{row.get('home_team') or '-'} vs {row.get('away_team') or '-'}",
        "score": row.get("score") or "-",
        "xg": f"{_safe_float(row.get('home_xg')):.2f}-{_safe_float(row.get('away_xg')):.2f}",
        "shots": f"{_safe_int(row.get('home_shots'))}-{_safe_int(row.get('away_shots'))}",
        "xg_margin": round(xg_margin, 4),
        "goal_margin": goal_margin,
        "diagnosis": diagnosis_text,
        "event_count": _safe_int(row.get("event_count")),
        "body": (
            f"{row.get('match_date') or '-'} | {row.get('league') or '-'} | {row.get('home_team') or '-'} vs {row.get('away_team') or '-'}\n"
            f"\u6bd4\u5206 {row.get('score') or '-'} | xG {_safe_float(row.get('home_xg')):.2f}-{_safe_float(row.get('away_xg')):.2f} | "
            f"\u5c04\u95e8 {_safe_int(row.get('home_shots'))}-{_safe_int(row.get('away_shots'))} | \u8bca\u65ad {diagnosis_text}"
        ),
        "evaluation_case": build_statsbomb_event_replay_case(row, baseline or {}),
    }


def _statsbomb_side_to_pick(side: object) -> str:
    text = str(side or "").strip().lower()
    if text == "home":
        return "HOME"
    if text == "away":
        return "AWAY"
    if text == "draw":
        return "DRAW"
    return "-"


def _statsbomb_event_summary_from_baseline_row(row: Mapping[str, object]) -> dict[str, object]:
    home = str(row.get("home_team") or "")
    away = str(row.get("away_team") or "")
    return {
        "event_count": _safe_int(row.get("event_count")),
        "team_stats": {
            home: {
                "xg": _safe_float(row.get("home_xg")),
                "shots": _safe_int(row.get("home_shots")),
                "shots_on_target": _safe_int(row.get("home_shots_on_target")),
                "goals": _safe_int(str(row.get("score") or "0-0").split("-", 1)[0]),
            },
            away: {
                "xg": _safe_float(row.get("away_xg")),
                "shots": _safe_int(row.get("away_shots")),
                "shots_on_target": _safe_int(row.get("away_shots_on_target")),
                "goals": _safe_int(str(row.get("score") or "0-0").split("-", 1)[1] if "-" in str(row.get("score") or "") else 0),
            },
        },
    }


def build_statsbomb_event_replay_case(
    row: Mapping[str, object] | object,
    baseline: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    source = _as_mapping(row)
    if not source:
        return {"status": "empty", "body": "-"}
    score_winner = str(source.get("score_winner") or "").strip().lower()
    xg_winner = str(source.get("xg_winner") or "").strip().lower()
    if not score_winner:
        score_winner = _side_from_margin(_safe_float(source.get("goal_margin")))
    if not xg_winner:
        xg_winner = _side_from_margin(_safe_float(source.get("xg_margin")), threshold=0.25)
    simulated_pick = xg_winner if xg_winner in {"home", "away", "draw"} else score_winner
    actual = score_winner if score_winner in {"home", "away", "draw"} else "draw"
    is_hit = simulated_pick == actual
    settlement = {
        "match_id": source.get("match_id"),
        "match_date": source.get("match_date"),
        "league": source.get("league"),
        "home_team": source.get("home_team"),
        "away_team": source.get("away_team"),
        "home_goals": _safe_int(str(source.get("score") or "0-0").split("-", 1)[0]),
        "away_goals": _safe_int(str(source.get("score") or "0-0").split("-", 1)[1] if "-" in str(source.get("score") or "") else 0),
        "statsbomb_event_summary": _statsbomb_event_summary_from_baseline_row(source),
        "high_accuracy_strategy_items": [
            {
                "data_layer": "statsbomb_event_sandbox",
                "play_type": "market_1x2",
                "pick": _statsbomb_side_to_pick(simulated_pick),
                "actual": _statsbomb_side_to_pick(actual),
                "confidence": 0.70 if bool(source.get("finishing_variance")) else 0.62,
                "min_confidence": 0.65,
                "backtest_accuracy": 0.72,
                "backtest_samples": 180,
                "is_hit": is_hit,
            }
        ],
    }
    evaluation = build_strategy_evaluation_agent_summary({"enabled": True}, [settlement], baseline or {})
    attribution = _as_mapping(evaluation.get("error_attribution"))
    event_review = _as_mapping(evaluation.get("statsbomb_event_review"))
    body = (
        f"Evaluation: {evaluation.get('status', '-')} / score {evaluation.get('score', '-')}\n"
        f"\u6a21\u62df\u7b56\u7565: \u6309xG\u65b9\u5411\u9009 {settlement['high_accuracy_strategy_items'][0]['pick']} | "
        f"\u5b9e\u9645 {settlement['high_accuracy_strategy_items'][0]['actual']} | {'\u547d\u4e2d' if is_hit else '\u672a\u547d\u4e2d'}\n"
        f"\u4e3b\u9519\u56e0: {attribution.get('top_reason') or '-'} | \u4e8b\u4ef6\u590d\u76d8: {event_review.get('summary_text') or '-'}"
    )
    recommendations = evaluation.get("recommendations") if isinstance(evaluation.get("recommendations"), list) else []
    if recommendations:
        body = f"{body}\n\u5efa\u8bae: " + " | ".join(str(item.get("title") or "-") for item in recommendations if isinstance(item, Mapping))
    return {
        "status": "hit" if is_hit else "miss",
        "settlement": settlement,
        "evaluation": evaluation,
        "body": body,
    }


def build_statsbomb_event_sandbox_summary(
    baseline: Mapping[str, object] | object,
    *,
    limit: int = 20,
) -> dict[str, object]:
    resolved = _as_mapping(baseline)
    summary = _as_mapping(resolved.get("summary"))
    item_rows = [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]
    variance_rows = [item for item in _as_list(resolved.get("variance_rows")) if isinstance(item, Mapping)]
    competition_profiles = _as_mapping(resolved.get("competition_profiles"))
    bucket_profiles = _as_mapping(resolved.get("xg_margin_buckets"))
    sandbox_rows = [_statsbomb_sandbox_row(item, resolved) for item in item_rows]
    sandbox_rows.sort(
        key=lambda row: (
            "终结波动" not in str(row.get("diagnosis") or ""),
            -abs(_safe_float(row.get("xg_margin"))),
            str(row.get("match_date") or ""),
        )
    )
    competition_rows = [
        {
            "label": str(key),
            "body": (
                f"\u6837\u672c {_safe_int(_as_mapping(value).get('match_count'))} | "
                f"xG\u5bf9\u9f50 {_as_mapping(value).get('xg_alignment_rate') or '-'} | "
                f"\u7ec8\u7ed3\u6ce2\u52a8 {_as_mapping(value).get('finishing_variance_rate') or '-'} | "
                f"\u573a\u5747xG {_safe_float(_as_mapping(value).get('avg_xg_total')):.2f}"
            ),
        }
        for key, value in sorted(competition_profiles.items())
    ]
    bucket_rows = [
        {
            "label": str(key),
            "body": (
                f"\u6837\u672c {_safe_int(_as_mapping(value).get('match_count'))} | "
                f"xG\u5bf9\u9f50 {_as_mapping(value).get('xg_alignment_rate') or '-'} | "
                f"\u5c04\u95e8\u5bf9\u9f50 {_as_mapping(value).get('shot_alignment_rate') or '-'} | "
                f"\u7ec8\u7ed3\u6ce2\u52a8 {_as_mapping(value).get('finishing_variance_rate') or '-'}"
            ),
        }
        for key, value in sorted(bucket_profiles.items())
    ]
    sample_count = _safe_int(summary.get("match_count"), len(item_rows))
    return {
        "status": "ready" if item_rows else "empty",
        "sample_count": sample_count,
        "source": resolved.get("source") or "-",
        "updated_at": resolved.get("updated_at") or "-",
        "summary_text": (
            f"\u6837\u672c {sample_count} | xG\u5bf9\u9f50 {summary.get('xg_alignment_rate') or '-'} | "
            f"\u5c04\u95e8\u5bf9\u9f50 {summary.get('shot_alignment_rate') or '-'} | "
            f"\u7ec8\u7ed3\u6ce2\u52a8 {summary.get('finishing_variance_rate') or '-'}"
        ),
        "leakage_note": resolved.get("leakage_note") or "\u8be5\u6a21\u5757\u4ec5\u7528\u4e8e\u8d5b\u540e\u590d\u76d8\uff0c\u4e0d\u53c2\u4e0e\u8d5b\u524d\u9884\u6d4b\u8f93\u5165\u3002",
        "competition_rows": competition_rows,
        "bucket_rows": bucket_rows,
        "rows": sandbox_rows[: max(0, int(limit))],
        "variance_rows": [_statsbomb_sandbox_row(item, resolved) for item in variance_rows][: max(0, int(limit))],
    }


def build_statsbomb_event_sandbox_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"statsbomb_event_sandbox_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_statsbomb_event_sandbox_report_lines(
    baseline: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
    limit: int = 20,
) -> list[str]:
    current = generated_at or datetime.now()
    sandbox = build_statsbomb_event_sandbox_summary(baseline, limit=limit)
    lines = [
        "# StatsBomb \u5386\u53f2\u4e8b\u4ef6\u590d\u76d8\u6c99\u76d2",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u6570\u636e\u6e90: {sandbox.get('source', '-')}",
        f"- \u57fa\u7ebf\u66f4\u65b0: {sandbox.get('updated_at', '-')}",
        f"- \u6458\u8981: {sandbox.get('summary_text', '-')}",
        f"- \u9632\u6cc4\u6f0f\u8fb9\u754c: {sandbox.get('leakage_note', '-')}",
        "",
        "## \u8d5b\u4e8b\u57fa\u7ebf",
        "",
        "| \u8d5b\u4e8b | \u6458\u8981 |",
        "| --- | --- |",
    ]
    competition_rows = [row for row in _as_list(sandbox.get("competition_rows")) if isinstance(row, Mapping)]
    if competition_rows:
        for row in competition_rows:
            lines.append(f"| {_md_cell(row.get('label'))} | {_md_cell(row.get('body'))} |")
    else:
        lines.append("| - | \u6682\u65e0\u8d5b\u4e8b\u57fa\u7ebf |")
    lines.extend(
        [
            "",
            "## xG\u5dee\u503c\u5206\u6876",
            "",
            "| \u5206\u6876 | \u6458\u8981 |",
            "| --- | --- |",
        ]
    )
    bucket_rows = [row for row in _as_list(sandbox.get("bucket_rows")) if isinstance(row, Mapping)]
    if bucket_rows:
        for row in bucket_rows:
            lines.append(f"| {_md_cell(row.get('label'))} | {_md_cell(row.get('body'))} |")
    else:
        lines.append("| - | \u6682\u65e0xG\u5206\u6876 |")
    lines.extend(
        [
            "",
            "## Evaluation Agent \u6a21\u62df\u590d\u76d8\u6848\u4f8b",
            "",
            "| \u65e5\u671f | \u8d5b\u4e8b | \u5bf9\u9635 | \u6bd4\u5206 | xG | \u8bca\u65ad | Evaluation | \u4e3b\u9519\u56e0 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    rows = [row for row in _as_list(sandbox.get("variance_rows")) if isinstance(row, Mapping)]
    if not rows:
        rows = [row for row in _as_list(sandbox.get("rows")) if isinstance(row, Mapping)]
    if not rows:
        lines.append("| - | - | - | - | - | - | - | - |")
    for row in rows[: max(0, int(limit))]:
        case = _as_mapping(row.get("evaluation_case"))
        evaluation = _as_mapping(case.get("evaluation"))
        attribution = _as_mapping(evaluation.get("error_attribution"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("match_date")),
                    _md_cell(row.get("league")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("score")),
                    _md_cell(row.get("xg")),
                    _md_cell(row.get("diagnosis")),
                    _md_cell(f"{evaluation.get('status', '-')} / {evaluation.get('score', '-')}"),
                    _md_cell(attribution.get("top_reason")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## \u6848\u4f8b\u8be6\u60c5", ""])
    for index, row in enumerate(rows[: max(0, int(limit))], start=1):
        case = _as_mapping(row.get("evaluation_case"))
        lines.extend(
            [
                f"### {index}. {_text(row.get('title'))}",
                "",
                f"- \u65e5\u671f: {_text(row.get('match_date'))}",
                f"- \u8d5b\u4e8b: {_text(row.get('league'))}",
                f"- \u6bd4\u5206 / xG / \u5c04\u95e8: {_text(row.get('score'))} / {_text(row.get('xg'))} / {_text(row.get('shots'))}",
                f"- \u6837\u672c\u8bca\u65ad: {_text(row.get('diagnosis'))}",
                "",
                "```text",
                _text(case.get("body")),
                "```",
                "",
            ]
        )
    return lines


def _strategy_error_codes(settlement: Mapping[str, object], item: Mapping[str, object]) -> list[str]:
    if item.get("is_hit") is None:
        return ["data_missing"]
    if item.get("is_hit") is not False:
        return []
    codes: list[str] = []
    pick = str(item.get("pick") or "").strip()
    actual = str(item.get("actual") or "").strip()
    if not pick or not actual or pick == "-" or actual == "-":
        codes.append("data_missing")
    confidence = _safe_float(item.get("confidence"))
    min_confidence = _safe_float(item.get("min_confidence"))
    if confidence >= max(0.65, min_confidence):
        codes.append("high_confidence_miss")
    backtest_accuracy = _safe_float(item.get("backtest_accuracy") or item.get("accuracy"))
    if backtest_accuracy >= 0.68:
        codes.append("historical_gap")
    sample_count = _safe_int(item.get("backtest_samples") or item.get("sample_count"))
    if sample_count and sample_count < 120:
        codes.append("small_sample")
    if bool(item.get("is_shadow")) or bool(item.get("blocked_by_breaker")):
        codes.append("shadow_observation")
    if _is_jc_bucket_item(item):
        feedback = _as_mapping(item.get("jc_live_feedback"))
        bucket = _as_mapping(item.get("jc_bucket"))
        status = str(feedback.get("status") or "").lower()
        if status == "downgraded" or str(item.get("breaker_status") or "").lower() == "jc_live_downgraded":
            codes.append("jc_live_downgraded")
        wilson = _safe_float(feedback.get("historical_wilson_lower", bucket.get("wilson_lower")))
        live_rate = feedback.get("live_hit_rate")
        if live_rate is not None and _safe_float(live_rate) < wilson:
            codes.append("jc_wilson_breach")
        deviation = feedback.get("deviation")
        if deviation is not None and _safe_float(deviation) <= -0.10:
            codes.append("historical_gap")
        context = _as_mapping(item.get("jc_context"))
        live_odds = context.get("pick_odds")
        historical_odds = bucket.get("avg_pick_odds")
        if live_odds not in (None, "") and historical_odds not in (None, "") and abs(_safe_float(live_odds) - _safe_float(historical_odds)) >= 0.25:
            codes.append("jc_odds_drift")
        historical_confidence = bucket.get("avg_confidence")
        if historical_confidence not in (None, "") and confidence + 0.05 < _safe_float(historical_confidence):
            codes.append("jc_confidence_drift")
    statsbomb_evidence = _statsbomb_event_evidence(settlement, item)
    for code in _as_list(statsbomb_evidence.get("codes")):
        codes.append(str(code))
    video_evidence = _video_review_evidence(settlement)
    for code in _as_list(video_evidence.get("codes")):
        codes.append(str(code))
    if not codes:
        codes.append("unknown")
    deduped: list[str] = []
    for code in codes:
        if code not in deduped:
            deduped.append(code)
    return deduped


def build_strategy_error_attribution_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
    error_weight_overrides: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    rows: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    miss_count = 0
    unknown_count = 0
    resolved_weights = dict(ERROR_ATTRIBUTION_WEIGHTS)
    for key, value in _as_mapping(error_weight_overrides).items():
        resolved_weights[str(key)] = _safe_float(value, resolved_weights.get(str(key), 1.0))
    for settlement, item in _known_strategy_settlement_items(settlement_items):
        codes = _strategy_error_codes(settlement, item)
        if item.get("is_hit") is False:
            miss_count += 1
        elif item.get("is_hit") is None:
            unknown_count += 1
        else:
            continue
        for code in codes:
            counts[code] = counts.get(code, 0) + 1
        if item.get("is_hit") is False:
            labels = [ERROR_ATTRIBUTION_LABELS.get(code, code) for code in codes]
            labels_text = "\u3001".join(labels)
            statsbomb_evidence = _statsbomb_event_evidence(settlement, item)
            evidence_body = str(statsbomb_evidence.get("body") or "")
            video_evidence = _video_review_evidence(settlement)
            video_body = str(video_evidence.get("body") or "")
            base_body = (
                f"\u73a9\u6cd5: {_label(PLAY_LABELS, item.get('play_type'))} | \u9884\u6d4b {item.get('pick') or '-'} / \u5b9e\u9645 {item.get('actual') or '-'}\n"
                f"\u9519\u56e0: {labels_text}\n"
                f"\u7f6e\u4fe1: {_pct(item.get('confidence'))} | \u56de\u6d4b {_pct(item.get('backtest_accuracy') or item.get('accuracy'))} | \u6837\u672c {_safe_int(item.get('backtest_samples') or item.get('sample_count'))}"
            )
            if evidence_body:
                base_body = f"{base_body}\n{evidence_body}"
            if video_body:
                base_body = f"{base_body}\n{video_body}"
            rows.append(
                {
                    "title": f"{settlement.get('league') or '-'} | {settlement.get('home_team') or '-'} vs {settlement.get('away_team') or '-'}",
                    "body": base_body,
                }
            )
    ranked = sorted(counts.items(), key=lambda item: _error_attribution_rank_key(item, resolved_weights))
    top_reason = "-"
    if ranked:
        top_reason = f"{ERROR_ATTRIBUTION_LABELS.get(ranked[0][0], ranked[0][0])} {ranked[0][1]}\u6b21"
    return {
        "miss_count": miss_count,
        "unknown_count": unknown_count,
        "reason_counts": dict(ranked),
        "rank_weights": {code: resolved_weights.get(code, 1.0) for code, _count in ranked},
        "top_reason": top_reason,
        "rows": rows[: max(0, int(limit))],
        "summary_text": f"\u9519\u56e0 {miss_count}\u9879 | \u4e3b\u56e0 {top_reason}",
    }


def build_agent_trace_replay_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if isinstance(item.get("supervisor_agent_statuses"), Mapping)
        and (item.get("is_correct") is not None or item.get("handicap_is_correct") is not None)
    ]
    agent_rows: dict[str, dict[str, object]] = {}
    action_counts: dict[str, int] = {}
    for item in known:
        statuses = _as_mapping(item.get("supervisor_agent_statuses"))
        actions = item.get("supervisor_agent_actions") if isinstance(item.get("supervisor_agent_actions"), list) else []
        for action in actions:
            key = str(action)
            action_counts[key] = _safe_int(action_counts.get(key)) + 1
        for agent_name, status_value in statuses.items():
            status = _text(status_value).lower()
            if status not in {"alert", "watch", "blocked"}:
                continue
            name = str(agent_name)
            row = agent_rows.setdefault(
                name,
                {
                    "agent": name,
                    "trigger_count": 0,
                    "alert_count": 0,
                    "watch_count": 0,
                    "blocked_count": 0,
                    "prediction_known": 0,
                    "prediction_miss": 0,
                    "handicap_known": 0,
                    "handicap_miss": 0,
                    "actions": {},
                },
            )
            row["trigger_count"] = _safe_int(row.get("trigger_count")) + 1
            if status == "alert":
                row["alert_count"] = _safe_int(row.get("alert_count")) + 1
            elif status == "watch":
                row["watch_count"] = _safe_int(row.get("watch_count")) + 1
            elif status == "blocked":
                row["blocked_count"] = _safe_int(row.get("blocked_count")) + 1
            if item.get("is_correct") is not None:
                row["prediction_known"] = _safe_int(row.get("prediction_known")) + 1
                row["prediction_miss"] = _safe_int(row.get("prediction_miss")) + (1 if item.get("is_correct") is False else 0)
            if item.get("handicap_is_correct") is not None:
                row["handicap_known"] = _safe_int(row.get("handicap_known")) + 1
                row["handicap_miss"] = _safe_int(row.get("handicap_miss")) + (1 if item.get("handicap_is_correct") is False else 0)
            row_actions = row.get("actions")
            if not isinstance(row_actions, dict):
                row_actions = {}
                row["actions"] = row_actions
            for action in actions:
                key = str(action)
                row_actions[key] = _safe_int(row_actions.get(key)) + 1

    rows: list[dict[str, object]] = []
    for row in agent_rows.values():
        prediction_known = _safe_int(row.get("prediction_known"))
        handicap_known = _safe_int(row.get("handicap_known"))
        prediction_miss_rate = _safe_int(row.get("prediction_miss")) / prediction_known if prediction_known else None
        handicap_miss_rate = _safe_int(row.get("handicap_miss")) / handicap_known if handicap_known else None
        row_actions = row.get("actions") if isinstance(row.get("actions"), dict) else {}
        top_action = "-"
        if row_actions:
            top_action = sorted(row_actions.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                **row,
                "prediction_miss_rate": prediction_miss_rate,
                "prediction_miss_rate_text": _pct(prediction_miss_rate),
                "handicap_miss_rate": handicap_miss_rate,
                "handicap_miss_rate_text": _pct(handicap_miss_rate),
                "top_action": top_action,
            }
        )
    rows.sort(
        key=lambda row: (
            -_safe_int(row.get("alert_count")) - _safe_int(row.get("blocked_count")),
            -_safe_float(row.get("prediction_miss_rate"), 0.0),
            -_safe_float(row.get("handicap_miss_rate"), 0.0),
            str(row.get("agent") or ""),
        )
    )
    top_agent = rows[0].get("agent") if rows else "-"
    top_action = "-"
    if action_counts:
        top_action = sorted(action_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
    return {
        "sample_count": len(known),
        "agent_count": len(rows),
        "top_agent": top_agent,
        "top_action": top_action,
        "rows": rows[: max(0, int(limit))],
        "summary_text": f"样本 {len(known)} | 风险Agent {len(rows)} | 最高关联 {top_agent} | 主要动作 {top_action}",
    }


def build_agent_replay_downgrade_backtest_summary(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if _safe_bool(item.get("agent_replay_guard_applied"))
        and (item.get("is_correct") is not None or item.get("handicap_is_correct") is not None)
    ]
    by_agent: dict[str, dict[str, object]] = {}
    for item in known:
        agent = _text(item.get("agent_replay_guard_top_agent"), "unknown")
        row = by_agent.setdefault(
            agent,
            {
                "agent": agent,
                "count": 0,
                "prediction_known": 0,
                "prediction_avoided_misses": 0,
                "prediction_opportunity_cost": 0,
                "handicap_known": 0,
                "handicap_avoided_misses": 0,
                "handicap_opportunity_cost": 0,
                "actions": {},
            },
        )
        row["count"] = _safe_int(row.get("count")) + 1
        if item.get("is_correct") is not None:
            row["prediction_known"] = _safe_int(row.get("prediction_known")) + 1
            if item.get("is_correct") is False:
                row["prediction_avoided_misses"] = _safe_int(row.get("prediction_avoided_misses")) + 1
            else:
                row["prediction_opportunity_cost"] = _safe_int(row.get("prediction_opportunity_cost")) + 1
        if item.get("handicap_is_correct") is not None:
            row["handicap_known"] = _safe_int(row.get("handicap_known")) + 1
            if item.get("handicap_is_correct") is False:
                row["handicap_avoided_misses"] = _safe_int(row.get("handicap_avoided_misses")) + 1
            else:
                row["handicap_opportunity_cost"] = _safe_int(row.get("handicap_opportunity_cost")) + 1
        row_actions = row.get("actions") if isinstance(row.get("actions"), dict) else {}
        row["actions"] = row_actions
        actions = item.get("agent_replay_guard_actions") if isinstance(item.get("agent_replay_guard_actions"), list) else []
        for action in actions:
            key = str(action)
            row_actions[key] = _safe_int(row_actions.get(key)) + 1

    rows: list[dict[str, object]] = []
    for row in by_agent.values():
        prediction_known = _safe_int(row.get("prediction_known"))
        handicap_known = _safe_int(row.get("handicap_known"))
        prediction_net = _safe_int(row.get("prediction_avoided_misses")) - _safe_int(row.get("prediction_opportunity_cost"))
        handicap_net = _safe_int(row.get("handicap_avoided_misses")) - _safe_int(row.get("handicap_opportunity_cost"))
        actions = row.get("actions") if isinstance(row.get("actions"), dict) else {}
        top_action = "-"
        if actions:
            top_action = sorted(actions.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                **row,
                "prediction_avoid_rate": (
                    _safe_int(row.get("prediction_avoided_misses")) / prediction_known if prediction_known else None
                ),
                "prediction_avoid_rate_text": _pct(_safe_int(row.get("prediction_avoided_misses")) / prediction_known) if prediction_known else "-",
                "prediction_net": prediction_net,
                "handicap_avoid_rate": (
                    _safe_int(row.get("handicap_avoided_misses")) / handicap_known if handicap_known else None
                ),
                "handicap_avoid_rate_text": _pct(_safe_int(row.get("handicap_avoided_misses")) / handicap_known) if handicap_known else "-",
                "handicap_net": handicap_net,
                "top_action": top_action,
            }
        )
    rows.sort(
        key=lambda row: (
            -_safe_int(row.get("prediction_net")) - _safe_int(row.get("handicap_net")),
            -_safe_int(row.get("count")),
            str(row.get("agent") or ""),
        )
    )
    sample_count = len(known)
    prediction_known_total = sum(1 for item in known if item.get("is_correct") is not None)
    prediction_avoided = sum(1 for item in known if item.get("is_correct") is False)
    prediction_cost = sum(1 for item in known if item.get("is_correct") is True)
    handicap_known_total = sum(1 for item in known if item.get("handicap_is_correct") is not None)
    handicap_avoided = sum(1 for item in known if item.get("handicap_is_correct") is False)
    handicap_cost = sum(1 for item in known if item.get("handicap_is_correct") is True)
    net = (prediction_avoided - prediction_cost) + (handicap_avoided - handicap_cost)
    if sample_count < 5:
        recommendation = "collecting"
        recommendation_text = "Agent Replay 降级样本不足，继续观察。"
    elif net > 0:
        recommendation = "keep_guard"
        recommendation_text = "Agent Replay 降级的理论净收益为正，建议继续保留观察降级。"
    elif net < 0:
        recommendation = "review_guard"
        recommendation_text = "Agent Replay 降级机会成本偏高，建议复核触发门槛。"
    else:
        recommendation = "monitor"
        recommendation_text = "Agent Replay 降级收益与成本接近，继续监控。"
    return {
        "sample_count": sample_count,
        "prediction_known": prediction_known_total,
        "prediction_avoided_misses": prediction_avoided,
        "prediction_opportunity_cost": prediction_cost,
        "prediction_net": prediction_avoided - prediction_cost,
        "handicap_known": handicap_known_total,
        "handicap_avoided_misses": handicap_avoided,
        "handicap_opportunity_cost": handicap_cost,
        "handicap_net": handicap_avoided - handicap_cost,
        "net": net,
        "rows": rows[: max(0, int(limit))],
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "summary_text": (
            f"样本 {sample_count} | 1X2避错 {prediction_avoided}/成本 {prediction_cost} | "
            f"让球避错 {handicap_avoided}/成本 {handicap_cost} | 净值 {net:+d}"
        ),
    }


def build_agent_replay_guard_tuning_recommendation(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    base_min_samples: int = 5,
    base_prediction_miss_threshold: float = 0.55,
    base_handicap_miss_threshold: float = 0.60,
) -> dict[str, object]:
    summary = build_agent_replay_downgrade_backtest_summary(settlements)
    sample_count = _safe_int(summary.get("sample_count"))
    net = _safe_int(summary.get("net"))
    prediction_net = _safe_int(summary.get("prediction_net"))
    handicap_net = _safe_int(summary.get("handicap_net"))
    min_samples = max(3, min(20, _safe_int(base_min_samples, 5)))
    prediction_threshold = max(0.45, min(0.80, _safe_float(base_prediction_miss_threshold, 0.55)))
    handicap_threshold = max(0.45, min(0.85, _safe_float(base_handicap_miss_threshold, 0.60)))
    next_min_samples = min_samples
    next_prediction_threshold = prediction_threshold
    next_handicap_threshold = handicap_threshold
    action = "collect"
    label = "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c"
    tone = "neutral"
    reasons: list[str] = []

    if sample_count < 8:
        reasons.append(f"Replay Guard \u5df2\u7ed3\u7b97\u6837\u672c {sample_count} \u573a\uff0c\u6682\u4e0d\u6839\u636e\u5c0f\u6837\u672c\u6539\u53d8\u89e6\u53d1\u95e8\u69db\u3002")
    elif net >= 3:
        action = "tighten_guard"
        label = "\u6536\u7d27 Replay Guard"
        tone = "good"
        if prediction_net > 0:
            next_prediction_threshold = max(0.45, prediction_threshold - 0.03)
        if handicap_net > 0:
            next_handicap_threshold = max(0.45, handicap_threshold - 0.03)
        reasons.append(f"Replay Guard \u7406\u8bba\u51c0\u503c {net:+d}\uff0c\u964d\u7ea7\u5e2e\u52a9\u56de\u907f\u7684\u9519\u8bef\u5927\u4e8e\u673a\u4f1a\u6210\u672c\u3002")
    elif net <= -2:
        action = "loosen_guard"
        label = "\u653e\u5bbd Replay Guard"
        tone = "warning"
        next_min_samples = min(20, min_samples + 1)
        next_prediction_threshold = min(0.80, prediction_threshold + 0.03)
        next_handicap_threshold = min(0.85, handicap_threshold + 0.03)
        reasons.append(f"Replay Guard \u7406\u8bba\u51c0\u503c {net:+d}\uff0c\u673a\u4f1a\u6210\u672c\u9ad8\u4e8e\u53ef\u56de\u907f\u9519\u8bef\u3002")
    elif net > 0:
        action = "keep_guard"
        label = "\u4fdd\u6301 Replay Guard"
        tone = "good"
        reasons.append(f"Replay Guard \u51c0\u503c {net:+d}\uff0c\u5df2\u4e3a\u6b63\u4f46\u5c1a\u672a\u8fbe\u5230\u81ea\u52a8\u6536\u7d27\u6761\u4ef6\u3002")
    else:
        action = "monitor"
        label = "\u7ee7\u7eed\u89c2\u5bdf"
        tone = "neutral"
        reasons.append("Replay Guard \u51c0\u503c\u63a5\u8fd1 0\uff0c\u5efa\u8bae\u4fdd\u6301\u73b0\u6709\u95e8\u69db\u5e76\u7ee7\u7eed\u56de\u6536\u8d5b\u679c\u3002")

    next_prediction_threshold = round(next_prediction_threshold, 2)
    next_handicap_threshold = round(next_handicap_threshold, 2)
    policy_update = {
        "agent_replay_guard_enabled": True,
        "agent_replay_min_samples": next_min_samples,
        "agent_replay_prediction_miss_threshold": next_prediction_threshold,
        "agent_replay_handicap_miss_threshold": next_handicap_threshold,
    }
    if action in {"collect", "keep_guard", "monitor"}:
        policy_update = {}
    rows = [
        ("\u52a8\u4f5c", label),
        ("\u56de\u6d4b\u51c0\u503c", f"{net:+d} | 1X2 {prediction_net:+d} / \u8ba9\u7403 {handicap_net:+d}"),
        ("\u6837\u672c", f"{sample_count} \u573a | {summary.get('summary_text', '-')}"),
        ("\u89e6\u53d1\u6837\u672c", f"{min_samples} -> {next_min_samples}"),
        ("\u80dc\u5e73\u8d1f\u5931\u8bef\u7ebf", f"{prediction_threshold:.2f} -> {next_prediction_threshold:.2f}"),
        ("\u8ba9\u7403\u5931\u8bef\u7ebf", f"{handicap_threshold:.2f} -> {next_handicap_threshold:.2f}"),
        ("\u8c03\u6574\u4f9d\u636e", "\n".join(reasons) if reasons else "-"),
    ]
    return {
        "action": action,
        "label": label,
        "tone": tone,
        "sample_count": sample_count,
        "net": net,
        "next_min_samples": next_min_samples,
        "next_prediction_miss_threshold": next_prediction_threshold,
        "next_handicap_miss_threshold": next_handicap_threshold,
        "policy_update": policy_update,
        "reasons": reasons,
        "rows": rows,
        "summary": summary,
    }


def _parse_policy_review_time(value: object) -> datetime | None:
    text = _text(value, "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            try:
                return datetime.strptime(text[:10], fmt)
            except Exception:
                continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _settlement_review_time(item: Mapping[str, object]) -> datetime | None:
    for key in ("settled_at", "timestamp", "updated_at", "match_date"):
        parsed = _parse_policy_review_time(item.get(key))
        if parsed is not None:
            return parsed
    return None


def _policy_effect_settlement_title(item: Mapping[str, object]) -> str:
    league = _text(item.get("league"), "-")
    home = _text(item.get("home_team"), "-")
    away = _text(item.get("away_team"), "-")
    return f"{league} | {home} vs {away}"


def _policy_effect_bool_label(value: object) -> str:
    if value is True:
        return "\u547d\u4e2d"
    if value is False:
        return "\u5931\u8bef"
    return "\u672a\u5224\u5b9a"


def _policy_effect_drag_reasons(item: Mapping[str, object], replay_net_hint: int) -> list[str]:
    reasons: list[str] = []
    decision = str(item.get("strategy_admission_decision") or "").strip()
    if decision == "allow" and item.get("is_correct") is False:
        reasons.append("\u653e\u884c\u540e1X2\u5931\u8bef")
    if decision == "allow" and item.get("handicap_is_correct") is False:
        reasons.append("\u653e\u884c\u540e\u8ba9\u7403\u5931\u8bef")
    if bool(item.get("agent_replay_guard_applied")) and replay_net_hint < 0:
        reasons.append("Replay Guard\u673a\u4f1a\u6210\u672c")
    if bool(item.get("agent_replay_guard_applied")) and replay_net_hint > 0:
        reasons.append("Replay Guard\u56de\u907f\u9519\u8bef")
    return reasons


def _policy_effect_settlement_rows(items: Sequence[Mapping[str, object]], *, limit: int = 20) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    ordered = sorted(
        [item for item in items if isinstance(item, Mapping)],
        key=lambda item: _settlement_review_time(item) or datetime.min,
        reverse=True,
    )
    for item in ordered[: max(0, int(limit))]:
        replay_applied = bool(item.get("agent_replay_guard_applied"))
        replay_agent = _text(item.get("agent_replay_guard_top_agent"), "-")
        replay_net_hint = 0
        if replay_applied:
            if item.get("is_correct") is False:
                replay_net_hint += 1
            elif item.get("is_correct") is True:
                replay_net_hint -= 1
            if item.get("handicap_is_correct") is False:
                replay_net_hint += 1
            elif item.get("handicap_is_correct") is True:
                replay_net_hint -= 1
        drag_reasons = _policy_effect_drag_reasons(item, replay_net_hint)
        drag_score = 0
        if "\u653e\u884c\u540e1X2\u5931\u8bef" in drag_reasons:
            drag_score += 2
        if "\u653e\u884c\u540e\u8ba9\u7403\u5931\u8bef" in drag_reasons:
            drag_score += 1
        if "Replay Guard\u673a\u4f1a\u6210\u672c" in drag_reasons:
            drag_score += abs(replay_net_hint)
        elif replay_net_hint < 0:
            drag_score += abs(replay_net_hint)
        rows.append(
            {
                "match_id": _text(item.get("match_id"), "-"),
                "time": _text(item.get("settled_at") or item.get("timestamp") or item.get("match_date"), "-"),
                "title": _policy_effect_settlement_title(item),
                "league": _text(item.get("league"), "-"),
                "home_team": _text(item.get("home_team"), "-"),
                "away_team": _text(item.get("away_team"), "-"),
                "decision": _text(item.get("strategy_admission_decision"), "-"),
                "prediction_result": _policy_effect_bool_label(item.get("is_correct")),
                "handicap_result": _policy_effect_bool_label(item.get("handicap_is_correct")),
                "replay_guard": "\u89e6\u53d1" if replay_applied else "\u672a\u89e6\u53d1",
                "replay_agent": replay_agent,
                "replay_net_hint": replay_net_hint,
                "drag_score": drag_score,
                "drag_reasons": drag_reasons,
                "drag_reason_text": "\u3001".join(drag_reasons) if drag_reasons else "-",
                "summary": (
                    f"{_policy_effect_settlement_title(item)} | "
                    f"\u51c6\u5165 {_text(item.get('strategy_admission_decision'), '-')} | "
                    f"1X2 {_policy_effect_bool_label(item.get('is_correct'))} | "
                    f"\u8ba9\u7403 {_policy_effect_bool_label(item.get('handicap_is_correct'))} | "
                    f"Replay {'ON' if replay_applied else 'OFF'} {replay_agent}"
                ),
            }
        )
    return rows


def _policy_effect_negative_diagnostics(
    sample_rows: Sequence[Mapping[str, object]],
    *,
    effect_status: str,
    allow_hit_rate: float | None,
    replay_net: int,
) -> dict[str, object]:
    negative_rows = [dict(row) for row in sample_rows if _safe_int(row.get("drag_score")) > 0]
    negative_rows.sort(
        key=lambda row: (
            -_safe_int(row.get("drag_score")),
            _safe_float(row.get("replay_net_hint"), 0.0),
            str(row.get("time") or ""),
        )
    )
    reason_counts: dict[str, int] = {}
    for row in negative_rows:
        for reason in row.get("drag_reasons", []) if isinstance(row.get("drag_reasons"), list) else []:
            key = _text(reason, "-")
            reason_counts[key] = reason_counts.get(key, 0) + 1
    top_reason = "-"
    if reason_counts:
        top_reason = sorted(reason_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
    rollback_recommended = (
        effect_status == "negative"
        and (
            (allow_hit_rate is not None and allow_hit_rate < 0.55)
            or replay_net < 0
            or len(negative_rows) >= 2
        )
    )
    if rollback_recommended:
        action_label = "\u5efa\u8bae\u590d\u6838\u56de\u6eda"
    elif effect_status == "negative":
        action_label = "\u5efa\u8bae\u4eba\u5de5\u590d\u6838"
    else:
        action_label = "\u6682\u65e0\u56de\u6eda\u5efa\u8bae"
    return {
        "top_negative_rows": negative_rows[:5],
        "negative_count": len(negative_rows),
        "negative_reason_counts": reason_counts,
        "top_negative_reason": top_reason,
        "rollback_recommended": rollback_recommended,
        "action_label": action_label,
        "summary_text": (
            f"{action_label} | \u4e3b\u56e0 {top_reason} | "
            f"\u62d6\u7d2f\u6837\u672c {len(negative_rows)} | Replay\u51c0\u503c {replay_net:+d}"
        ),
    }


def _policy_effect_stability_tone(status: str) -> str:
    if status in {"improving", "stable"}:
        return "good"
    if status in {"regression", "volatile"}:
        return "bad"
    if status == "watch":
        return "warning"
    return "neutral"


def _policy_effect_stability_label(status: str) -> str:
    labels = {
        "improving": "\u8d8b\u52bf\u6539\u5584",
        "stable": "\u7a33\u5b9a\u751f\u6548",
        "watch": "\u9700\u89c2\u5bdf",
        "regression": "\u51fa\u73b0\u56de\u9000",
        "volatile": "\u6ce2\u52a8\u8fc7\u5927",
        "collecting": "\u6837\u672c\u79ef\u7d2f\u4e2d",
        "none": "\u6682\u65e0\u7248\u672c",
    }
    return labels.get(status, "\u9700\u89c2\u5bdf")


def _policy_effect_stability_recommendation(status: str) -> str:
    if status == "improving":
        return "\u6700\u8fd1\u7248\u672c\u5448\u6b63\u5411\u6539\u5584\uff0c\u7ee7\u7eed\u6309\u5f53\u524d\u95e8\u69db\u6536\u96c6\u8d5b\u679c\u3002"
    if status == "stable":
        return "\u7b56\u7565\u53c2\u6570\u5df2\u8fdb\u5165\u7a33\u5b9a\u89c2\u5bdf\uff0c\u4e0d\u5efa\u8bae\u9891\u7e41\u518d\u8c03\u53c2\u3002"
    if status == "regression":
        return "\u6700\u65b0\u7248\u672c\u51fa\u73b0\u56de\u9000\uff0c\u4f18\u5148\u590d\u6838\u8d1f\u5411\u6837\u672c\uff0c\u5fc5\u8981\u65f6\u56de\u6eda\u4e0a\u4e00\u7248\u3002"
    if status == "volatile":
        return "\u7248\u672c\u95f4\u547d\u4e2d\u6ce2\u52a8\u504f\u5927\uff0c\u5efa\u8bae\u5ef6\u957f\u89c2\u5bdf\u7a97\u53e3\uff0c\u907f\u514d\u8fde\u7eed\u81ea\u52a8\u6536\u7d27\u6216\u653e\u5bbd\u3002"
    if status == "watch":
        return "\u5df2\u6709\u8d1f\u5411\u4fe1\u53f7\uff0c\u5148\u4fdd\u6301\u89c2\u5bdf\uff0c\u7b49\u5f85\u66f4\u591a\u53ef\u56de\u6536\u6837\u672c\u786e\u8ba4\u3002"
    return "\u5f53\u524d\u6837\u672c\u4e0d\u8db3\uff0c\u6682\u4e0d\u5efa\u8bae\u6839\u636e\u8be5\u76d1\u63a7\u7ed3\u679c\u8c03\u53c2\u3002"


def build_strategy_policy_stability_monitor(policy_effect_review: Mapping[str, object] | object) -> dict[str, object]:
    review = _as_mapping(policy_effect_review)
    rows = [dict(row) for row in _as_list(review.get("rows")) if isinstance(row, Mapping)]
    rows.sort(key=lambda row: _parse_policy_review_time(row.get("updated_at")) or datetime.min)
    evaluated = [
        row
        for row in rows
        if str(row.get("effect_status") or "") != "collecting"
        and row.get("allow_hit_rate") is not None
        and _safe_int(row.get("known_allow_count")) > 0
    ]
    status_counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("effect_status") or "unknown")
        status_counts[key] = status_counts.get(key, 0) + 1

    rates = [_safe_float(row.get("allow_hit_rate")) for row in evaluated]
    deltas = [rates[index] - rates[index - 1] for index in range(1, len(rates))]
    latest = rows[-1] if rows else {}
    latest_status = str(latest.get("effect_status") or "none")
    latest_delta = deltas[-1] if deltas else None
    avg_abs_delta = sum(abs(item) for item in deltas) / len(deltas) if deltas else 0.0
    cumulative_replay_net = sum(_safe_int(row.get("replay_guard_net")) for row in rows)

    negative_streak = 0
    effective_streak = 0
    for row in reversed(rows):
        status = str(row.get("effect_status") or "")
        if status == "negative" and effective_streak == 0:
            negative_streak += 1
            continue
        if status == "effective" and negative_streak == 0:
            effective_streak += 1
            continue
        break

    if not rows:
        stability_status = "none"
    elif len(evaluated) < 2:
        stability_status = "collecting"
    elif negative_streak >= 2 or (latest_status == "negative" and latest_delta is not None and latest_delta <= -0.05):
        stability_status = "regression"
    elif avg_abs_delta >= 0.12 and status_counts.get("negative", 0) and status_counts.get("effective", 0):
        stability_status = "volatile"
    elif effective_streak >= 2 or (latest_status == "effective" and latest_delta is not None and latest_delta >= 0):
        stability_status = "improving"
    elif latest_status == "effective":
        stability_status = "stable"
    elif latest_status == "negative":
        stability_status = "watch"
    else:
        stability_status = "collecting"

    week_groups: dict[str, dict[str, object]] = {}
    for row in rows:
        updated_at = _parse_policy_review_time(row.get("updated_at"))
        if updated_at is None:
            week_label = "\u672a\u77e5\u5468\u671f"
        else:
            iso = updated_at.isocalendar()
            week_label = f"{iso.year}-W{iso.week:02d}"
        bucket = week_groups.setdefault(
            week_label,
            {
                "week": week_label,
                "version_count": 0,
                "sample_count": 0,
                "known_allow_count": 0,
                "allow_hits": 0,
                "replay_guard_net": 0,
                "effective_count": 0,
                "negative_count": 0,
                "collecting_count": 0,
            },
        )
        bucket["version_count"] = _safe_int(bucket.get("version_count")) + 1
        bucket["sample_count"] = _safe_int(bucket.get("sample_count")) + _safe_int(row.get("sample_count"))
        known_allow_count = _safe_int(row.get("known_allow_count"))
        bucket["known_allow_count"] = _safe_int(bucket.get("known_allow_count")) + known_allow_count
        if row.get("allow_hit_rate") is not None and known_allow_count:
            bucket["allow_hits"] = _safe_int(bucket.get("allow_hits")) + round(_safe_float(row.get("allow_hit_rate")) * known_allow_count)
        bucket["replay_guard_net"] = _safe_int(bucket.get("replay_guard_net")) + _safe_int(row.get("replay_guard_net"))
        status = str(row.get("effect_status") or "collecting")
        if status == "effective":
            bucket["effective_count"] = _safe_int(bucket.get("effective_count")) + 1
        elif status == "negative":
            bucket["negative_count"] = _safe_int(bucket.get("negative_count")) + 1
        elif status == "collecting":
            bucket["collecting_count"] = _safe_int(bucket.get("collecting_count")) + 1

    weekly_rows: list[dict[str, object]] = []
    for bucket in week_groups.values():
        known_allow_count = _safe_int(bucket.get("known_allow_count"))
        allow_hits = _safe_int(bucket.get("allow_hits"))
        hit_rate = allow_hits / known_allow_count if known_allow_count else None
        weekly_rows.append(
            {
                **bucket,
                "allow_hit_rate": hit_rate,
                "allow_hit_rate_text": _pct(hit_rate) if hit_rate is not None else "-",
                "title": (
                    f"{bucket.get('week')} | \u7248\u672c {bucket.get('version_count')} | "
                    f"\u547d\u4e2d {allow_hits}/{known_allow_count if known_allow_count else 0}"
                ),
                "body": (
                    f"\u6837\u672c {_safe_int(bucket.get('sample_count'))} | "
                    f"Replay\u51c0\u503c {_safe_int(bucket.get('replay_guard_net')):+d} | "
                    f"\u6b63\u5411 {_safe_int(bucket.get('effective_count'))} / "
                    f"\u8d1f\u5411 {_safe_int(bucket.get('negative_count'))} / "
                    f"\u79ef\u7d2f {_safe_int(bucket.get('collecting_count'))}"
                ),
            }
        )
    weekly_rows.sort(key=lambda row: str(row.get("week") or ""), reverse=True)

    latest_rate_text = _pct(rates[-1]) if rates else "-"
    delta_text = f"{latest_delta:+.1%}" if latest_delta is not None else "-"
    label = _policy_effect_stability_label(stability_status)
    return {
        "status": stability_status,
        "label": label,
        "tone": _policy_effect_stability_tone(stability_status),
        "version_count": len(rows),
        "evaluated_count": len(evaluated),
        "latest_status": latest_status,
        "latest_delta": latest_delta,
        "latest_delta_text": delta_text,
        "avg_abs_delta": avg_abs_delta,
        "avg_abs_delta_text": f"{avg_abs_delta:.1%}" if deltas else "-",
        "latest_allow_hit_rate_text": latest_rate_text,
        "cumulative_replay_net": cumulative_replay_net,
        "negative_streak": negative_streak,
        "effective_streak": effective_streak,
        "status_counts": status_counts,
        "weekly_rows": weekly_rows[:8],
        "recommendation_text": _policy_effect_stability_recommendation(stability_status),
        "summary_text": (
            f"{label} | \u6700\u65b0\u547d\u4e2d {latest_rate_text} | "
            f"\u73af\u6bd4 {delta_text} | \u7248\u672c {len(rows)} | Replay\u7d2f\u8ba1 {cumulative_replay_net:+d}"
        ),
    }


def build_strategy_policy_tuning_guard(
    stability_monitor: Mapping[str, object] | object,
    tuning: Mapping[str, object] | object | None = None,
    *,
    source: str = "",
    trend_tuning_effect_review: Mapping[str, object] | object | None = None,
    rollback_effect_review: Mapping[str, object] | object | None = None,
    freeze_override_status: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    monitor = _as_mapping(stability_monitor)
    tuning_payload = _as_mapping(tuning)
    trend_effect = _as_mapping(trend_tuning_effect_review)
    rollback_effect = _as_mapping(rollback_effect_review)
    freeze_override = _as_mapping(freeze_override_status)
    status = str(monitor.get("status") or "none")
    trend_status = str(trend_effect.get("status") or "")
    rollback_status = str(rollback_effect.get("status") or "")
    override_status = str(freeze_override.get("status") or "")
    action = str(tuning_payload.get("action") or "").strip()
    source_label = {
        "strategy_allowlist_tuning": "\u653e\u884c\u95e8\u69db",
        "release_quality_trend": "\u8d8b\u52bf\u95e8\u63a7",
        "agent_replay_guard_tuning": "Replay Guard",
    }.get(source, "\u7b56\u7565\u8c03\u53c2")
    if rollback_status == "negative" and override_status == "overridden":
        decision = "confirm"
        label = "\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664"
        tone = "warning"
        reasons = [
            f"\u56de\u6eda\u4fee\u590d\u72b6\u6001: {rollback_effect.get('label', '-')}",
            str(rollback_effect.get("summary_text") or "-"),
            f"\u89e3\u9664\u51bb\u7ed3\u5ba1\u8ba1: {freeze_override.get('summary_text', '-')}",
            "\u56de\u6eda\u5931\u8d25\u4fe1\u53f7\u4ecd\u5b58\u5728\uff0c\u8c03\u53c2\u524d\u9700\u518d\u6b21\u4eba\u5de5\u786e\u8ba4\u3002",
        ]
    elif rollback_status == "negative":
        decision = "freeze"
        label = "\u56de\u6eda\u5931\u8d25\uff0c\u51bb\u7ed3\u8c03\u53c2"
        tone = "bad"
        reasons = [
            f"\u56de\u6eda\u4fee\u590d\u72b6\u6001: {rollback_effect.get('label', '-')}",
            str(rollback_effect.get("summary_text") or "-"),
            "\u56de\u6eda\u540e\u4ecd\u7136\u56de\u9000\uff0c\u7ee7\u7eed\u5199\u5165\u65b0\u53c2\u6570\u53ef\u80fd\u8ba9\u7b56\u7565\u5f80\u9519\u8bef\u65b9\u5411\u8fed\u4ee3\u3002",
            "\u5148\u590d\u6838\u56de\u6eda\u540e\u9519\u8bef\u6837\u672c\uff0c\u6216\u7531\u4eba\u5de5\u786e\u8ba4\u89e3\u9664\u51bb\u7ed3\u540e\u518d\u8c03\u53c2\u3002",
        ]
        recommendation = str(rollback_effect.get("recommendation_text") or "").strip()
        if recommendation:
            reasons.append(recommendation)
    elif trend_status == "negative":
        decision = "block"
        label = "\u95e8\u63a7\u56de\u9000\uff0c\u6682\u505c\u8c03\u53c2"
        tone = "bad"
        reasons = [
            f"\u95e8\u63a7\u751f\u6548\u72b6\u6001: {trend_effect.get('label', '-')}",
            str(trend_effect.get("summary_text") or "-"),
            "\u95e8\u63a7\u5e94\u7528\u540e\u547d\u4e2d\u56de\u9000\uff0c\u7ee7\u7eed\u5199\u5165\u65b0\u6536\u7d27\u53c2\u6570\u53ef\u80fd\u653e\u5927\u8bef\u5dee\u3002",
            f"\u56de\u6eda\u5019\u9009\u7248\u672c: {trend_effect.get('rollback_candidate_version_id', '-')}",
        ]
        recommendation = str(trend_effect.get("recommendation_text") or "").strip()
        if recommendation:
            reasons.append(recommendation)
    elif status in {"regression", "volatile"}:
        decision = "block"
        label = "\u6682\u505c\u81ea\u52a8\u8c03\u53c2"
        tone = "bad"
        reasons = [
            f"\u7248\u672c\u7a33\u5b9a\u72b6\u6001: {monitor.get('label', '-')}",
            "\u6700\u65b0\u53c2\u6570\u6548\u679c\u5c1a\u672a\u7a33\u5b9a\uff0c\u7ee7\u7eed\u81ea\u52a8\u5199\u5165\u65b0\u53c2\u6570\u53ef\u80fd\u653e\u5927\u56de\u9000\u3002",
            "\u5efa\u8bae\u5148\u67e5\u770b\u751f\u6548\u8be6\u60c5\uff0c\u590d\u6838\u8d1f\u5411\u6837\u672c\uff0c\u5fc5\u8981\u65f6\u56de\u6eda\u4e0a\u4e00\u7248\u3002",
        ]
    elif status == "watch" or trend_status == "watch":
        decision = "confirm"
        label = "\u9700\u4eba\u5de5\u786e\u8ba4"
        tone = "warning"
        reasons = [
            f"\u7248\u672c\u7a33\u5b9a\u72b6\u6001: {monitor.get('label', '-')}",
            "\u5df2\u6709\u8d1f\u5411\u4fe1\u53f7\uff0c\u8c03\u53c2\u524d\u9700\u786e\u8ba4\u6837\u672c\u4e0d\u662f\u77ed\u671f\u566a\u58f0\u3002",
        ]
        if trend_status == "watch":
            reasons.append(f"\u95e8\u63a7\u751f\u6548\u72b6\u6001: {trend_effect.get('summary_text', '-')}")
    else:
        decision = "allow"
        label = "\u5141\u8bb8\u8c03\u53c2"
        tone = "good" if status in {"improving", "stable"} else "neutral"
        reasons = [f"\u7248\u672c\u7a33\u5b9a\u72b6\u6001: {monitor.get('label', '-')}"]
    if action:
        reasons.append(f"\u5f85\u5e94\u7528\u52a8\u4f5c: {action}")
    body = "\n".join(str(item) for item in reasons if item)
    return {
        "decision": decision,
        "allowed": decision in {"allow", "confirm"},
        "confirm_required": decision == "confirm",
        "label": label,
        "tone": tone,
        "source": source,
        "source_label": source_label,
        "status": status,
        "trend_effect_status": trend_status or "-",
        "trend_effect_label": str(trend_effect.get("label") or "-"),
        "trend_effect_summary": str(trend_effect.get("summary_text") or "-"),
        "rollback_effect_status": rollback_status or "-",
        "rollback_effect_label": str(rollback_effect.get("label") or "-"),
        "rollback_effect_summary": str(rollback_effect.get("summary_text") or "-"),
        "freeze_override_status": override_status or "-",
        "freeze_override_label": str(freeze_override.get("label") or "-"),
        "freeze_override_summary": str(freeze_override.get("summary_text") or "-"),
        "rollback_recommended": trend_status == "negative" or rollback_status == "negative",
        "rollback_candidate_version_id": str(
            rollback_effect.get("rolled_back_version_id")
            or trend_effect.get("rollback_candidate_version_id")
            or "-"
        ),
        "freeze_active": decision == "freeze",
        "freeze_override_active": override_status == "overridden",
        "action": action or "-",
        "reasons": reasons,
        "body": body,
        "summary_text": (
            f"{source_label}: {label} | "
            f"{rollback_effect.get('summary_text') if rollback_status == 'negative' else trend_effect.get('summary_text') if trend_status == 'negative' else monitor.get('summary_text', '-')}"
        ),
    }


POLICY_ROLLBACK_FIELD_LABELS: tuple[tuple[str, str, str], ...] = (
    ("min_confidence", "\u6700\u4f4e\u7f6e\u4fe1", "float"),
    ("block_confidence", "\u963b\u65ad\u7f6e\u4fe1", "float"),
    ("active_strategy_min", "\u9ad8\u51c6\u7b56\u7565\u6570", "int"),
    ("medium_risk_allowed", "\u4e2d\u98ce\u9669\u653e\u884c", "bool"),
    ("high_risk_allowed", "\u9ad8\u98ce\u9669\u653e\u884c", "bool"),
    ("agent_replay_guard_enabled", "Replay Guard", "bool"),
    ("agent_replay_min_samples", "Replay\u6700\u5c0f\u6837\u672c", "int"),
    ("agent_replay_prediction_miss_threshold", "Replay 1X2\u5931\u8bef\u7ebf", "float"),
    ("agent_replay_handicap_miss_threshold", "Replay\u8ba9\u7403\u5931\u8bef\u7ebf", "float"),
)


def _policy_value_text(value: object, value_type: str) -> str:
    if value_type == "bool":
        return "ON" if bool(value) else "OFF"
    if value_type == "float":
        return f"{_safe_float(value):.2f}"
    if value_type == "int":
        return str(_safe_int(value))
    return _text(value, "-")


def _policy_values_equal(left: object, right: object, value_type: str) -> bool:
    if value_type == "bool":
        return bool(left) == bool(right)
    if value_type == "float":
        return round(_safe_float(left), 4) == round(_safe_float(right), 4)
    if value_type == "int":
        return _safe_int(left) == _safe_int(right)
    return _text(left, "") == _text(right, "")


def _policy_direction_text(key: str, current: object, target: object, value_type: str) -> str:
    if _policy_values_equal(current, target, value_type):
        return "\u4e0d\u53d8"
    if value_type == "bool":
        if bool(target):
            return "\u653e\u5bbd"
        return "\u6536\u7d27"
    current_value = _safe_float(current)
    target_value = _safe_float(target)
    stricter_when_higher = {
        "min_confidence",
        "active_strategy_min",
        "agent_replay_min_samples",
    }
    stricter_when_lower = {
        "block_confidence",
        "agent_replay_prediction_miss_threshold",
        "agent_replay_handicap_miss_threshold",
    }
    if key in stricter_when_higher:
        return "\u6536\u7d27" if target_value > current_value else "\u653e\u5bbd"
    if key in stricter_when_lower:
        return "\u6536\u7d27" if target_value < current_value else "\u653e\u5bbd"
    return "\u8c03\u6574"


def _policy_effect_row_by_version(policy_effect_review: Mapping[str, object], version_id: object) -> dict[str, object]:
    key = _text(version_id, "")
    if not key:
        return {}
    for row in _as_list(policy_effect_review.get("all_rows")) or _as_list(policy_effect_review.get("rows")):
        if isinstance(row, Mapping) and _text(row.get("version_id"), "") == key:
            return dict(row)
    return {}


def _previous_policy_effect_row(policy_effect_review: Mapping[str, object], latest_version_id: object) -> dict[str, object]:
    rows = [dict(row) for row in (_as_list(policy_effect_review.get("all_rows")) or _as_list(policy_effect_review.get("rows"))) if isinstance(row, Mapping)]
    rows.sort(
        key=lambda row: (
            _parse_policy_review_time(row.get("updated_at")) or datetime.min,
            str(row.get("version_id") or ""),
        ),
        reverse=True,
    )
    key = _text(latest_version_id, "")
    for index, row in enumerate(rows):
        if _text(row.get("version_id"), "") == key:
            if index + 1 < len(rows):
                return rows[index + 1]
            return {}
    return rows[1] if len(rows) > 1 else {}


def _policy_effect_summary_for_preview(row: Mapping[str, object]) -> dict[str, object]:
    if not row:
        return {
            "version_id": "-",
            "effect_label": "-",
            "allow_hit_rate_text": "-",
            "known_allow_count": 0,
            "sample_count": 0,
            "replay_guard_net": 0,
            "summary_text": "-",
        }
    return {
        "version_id": row.get("version_id", "-"),
        "effect_label": row.get("effect_label", "-"),
        "allow_hit_rate_text": row.get("allow_hit_rate_text", "-"),
        "known_allow_count": _safe_int(row.get("known_allow_count")),
        "sample_count": _safe_int(row.get("sample_count")),
        "replay_guard_net": _safe_int(row.get("replay_guard_net")),
        "summary_text": str(row.get("body") or "-"),
    }


def build_strategy_policy_rollback_preview(
    latest_history: Mapping[str, object] | object,
    current_policy: Mapping[str, object] | object | None = None,
    policy_effect_review: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    latest = _as_mapping(latest_history)
    current = _as_mapping(current_policy) or _as_mapping(latest.get("policy"))
    target = _as_mapping(latest.get("previous_policy"))
    if not latest:
        return {
            "available": False,
            "reason": "\u5c1a\u65e0\u53ef\u56de\u6eda\u7684\u53c2\u6570\u7248\u672c\u3002",
            "summary_text": "\u5c1a\u65e0\u53ef\u56de\u6eda\u7684\u53c2\u6570\u7248\u672c\u3002",
            "rows": [],
            "effect_rows": [],
            "confirm_text": "\u5c1a\u65e0\u53ef\u56de\u6eda\u7684\u53c2\u6570\u7248\u672c\u3002",
        }
    if not target:
        return {
            "available": False,
            "reason": "\u6700\u8fd1\u4e00\u6b21\u8c03\u53c2\u6ca1\u6709\u53ef\u6062\u590d\u7684\u4e0a\u4e00\u7248\u53c2\u6570\u3002",
            "summary_text": "\u6700\u8fd1\u4e00\u6b21\u8c03\u53c2\u6ca1\u6709\u53ef\u6062\u590d\u7684\u4e0a\u4e00\u7248\u53c2\u6570\u3002",
            "rows": [],
            "effect_rows": [],
            "confirm_text": "\u6700\u8fd1\u4e00\u6b21\u8c03\u53c2\u6ca1\u6709\u53ef\u6062\u590d\u7684\u4e0a\u4e00\u7248\u53c2\u6570\u3002",
        }

    rows: list[dict[str, object]] = []
    changed_count = 0
    loosen_count = 0
    tighten_count = 0
    for key, label, value_type in POLICY_ROLLBACK_FIELD_LABELS:
        current_value = current.get(key)
        target_value = target.get(key)
        changed = not _policy_values_equal(current_value, target_value, value_type)
        direction = _policy_direction_text(key, current_value, target_value, value_type)
        if changed:
            changed_count += 1
            if direction == "\u653e\u5bbd":
                loosen_count += 1
            elif direction == "\u6536\u7d27":
                tighten_count += 1
        rows.append(
            {
                "key": key,
                "label": label,
                "current_value": current_value,
                "target_value": target_value,
                "current_text": _policy_value_text(current_value, value_type),
                "target_text": _policy_value_text(target_value, value_type),
                "changed": changed,
                "direction": direction,
                "summary": f"{label}: {_policy_value_text(current_value, value_type)} -> {_policy_value_text(target_value, value_type)} ({direction})",
            }
        )

    review = _as_mapping(policy_effect_review)
    latest_effect = _policy_effect_summary_for_preview(_policy_effect_row_by_version(review, latest.get("version_id")))
    previous_effect = _policy_effect_summary_for_preview(_previous_policy_effect_row(review, latest.get("version_id")))
    effect_rows = [
        {
            "label": "\u5f53\u524d\u7248\u672c\u751f\u6548",
            "version_id": latest_effect.get("version_id", "-"),
            "summary": (
                f"{latest_effect.get('effect_label', '-')} | \u653e\u884c\u547d\u4e2d {latest_effect.get('allow_hit_rate_text', '-')} | "
                f"\u6837\u672c {latest_effect.get('known_allow_count', 0)}/{latest_effect.get('sample_count', 0)} | "
                f"Replay {int(latest_effect.get('replay_guard_net', 0) or 0):+d}"
            ),
        },
        {
            "label": "\u56de\u6eda\u5019\u9009\u53c2\u7167",
            "version_id": previous_effect.get("version_id", "-"),
            "summary": (
                f"{previous_effect.get('effect_label', '-')} | \u653e\u884c\u547d\u4e2d {previous_effect.get('allow_hit_rate_text', '-')} | "
                f"\u6837\u672c {previous_effect.get('known_allow_count', 0)}/{previous_effect.get('sample_count', 0)} | "
                f"Replay {int(previous_effect.get('replay_guard_net', 0) or 0):+d}"
            ),
        },
    ]
    impact_text = (
        f"\u53d8\u66f4 {changed_count} \u9879 | \u56de\u6eda\u540e\u653e\u5bbd {loosen_count} \u9879 / \u6536\u7d27 {tighten_count} \u9879"
    )
    summary_text = (
        f"\u56de\u6eda\u9884\u89c8 | \u5f53\u524d {latest.get('version_id', '-')} | "
        f"\u6765\u6e90 {latest.get('source', '-')} | {impact_text}"
    )
    changed_lines = [str(row.get("summary") or "-") for row in rows if bool(row.get("changed"))]
    if not changed_lines:
        changed_lines = ["\u76ee\u6807\u53c2\u6570\u4e0e\u5f53\u524d\u53c2\u6570\u4e00\u81f4\uff0c\u56de\u6eda\u4e0d\u4f1a\u4ea7\u751f\u95e8\u69db\u53d8\u5316\u3002"]
    effect_lines = [f"{row.get('label')}: {row.get('summary')}" for row in effect_rows]
    confirm_text = (
        f"\u5c06\u56de\u6eda\u6700\u8fd1\u4e00\u6b21\u8c03\u53c2:\n\n"
        f"\u7248\u672c: {latest.get('version_id', '-')}\n"
        f"\u6765\u6e90: {latest.get('source', '-')}\n"
        f"\u65f6\u95f4: {latest.get('updated_at', '-')}\n\n"
        f"\u53c2\u6570\u5dee\u5f02:\n" + "\n".join(changed_lines[:9]) + "\n\n"
        f"\u751f\u6548\u5bf9\u6bd4:\n" + "\n".join(effect_lines) + "\n\n"
        f"\u5f71\u54cd\u8303\u56f4: {impact_text}\n\n"
        "\u786e\u8ba4\u540e\uff0c\u540e\u7eed\u5206\u6790\u4f1a\u6062\u590d\u4e3a\u8be5\u6b21\u8c03\u53c2\u524d\u7684\u51c6\u5165\u53c2\u6570\u3002"
    )
    return {
        "available": True,
        "reason": "ok",
        "version_id": latest.get("version_id", "-"),
        "source": latest.get("source", "-"),
        "updated_at": latest.get("updated_at", "-"),
        "changed_count": changed_count,
        "loosen_count": loosen_count,
        "tighten_count": tighten_count,
        "impact_text": impact_text,
        "summary_text": summary_text,
        "rows": rows,
        "effect_rows": effect_rows,
        "confirm_text": confirm_text,
    }


def build_strategy_policy_effect_review(
    policy_history: Sequence[Mapping[str, object]] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 5,
) -> dict[str, object]:
    history_items = [item for item in policy_history if isinstance(item, Mapping)] if isinstance(policy_history, Sequence) else []
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    parsed_history: list[dict[str, object]] = []
    for item in history_items:
        updated_at = _parse_policy_review_time(item.get("updated_at"))
        if updated_at is None:
            continue
        parsed_history.append({**dict(item), "_updated_dt": updated_at})
    parsed_history.sort(key=lambda item: item["_updated_dt"])
    rows: list[dict[str, object]] = []
    previous_hit_rate: float | None = None
    previous_replay_net: int | None = None
    for index, item in enumerate(parsed_history):
        start = item["_updated_dt"]
        end = parsed_history[index + 1]["_updated_dt"] if index + 1 < len(parsed_history) else None
        window_items = []
        for settlement in settlement_items:
            settled_at = _settlement_review_time(settlement)
            if settled_at is None or settled_at < start:
                continue
            if end is not None and settled_at >= end:
                continue
            window_items.append(settlement)
        allowed = [settlement for settlement in window_items if str(settlement.get("strategy_admission_decision") or "").strip() == "allow"]
        known_allowed = [settlement for settlement in allowed if settlement.get("is_correct") is not None]
        allow_hits = sum(1 for settlement in known_allowed if settlement.get("is_correct") is True)
        allow_misses = sum(1 for settlement in known_allowed if settlement.get("is_correct") is False)
        allow_hit_rate = allow_hits / len(known_allowed) if known_allowed else None
        replay_summary = build_agent_replay_downgrade_backtest_summary(window_items)
        sample_rows = _policy_effect_settlement_rows(window_items)
        replay_net = _safe_int(replay_summary.get("net"))
        sample_count = len(known_allowed)
        if sample_count < 3 and _safe_int(replay_summary.get("sample_count")) < 3:
            effect_status = "collecting"
            effect_label = "\u6837\u672c\u79ef\u7d2f\u4e2d"
            tone = "neutral"
        else:
            hit_delta = None if previous_hit_rate is None or allow_hit_rate is None else allow_hit_rate - previous_hit_rate
            replay_delta = None if previous_replay_net is None else replay_net - previous_replay_net
            if (hit_delta is not None and hit_delta >= 0.05) or replay_net > 0 or (replay_delta is not None and replay_delta > 0):
                effect_status = "effective"
                effect_label = "\u6b63\u5411\u751f\u6548"
                tone = "good"
            elif (hit_delta is not None and hit_delta <= -0.05) or replay_net < 0:
                effect_status = "negative"
                effect_label = "\u9700\u8981\u590d\u6838"
                tone = "bad"
            else:
                effect_status = "flat"
                effect_label = "\u65e0\u660e\u663e\u53d8\u5316"
                tone = "warning"
        previous_hit_rate = allow_hit_rate if allow_hit_rate is not None else previous_hit_rate
        previous_replay_net = replay_net
        diagnostics = _policy_effect_negative_diagnostics(
            sample_rows,
            effect_status=effect_status,
            allow_hit_rate=allow_hit_rate,
            replay_net=replay_net,
        )
        source = _text(item.get("source") or item.get("reason"), "-")
        version_id = _text(item.get("version_id"), "-")
        title = f"{effect_label} | {source} | {item.get('updated_at', '-')}"
        body = (
            f"\u7248\u672c {version_id} | \u533a\u95f4\u6837\u672c {len(window_items)} | "
            f"\u653e\u884c {allow_hits}/{len(known_allowed)} ({_pct(allow_hit_rate) if allow_hit_rate is not None else '-'}) | "
            f"\u653e\u884c\u9519\u8bef {allow_misses} | Replay Guard \u51c0\u503c {replay_net:+d} | "
            f"{diagnostics.get('action_label', '-')}"
        )
        rows.append(
            {
                "version_id": version_id,
                "updated_at": item.get("updated_at", "-"),
                "source": source,
                "sample_count": len(window_items),
                "allow_count": len(allowed),
                "allow_hits": allow_hits,
                "known_allow_count": len(known_allowed),
                "allow_hit_rate": allow_hit_rate,
                "allow_hit_rate_text": _pct(allow_hit_rate) if allow_hit_rate is not None else "-",
                "allow_misses": allow_misses,
                "replay_guard_net": replay_net,
                "sample_rows": sample_rows,
                "sample_rows_total": len(window_items),
                "negative_diagnostics": diagnostics,
                "top_negative_rows": diagnostics.get("top_negative_rows", []),
                "rollback_recommended": bool(diagnostics.get("rollback_recommended")),
                "effect_status": effect_status,
                "effect_label": effect_label,
                "tone": tone,
                "title": title,
                "body": body,
            }
        )
    rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    latest = rows[0] if rows else {}
    status_counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("effect_status") or "unknown")
        status_counts[key] = status_counts.get(key, 0) + 1
    full_rows = list(rows)
    stability_monitor = build_strategy_policy_stability_monitor({"rows": full_rows, "history_count": len(parsed_history)})
    return {
        "history_count": len(parsed_history),
        "rows": rows[: max(0, int(limit))],
        "all_rows": full_rows,
        "latest_status": latest.get("effect_status", "none") if latest else "none",
        "latest_label": latest.get("effect_label", "\u6682\u65e0\u7248\u672c") if latest else "\u6682\u65e0\u7248\u672c",
        "status_counts": status_counts,
        "stability_monitor": stability_monitor,
        "summary_text": (
            f"\u7248\u672c {len(parsed_history)} | \u6700\u65b0 {latest.get('effect_label', '-') if latest else '-'} | "
            f"\u6b63\u5411 {status_counts.get('effective', 0)} / \u590d\u6838 {status_counts.get('negative', 0)}"
        ),
    }


def _policy_gate_source_matches(source: object, target_sources: Sequence[str]) -> bool:
    key = str(source or "").strip().lower()
    if not key:
        return False
    normalized_targets = [str(item or "").strip().lower() for item in target_sources]
    return any(target and target in key for target in normalized_targets)


def _policy_effect_rate_parts(row: Mapping[str, object]) -> tuple[int, int, float | None]:
    known = _safe_int(row.get("known_allow_count"))
    raw_rate = row.get("allow_hit_rate")
    rate = _safe_float(raw_rate) if raw_rate is not None else None
    if row.get("allow_hits") is not None:
        hits = _safe_int(row.get("allow_hits"))
    elif rate is not None and known:
        hits = round(rate * known)
    else:
        hits = 0
    if rate is None and known:
        rate = hits / known
    return hits, known, rate


def _trend_tuning_effect_label(status: str) -> str:
    labels = {
        "effective": "\u95e8\u63a7\u6539\u5584\u751f\u6548",
        "negative": "\u95e8\u63a7\u540e\u56de\u9000",
        "watch": "\u95e8\u63a7\u540e\u89c2\u5bdf",
        "collecting": "\u95e8\u63a7\u6837\u672c\u79ef\u7d2f\u4e2d",
        "none": "\u6682\u65e0\u95e8\u63a7\u7248\u672c",
    }
    return labels.get(status, labels["watch"])


def _trend_tuning_effect_tone(status: str) -> str:
    if status == "effective":
        return "good"
    if status == "negative":
        return "bad"
    if status == "watch":
        return "warning"
    return "neutral"


def build_strategy_trend_tuning_effect_review(
    policy_effect_review: Mapping[str, object] | object,
    *,
    target_sources: Sequence[str] = ("release_quality_trend", "strategy_allowlist_tuning"),
    min_known_samples: int = 3,
    min_delta: float = 0.05,
    min_watch_hit_rate: float = 0.55,
    limit: int = 5,
) -> dict[str, object]:
    review = _as_mapping(policy_effect_review)
    row_source = _as_list(review.get("all_rows")) or _as_list(review.get("rows"))
    rows = [dict(row) for row in row_source if isinstance(row, Mapping)]
    rows.sort(key=lambda row: (_parse_policy_review_time(row.get("updated_at")) or datetime.min, str(row.get("version_id") or "")))
    target_indexes = [
        (index, row)
        for index, row in enumerate(rows)
        if _policy_gate_source_matches(row.get("source"), target_sources)
    ]
    if not target_indexes:
        label = _trend_tuning_effect_label("collecting")
        return {
            "status": "collecting",
            "label": label,
            "tone": "neutral",
            "summary_text": f"{label} | \u5c1a\u672a\u627e\u5230\u653e\u884c\u95e8\u69db\u6216\u8d8b\u52bf\u95e8\u63a7\u7248\u672c\u3002",
            "recommendation_text": "\u7b49\u5f85\u95e8\u63a7\u5efa\u8bae\u5e94\u7528\u4ee5\u53ca\u540e\u7eed\u8d5b\u679c\u56de\u6536\u540e\u518d\u5224\u5b9a\u6548\u679c\u3002",
            "latest_version_id": "-",
            "latest_source": "-",
            "latest_updated_at": "-",
            "rollback_recommended": False,
            "rollback_candidate_version_id": "-",
            "post_known_count": 0,
            "pre_known_count": 0,
            "post_allow_hit_rate": None,
            "pre_allow_hit_rate": None,
            "post_allow_hit_rate_text": "-",
            "pre_allow_hit_rate_text": "-",
            "allow_hit_rate_delta": None,
            "allow_hit_rate_delta_text": "-",
            "metrics": [],
            "rows": [],
        }

    latest_index, latest = target_indexes[-1]
    previous = rows[latest_index - 1] if latest_index > 0 else {}
    post_hits, post_known, post_rate = _policy_effect_rate_parts(latest)
    pre_hits, pre_known, pre_rate = _policy_effect_rate_parts(previous) if previous else (0, 0, None)
    delta = post_rate - pre_rate if post_rate is not None and pre_rate is not None else None

    if post_known < max(1, int(min_known_samples)) or post_rate is None or pre_rate is None:
        status = "collecting"
    elif delta is not None and delta >= abs(float(min_delta)):
        status = "effective"
    elif delta is not None and delta <= -abs(float(min_delta)):
        status = "negative"
    elif post_rate < float(min_watch_hit_rate):
        status = "watch"
    else:
        status = "watch"
    label = _trend_tuning_effect_label(status)
    tone = _trend_tuning_effect_tone(status)
    delta_text = _pct(delta) if delta is not None else "-"
    pre_rate_text = _pct(pre_rate) if pre_rate is not None else "-"
    post_rate_text = _pct(post_rate) if post_rate is not None else "-"

    if status == "effective":
        recommendation = "\u95e8\u63a7\u5e94\u7528\u540e\u547d\u4e2d\u6709\u6539\u5584\uff0c\u7ee7\u7eed\u6309\u5f53\u524d\u95e8\u69db\u6536\u96c6\u6837\u672c\u3002"
    elif status == "negative":
        recommendation = "\u95e8\u63a7\u5e94\u7528\u540e\u547d\u4e2d\u56de\u9000\uff0c\u4f18\u5148\u590d\u6838\u653e\u884c\u9519\u8bef\u6837\u672c\uff0c\u5fc5\u8981\u65f6\u56de\u6eda\u4e0a\u4e00\u7248\u3002"
    elif status == "watch":
        recommendation = "\u95e8\u63a7\u5e94\u7528\u540e\u672a\u51fa\u73b0\u8db3\u591f\u660e\u786e\u6539\u5584\uff0c\u6682\u65f6\u7ef4\u6301\u89c2\u5bdf\u3002"
    else:
        recommendation = "\u6837\u672c\u6216\u5bf9\u7167\u7248\u672c\u4e0d\u8db3\uff0c\u6682\u4e0d\u5224\u5b9a\u95e8\u63a7\u751f\u6548\u3002"

    detail_rows: list[dict[str, object]] = []
    for _index, row in reversed(target_indexes[-max(1, int(limit)) :]):
        hits, known, rate = _policy_effect_rate_parts(row)
        detail_rows.append(
            {
                "title": f"{row.get('updated_at', '-')} | {row.get('source', '-')} | {row.get('effect_label', '-')}",
                "body": (
                    f"\u7248\u672c {row.get('version_id', '-')} | "
                    f"\u653e\u884c\u547d\u4e2d {hits}/{known} ({_pct(rate) if rate is not None else '-'}) | "
                    f"\u6837\u672c {_safe_int(row.get('sample_count'))} | Replay\u51c0\u503c {_safe_int(row.get('replay_guard_net')):+d}"
                ),
                "version_id": row.get("version_id", "-"),
                "updated_at": row.get("updated_at", "-"),
                "source": row.get("source", "-"),
                "known_allow_count": known,
                "allow_hits": hits,
                "allow_hit_rate": rate,
                "allow_hit_rate_text": _pct(rate) if rate is not None else "-",
                "effect_status": row.get("effect_status", "-"),
                "effect_label": row.get("effect_label", "-"),
            }
        )

    metrics = [
        {"label": "\u751f\u6548\u72b6\u6001", "value": label, "tone": tone},
        {"label": "\u540e\u7eed\u547d\u4e2d", "value": f"{post_hits}/{post_known} ({post_rate_text})", "tone": tone if post_known else "neutral"},
        {"label": "\u524d\u5e8f\u547d\u4e2d", "value": f"{pre_hits}/{pre_known} ({pre_rate_text})", "tone": "neutral"},
        {"label": "\u547d\u4e2d\u53d8\u5316", "value": delta_text, "tone": "good" if delta is not None and delta >= 0 else "bad" if delta is not None else "neutral"},
    ]
    summary_text = (
        f"{label} | \u6765\u6e90 {latest.get('source', '-')} | "
        f"\u540e\u7eed {post_hits}/{post_known} ({post_rate_text}) | "
        f"\u524d\u5e8f {pre_hits}/{pre_known} ({pre_rate_text}) | "
        f"\u53d8\u5316 {delta_text}"
    )
    return {
        "status": status,
        "label": label,
        "tone": tone,
        "summary_text": summary_text,
        "recommendation_text": recommendation,
        "latest_version_id": latest.get("version_id", "-"),
        "latest_source": latest.get("source", "-"),
        "latest_updated_at": latest.get("updated_at", "-"),
        "previous_version_id": previous.get("version_id", "-") if previous else "-",
        "rollback_recommended": status == "negative",
        "rollback_candidate_version_id": previous.get("version_id", "-") if status == "negative" and previous else "-",
        "post_known_count": post_known,
        "pre_known_count": pre_known,
        "post_allow_hits": post_hits,
        "pre_allow_hits": pre_hits,
        "post_allow_hit_rate": post_rate,
        "pre_allow_hit_rate": pre_rate,
        "post_allow_hit_rate_text": post_rate_text,
        "pre_allow_hit_rate_text": pre_rate_text,
        "allow_hit_rate_delta": delta,
        "allow_hit_rate_delta_text": delta_text,
        "min_known_samples": max(1, int(min_known_samples)),
        "metrics": metrics,
        "rows": detail_rows,
    }


def _policy_rollback_source_version(source: object) -> str:
    text = _text(source, "").strip()
    if not text:
        return ""
    prefix = "policy_rollback:"
    if text.lower().startswith(prefix):
        return text[len(prefix) :].strip()
    return ""


def _policy_freeze_override_source_version(source: object) -> str:
    text = _text(source, "").strip()
    if not text:
        return ""
    prefix = "policy_freeze_override:"
    if text.lower().startswith(prefix):
        return text[len(prefix) :].strip()
    return ""


def build_strategy_policy_freeze_override_status(
    policy_history: Sequence[Mapping[str, object]] | object,
    rollback_effect_review: Mapping[str, object] | object,
) -> dict[str, object]:
    rollback_effect = _as_mapping(rollback_effect_review)
    rollback_status = str(rollback_effect.get("status") or "")
    rollback_version = _text(rollback_effect.get("latest_version_id"), "")
    rollback_updated_at = _parse_policy_review_time(rollback_effect.get("latest_updated_at")) or datetime.min
    if rollback_status != "negative":
        return {
            "status": "inactive",
            "label": "\u65e0\u9700\u89e3\u9664\u51bb\u7ed3",
            "tone": "neutral",
            "override_active": False,
            "rollback_version_id": rollback_version or "-",
            "override_version_id": "-",
            "summary_text": "\u5f53\u524d\u6ca1\u6709\u56de\u6eda\u5931\u8d25\u5bfc\u81f4\u7684\u8c03\u53c2\u51bb\u7ed3\u3002",
        }

    history_items = [dict(item) for item in policy_history if isinstance(item, Mapping)] if isinstance(policy_history, Sequence) else []
    overrides: list[dict[str, object]] = []
    for item in history_items:
        source = str(item.get("source") or "")
        if not source.lower().startswith("policy_freeze_override"):
            continue
        source_version = _policy_freeze_override_source_version(source)
        updated_at = _parse_policy_review_time(item.get("updated_at")) or datetime.min
        if source_version and rollback_version and source_version != rollback_version:
            continue
        if updated_at < rollback_updated_at:
            continue
        overrides.append({**item, "_updated_dt": updated_at, "_source_version": source_version})
    overrides.sort(key=lambda item: (_parse_policy_review_time(item.get("updated_at")) or datetime.min, str(item.get("version_id") or "")), reverse=True)
    if overrides:
        latest = overrides[0]
        label = "\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664"
        summary_text = (
            f"{label} | \u56de\u6eda {rollback_version or '-'} | "
            f"\u5ba1\u8ba1 {latest.get('version_id', '-')} | {latest.get('updated_at', '-')}"
        )
        return {
            "status": "overridden",
            "label": label,
            "tone": "warning",
            "override_active": True,
            "rollback_version_id": rollback_version or "-",
            "override_version_id": latest.get("version_id", "-"),
            "override_source": latest.get("source", "-"),
            "override_updated_at": latest.get("updated_at", "-"),
            "summary_text": summary_text,
        }

    label = "\u8c03\u53c2\u51bb\u7ed3\u4e2d"
    return {
        "status": "frozen",
        "label": label,
        "tone": "bad",
        "override_active": False,
        "rollback_version_id": rollback_version or "-",
        "override_version_id": "-",
        "summary_text": f"{label} | \u56de\u6eda {rollback_version or '-'} \u4fee\u590d\u5931\u8d25\uff0c\u9700\u4eba\u5de5\u590d\u6838\u540e\u89e3\u9664\u3002",
    }


def _policy_rollback_effect_label(status: str) -> str:
    labels = {
        "effective": "\u56de\u6eda\u4fee\u590d\u751f\u6548",
        "negative": "\u56de\u6eda\u540e\u4ecd\u56de\u9000",
        "watch": "\u56de\u6eda\u540e\u89c2\u5bdf",
        "collecting": "\u56de\u6eda\u6837\u672c\u79ef\u7d2f\u4e2d",
        "none": "\u6682\u65e0\u56de\u6eda\u7248\u672c",
    }
    return labels.get(status, labels["watch"])


def _policy_rollback_effect_tone(status: str) -> str:
    if status == "effective":
        return "good"
    if status == "negative":
        return "bad"
    if status == "watch":
        return "warning"
    return "neutral"


def build_strategy_policy_rollback_effect_review(
    policy_effect_review: Mapping[str, object] | object,
    *,
    min_known_samples: int = 3,
    min_delta: float = 0.05,
    limit: int = 5,
) -> dict[str, object]:
    review = _as_mapping(policy_effect_review)
    row_source = _as_list(review.get("all_rows")) or _as_list(review.get("rows"))
    rows = [dict(row) for row in row_source if isinstance(row, Mapping)]
    rows.sort(key=lambda row: (_parse_policy_review_time(row.get("updated_at")) or datetime.min, str(row.get("version_id") or "")))
    rollback_indexes = [
        (index, row)
        for index, row in enumerate(rows)
        if str(row.get("source") or "").strip().lower().startswith("policy_rollback")
    ]
    if not rollback_indexes:
        label = _policy_rollback_effect_label("none")
        return {
            "status": "collecting",
            "label": label,
            "tone": "neutral",
            "summary_text": f"{label} | \u5c1a\u672a\u627e\u5230\u7b56\u7565\u53c2\u6570\u56de\u6eda\u7248\u672c\u3002",
            "recommendation_text": "\u56de\u6eda\u6267\u884c\u540e\uff0c\u5b8c\u6210\u540e\u7eed\u8d5b\u679c\u56de\u6536\u5373\u53ef\u8bc4\u4f30\u4fee\u590d\u6548\u679c\u3002",
            "latest_version_id": "-",
            "rolled_back_version_id": "-",
            "post_known_count": 0,
            "rolled_back_known_count": 0,
            "post_allow_hit_rate": None,
            "rolled_back_allow_hit_rate": None,
            "allow_hit_rate_delta": None,
            "allow_hit_rate_delta_text": "-",
            "metrics": [],
            "rows": [],
        }

    latest_index, rollback_row = rollback_indexes[-1]
    source_version_id = _policy_rollback_source_version(rollback_row.get("source"))
    rolled_back_row = _policy_effect_row_by_version(review, source_version_id) if source_version_id else {}
    if not rolled_back_row and latest_index > 0:
        rolled_back_row = rows[latest_index - 1]
    post_hits, post_known, post_rate = _policy_effect_rate_parts(rollback_row)
    prior_hits, prior_known, prior_rate = _policy_effect_rate_parts(rolled_back_row)
    delta = post_rate - prior_rate if post_rate is not None and prior_rate is not None else None
    prior_status = str(rolled_back_row.get("effect_status") or "")
    rollback_status = str(rollback_row.get("effect_status") or "")

    if post_known < max(1, int(min_known_samples)) or post_rate is None or prior_rate is None:
        status = "collecting"
    elif delta is not None and delta >= abs(float(min_delta)):
        status = "effective"
    elif prior_status == "negative" and rollback_status in {"effective", "flat"} and post_rate >= prior_rate:
        status = "effective"
    elif delta is not None and delta <= -abs(float(min_delta)):
        status = "negative"
    elif rollback_status == "negative":
        status = "negative"
    else:
        status = "watch"

    label = _policy_rollback_effect_label(status)
    tone = _policy_rollback_effect_tone(status)
    post_rate_text = _pct(post_rate) if post_rate is not None else "-"
    prior_rate_text = _pct(prior_rate) if prior_rate is not None else "-"
    delta_text = _pct(delta) if delta is not None else "-"
    if status == "effective":
        recommendation = "\u56de\u6eda\u540e\u653e\u884c\u547d\u4e2d\u76f8\u6bd4\u88ab\u56de\u6eda\u7248\u672c\u5df2\u6539\u5584\uff0c\u7ee7\u7eed\u6309\u56de\u6eda\u540e\u95e8\u69db\u6536\u96c6\u6837\u672c\u3002"
    elif status == "negative":
        recommendation = "\u56de\u6eda\u540e\u547d\u4e2d\u4ecd\u672a\u4fee\u590d\uff0c\u6682\u505c\u8fdb\u4e00\u6b65\u81ea\u52a8\u8c03\u53c2\uff0c\u5148\u590d\u6838\u56de\u6eda\u540e\u9519\u8bef\u6837\u672c\u3002"
    elif status == "watch":
        recommendation = "\u56de\u6eda\u540e\u672a\u51fa\u73b0\u660e\u786e\u4fee\u590d\u6216\u6076\u5316\uff0c\u7ee7\u7eed\u89c2\u5bdf\u4e0b\u4e00\u6279\u53ef\u56de\u6536\u6837\u672c\u3002"
    else:
        recommendation = "\u56de\u6eda\u540e\u53ef\u5224\u5b9a\u6837\u672c\u4e0d\u8db3\uff0c\u6682\u4e0d\u7ed9\u51fa\u4fee\u590d\u7ed3\u8bba\u3002"

    detail_rows: list[dict[str, object]] = []
    for _index, row in reversed(rollback_indexes[-max(1, int(limit)) :]):
        row_source_version = _policy_rollback_source_version(row.get("source"))
        compare_row = _policy_effect_row_by_version(review, row_source_version) if row_source_version else {}
        if not compare_row and _index > 0:
            compare_row = rows[_index - 1]
        row_hits, row_known, row_rate = _policy_effect_rate_parts(row)
        compare_hits, compare_known, compare_rate = _policy_effect_rate_parts(compare_row)
        row_delta = row_rate - compare_rate if row_rate is not None and compare_rate is not None else None
        detail_rows.append(
            {
                "title": f"{row.get('updated_at', '-')} | \u56de\u6eda {row.get('version_id', '-')} -> \u5bf9\u7167 {compare_row.get('version_id', '-')}",
                "body": (
                    f"\u56de\u6eda\u540e {row_hits}/{row_known} ({_pct(row_rate) if row_rate is not None else '-'}) | "
                    f"\u88ab\u56de\u6eda {compare_hits}/{compare_known} ({_pct(compare_rate) if compare_rate is not None else '-'}) | "
                    f"\u53d8\u5316 {_pct(row_delta) if row_delta is not None else '-'}"
                ),
                "version_id": row.get("version_id", "-"),
                "rolled_back_version_id": compare_row.get("version_id", row_source_version or "-"),
                "post_allow_hit_rate": row_rate,
                "rolled_back_allow_hit_rate": compare_rate,
                "allow_hit_rate_delta": row_delta,
                "allow_hit_rate_delta_text": _pct(row_delta) if row_delta is not None else "-",
            }
        )

    metrics = [
        {"label": "\u56de\u6eda\u4fee\u590d", "value": label, "tone": tone},
        {"label": "\u56de\u6eda\u540e\u547d\u4e2d", "value": f"{post_hits}/{post_known} ({post_rate_text})", "tone": tone if post_known else "neutral"},
        {"label": "\u88ab\u56de\u6eda\u547d\u4e2d", "value": f"{prior_hits}/{prior_known} ({prior_rate_text})", "tone": "neutral"},
        {"label": "\u4fee\u590d\u53d8\u5316", "value": delta_text, "tone": "good" if delta is not None and delta >= 0 else "bad" if delta is not None else "neutral"},
    ]
    summary_text = (
        f"{label} | \u56de\u6eda {rollback_row.get('version_id', '-')} | "
        f"\u88ab\u56de\u6eda {rolled_back_row.get('version_id', source_version_id or '-')} | "
        f"\u56de\u6eda\u540e {post_hits}/{post_known} ({post_rate_text}) | "
        f"\u5bf9\u7167 {prior_hits}/{prior_known} ({prior_rate_text}) | \u53d8\u5316 {delta_text}"
    )
    return {
        "status": status,
        "label": label,
        "tone": tone,
        "summary_text": summary_text,
        "recommendation_text": recommendation,
        "latest_version_id": rollback_row.get("version_id", "-"),
        "latest_source": rollback_row.get("source", "-"),
        "latest_updated_at": rollback_row.get("updated_at", "-"),
        "rolled_back_version_id": rolled_back_row.get("version_id", source_version_id or "-"),
        "post_known_count": post_known,
        "rolled_back_known_count": prior_known,
        "post_allow_hits": post_hits,
        "rolled_back_allow_hits": prior_hits,
        "post_allow_hit_rate": post_rate,
        "rolled_back_allow_hit_rate": prior_rate,
        "post_allow_hit_rate_text": post_rate_text,
        "rolled_back_allow_hit_rate_text": prior_rate_text,
        "allow_hit_rate_delta": delta,
        "allow_hit_rate_delta_text": delta_text,
        "min_known_samples": max(1, int(min_known_samples)),
        "metrics": metrics,
        "rows": detail_rows,
    }


def _strategy_policy_governance_event_type(source: object) -> tuple[str, str, str]:
    text = str(source or "").strip()
    lowered = text.lower()
    if lowered.startswith("policy_freeze_override"):
        return "freeze_override", "\u89e3\u9664\u51bb\u7ed3", "\u4eba\u5de5\u89e3\u9664\u8c03\u53c2\u51bb\u7ed3\u5ba1\u8ba1"
    if lowered.startswith("policy_rollback"):
        return "rollback", "\u53c2\u6570\u56de\u6eda", "\u56de\u6eda\u5230\u4e0a\u4e00\u7248\u6216\u6307\u5b9a\u7248\u672c"
    if "release_quality_trend" in lowered:
        return "trend_gate", "\u8d8b\u52bf\u95e8\u63a7", "\u653e\u884c\u8d28\u91cf\u8d8b\u52bf\u89e6\u53d1\u7684\u95e8\u69db\u8c03\u6574"
    if "strategy_allowlist_tuning" in lowered:
        return "allowlist_tuning", "\u653e\u884c\u95e8\u69db", "\u653e\u884c\u6c60\u8d28\u91cf\u89e6\u53d1\u7684\u95e8\u69db\u8c03\u6574"
    if "agent_replay_guard_tuning" in lowered:
        return "replay_guard_tuning", "Replay Guard", "Replay Guard \u53c2\u6570\u8c03\u6574"
    return "manual", "\u666e\u901a\u8c03\u53c2", "\u624b\u52a8\u6216\u5176\u4ed6\u6765\u6e90\u53c2\u6570\u8c03\u6574"


def _strategy_policy_governance_related_version(source: object) -> str:
    rollback_version = _policy_rollback_source_version(source)
    if rollback_version:
        return rollback_version
    override_version = _policy_freeze_override_source_version(source)
    if override_version:
        return override_version
    return "-"


def _draw_guard_governance_event_type(source: object) -> tuple[str, str, str]:
    lowered = str(source or "").strip().lower()
    if lowered.startswith("draw_guard_freeze_override") or lowered.startswith("draw_release_guard_freeze_override"):
        return "draw_guard_freeze_override", "DrawGuard解除冻结", "人工解除 DrawGuard 调参冻结审计"
    if "draw_guard_policy_rollback" in lowered or "draw_release_guard_policy_rollback" in lowered:
        return "draw_guard_rollback", "DrawGuard参数回滚", "回滚 DrawGuard 到上一版或指定版本"
    if "draw_release_guard_tuning" in lowered:
        return "draw_guard_tuning", "DrawGuard调参", "平局拦截复盘触发的 DrawGuard 参数调整"
    return "draw_guard_manual", "DrawGuard手动调整", "DrawGuard 手动或其他来源参数调整"


def _draw_guard_governance_related_version(source: object) -> str:
    rollback_version = _draw_guard_rollback_source_version(source)
    if rollback_version:
        return rollback_version
    override_version = _draw_guard_freeze_override_source_version(source)
    if override_version:
        return override_version
    return "-"


def _draw_guard_governance_event_rows(
    policy_history: Sequence[Mapping[str, object]] | object,
    *,
    tuning_effect_review: Mapping[str, object] | object | None = None,
    rollback_effect_review: Mapping[str, object] | object | None = None,
    freeze_override_status: Mapping[str, object] | object | None = None,
    tuning_guard: Mapping[str, object] | object | None = None,
) -> list[dict[str, object]]:
    history_items = [item for item in policy_history if isinstance(item, Mapping)] if isinstance(policy_history, Sequence) else []
    effect = _as_mapping(tuning_effect_review)
    if not effect and history_items:
        effect = build_draw_release_guard_tuning_effect_review(history_items, [])
    rows = [dict(row) for row in (_as_list(effect.get("all_rows")) or _as_list(effect.get("rows"))) if isinstance(row, Mapping)]
    event_rows: list[dict[str, object]] = []
    for row in rows:
        event_type, event_label, description = _draw_guard_governance_event_type(row.get("source"))
        related_version = _draw_guard_governance_related_version(row.get("source"))
        effect_status = str(row.get("effect_status") or "")
        tone = "bad" if event_type == "draw_guard_rollback" and effect_status == "negative" else "warning" if event_type in {"draw_guard_rollback", "draw_guard_freeze_override"} else "neutral"
        if event_type == "draw_guard_rollback" and effect_status == "effective":
            tone = "good"
        avoid_text = _text(row.get("avoid_rate_text"), "-")
        missed_text = _text(row.get("missed_rate_text"), "-")
        event_rows.append(
            {
                "domain": "draw_guard",
                "event_type": event_type,
                "event_label": event_label,
                "version_id": row.get("version_id", "-"),
                "updated_at": row.get("updated_at", "-"),
                "source": row.get("source", "-"),
                "related_version_id": related_version,
                "effect_label": row.get("effect_label", "-"),
                "effect_status": effect_status or "-",
                "allow_hit_rate_text": f"避 {avoid_text} / 错 {missed_text}",
                "known_allow_count": 0,
                "sample_count": _safe_int(row.get("sample_count")),
                "replay_guard_net": 0,
                "draw_guard_blocked_count": _safe_int(row.get("blocked_count")),
                "draw_guard_avoid_rate_text": avoid_text,
                "draw_guard_missed_rate_text": missed_text,
                "description": description,
                "tone": tone,
                "summary": (
                    f"{event_label} | 版本 {row.get('version_id', '-')} | "
                    f"关联 {related_version} | 效果 {row.get('effect_label', '-')} | "
                    f"避免 {avoid_text} / 错过 {missed_text}"
                ),
            }
        )

    guard = _as_mapping(tuning_guard)
    rollback_effect = _as_mapping(rollback_effect_review)
    freeze_override = _as_mapping(freeze_override_status)
    if bool(guard.get("freeze_active")):
        latest_version = _text(rollback_effect.get("latest_version_id"), "-")
        related_version = _text(rollback_effect.get("rolled_back_version_id"), "-")
        event_rows.append(
            {
                "domain": "draw_guard",
                "event_type": "draw_guard_freeze",
                "event_label": "DrawGuard调参冻结",
                "version_id": latest_version,
                "updated_at": rollback_effect.get("latest_updated_at", "-"),
                "source": "draw_guard_tuning_guard",
                "related_version_id": related_version,
                "effect_label": rollback_effect.get("label", "-"),
                "effect_status": rollback_effect.get("status", "-"),
                "allow_hit_rate_text": f"避 {rollback_effect.get('avoid_rate_delta_text', '-')} / 错 {rollback_effect.get('missed_rate_delta_text', '-')}",
                "known_allow_count": 0,
                "sample_count": _safe_int(rollback_effect.get("post_blocked_count")),
                "replay_guard_net": 0,
                "draw_guard_blocked_count": _safe_int(rollback_effect.get("post_blocked_count")),
                "draw_guard_avoid_rate_text": _text(rollback_effect.get("avoid_rate_delta_text"), "-"),
                "draw_guard_missed_rate_text": _text(rollback_effect.get("missed_rate_delta_text"), "-"),
                "description": "DrawGuard 回滚修复失败后冻结继续调参",
                "tone": "bad",
                "summary": f"DrawGuard调参冻结 | 回滚 {latest_version} | 关联 {related_version} | {guard.get('label', '-')}",
            }
        )
    return event_rows


def _normalize_governance_filter_value(value: object, default: str = "\u5168\u90e8") -> str:
    text = _text(value, default).strip() or default
    if text.lower() in {"all", "any"}:
        return default
    return text


def filter_strategy_policy_governance_event_rows(
    rows: Sequence[Mapping[str, object]] | object,
    *,
    domain_filter: object = "\u5168\u90e8",
    event_type_filter: object = "\u5168\u90e8",
) -> list[dict[str, object]]:
    row_items = [
        dict(item)
        for item in rows
        if isinstance(item, Mapping)
    ] if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)) else []
    domain_value = _normalize_governance_filter_value(domain_filter)
    event_type_value = _normalize_governance_filter_value(event_type_filter)

    filtered: list[dict[str, object]] = []
    for row in row_items:
        row_domain = str(row.get("domain") or "").strip()
        row_event_type = str(row.get("event_type") or "").strip()
        if domain_value != "\u5168\u90e8" and row_domain != domain_value:
            continue
        if event_type_value != "\u5168\u90e8" and row_event_type != event_type_value:
            continue
        filtered.append(row)
    return filtered


def build_strategy_policy_governance_event_summary(
    policy_effect_review: Mapping[str, object] | object,
    *,
    draw_release_guard_policy_history: Sequence[Mapping[str, object]] | object | None = None,
    draw_release_guard_tuning_effect_review: Mapping[str, object] | object | None = None,
    draw_release_guard_rollback_effect_review: Mapping[str, object] | object | None = None,
    draw_release_guard_freeze_override_status: Mapping[str, object] | object | None = None,
    draw_release_guard_tuning_guard: Mapping[str, object] | object | None = None,
    domain_filter: object = "\u5168\u90e8",
    event_type_filter: object = "\u5168\u90e8",
) -> dict[str, object]:
    review = _as_mapping(policy_effect_review)
    row_source = _as_list(review.get("all_rows")) or _as_list(review.get("rows"))
    rows = [dict(row) for row in row_source if isinstance(row, Mapping)]
    rows.sort(
        key=lambda row: (
            _parse_policy_review_time(row.get("updated_at")) or datetime.min,
            str(row.get("version_id") or ""),
        ),
        reverse=True,
    )
    event_rows: list[dict[str, object]] = []
    for row in rows:
        event_type, event_label, description = _strategy_policy_governance_event_type(row.get("source"))
        related_version = _strategy_policy_governance_related_version(row.get("source"))
        tone = "bad" if event_type == "rollback" and str(row.get("effect_status") or "") == "negative" else "warning" if event_type in {"rollback", "freeze_override", "trend_gate"} else "neutral"
        if event_type == "freeze_override":
            tone = "warning"
        elif event_type == "rollback" and str(row.get("effect_status") or "") == "effective":
            tone = "good"
        event_rows.append(
            {
                "event_type": event_type,
                "domain": "strategy",
                "event_label": event_label,
                "version_id": row.get("version_id", "-"),
                "updated_at": row.get("updated_at", "-"),
                "source": row.get("source", "-"),
                "related_version_id": related_version,
                "effect_label": row.get("effect_label", "-"),
                "effect_status": row.get("effect_status", "-"),
                "allow_hit_rate_text": row.get("allow_hit_rate_text", "-"),
                "known_allow_count": _safe_int(row.get("known_allow_count")),
                "sample_count": _safe_int(row.get("sample_count")),
                "replay_guard_net": _safe_int(row.get("replay_guard_net")),
                "description": description,
                "tone": tone,
                "summary": (
                    f"{event_label} | \u7248\u672c {row.get('version_id', '-')} | "
                    f"\u5173\u8054 {related_version} | \u6548\u679c {row.get('effect_label', '-')} | "
                    f"\u547d\u4e2d {row.get('allow_hit_rate_text', '-')}"
                ),
            }
        )
    event_rows.extend(
        _draw_guard_governance_event_rows(
            draw_release_guard_policy_history or [],
            tuning_effect_review=draw_release_guard_tuning_effect_review,
            rollback_effect_review=draw_release_guard_rollback_effect_review,
            freeze_override_status=draw_release_guard_freeze_override_status,
            tuning_guard=draw_release_guard_tuning_guard,
        )
    )
    event_rows.sort(
        key=lambda row: (
            _parse_policy_review_time(row.get("updated_at")) or datetime.min,
            str(row.get("version_id") or ""),
            str(row.get("event_type") or ""),
        ),
        reverse=True,
    )
    all_event_rows = list(event_rows)
    filtered_rows = filter_strategy_policy_governance_event_rows(
        all_event_rows,
        domain_filter=domain_filter,
        event_type_filter=event_type_filter,
    )
    counts: dict[str, int] = {}
    for row in filtered_rows:
        key = str(row.get("event_type") or "")
        counts[key] = counts.get(key, 0) + 1
    governance_count = sum(counts.get(key, 0) for key in ("trend_gate", "allowlist_tuning", "replay_guard_tuning", "rollback", "freeze_override"))
    draw_guard_governance_count = sum(
        counts.get(key, 0)
        for key in (
            "draw_guard_tuning",
            "draw_guard_rollback",
            "draw_guard_freeze",
            "draw_guard_freeze_override",
        )
    )
    governance_count += draw_guard_governance_count
    rollback_count = counts.get("rollback", 0)
    freeze_override_count = counts.get("freeze_override", 0)
    trend_gate_count = counts.get("trend_gate", 0)
    draw_guard_rollback_count = counts.get("draw_guard_rollback", 0)
    draw_guard_freeze_count = counts.get("draw_guard_freeze", 0)
    draw_guard_freeze_override_count = counts.get("draw_guard_freeze_override", 0)
    latest = filtered_rows[0] if filtered_rows else {}
    domain_value = _normalize_governance_filter_value(domain_filter)
    event_type_value = _normalize_governance_filter_value(event_type_filter)
    domain_options = ["\u5168\u90e8", "strategy", "draw_guard"]
    event_type_order = [
        "trend_gate",
        "allowlist_tuning",
        "replay_guard_tuning",
        "rollback",
        "freeze_override",
        "draw_guard_tuning",
        "draw_guard_rollback",
        "draw_guard_freeze",
        "draw_guard_freeze_override",
        "manual",
        "draw_guard_manual",
    ]
    event_type_options: list[str] = ["\u5168\u90e8"]
    seen_event_types: set[str] = set()
    for name in event_type_order:
        if any(str(row.get("event_type") or "") == name for row in all_event_rows):
            event_type_options.append(name)
            seen_event_types.add(name)
    for row in all_event_rows:
        name = str(row.get("event_type") or "").strip()
        if name and name not in seen_event_types:
            event_type_options.append(name)
            seen_event_types.add(name)
    total_event_count = len(all_event_rows)
    summary_text = (
        f"\u6cbb\u7406\u4e8b\u4ef6 {governance_count} | "
        f"\u8d8b\u52bf\u95e8\u63a7 {trend_gate_count} | \u56de\u6eda {rollback_count} | \u89e3\u9664\u51bb\u7ed3 {freeze_override_count}"
    )
    if draw_guard_governance_count:
        summary_text = f"{summary_text} | DrawGuard {draw_guard_governance_count}"
    filter_summary_text = (
        f"\u7b5b\u9009\u6761\u4ef6: \u57df={domain_value} / \u4e8b\u4ef6={event_type_value} | "
        f"\u663e\u793a {len(filtered_rows)} / \u5171 {total_event_count}"
    )
    return {
        "event_count": len(filtered_rows),
        "total_event_count": total_event_count,
        "governance_count": governance_count,
        "rollback_count": rollback_count,
        "freeze_override_count": freeze_override_count,
        "trend_gate_count": trend_gate_count,
        "draw_guard_governance_count": draw_guard_governance_count,
        "draw_guard_rollback_count": draw_guard_rollback_count,
        "draw_guard_freeze_count": draw_guard_freeze_count,
        "draw_guard_freeze_override_count": draw_guard_freeze_override_count,
        "counts": counts,
        "domain_filter": domain_value,
        "event_type_filter": event_type_value,
        "domain_options": domain_options,
        "event_type_options": event_type_options,
        "filter_summary_text": filter_summary_text,
        "latest_label": latest.get("event_label", "-") if latest else "-",
        "latest_summary": latest.get("summary", "-") if latest else "-",
        "summary_text": summary_text,
        "rows": filtered_rows,
        "all_rows": all_event_rows,
    }


def build_strategy_policy_freeze_alerts(
    freeze_override_status: Mapping[str, object] | object | None = None,
    draw_guard_freeze_override_status: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    strategy_freeze = _as_mapping(freeze_override_status)
    draw_guard_freeze = _as_mapping(draw_guard_freeze_override_status)

    def _freeze_alert(
        *,
        family: str,
        title: str,
        state_label: str,
        source: str,
        related_version_id: str,
        recommended_action: str,
        tone: str,
        blocking: bool,
        status_label: str,
    ) -> dict[str, object]:
        body = (
            f"\u51bb\u7ed3\u6765\u6e90: {source}\n"
            f"\u5173\u8054\u7248\u672c: {related_version_id}\n"
            f"\u5efa\u8bae\u52a8\u4f5c: {recommended_action}"
        )
        return {
            "family": family,
            "title": title,
            "body": body,
            "tone": tone,
            "blocking": blocking,
            "state_label": state_label,
            "status_label": status_label,
            "freeze_source": source,
            "related_version_id": related_version_id,
            "recommended_action": recommended_action,
        }

    alerts: list[dict[str, object]] = []
    strategy_status = str(strategy_freeze.get("status") or "")
    if strategy_status in {"frozen", "overridden"}:
        rollback_version = str(strategy_freeze.get("rollback_version_id") or "-")
        strategy_source = str(strategy_freeze.get("freeze_source") or "").strip()
        strategy_related_version = str(strategy_freeze.get("related_version_id") or "").strip() or rollback_version
        strategy_action = str(strategy_freeze.get("recommended_action") or "").strip()
        if strategy_status == "frozen":
            alerts.append(
                _freeze_alert(
                    family="strategy",
                    title="\u7b56\u7565\u8c03\u53c2\u51bb\u7ed3\u98ce\u9669",
                    state_label="\u963b\u65ad\u98ce\u9669",
                    source=strategy_source or f"policy_rollback:{rollback_version}",
                    related_version_id=strategy_related_version,
                    recommended_action=strategy_action or "\u590d\u6838\u56de\u6eda\u6240\u5bf9\u5e94\u7684\u7b56\u7565\u7248\u672c\uff0c\u786e\u8ba4\u540e\u518d\u89e3\u9664\u51bb\u7ed3\u3002",
                    tone="bad",
                    blocking=True,
                    status_label=str(strategy_freeze.get("label") or "\u8c03\u53c2\u51bb\u7ed3\u4e2d"),
                )
            )
        else:
            override_source = str(strategy_freeze.get("override_source") or "").strip()
            override_version_id = str(strategy_freeze.get("override_version_id") or "").strip()
            alerts.append(
                _freeze_alert(
                    family="strategy",
                    title="\u7b56\u7565\u8c03\u53c2\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664",
                    state_label="\u9700\u786e\u8ba4",
                    source=override_source or f"policy_freeze_override:{override_version_id or '-'}",
                    related_version_id=strategy_related_version,
                    recommended_action=strategy_action or "\u786e\u8ba4\u4eba\u5de5\u89e3\u9664\u8bb0\u5f55\uff0c\u7ee7\u7eed\u89c2\u5bdf\u540e\u7eed\u6587\u4ef6\u7248\u672c\u3002",
                    tone="warning",
                    blocking=False,
                    status_label=str(strategy_freeze.get("label") or "\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664"),
                )
            )

    draw_status = str(draw_guard_freeze.get("status") or "")
    if draw_status in {"frozen", "overridden"}:
        rollback_version = str(draw_guard_freeze.get("rollback_version_id") or "-")
        draw_source = str(draw_guard_freeze.get("freeze_source") or "").strip()
        draw_related_version = str(draw_guard_freeze.get("related_version_id") or "").strip() or rollback_version
        draw_action = str(draw_guard_freeze.get("recommended_action") or "").strip()
        if draw_status == "frozen":
            alerts.append(
                _freeze_alert(
                    family="draw_guard",
                    title="DrawGuard\u8c03\u53c2\u51bb\u7ed3\u98ce\u9669",
                    state_label="\u963b\u65ad\u98ce\u9669",
                    source=draw_source or f"draw_guard_policy_rollback:{rollback_version}",
                    related_version_id=draw_related_version,
                    recommended_action=draw_action or "\u590d\u6838 DrawGuard \u56de\u6eda\u6240\u5bf9\u5e94\u7684\u7248\u672c\uff0c\u786e\u8ba4\u540e\u518d\u89e3\u9664\u51bb\u7ed3\u3002",
                    tone="bad",
                    blocking=True,
                    status_label=str(draw_guard_freeze.get("label") or "DrawGuard\u8c03\u53c2\u51bb\u7ed3\u4e2d"),
                )
            )
        else:
            override_source = str(draw_guard_freeze.get("override_source") or "").strip()
            override_version_id = str(draw_guard_freeze.get("override_version_id") or "").strip()
            alerts.append(
                _freeze_alert(
                    family="draw_guard",
                    title="DrawGuard\u8c03\u53c2\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664",
                    state_label="\u9700\u786e\u8ba4",
                    source=override_source or f"draw_guard_freeze_override:{override_version_id or '-'}",
                    related_version_id=draw_related_version,
                    recommended_action=draw_action or "\u786e\u8ba4\u4eba\u5de5\u89e3\u9664\u8bb0\u5f55\uff0c\u7ee7\u7eed\u89c2\u5bdf DrawGuard \u540e\u7eed\u53d8\u5316\u3002",
                    tone="warning",
                    blocking=False,
                    status_label=str(draw_guard_freeze.get("label") or "DrawGuard\u51bb\u7ed3\u5df2\u4eba\u5de5\u89e3\u9664"),
                )
            )

    return {
        "count": len(alerts),
        "alerts": alerts,
    }


def build_strategy_evaluation_agent_summary(
    status: Mapping[str, object] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    statsbomb_fewshot_memory: Mapping[str, object] | object | None = None,
    *,
    settlement_summary: Mapping[str, object] | object | None = None,
    error_attribution: Mapping[str, object] | object | None = None,
    allowlist_summary: Mapping[str, object] | object | None = None,
    jc_feedback: Mapping[str, object] | object | None = None,
    event_review: Mapping[str, object] | object | None = None,
    video_review_memory: Mapping[str, object] | object | None = None,
    video_review_fewshot_memory: Mapping[str, object] | object | None = None,
    statsbomb_review_training_samples: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    settlement_summary = (
        _as_mapping(settlement_summary)
        if settlement_summary is not None
        else build_high_accuracy_strategy_settlement_summary(settlement_items)
    )
    review_training_quality = build_statsbomb_review_training_quality_summary(statsbomb_review_training_samples or {})
    review_training_signal = _as_mapping(review_training_quality.get("signal"))
    review_training_weight_gate = _as_mapping(review_training_signal.get("weight_gate"))
    review_training_weights = _as_mapping(review_training_signal.get("attribution_weights"))
    error_attribution = (
        _as_mapping(error_attribution)
        if error_attribution is not None
        else build_strategy_error_attribution_summary(
            settlement_items,
            error_weight_overrides=review_training_weights,
        )
    )
    allowlist_summary = (
        _as_mapping(allowlist_summary)
        if allowlist_summary is not None
        else build_strategy_allowlist_settlement_summary(settlement_items)
    )
    jc_feedback = _as_mapping(jc_feedback) if jc_feedback is not None else build_jc_bucket_feedback_summary(status, settlement_items)
    event_review = (
        _as_mapping(event_review)
        if event_review is not None
        else build_statsbomb_event_review_summary(settlement_items, statsbomb_event_baseline or {})
    )
    video_review_memory = (
        _as_mapping(video_review_memory)
        if video_review_memory is not None
        else build_video_review_memory_summary(settlement_items)
    )
    fewshot_memory = build_statsbomb_fewshot_memory_summary(error_attribution, event_review, statsbomb_fewshot_memory or {})
    fewshot_monitor = build_statsbomb_fewshot_memory_monitor(statsbomb_fewshot_memory or {}, fewshot_memory)
    fewshot_quality = build_statsbomb_fewshot_memory_quality_alerts(fewshot_monitor)
    video_fewshot_memory = build_video_review_fewshot_memory_summary(
        error_attribution,
        video_review_memory,
        video_review_fewshot_memory or {},
    )
    known_count = _safe_int(settlement_summary.get("known_count"))
    hit_rate = settlement_summary.get("hit_rate")
    hit_rate_value = _safe_float(hit_rate, -1.0) if hit_rate is not None else -1.0
    allow_rate = allowlist_summary.get("hit_rate")
    allow_rate_value = _safe_float(allow_rate, -1.0) if allow_rate is not None else -1.0
    reason_counts = _as_mapping(error_attribution.get("reason_counts"))
    jc_status_counts = _as_mapping(jc_feedback.get("status_counts"))
    downgraded_count = _safe_int(jc_status_counts.get("downgraded"))
    watch_count = _safe_int(jc_status_counts.get("watch"))
    high_conf_miss_count = _safe_int(reason_counts.get("high_confidence_miss"))
    historical_gap_count = _safe_int(reason_counts.get("historical_gap"))
    data_missing_count = _safe_int(reason_counts.get("data_missing"))
    statsbomb_against_count = _safe_int(reason_counts.get("statsbomb_xg_against_pick"))
    statsbomb_variance_count = _safe_int(reason_counts.get("statsbomb_finishing_variance"))
    statsbomb_control_gap_count = _safe_int(reason_counts.get("statsbomb_event_control_gap"))
    video_tempo_shift_count = _safe_int(reason_counts.get("video_tempo_shift"))
    video_finishing_variance_count = _safe_int(reason_counts.get("video_finishing_variance"))
    video_margin_risk_count = _safe_int(reason_counts.get("video_margin_risk"))
    video_low_quality_count = _safe_int(reason_counts.get("video_low_quality_evidence"))
    video_manual_review_count = _safe_int(reason_counts.get("video_manual_review_needed"))
    event_review_sample_count = _safe_int(event_review.get("sample_count"))
    event_review_variance_count = _safe_int(event_review.get("finishing_variance_count"))
    event_review_control_gap_count = _safe_int(event_review.get("control_gap_count"))
    recommendations: list[dict[str, str]] = []
    memory_tags: list[str] = []
    score = 100
    status_text = "healthy"

    if known_count < 5:
        status_text = "collecting"
        score = 55
        recommendations.append(
            {
                "title": "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c",
                "body": f"\u5df2\u5224\u5b9a\u7b56\u7565\u6837\u672c {known_count} \u9879\uff0c\u6682\u4e0d\u5efa\u8bae\u6839\u636e\u5355\u6b21\u6ce2\u52a8\u8c03\u6574\u95e8\u69db\u3002",
            }
        )
        memory_tags.append("sample_collecting")
    if hit_rate_value >= 0 and hit_rate_value < 0.55:
        status_text = "tighten"
        score -= 25
        recommendations.append(
            {
                "title": "\u6536\u7d27\u7b56\u7565\u51c6\u5165",
                "body": f"\u7b56\u7565\u5b9e\u76d8\u547d\u4e2d {settlement_summary.get('summary_text')}\uff0c\u4f4e\u4e8e 55% \u89c2\u5bdf\u7ebf\uff0c\u5efa\u8bae\u63d0\u9ad8\u6b63\u5f0f\u653e\u884c\u95e8\u69db\u3002",
            }
        )
        memory_tags.append("low_live_hit_rate")
    if allow_rate_value >= 0 and allow_rate_value < 0.55:
        status_text = "tighten"
        score -= 15
        recommendations.append(
            {
                "title": "\u590d\u6838\u653e\u884c\u6e05\u5355",
                "body": f"\u653e\u884c\u547d\u4e2d {allowlist_summary.get('hit_rate_text')}\uff0c\u5efa\u8bae\u964d\u4f4e\u4e2d\u98ce\u9669\u573a\u6b21\u7684\u6b63\u5f0f\u653e\u884c\u6743\u91cd\u3002",
            }
        )
        memory_tags.append("allowlist_underperforming")
    if high_conf_miss_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= min(20, high_conf_miss_count * 6)
        recommendations.append(
            {
                "title": "\u6821\u51c6\u7f6e\u4fe1\u5ea6",
                "body": f"\u51fa\u73b0 {high_conf_miss_count} \u9879\u9ad8\u7f6e\u4fe1\u5931\u8bef\uff0c\u5efa\u8bae\u4f18\u5148\u68c0\u67e5\u6982\u7387\u6821\u51c6\u548c\u8d5b\u524d\u98ce\u9669\u62e6\u622a\u3002",
            }
        )
        memory_tags.append("confidence_overstated")
    if historical_gap_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= min(18, historical_gap_count * 5)
        recommendations.append(
            {
                "title": "\u68c0\u67e5\u5386\u53f2\u7b56\u7565\u5931\u6548",
                "body": f"\u5386\u53f2\u56de\u6d4b\u4e0e\u5b9e\u76d8\u80cc\u79bb {historical_gap_count} \u9879\uff0c\u5efa\u8bae\u5bf9\u8054\u8d5b/\u8d54\u7387/\u7f6e\u4fe1\u5206\u5c42\u91cd\u65b0\u56de\u6d4b\u3002",
            }
        )
        memory_tags.append("historical_drift")
    if downgraded_count or watch_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= downgraded_count * 10 + watch_count * 4
        recommendations.append(
            {
                "title": "\u7ef4\u6301JC\u6876\u89c2\u5bdf",
                "body": f"JC \u7a33\u5b9a\u6876\u964d\u7ea7 {downgraded_count} / \u89c2\u5bdf {watch_count}\uff0c\u672a\u8fbe\u6062\u590d\u6761\u4ef6\u524d\u4e0d\u5efa\u8bae\u6062\u590d\u6b63\u5f0f\u653e\u884c\u3002",
            }
        )
        memory_tags.append("jc_bucket_watch")
    if statsbomb_against_count or statsbomb_control_gap_count:
        status_text = "watch" if status_text == "healthy" else status_text
        score -= min(18, (statsbomb_against_count + statsbomb_control_gap_count) * 5)
        recommendations.append(
            {
                "title": "\u7eb3\u5165\u8d5b\u540e\u4e8b\u4ef6\u8bc1\u636e",
                "body": f"StatsBomb \u663e\u793a xG \u53cd\u5411 {statsbomb_against_count} / \u573a\u9762\u52a3\u52bf {statsbomb_control_gap_count}\uff0c\u5efa\u8bae\u5c06\u5c04\u95e8\u3001xG\u3001\u538b\u8feb\u7b49\u8d5b\u540e\u7279\u5f81\u7eb3\u5165\u9519\u56e0\u8bb0\u5fc6\u3002",
            }
        )
        memory_tags.append("statsbomb_event_gap")
    if statsbomb_variance_count:
        recommendations.append(
            {
                "title": "\u6807\u8bb0\u7ec8\u7ed3\u6ce2\u52a8",
                "body": f"StatsBomb \u8bc6\u522b {statsbomb_variance_count} \u9879 xG \u5360\u4f18\u4f46\u672a\u547d\u4e2d\u7684\u7ec8\u7ed3\u504f\u5dee\uff0c\u8fd9\u7c7b\u4e0d\u5e94\u7b80\u5355\u5f52\u4e3a\u6a21\u578b\u65b9\u5411\u9519\u8bef\u3002",
            }
        )
        memory_tags.append("finishing_variance")
    if _safe_int(video_review_memory.get("review_count")):
        for tag in _as_list(video_review_memory.get("memory_tags")):
            tag_text = str(tag)
            if tag_text and tag_text not in memory_tags:
                memory_tags.append(tag_text)
        if video_tempo_shift_count or video_finishing_variance_count or video_margin_risk_count:
            status_text = "watch" if status_text == "healthy" else status_text
            score -= min(12, (video_tempo_shift_count + video_finishing_variance_count + video_margin_risk_count) * 3)
            recommendations.append(
                {
                    "title": "纳入AI视频复盘记忆",
                    "body": (
                        f"{video_review_memory.get('summary_text') or '-'}。"
                        f"节奏变化 {video_tempo_shift_count}，终结波动 {video_finishing_variance_count}，胜差风险 {video_margin_risk_count}。"
                        "这些结论只用于赛后 Evaluation Agent 归因，不进入赛前预测特征。"
                    ),
                }
            )
        if video_low_quality_count or video_manual_review_count:
            recommendations.append(
                {
                    "title": "补强视频证据",
                    "body": (
                        f"视频证据不足 {video_low_quality_count} / 需人工复核 {video_manual_review_count}。"
                        "优先补充更密集抽帧、清晰回放或事件标注，再写入复盘记忆。"
                    ),
                }
            )
    if event_review_sample_count:
        memory_tags.append("statsbomb_post_match_review")
        if event_review_variance_count or event_review_control_gap_count:
            status_text = "watch" if status_text == "healthy" else status_text
            score -= min(10, event_review_variance_count * 3 + event_review_control_gap_count * 2)
            recommendations.append(
                {
                    "title": "\u5bf9\u7167StatsBomb\u4e8b\u4ef6\u57fa\u7ebf",
                    "body": (
                        f"\u8d5b\u540e\u4e8b\u4ef6\u590d\u76d8 {event_review_sample_count} \u573a\uff0c"
                        f"\u7ec8\u7ed3\u6ce2\u52a8 {event_review_variance_count}\uff0c\u573a\u9762\u5dee\u5f02 {event_review_control_gap_count}\u3002"
                        f"\u5386\u53f2\u57fa\u7ebf {_safe_int(event_review.get('baseline_match_count'))} \u573a\uff0c"
                        f"\u7ec8\u7ed3\u6ce2\u52a8\u7387 {event_review.get('baseline_finishing_variance_rate') or '-'}\u3002"
                    ),
                }
            )
    if _safe_int(review_training_signal.get("sample_count")):
        for tag in _as_list(review_training_signal.get("memory_tags")):
            tag_text = str(tag)
            if tag_text and tag_text not in memory_tags:
                memory_tags.append(tag_text)
        has_statsbomb_reason = any(_safe_int(reason_counts.get(code)) for code in STATSBOMB_EVENT_ATTRIBUTION_CODES)
        if bool(review_training_weight_gate.get("enabled")) and has_statsbomb_reason:
            recommendations.append(
                {
                    "title": "应用StatsBomb事件代理权重",
                    "body": (
                        f"{review_training_signal.get('summary_text') or '-'}。"
                        "当前错因包含StatsBomb事件证据，排序已优先参考事件代理训练样本池；"
                        "该权重仅用于赛后Evaluation Agent归因，不进入赛前预测特征。"
                    ),
                }
            )
        elif has_statsbomb_reason:
            recommendations.append(
                {
                    "title": "StatsBomb事件代理权重已守门",
                    "body": (
                        f"{review_training_signal.get('summary_text') or '-'}。"
                        f"质量状态 {review_training_weight_gate.get('quality_status') or '-'}，"
                        f"模式 {review_training_weight_gate.get('mode') or '-'}；"
                        "当前只展示赛后报告，不参与 Evaluation Agent 错因加权。"
                    ),
                }
            )
    if _safe_int(fewshot_memory.get("matched_count")):
        memory_tags.append("statsbomb_fewshot_memory")
        recommendations.append(
            {
                "title": "\u53c2\u8003StatsBomb\u5386\u53f2\u590d\u76d8\u8bb0\u5fc6",
                "body": (
                    f"{fewshot_memory.get('summary_text') or '-'}\u3002"
                    "\u5efa\u8bae\u5c06\u76f8\u4f3c\u6848\u4f8b\u4f5c\u4e3a\u590d\u76d8\u8bed\u5883\uff0c\u533a\u5206\u7ec8\u7ed3\u6ce2\u52a8\u3001\u573a\u9762\u52a3\u52bf\u548c\u771f\u6b63\u7684\u8d5b\u524d\u5224\u65ad\u5931\u6548\u3002"
                ),
            }
        )
    if _safe_int(video_fewshot_memory.get("matched_count")):
        if "video_review_fewshot_memory" not in memory_tags:
            memory_tags.append("video_review_fewshot_memory")
        recommendations.append(
            {
                "title": "\u53c2\u8003AI\u89c6\u9891\u5386\u53f2\u590d\u76d8\u8bb0\u5fc6",
                "body": (
                    f"{video_fewshot_memory.get('summary_text') or '-'}\u3002"
                    "\u5efa\u8bae\u5c06\u76f8\u4f3c\u89c6\u9891\u6807\u6ce8\u6848\u4f8b\u7528\u4e8e\u8d5b\u540e\u9519\u56e0\u89e3\u91ca\uff0c\u4e0d\u5f71\u54cd\u8d5b\u524d\u7279\u5f81\u548c\u9884\u6d4b\u3002"
                ),
            }
        )
    if _safe_int(fewshot_quality.get("alert_count")):
        status_text = "watch" if status_text == "healthy" else status_text
        score += _safe_int(fewshot_quality.get("score_delta"))
        for tag in _as_list(fewshot_quality.get("memory_tags")):
            tag_text = str(tag)
            if tag_text and tag_text not in memory_tags:
                memory_tags.append(tag_text)
        alert_priority = {"statsbomb_memory_no_current_match": 0, "statsbomb_memory_tag_gap": 1}
        quality_alerts = sorted(
            [_as_mapping(alert) for alert in _as_list(fewshot_quality.get("alerts"))],
            key=lambda alert: alert_priority.get(str(alert.get("tag") or ""), 5),
        )
        for alert_map in quality_alerts:
            if alert_map:
                recommendations.append(
                    {
                        "title": str(alert_map.get("title") or "StatsBomb记忆质量告警"),
                        "body": str(alert_map.get("body") or "-"),
                    }
                )
    if data_missing_count:
        score -= min(12, data_missing_count * 4)
        recommendations.append(
            {
                "title": "\u4fee\u590d\u8d5b\u679c/\u5feb\u7167\u6570\u636e",
                "body": f"\u5b58\u5728 {data_missing_count} \u9879\u6570\u636e\u7f3a\u5931\uff0c\u9700\u4f18\u5148\u68c0\u67e5\u8d5b\u524d\u5feb\u7167\u548c\u8d5b\u679c\u56de\u6536\u94fe\u8def\u3002",
            }
        )
        memory_tags.append("data_quality_gap")
    if not recommendations:
        recommendations.append(
            {
                "title": "\u7ef4\u6301\u5f53\u524d\u7b56\u7565",
                "body": "\u672a\u53d1\u73b0\u9700\u8981\u6536\u7d27\u7684\u4e3b\u8981\u9519\u56e0\uff0c\u7ee7\u7eed\u6309\u5f53\u524d\u51c6\u5165\u548c\u590d\u76d8\u89c4\u5219\u8fd0\u884c\u3002",
            }
        )
        memory_tags.append("stable")

    score = max(0, min(100, int(round(score))))
    if score < 60 and status_text not in {"tighten", "collecting"}:
        status_text = "watch"
    return {
        "agent": "Evaluation Agent",
        "status": status_text,
        "score": score,
        "summary_text": (
            f"\u6837\u672c {known_count} | \u7b56\u7565\u547d\u4e2d {settlement_summary.get('hit_rate_text')} | "
            f"\u4e3b\u9519\u56e0 {error_attribution.get('top_reason')} | JC {jc_feedback.get('summary_text')}"
        ),
        "settlement_summary": settlement_summary,
        "error_attribution": error_attribution,
        "jc_bucket_feedback": jc_feedback,
        "statsbomb_event_review": event_review,
        "statsbomb_review_training_quality": review_training_quality,
        "statsbomb_review_training_signal": review_training_signal,
        "video_review_memory": video_review_memory,
        "video_review_fewshot_memory": video_fewshot_memory,
        "statsbomb_fewshot_memory": fewshot_memory,
        "statsbomb_fewshot_monitor": fewshot_monitor,
        "statsbomb_fewshot_quality": fewshot_quality,
        "recommendations": recommendations[:8],
        "memory_tags": memory_tags,
    }


def _build_high_accuracy_strategy_pool_rows_legacy(status: Mapping[str, object] | object) -> list[dict[str, str]]:
    resolved = _as_mapping(status)
    rows: list[dict[str, str]] = []
    for index, item in enumerate(_strategy_pool(resolved), start=1):
        layer = _strategy_layer(item)
        stability = _strategy_stability(item)
        breaker = _as_mapping(item.get("breaker"))
        role = _label(ROLE_LABELS, item.get("effective_role") or item.get("role"))
        original_role = _label(ROLE_LABELS, item.get("original_role") or item.get("role"))
        if role != original_role:
            role = f"{role}(\u539f{original_role})"
        play = _label(PLAY_LABELS, item.get("play_type"))
        scope = _label(SCOPE_LABELS, item.get("scope"))
        data_layer = _label(DATA_LAYER_LABELS, layer.get("data_layer"))
        breaker_status = "ON" if bool(breaker.get("breaker_on")) else str(breaker.get("status") or "pending").upper()
        title = f"{index}. {role} | {play}"
        jc_bucket = _as_mapping(item.get("jc_bucket"))
        jc_context = _as_mapping(item.get("jc_context"))
        jc_feedback = _as_mapping(item.get("jc_live_feedback"))
        jc_lines: list[str] = []
        if str(layer.get("data_layer") or "") == "jc_stratified_market":
            live_status = str(jc_feedback.get("status") or "pending").upper()
            live_line = (
                f"JC实盘: {_safe_int(jc_feedback.get('live_hit_count'))}/{_safe_int(jc_feedback.get('live_count'))}"
                f" ({_pct(jc_feedback.get('live_hit_rate'))}) | 偏差 {_pct(jc_feedback.get('deviation'))} | 状态 {live_status}"
                if jc_feedback
                else "JC实盘: 待积累赛后样本"
            )
            jc_lines = [
                f"JC稳定桶: {jc_bucket.get('dimension') or item.get('dimension') or '-'} / {jc_bucket.get('bucket') or item.get('scope_value') or '-'}",
                f"JC当前匹配: confidence_bucket={jc_context.get('confidence_bucket') or '-'} | odds_bucket={jc_context.get('odds_bucket') or '-'} | pick_odds={_safe_float(jc_context.get('pick_odds')):.2f}",
            ]
        if str(layer.get("data_layer") or "") == "jc_stratified_market":
            jc_lines.append(live_line)
        body = "\n".join(
            [
                f"\u8303\u56f4: {scope} / {item.get('scope_value') or '-'} | \u6570\u636e\u5c42: {data_layer}",
                f"\u95e8\u69db: {_safe_float(item.get('min_confidence')):.2f} | \u56de\u6d4b: {_pct(item.get('accuracy'))} ({_safe_int(item.get('hit_count'))}/{_safe_int(item.get('sample_count'))})",
                f"Wilson: {_pct(item.get('wilson_lower'))} | \u8986\u76d6: {_pct(item.get('coverage'))} | \u8fb9\u9645: {_safe_float(item.get('edge')):+.1%}",
                f"\u7a33\u5b9a: {'OK' if bool(stability.get('stable')) else 'WATCH'} | \u8bc4\u5206 {_pct(stability.get('stability_score'))} | \u8fd130/90 {_pct(stability.get('recent_30_accuracy'))}/{_pct(stability.get('recent_90_accuracy'))}",
                f"\u65ad\u8def: {breaker_status} | \u8fde\u9519 {_safe_int(breaker.get('miss_streak'))}/{_safe_int(breaker.get('threshold'), 3)} | \u6062\u590d {_safe_int(breaker.get('recovery_streak'))}/{_safe_int(breaker.get('recovery_hits_required'), 2)} | \u8fd1\u671f {_safe_int(breaker.get('hit_count'))}/{_safe_int(breaker.get('known_count'))}",
            ]
            + jc_lines
        )
        rows.append({"title": title, "body": body})
    return rows


def build_high_accuracy_strategy_pool_rows(status: Mapping[str, object] | object) -> list[dict[str, str]]:
    resolved = _as_mapping(status)
    rows: list[dict[str, str]] = []
    for index, item in enumerate(_strategy_pool(resolved), start=1):
        layer = _strategy_layer(item)
        stability = _strategy_stability(item)
        breaker = _as_mapping(item.get("breaker"))
        role = _label(ROLE_LABELS, item.get("effective_role") or item.get("role"))
        original_role = _label(ROLE_LABELS, item.get("original_role") or item.get("role"))
        if role != original_role:
            role = f"{role}(\u539f{original_role})"
        play = _label(PLAY_LABELS, item.get("play_type"))
        scope = _label(SCOPE_LABELS, item.get("scope"))
        data_layer = _label(DATA_LAYER_LABELS, layer.get("data_layer"))
        breaker_status = "ON" if bool(breaker.get("breaker_on")) else str(breaker.get("status") or "pending").upper()
        title = f"{index}. {role} | {play}"
        jc_bucket = _as_mapping(item.get("jc_bucket"))
        jc_context = _as_mapping(item.get("jc_context"))
        jc_feedback = _as_mapping(item.get("jc_live_feedback"))
        jc_calibration = _as_mapping(item.get("jc_auto_calibration"))
        jc_lines: list[str] = []
        if str(layer.get("data_layer") or "") == "jc_stratified_market":
            live_status = str(jc_feedback.get("status") or "pending").upper()
            calibration_thresholds = _as_mapping(jc_calibration.get("thresholds"))
            calibration_line = (
                f"JC\u6821\u51c6: {str(jc_calibration.get('mode') or 'base').upper()} | "
                f"\u6837\u672c>={_safe_int(calibration_thresholds.get('min_samples'), 120)} | "
                f"\u51c6\u786e>={_pct(calibration_thresholds.get('min_accuracy'))} | "
                f"Wilson>={_pct(calibration_thresholds.get('min_wilson'))}"
                if jc_calibration
                else "JC\u6821\u51c6: BASE"
            )
            if jc_feedback:
                live_line = (
                    f"JC\u5b9e\u76d8: {_safe_int(jc_feedback.get('live_hit_count'))}/{_safe_int(jc_feedback.get('live_count'))}"
                    f" ({_pct(jc_feedback.get('live_hit_rate'))}) | \u504f\u5dee {_pct(jc_feedback.get('deviation'))} | \u72b6\u6001 {live_status}"
                )
            else:
                live_line = "JC\u5b9e\u76d8: \u5f85\u79ef\u7d2f\u8d5b\u540e\u6837\u672c"
            jc_lines = [
                f"JC\u7a33\u5b9a\u6876: {jc_bucket.get('dimension') or item.get('dimension') or '-'} / {jc_bucket.get('bucket') or item.get('scope_value') or '-'}",
                f"JC\u5f53\u524d\u5339\u914d: confidence_bucket={jc_context.get('confidence_bucket') or '-'} | odds_bucket={jc_context.get('odds_bucket') or '-'} | pick_odds={_safe_float(jc_context.get('pick_odds')):.2f}",
                live_line,
                calibration_line,
            ]
        body = "\n".join(
            [
                f"\u8303\u56f4: {scope} / {item.get('scope_value') or '-'} | \u6570\u636e\u5c42: {data_layer}",
                f"\u95e8\u69db: {_safe_float(item.get('min_confidence')):.2f} | \u56de\u6d4b: {_pct(item.get('accuracy'))} ({_safe_int(item.get('hit_count'))}/{_safe_int(item.get('sample_count'))})",
                f"Wilson: {_pct(item.get('wilson_lower'))} | \u8986\u76d6: {_pct(item.get('coverage'))} | \u8fb9\u9645: {_safe_float(item.get('edge')):+.1%}",
                f"\u7a33\u5b9a: {'OK' if bool(stability.get('stable')) else 'WATCH'} | \u8bc4\u5206 {_pct(stability.get('stability_score'))} | \u8fd130/90 {_pct(stability.get('recent_30_accuracy'))}/{_pct(stability.get('recent_90_accuracy'))}",
                f"\u65ad\u8def: {breaker_status} | \u8fde\u9519 {_safe_int(breaker.get('miss_streak'))}/{_safe_int(breaker.get('threshold'), 3)} | \u6062\u590d {_safe_int(breaker.get('recovery_streak'))}/{_safe_int(breaker.get('recovery_hits_required'), 2)} | \u8fd1\u671f {_safe_int(breaker.get('hit_count'))}/{_safe_int(breaker.get('known_count'))}",
            ]
            + jc_lines
        )
        rows.append({"title": title, "body": body})
    return rows


def build_high_accuracy_live_feedback_summary(status: Mapping[str, object] | object) -> dict[str, object]:
    resolved = _as_mapping(status)
    pool = _strategy_pool(resolved)
    rows: list[dict[str, str]] = []
    pending_count = 0
    known_strategy_count = 0
    paused_count = 0
    recovering_count = 0
    recovered_count = 0
    feedback_hit_count = 0
    feedback_known_count = 0
    computed_active_count = 0

    for index, item in enumerate(pool, start=1):
        layer = _strategy_layer(item)
        breaker = _as_mapping(item.get("breaker"))
        jc_feedback = _as_mapping(item.get("jc_live_feedback"))
        role = _label(ROLE_LABELS, item.get("effective_role") or item.get("role"))
        play = _label(PLAY_LABELS, item.get("play_type"))
        scope = _label(SCOPE_LABELS, item.get("scope"))
        data_layer = _label(DATA_LAYER_LABELS, layer.get("data_layer") or item.get("data_layer"))
        breaker_status = str(breaker.get("status") or "pending").strip().lower()
        jc_status = str(jc_feedback.get("status") or "").strip().lower()
        recovery_status = str(jc_feedback.get("recovery_status") or breaker.get("recovery_status") or "").strip().lower()
        breaker_on = _safe_bool(breaker.get("breaker_on"))
        breaker_known_count = _safe_int(breaker.get("known_count"))
        jc_known_count = _safe_int(jc_feedback.get("live_count"))
        feedback_known = max(breaker_known_count, jc_known_count)
        feedback_hits = (
            _safe_int(jc_feedback.get("live_hit_count"))
            if jc_known_count > breaker_known_count
            else _safe_int(breaker.get("hit_count"))
        )
        if feedback_known <= 0 and _safe_int(jc_feedback.get("live_hit_count")):
            feedback_hits = _safe_int(jc_feedback.get("live_hit_count"))
        feedback_hit_rate = feedback_hits / feedback_known if feedback_known else None
        feedback_hit_rate_text = _pct(feedback_hit_rate) if feedback_hit_rate is not None else "-"
        miss_streak = _safe_int(breaker.get("miss_streak") or jc_feedback.get("miss_streak"))
        breaker_threshold = _safe_int(breaker.get("threshold"), 3)
        recovery_streak = _safe_int(breaker.get("recovery_streak") or jc_feedback.get("recovery_streak"))
        recovery_required = _safe_int(breaker.get("recovery_hits_required") or jc_feedback.get("recovery_hits_required"), 2)

        if breaker_on and (breaker_status == "recovering" or recovery_status in {"in_progress", "recovering"}):
            state = "recovering"
        elif breaker_on or breaker_status in {"paused", "blocked"} or jc_status in {"downgraded", "blocked"}:
            state = "paused"
        elif feedback_known <= 0:
            state = "pending"
        elif breaker_status == "recovered" or recovery_status in {"eligible", "recovered"}:
            state = "recovered"
        else:
            state = "known"

        if state == "pending":
            pending_count += 1
        else:
            known_strategy_count += 1
        if state == "paused":
            paused_count += 1
        if state == "recovering":
            recovering_count += 1
        if state == "recovered":
            recovered_count += 1
        if state not in {"paused", "recovering"}:
            computed_active_count += 1
        feedback_hit_count += feedback_hits
        feedback_known_count += feedback_known

        state_label = {
            "pending": "待反馈",
            "known": "实盘反馈",
            "paused": "暂停/观察",
            "recovering": "恢复中",
            "recovered": "已恢复",
        }.get(state, "实盘反馈")
        hints: list[str] = []
        if state == "pending":
            hints.append("等待赛果回收")
        if not breaker_on and breaker_threshold and miss_streak >= max(1, breaker_threshold - 1):
            hints.append("接近断路")
        if breaker_on and recovery_required and recovery_streak >= max(1, recovery_required - 1):
            hints.append("接近恢复")
        if breaker_on and not hints:
            hints.append("断路观察")
        hint_text = " / ".join(hints) if hints else "正常跟踪"
        jc_live_line = ""
        if jc_feedback:
            jc_live_rate = jc_feedback.get("live_hit_rate")
            if jc_live_rate in (None, "") and jc_known_count:
                jc_live_rate = _safe_int(jc_feedback.get("live_hit_count")) / jc_known_count
            jc_live_line = (
                f"\nJC实盘: {_safe_int(jc_feedback.get('live_hit_count'))}/{jc_known_count}"
                f" ({_pct(jc_live_rate)}) | 偏差 {_pct(jc_feedback.get('deviation'))} | 状态 {jc_status.upper() or '-'}"
            )
        body = (
            f"范围: {scope} / {item.get('scope_value') or '-'} | 数据层: {data_layer}\n"
            f"门槛: {_safe_float(item.get('min_confidence')):.2f} | 回测: {_pct(item.get('accuracy'))}"
            f" ({_safe_int(item.get('hit_count'))}/{_safe_int(item.get('sample_count'))}) | Wilson {_pct(item.get('wilson_lower'))}\n"
            f"实盘反馈: 命中 {feedback_hits}/{feedback_known} ({feedback_hit_rate_text}) | 状态 {breaker_status.upper()}"
            f" | {hint_text}\n"
            f"断路计数: 连错 {miss_streak}/{breaker_threshold} | 恢复 {recovery_streak}/{recovery_required}"
            f"{jc_live_line}"
        )
        rows.append({"title": f"{index}. {state_label} | {role} | {play}", "body": body})

    runtime_source = resolved.get("runtime_active_count")
    runtime_active_count = _safe_int(runtime_source) if runtime_source not in (None, "") else computed_active_count
    hit_rate = feedback_hit_count / feedback_known_count if feedback_known_count else None
    summary_parts = [
        f"可用 {runtime_active_count}/{len(pool)}",
        f"待反馈 {pending_count}",
        f"已反馈 {known_strategy_count}",
        f"命中 {feedback_hit_count}/{feedback_known_count}",
        f"暂停 {paused_count}",
    ]
    if recovering_count:
        summary_parts.append(f"恢复中 {recovering_count}")
    tone = "neutral"
    if pool:
        if paused_count and runtime_active_count <= 0:
            tone = "bad"
        elif paused_count or recovering_count or pending_count:
            tone = "warning"
        else:
            tone = "good"
    return {
        "strategy_count": len(pool),
        "runtime_active_count": runtime_active_count,
        "pending_count": pending_count,
        "known_count": known_strategy_count,
        "feedback_strategy_count": known_strategy_count,
        "paused_count": paused_count,
        "recovering_count": recovering_count,
        "recovered_count": recovered_count,
        "hit_count": feedback_hit_count,
        "feedback_known_count": feedback_known_count,
        "hit_rate": hit_rate,
        "hit_rate_text": _pct(hit_rate) if hit_rate is not None else "-",
        "summary_text": " | ".join(summary_parts),
        "tone": tone,
        "rows": rows,
    }


def build_high_accuracy_live_feedback_recovery_validation(
    before: Mapping[str, object] | object,
    after: Mapping[str, object] | object,
    *,
    new_settled: int = 0,
) -> dict[str, object]:
    before_summary = _as_mapping(before)
    after_summary = _as_mapping(after)
    before_pending = _safe_int(before_summary.get("pending_count"))
    after_pending = _safe_int(after_summary.get("pending_count"))
    before_known = _safe_int(before_summary.get("feedback_known_count"))
    after_known = _safe_int(after_summary.get("feedback_known_count"))
    before_hits = _safe_int(before_summary.get("hit_count"))
    after_hits = _safe_int(after_summary.get("hit_count"))
    before_paused = _safe_int(before_summary.get("paused_count"))
    after_paused = _safe_int(after_summary.get("paused_count"))
    before_recovering = _safe_int(before_summary.get("recovering_count"))
    after_recovering = _safe_int(after_summary.get("recovering_count"))
    before_active = _safe_int(before_summary.get("runtime_active_count"))
    after_active = _safe_int(after_summary.get("runtime_active_count"))
    pending_reduced = max(0, before_pending - after_pending)
    pending_delta = after_pending - before_pending
    feedback_known_delta = after_known - before_known
    hit_delta = after_hits - before_hits
    paused_delta = after_paused - before_paused
    recovering_delta = after_recovering - before_recovering
    active_delta = after_active - before_active

    if not before_summary and not after_summary:
        status = "unavailable"
        tone = "neutral"
        summary_text = "实盘反馈验证不可用"
    elif pending_reduced > 0 or feedback_known_delta > 0 or hit_delta > 0:
        status = "verified"
        tone = "good"
        summary_text = (
            f"已验证 | 待反馈减少 {pending_reduced} | 实盘样本 +{max(0, feedback_known_delta)} | "
            f"命中 +{max(0, hit_delta)}"
        )
    elif _safe_int(new_settled) > 0:
        status = "no_strategy_feedback"
        tone = "warning"
        summary_text = f"本轮新增结算 {_safe_int(new_settled)} 场，但高准策略实盘反馈未变化"
    else:
        status = "waiting"
        tone = "neutral"
        summary_text = "本轮暂无新增结算，高准策略实盘反馈等待后续赛果"
    if pending_delta > 0 or paused_delta > 0:
        tone = "warning" if tone != "bad" else tone

    rows = [
        {
            "title": "待反馈变化",
            "body": f"{before_pending} -> {after_pending} | 减少 {pending_reduced} | 净变化 {pending_delta:+d}",
        },
        {
            "title": "实盘样本变化",
            "body": f"样本 {before_known} -> {after_known} ({feedback_known_delta:+d}) | 命中 {before_hits} -> {after_hits} ({hit_delta:+d})",
        },
        {
            "title": "断路/恢复变化",
            "body": (
                f"可用 {before_active} -> {after_active} ({active_delta:+d}) | "
                f"暂停 {before_paused} -> {after_paused} ({paused_delta:+d}) | "
                f"恢复中 {before_recovering} -> {after_recovering} ({recovering_delta:+d})"
            ),
        },
    ]
    return {
        "status": status,
        "tone": tone,
        "summary_text": summary_text,
        "new_settled": _safe_int(new_settled),
        "pending_before": before_pending,
        "pending_after": after_pending,
        "pending_reduced": pending_reduced,
        "pending_delta": pending_delta,
        "feedback_known_before": before_known,
        "feedback_known_after": after_known,
        "feedback_known_delta": feedback_known_delta,
        "hit_before": before_hits,
        "hit_after": after_hits,
        "hit_delta": hit_delta,
        "paused_before": before_paused,
        "paused_after": after_paused,
        "paused_delta": paused_delta,
        "recovering_before": before_recovering,
        "recovering_after": after_recovering,
        "recovering_delta": recovering_delta,
        "runtime_active_before": before_active,
        "runtime_active_after": after_active,
        "runtime_active_delta": active_delta,
        "rows": rows,
    }


def build_high_accuracy_strategy_settlement_rows(
    settlements: Sequence[Mapping[str, object]],
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for settlement, item in _known_strategy_settlement_items(settlements)[: max(0, int(limit))]:
        hit = item.get("is_hit")
        hit_label = "\u547d\u4e2d" if hit is True else "\u672a\u547d\u4e2d" if hit is False else "\u5f85\u5224\u5b9a"
        shadow_label = "\u89c2\u5bdf" if bool(item.get("is_shadow")) else "\u6b63\u5f0f"
        title = f"{hit_label} | {shadow_label} | {_label(ROLE_LABELS, item.get('role'))} | {_label(PLAY_LABELS, item.get('play_type'))}"
        match_text = (
            f"{settlement.get('league') or '-'} | {settlement.get('home_team') or '-'}"
            f" vs {settlement.get('away_team') or '-'}"
        )
        body = "\n".join(
            [
                match_text,
                f"\u9884\u6d4b: {item.get('pick') or '-'} | \u5b9e\u9645: {item.get('actual') or '-'}",
                f"\u7f6e\u4fe1: {_pct(item.get('confidence'))} / \u95e8\u69db {_safe_float(item.get('min_confidence')):.2f} | \u56de\u6d4b {_pct(item.get('backtest_accuracy'))} ({_safe_int(item.get('backtest_samples'))}\u6837\u672c)",
            ]
        )
        rows.append({"title": title, "body": body})
    return rows


def _jc_bucket_key_from_item(item: Mapping[str, object]) -> str:
    explicit = str(item.get("jc_bucket_key") or "").strip()
    if explicit:
        return explicit
    bucket = _as_mapping(item.get("jc_bucket"))
    dimension = str(bucket.get("dimension") or item.get("dimension") or "").strip()
    bucket_value = str(bucket.get("bucket") or item.get("scope_value") or "").strip()
    if not dimension or not bucket_value:
        return ""
    return f"{dimension}|{bucket_value}"


def _is_jc_bucket_item(item: Mapping[str, object]) -> bool:
    layer = _as_mapping(item.get("layer"))
    return str(item.get("data_layer") or layer.get("data_layer") or "") == "jc_stratified_market" or bool(_as_mapping(item.get("jc_bucket")))


def _jc_bucket_summary_status(
    *,
    live_count: int,
    live_hit_rate: float | None,
    wilson_lower: float,
    miss_streak: int,
    explicit_status: str = "",
) -> str:
    explicit = explicit_status.strip().lower()
    if explicit in {"downgraded", "watch", "healthy", "pending"}:
        return explicit
    if live_count < 5 or live_hit_rate is None:
        return "pending"
    if live_count >= 10 and live_hit_rate < max(0.45, wilson_lower - 0.10):
        return "downgraded"
    if miss_streak >= 3 or live_hit_rate < max(0.45, wilson_lower - 0.05):
        return "watch"
    return "healthy"


def _most_common_text(values: Sequence[object]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        counts[text] = counts.get(text, 0) + 1
    if not counts:
        return "-"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _avg_float(values: Sequence[object]) -> float | None:
    numbers = [_safe_float(value) for value in values if value not in (None, "")]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _jc_bucket_diagnostics(
    *,
    status_text: str,
    live_count: int,
    live_hit_rate: float | None,
    historical_accuracy: float,
    historical_wilson: float,
    deviation: object,
    miss_streak: int,
    live_avg_odds: float | None,
    historical_avg_odds: float | None,
    live_avg_confidence: float | None,
    historical_avg_confidence: float | None,
) -> str:
    reasons: list[str] = []
    deviation_value = _safe_float(deviation) if deviation is not None else None
    if live_count < 10:
        reasons.append("\u5b9e\u76d8\u6837\u672c\u504f\u5c11")
    if live_hit_rate is not None and live_hit_rate < historical_wilson:
        reasons.append("\u5b9e\u76d8\u8dcc\u7834Wilson\u4e0b\u9650")
    if deviation_value is not None and deviation_value <= -0.10:
        reasons.append("\u547d\u4e2d\u7387\u8f83\u5386\u53f2\u660e\u663e\u56de\u843d")
    if miss_streak >= 3:
        reasons.append("\u8fde\u7eed\u672a\u547d\u4e2d")
    if live_avg_odds is not None and historical_avg_odds is not None and abs(live_avg_odds - historical_avg_odds) >= 0.25:
        reasons.append("\u5b9e\u76d8\u8d54\u7387\u4e0e\u5386\u53f2\u5747\u503c\u504f\u79bb")
    if live_avg_confidence is not None and historical_avg_confidence is not None and live_avg_confidence + 0.05 < historical_avg_confidence:
        reasons.append("\u5b9e\u76d8\u7f6e\u4fe1\u4f4e\u4e8e\u5386\u53f2\u5747\u503c")
    if status_text == "healthy" and not reasons:
        reasons.append("\u5b9e\u76d8\u8868\u73b0\u4e0e\u5386\u53f2\u5339\u914d")
    if status_text == "pending" and not reasons:
        reasons.append("\u7b49\u5f85\u66f4\u591a\u8d5b\u540e\u6837\u672c")
    return " | ".join(reasons[:4]) if reasons else "-"


def _jc_recovery_label(
    *,
    status_text: str,
    recovery_status: str,
    recovery_streak: int,
    recovery_required: int,
) -> str:
    required = max(1, int(recovery_required or 1))
    if recovery_status == "eligible":
        return f"\u5df2\u8fbe\u5230\u6062\u590d\u6761\u4ef6 {recovery_streak}/{required}\uff0c\u4fdd\u6301\u89c2\u5bdf"
    if recovery_status == "in_progress":
        return f"\u6062\u590d\u4e2d {recovery_streak}/{required}\uff0c\u7ee7\u7eed\u8bb0\u5f55\u5f71\u5b50\u7ed3\u7b97"
    if recovery_status == "recovered" or status_text == "healthy":
        return "\u6682\u65e0\u6062\u590d\u538b\u529b"
    if status_text in {"watch", "downgraded"}:
        return f"\u672a\u8fbe\u6062\u590d\u6761\u4ef6 0/{required}\uff0c\u9700\u8fde\u7eed\u547d\u4e2d"
    return "\u7b49\u5f85\u66f4\u591a\u8d5b\u540e\u6837\u672c"


def build_jc_bucket_feedback_summary(
    status: Mapping[str, object] | object,
    settlements: Sequence[Mapping[str, object]] | object,
) -> dict[str, object]:
    resolved = _as_mapping(status)
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    buckets: dict[str, dict[str, object]] = {}

    def ensure_bucket(item: Mapping[str, object]) -> dict[str, object] | None:
        if not _is_jc_bucket_item(item):
            return None
        key = _jc_bucket_key_from_item(item)
        if not key:
            return None
        bucket = _as_mapping(item.get("jc_bucket"))
        feedback = _as_mapping(item.get("jc_live_feedback"))
        current = buckets.setdefault(
            key,
            {
                "key": key,
                "dimension": bucket.get("dimension") or item.get("dimension") or "-",
                "bucket": bucket.get("bucket") or item.get("scope_value") or "-",
                "historical_accuracy": feedback.get("historical_accuracy", bucket.get("accuracy", item.get("accuracy", item.get("backtest_accuracy")))),
                "historical_wilson_lower": feedback.get("historical_wilson_lower", bucket.get("wilson_lower", item.get("wilson_lower"))),
                "historical_samples": bucket.get("sample_count", item.get("sample_count", item.get("backtest_samples", 0))),
                "historical_avg_confidence": bucket.get("avg_confidence", item.get("avg_confidence")),
                "historical_avg_pick_odds": bucket.get("avg_pick_odds", item.get("avg_pick_odds")),
                "hits": [],
                "confidence_buckets": [],
                "odds_buckets": [],
                "pick_odds_values": [],
                "confidence_values": [],
                "explicit_status": "",
            },
        )
        if feedback:
            current["explicit_status"] = str(feedback.get("status") or current.get("explicit_status") or "")
            for source_key, target_key in (
                ("historical_accuracy", "historical_accuracy"),
                ("historical_wilson_lower", "historical_wilson_lower"),
                ("live_count", "feedback_live_count"),
                ("live_hit_count", "feedback_live_hit_count"),
                ("live_hit_rate", "feedback_live_hit_rate"),
                ("deviation", "feedback_deviation"),
                ("miss_streak", "feedback_miss_streak"),
                ("recovery_streak", "feedback_recovery_streak"),
                ("recovery_hits_required", "feedback_recovery_hits_required"),
            ):
                if feedback.get(source_key) is not None:
                    current[target_key] = feedback.get(source_key)
            if feedback.get("recovery_status"):
                current["feedback_recovery_status"] = feedback.get("recovery_status")
        for source_key, target_key in (
            ("avg_confidence", "historical_avg_confidence"),
            ("avg_pick_odds", "historical_avg_pick_odds"),
            ("accuracy", "historical_accuracy"),
            ("wilson_lower", "historical_wilson_lower"),
            ("sample_count", "historical_samples"),
        ):
            if current.get(target_key) in (None, "") and bucket.get(source_key) not in (None, ""):
                current[target_key] = bucket.get(source_key)
        return current

    for pool_item in _strategy_pool(resolved):
        ensure_bucket(pool_item)
    for _settlement, item in _known_strategy_settlement_items(settlement_items):
        bucket_row = ensure_bucket(item)
        if bucket_row is None or item.get("is_hit") is None:
            continue
        hits = bucket_row.setdefault("hits", [])
        if isinstance(hits, list):
            hits.append(bool(item.get("is_hit")))
        context = _as_mapping(item.get("jc_context"))
        confidence_buckets = bucket_row.setdefault("confidence_buckets", [])
        odds_buckets = bucket_row.setdefault("odds_buckets", [])
        pick_odds_values = bucket_row.setdefault("pick_odds_values", [])
        confidence_values = bucket_row.setdefault("confidence_values", [])
        if isinstance(confidence_buckets, list) and context.get("confidence_bucket"):
            confidence_buckets.append(context.get("confidence_bucket"))
        if isinstance(odds_buckets, list) and context.get("odds_bucket"):
            odds_buckets.append(context.get("odds_bucket"))
        if isinstance(pick_odds_values, list) and context.get("pick_odds") not in (None, ""):
            pick_odds_values.append(context.get("pick_odds"))
        if isinstance(confidence_values, list) and item.get("confidence") not in (None, ""):
            confidence_values.append(item.get("confidence"))

    rows: list[dict[str, str]] = []
    status_counts = {"healthy": 0, "watch": 0, "downgraded": 0, "pending": 0}
    for bucket in buckets.values():
        hits = bucket.get("hits") if isinstance(bucket.get("hits"), list) else []
        live_count = len(hits) if hits else _safe_int(bucket.get("feedback_live_count"))
        live_hit_count = sum(1 for hit in hits if hit) if hits else _safe_int(bucket.get("feedback_live_hit_count"))
        live_hit_rate = live_hit_count / live_count if live_count else None
        if live_hit_rate is None and bucket.get("feedback_live_hit_rate") is not None:
            live_hit_rate = _safe_float(bucket.get("feedback_live_hit_rate"))
        miss_streak = 0
        if hits:
            for hit in hits:
                if hit:
                    break
                miss_streak += 1
        else:
            miss_streak = _safe_int(bucket.get("feedback_miss_streak"))
        recovery_streak = 0
        if hits:
            for hit in hits:
                if not hit:
                    break
                recovery_streak += 1
        else:
            recovery_streak = _safe_int(bucket.get("feedback_recovery_streak"))
        recovery_required = _safe_int(bucket.get("feedback_recovery_hits_required"), 3)
        recovery_status = str(bucket.get("feedback_recovery_status") or "")
        historical_accuracy = _safe_float(bucket.get("historical_accuracy"))
        historical_wilson = _safe_float(bucket.get("historical_wilson_lower"))
        deviation = live_hit_rate - historical_accuracy if live_hit_rate is not None else bucket.get("feedback_deviation")
        confidence_buckets = bucket.get("confidence_buckets") if isinstance(bucket.get("confidence_buckets"), list) else []
        odds_buckets = bucket.get("odds_buckets") if isinstance(bucket.get("odds_buckets"), list) else []
        live_avg_odds = _avg_float(bucket.get("pick_odds_values") if isinstance(bucket.get("pick_odds_values"), list) else [])
        live_avg_confidence = _avg_float(bucket.get("confidence_values") if isinstance(bucket.get("confidence_values"), list) else [])
        historical_avg_odds = _safe_float(bucket.get("historical_avg_pick_odds")) if bucket.get("historical_avg_pick_odds") not in (None, "") else None
        historical_avg_confidence = _safe_float(bucket.get("historical_avg_confidence")) if bucket.get("historical_avg_confidence") not in (None, "") else None
        status_text = _jc_bucket_summary_status(
            live_count=live_count,
            live_hit_rate=live_hit_rate,
            wilson_lower=historical_wilson,
            miss_streak=miss_streak,
            explicit_status=str(bucket.get("explicit_status") or ""),
        )
        status_counts[status_text] = status_counts.get(status_text, 0) + 1
        recovery_text = _jc_recovery_label(
            status_text=status_text,
            recovery_status=recovery_status,
            recovery_streak=recovery_streak,
            recovery_required=recovery_required,
        )
        diagnostics = _jc_bucket_diagnostics(
            status_text=status_text,
            live_count=live_count,
            live_hit_rate=live_hit_rate,
            historical_accuracy=historical_accuracy,
            historical_wilson=historical_wilson,
            deviation=deviation,
            miss_streak=miss_streak,
            live_avg_odds=live_avg_odds,
            historical_avg_odds=historical_avg_odds,
            live_avg_confidence=live_avg_confidence,
            historical_avg_confidence=historical_avg_confidence,
        )
        rows.append(
            {
                "title": f"{status_text.upper()} | {bucket.get('dimension') or '-'} / {bucket.get('bucket') or '-'}",
                "body": (
                    f"\u5386\u53f2: {_pct(historical_accuracy)} | Wilson {_pct(historical_wilson)} | \u6837\u672c {_safe_int(bucket.get('historical_samples'))}\n"
                    f"\u5b9e\u76d8: {live_hit_count}/{live_count} ({_pct(live_hit_rate)}) | \u504f\u5dee {_pct(deviation)} | \u8fde\u9519 {miss_streak}\n"
                    f"\u5206\u5e03: \u7f6e\u4fe1 {_most_common_text(confidence_buckets)} / \u8d54\u7387 {_most_common_text(odds_buckets)} | \u5747\u8d54 {_safe_float(live_avg_odds):.2f}/{_safe_float(historical_avg_odds):.2f}\n"
                    f"\u8bca\u65ad: {diagnostics}\n"
                    f"\u6062\u590d: {recovery_text}"
                ),
                "status": status_text,
                "live_count": str(live_count),
                "deviation": f"{_safe_float(deviation):.4f}" if deviation is not None else "",
                "diagnostics": diagnostics,
                "recovery_status": recovery_status,
                "recovery_streak": str(recovery_streak),
            }
        )

    priority = {"downgraded": 0, "watch": 1, "pending": 2, "healthy": 3}
    rows.sort(key=lambda row: (priority.get(row.get("status", "pending"), 9), _safe_float(row.get("deviation"), 0.0), -_safe_int(row.get("live_count"))))
    return {
        "total": len(rows),
        "status_counts": status_counts,
        "rows": rows[:8],
        "summary_text": (
            f"\u964d\u7ea7 {status_counts.get('downgraded', 0)} | \u89c2\u5bdf {status_counts.get('watch', 0)} | "
            f"\u5065\u5eb7 {status_counts.get('healthy', 0)} | \u5f85\u6837\u672c {status_counts.get('pending', 0)}"
        ),
    }


def _known_values(items: Sequence[Mapping[str, object]], key: str) -> list[bool]:
    return [bool(item.get(key)) for item in items if isinstance(item, Mapping) and item.get(key) is not None]


def _hit_rate(values: Sequence[bool]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def _strategy_decision_settlements(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    decision_field: str,
    decision_value: str = "allow",
) -> list[Mapping[str, object]]:
    if not isinstance(settlements, Sequence):
        return []
    target = str(decision_value or "").strip().lower()
    return [
        item
        for item in settlements
        if isinstance(item, Mapping) and str(item.get(decision_field) or "").strip().lower() == target
    ]


def _strategy_allowlist_settlements(settlements: Sequence[Mapping[str, object]] | object) -> list[Mapping[str, object]]:
    return _strategy_decision_settlements(settlements, decision_field="strategy_allowlist_decision")


def _strategy_formal_release_settlements(settlements: Sequence[Mapping[str, object]] | object) -> list[Mapping[str, object]]:
    return _strategy_decision_settlements(settlements, decision_field="strategy_admission_decision")


def _allowlist_failure_reasons(item: Mapping[str, object]) -> list[str]:
    reasons: list[str] = []
    if item.get("is_correct") is False:
        reasons.append("1X2 \u65b9\u5411\u5931\u8bef")
    if item.get("is_correct") is False and _safe_float(item.get("prediction_confidence")) >= 0.6:
        reasons.append("\u9ad8\u7f6e\u4fe1\u5931\u8bef")
    if item.get("handicap_is_correct") is False:
        reasons.append("\u8ba9\u7403\u5931\u8bef")
    if item.get("ou_is_correct") is False:
        reasons.append("\u5927\u5c0f\u7403\u5931\u8bef")
    active_count = _safe_int(item.get("high_accuracy_strategy_active_count"))
    hit_count = _safe_int(item.get("high_accuracy_strategy_hit_count"))
    if active_count > 0 and hit_count < active_count:
        reasons.append("\u9ad8\u51c6\u7b56\u7565\u672a\u5168\u547d\u4e2d")
    if not reasons:
        reasons.append("\u6682\u65e0\u660e\u663e\u5931\u8d25\u56e0\u5b50")
    return reasons


def _strategy_settlement_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    official_values = _known_values(rows, "is_correct")
    handicap_values = _known_values(rows, "handicap_is_correct")
    ou_values = _known_values(rows, "ou_is_correct")
    active_total = sum(_safe_int(item.get("high_accuracy_strategy_active_count")) for item in rows)
    active_hits = sum(_safe_int(item.get("high_accuracy_strategy_hit_count")) for item in rows)
    shadow_count = sum(1 for item in rows if _safe_int(item.get("high_accuracy_strategy_shadow_count")) > 0)
    high_conf_misses = sum(
        1
        for item in rows
        if item.get("is_correct") is False and _safe_float(item.get("prediction_confidence")) >= 0.6
    )
    reason_counter: dict[str, int] = {}
    for item in rows:
        if item.get("is_correct") is True:
            continue
        for reason in _allowlist_failure_reasons(item):
            if reason == "\u6682\u65e0\u660e\u663e\u5931\u8d25\u56e0\u5b50":
                continue
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
    top_failure = "-"
    if reason_counter:
        reason, count = sorted(reason_counter.items(), key=lambda pair: (-pair[1], pair[0]))[0]
        top_failure = f"{reason} {count}\u6b21"
    official_rate = _hit_rate(official_values)
    high_strategy_rate = active_hits / active_total if active_total else None
    return {
        "settled_count": len(rows),
        "sample_count": len(rows),
        "known_count": len(official_values),
        "hit_count": sum(1 for value in official_values if value),
        "miss_count": sum(1 for value in official_values if not value),
        "hit_rate": official_rate,
        "hit_rate_text": _pct(official_rate) if official_rate is not None else "-",
        "handicap_hit_rate_text": _pct(_hit_rate(handicap_values)) if handicap_values else "-",
        "ou_hit_rate_text": _pct(_hit_rate(ou_values)) if ou_values else "-",
        "high_strategy_summary": f"{active_hits}/{active_total}" if active_total else "-",
        "high_strategy_hit_rate": high_strategy_rate,
        "high_strategy_hit_rate_text": _pct(high_strategy_rate) if high_strategy_rate is not None else "-",
        "shadow_observed_count": shadow_count,
        "high_conf_misses": high_conf_misses,
        "top_failure": top_failure,
        "failure_counts": reason_counter,
        "settlements": list(rows),
    }


def build_strategy_allowlist_settlement_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    return _strategy_settlement_summary(_strategy_allowlist_settlements(settlements))


def build_strategy_formal_release_settlement_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    return _strategy_settlement_summary(_strategy_formal_release_settlements(settlements))


def build_strategy_allowlist_settlement_rows(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _strategy_allowlist_settlements(settlements)[: max(0, int(limit))]:
        hit = item.get("is_correct")
        hit_label = "\u547d\u4e2d" if hit is True else "\u5931\u8bef" if hit is False else "\u5f85\u5224\u5b9a"
        title = (
            f"{hit_label} | {item.get('league') or '-'} | "
            f"{item.get('home_team') or '-'} vs {item.get('away_team') or '-'}"
        )
        score = f"{item.get('home_goals', '-')}:{item.get('away_goals', '-')}"
        reasons_text = "\u3001".join(_allowlist_failure_reasons(item))
        body = "\n".join(
            [
                f"\u6e05\u5355: {item.get('strategy_allowlist_file') or '-'} | \u5bfc\u51fa {item.get('strategy_allowlist_exported_at') or '-'}",
                f"\u8d5b\u679c: {score} | \u9884\u6d4b {item.get('predicted') or '-'} | \u7f6e\u4fe1 {_pct(item.get('prediction_confidence'))}",
                f"\u9ad8\u51c6: {item.get('high_accuracy_strategy_summary') or '-'} | \u8ba9\u7403 {item.get('predicted_handicap') or '-'} / {'Y' if item.get('handicap_is_correct') is True else 'N' if item.get('handicap_is_correct') is False else '-'} | \u5927\u5c0f {item.get('predicted_ou') or '-'} / {'Y' if item.get('ou_is_correct') is True else 'N' if item.get('ou_is_correct') is False else '-'}",
                f"\u504f\u5dee: {reasons_text}",
            ]
        )
        rows.append({"title": title, "body": body})
    return rows


def _market_entropy_bucket(item: Mapping[str, object]) -> str:
    level = _text(item.get("market_entropy_level")).upper()
    score = _safe_float(item.get("market_entropy_score"))
    if level == "HIGH" or score >= 0.66:
        return "high"
    if level == "MEDIUM" or score >= 0.38:
        return "medium"
    return "low"


def _market_entropy_bucket_label(bucket: str) -> str:
    return {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(str(bucket or ""), "-")


def _handicap_margin_bucket(item: Mapping[str, object]) -> str:
    level = _text(item.get("handicap_margin_level")).upper()
    score = _safe_float(item.get("handicap_margin_score"))
    if level == "HIGH" or score >= 0.66:
        return "high"
    if level == "MEDIUM" or score >= 0.38:
        return "medium"
    return "low"


def _draw_guard_actual_is_draw(item: Mapping[str, object]) -> bool | None:
    home_goals = item.get("home_goals")
    away_goals = item.get("away_goals")
    if home_goals not in (None, "") and away_goals not in (None, ""):
        try:
            return int(home_goals) == int(away_goals)
        except (TypeError, ValueError):
            pass
    side = _actual_side(item.get("result"))
    if side:
        return side == "draw"
    return None


def _draw_guard_bucket_label(bucket: object) -> str:
    text = _text(bucket, "")
    return text or "unknown"


def build_draw_release_guard_review_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known: list[Mapping[str, object]] = []
    for item in settlement_items:
        if item.get("draw_release_guard_status") in (None, "") and item.get("draw_release_guard_blocked") is None:
            continue
        if _draw_guard_actual_is_draw(item) is None:
            continue
        known.append(item)

    bucket_rows: dict[str, dict[str, object]] = {}
    blocked_count = 0
    avoid_count = 0
    missed_count = 0
    allowed_draw_hits = 0
    score_sum = 0.0
    score_count = 0
    reason_counts: dict[str, int] = {}

    for item in known:
        bucket = _draw_guard_bucket_label(item.get("draw_release_guard_odds_bucket"))
        row = bucket_rows.setdefault(
            bucket,
            {
                "bucket": bucket,
                "label": bucket,
                "count": 0,
                "blocked_count": 0,
                "avoid_count": 0,
                "missed_count": 0,
                "allowed_draw_hits": 0,
                "score_sum": 0.0,
                "score_count": 0,
                "reasons": {},
            },
        )
        row["count"] = _safe_int(row.get("count")) + 1
        draw_score = item.get("draw_score")
        if draw_score not in (None, ""):
            row["score_sum"] = _safe_float(row.get("score_sum")) + _safe_float(draw_score)
            row["score_count"] = _safe_int(row.get("score_count")) + 1
            score_sum += _safe_float(draw_score)
            score_count += 1
        is_blocked = _safe_bool(item.get("draw_release_guard_blocked")) or _text(item.get("draw_release_guard_status"), "").lower() == "blocked"
        actual_draw = bool(_draw_guard_actual_is_draw(item))
        if is_blocked:
            blocked_count += 1
            row["blocked_count"] = _safe_int(row.get("blocked_count")) + 1
            reason = _text(item.get("draw_release_guard_reason"), "")
            if reason:
                reason_counts[reason] = _safe_int(reason_counts.get(reason)) + 1
                reasons = row.get("reasons") if isinstance(row.get("reasons"), dict) else {}
                reasons[reason] = _safe_int(reasons.get(reason)) + 1
                row["reasons"] = reasons
            if actual_draw:
                missed_count += 1
                row["missed_count"] = _safe_int(row.get("missed_count")) + 1
            else:
                avoid_count += 1
                row["avoid_count"] = _safe_int(row.get("avoid_count")) + 1
        elif actual_draw:
            allowed_draw_hits += 1
            row["allowed_draw_hits"] = _safe_int(row.get("allowed_draw_hits")) + 1

    rows: list[dict[str, object]] = []
    for bucket in sorted(bucket_rows):
        row = bucket_rows[bucket]
        row_blocked = _safe_int(row.get("blocked_count"))
        row_avoid = _safe_int(row.get("avoid_count"))
        row_missed = _safe_int(row.get("missed_count"))
        row_score_count = _safe_int(row.get("score_count"))
        reasons = row.get("reasons") if isinstance(row.get("reasons"), dict) else {}
        top_reason = "-"
        if reasons:
            top_reason = sorted(reasons.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        avoid_rate = row_avoid / row_blocked if row_blocked else None
        missed_rate = row_missed / row_blocked if row_blocked else None
        rows.append(
            {
                "bucket": bucket,
                "label": row.get("label") or bucket,
                "count": _safe_int(row.get("count")),
                "blocked_count": row_blocked,
                "avoid_count": row_avoid,
                "missed_count": row_missed,
                "allowed_draw_hits": _safe_int(row.get("allowed_draw_hits")),
                "avoid_rate": avoid_rate,
                "avoid_rate_text": _pct(avoid_rate) if avoid_rate is not None else "-",
                "missed_rate": missed_rate,
                "missed_rate_text": _pct(missed_rate) if missed_rate is not None else "-",
                "avg_draw_score": _safe_float(row.get("score_sum")) / row_score_count if row_score_count else None,
                "avg_draw_score_text": _pct(_safe_float(row.get("score_sum")) / row_score_count) if row_score_count else "-",
                "top_reason": top_reason,
            }
        )

    total = len(known)
    avoid_rate = avoid_count / blocked_count if blocked_count else None
    missed_rate = missed_count / blocked_count if blocked_count else None
    avg_draw_score = score_sum / score_count if score_count else None
    if total < 5 or blocked_count < 2:
        recommendation = "collecting"
        recommendation_text = "\u6837\u672c\u4e0d\u8db3\uff0c\u7ee7\u7eed\u89c2\u5bdf\u5e73\u5c40\u62e6\u622a\u540e\u7684\u8d5b\u679c\u56de\u6536\u6548\u679c\u3002"
    elif avoid_rate is not None and avoid_rate >= 0.67 and (missed_rate or 0.0) <= 0.20:
        recommendation = "keep_draw_guard"
        recommendation_text = "\u62e6\u622a\u5e73\u5c40\u63a5\u7ba1\u540e\u8f83\u591a\u907f\u514d\u5047\u9633\u6027\uff0c\u5efa\u8bae\u7ee7\u7eed\u4fdd\u7559\u5f53\u524d\u95e8\u69db\u3002"
    elif missed_rate is not None and missed_rate >= 0.34:
        recommendation = "loosen_draw_guard"
        recommendation_text = "\u88ab\u62e6\u622a\u573a\u6b21\u4e2d\u771f\u5e73\u5c40\u5360\u6bd4\u504f\u9ad8\uff0c\u5efa\u8bae\u653e\u5bbd\u5f31\u8d54\u7387\u6876\u95e8\u69db\u6216\u8f6c\u4eba\u5de5\u590d\u6838\u3002"
    else:
        recommendation = "monitor"
        recommendation_text = "\u6682\u672a\u8bc1\u660e\u9700\u8981\u8c03\u6574\u5e73\u5c40\u62e6\u622a\u95e8\u69db\uff0c\u7ee7\u7eed\u8ffd\u8e2a\u3002"
    return {
        "sample_count": total,
        "blocked_count": blocked_count,
        "avoided_false_positive": avoid_count,
        "missed_draw_hit": missed_count,
        "allowed_draw_hits": allowed_draw_hits,
        "avoid_rate": avoid_rate,
        "avoid_rate_text": _pct(avoid_rate) if avoid_rate is not None else "-",
        "missed_rate": missed_rate,
        "missed_rate_text": _pct(missed_rate) if missed_rate is not None else "-",
        "avg_draw_score": avg_draw_score,
        "avg_draw_score_text": _pct(avg_draw_score) if avg_draw_score is not None else "-",
        "top_reason": sorted(reason_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0] if reason_counts else "-",
        "rows": rows,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "summary_text": (
            f"\u6837\u672c {total} | \u62e6\u622a {blocked_count} | "
            f"\u907f\u514d\u5047\u9633 {avoid_count} | \u9519\u8fc7\u771f\u5e73 {missed_count} | \u907f\u514d\u7387 {_pct(avoid_rate) if avoid_rate is not None else '-'}"
        ),
    }


def _draw_guard_policy_from_status(policy_status: Mapping[str, object] | object | None) -> dict[str, object]:
    status = _as_mapping(policy_status)
    policy = _as_mapping(status.get("policy"))
    if not policy and status:
        policy = status
    weak_buckets = policy.get("weak_odds_buckets") if isinstance(policy.get("weak_odds_buckets"), Mapping) else {}
    return {
        "enabled": bool(policy.get("enabled", True)),
        "min_score": round(_safe_float(policy.get("min_score"), 0.58), 2),
        "weak_odds_buckets": {str(key): dict(value) for key, value in weak_buckets.items() if isinstance(value, Mapping)},
    }


def build_draw_release_guard_policy_tuning_recommendation(
    settlements: Sequence[Mapping[str, object]] | object,
    policy_status: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    review = build_draw_release_guard_review_summary(settlements)
    current_policy = _draw_guard_policy_from_status(policy_status)
    current_min_score = _safe_float(current_policy.get("min_score"), 0.58)
    current_buckets = current_policy.get("weak_odds_buckets") if isinstance(current_policy.get("weak_odds_buckets"), dict) else {}
    next_buckets = {str(key): dict(value) for key, value in current_buckets.items() if isinstance(value, Mapping)}
    next_min_score = current_min_score
    reasons: list[str] = []
    removed_buckets: list[str] = []
    action = "collect"
    label = "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c"
    tone = "neutral"

    sample_count = _safe_int(review.get("sample_count"))
    blocked_count = _safe_int(review.get("blocked_count"))
    avoid_rate = review.get("avoid_rate")
    missed_rate = review.get("missed_rate")
    avoid_value = _safe_float(avoid_rate, -1.0) if avoid_rate is not None else None
    missed_value = _safe_float(missed_rate, -1.0) if missed_rate is not None else None
    rows = [row for row in review.get("rows", []) if isinstance(row, Mapping)] if isinstance(review.get("rows"), list) else []

    if sample_count < 5 or blocked_count < 2:
        reasons.append(f"\u5e73\u5c40\u62e6\u622a\u53ef\u590d\u76d8\u6837\u672c {sample_count} \u573a\uff0c\u62e6\u622a {blocked_count} \u573a\uff0c\u6682\u4e0d\u81ea\u52a8\u6539\u53c2\u3002")
    else:
        for row in rows:
            bucket = str(row.get("bucket") or "")
            row_blocked = _safe_int(row.get("blocked_count"))
            row_avoid = row.get("avoid_rate")
            row_missed = row.get("missed_rate")
            row_avoid_value = _safe_float(row_avoid, -1.0) if row_avoid is not None else None
            row_missed_value = _safe_float(row_missed, -1.0) if row_missed is not None else None
            if (
                bucket in next_buckets
                and row_blocked >= 3
                and row_missed_value is not None
                and row_missed_value >= 0.34
                and (row_avoid_value is None or row_avoid_value < 0.67)
            ):
                removed_buckets.append(bucket)
        if removed_buckets:
            action = "loosen_guard"
            label = "\u79fb\u9664\u9ad8\u4ee3\u4ef7\u5f31\u8d54\u7387\u6876"
            tone = "warning"
            for bucket in removed_buckets:
                next_buckets.pop(bucket, None)
            reasons.append(f"\u4ee5\u4e0b\u8d54\u7387\u6876\u62e6\u622a\u540e\u771f\u5e73\u5c40\u6210\u672c\u504f\u9ad8\uff0c\u5efa\u8bae\u79fb\u9664\uff1a{', '.join(removed_buckets)}\u3002")
        elif missed_value is not None and missed_value >= 0.34:
            action = "loosen_guard"
            label = "\u62ac\u9ad8\u62e6\u622a\u5206\u6570\u7ebf"
            tone = "warning"
            next_min_score = round(min(0.72, current_min_score + 0.04), 2)
            reasons.append(f"\u88ab\u62e6\u622a\u573a\u6b21\u4e2d\u771f\u5e73\u5c40\u5360\u6bd4 {review.get('missed_rate_text', '-')}\uff0c\u5efa\u8bae\u63d0\u9ad8\u62e6\u622a\u5206\u6570\u7ebf\u3002")
        elif blocked_count >= 5 and avoid_value is not None and missed_value is not None and avoid_value >= 0.75 and missed_value <= 0.10:
            action = "tighten_guard"
            label = "\u5c0f\u5e45\u964d\u4f4e\u62e6\u622a\u5206\u6570\u7ebf"
            tone = "good"
            next_min_score = round(max(0.54, current_min_score - 0.02), 2)
            reasons.append(f"\u62e6\u622a\u907f\u514d\u5047\u9633\u7387 {review.get('avoid_rate_text', '-')}\uff0c\u4e14\u9519\u8fc7\u771f\u5e73 {review.get('missed_rate_text', '-')}\uff0c\u53ef\u5c0f\u5e45\u52a0\u5f3a\u62e6\u622a\u3002")
        else:
            action = "hold"
            label = "\u4fdd\u6301\u5f53\u524d\u7b56\u7565"
            tone = "good" if str(review.get("recommendation") or "") == "keep_draw_guard" else "neutral"
            reasons.append("\u5f53\u524d\u590d\u76d8\u4e0d\u652f\u6301\u8fdb\u4e00\u6b65\u6536\u7d27\u6216\u653e\u5bbd\uff0c\u5148\u7ef4\u6301\u73b0\u6709\u7b56\u7565\u3002")

    next_policy = {
        "enabled": bool(current_policy.get("enabled", True)),
        "min_score": round(next_min_score, 2),
        "weak_odds_buckets": next_buckets,
    }
    changed = round(next_min_score, 2) != round(current_min_score, 2) or sorted(next_buckets.keys()) != sorted(current_buckets.keys())
    policy_update = next_policy if action in {"loosen_guard", "tighten_guard"} and changed else {}
    rows_out = [
        ("\u52a8\u4f5c", label),
        ("\u6837\u672c", f"{sample_count} \u573a | \u62e6\u622a {blocked_count} | \u907f\u514d {review.get('avoid_rate_text', '-')} | \u9519\u8fc7 {review.get('missed_rate_text', '-')}"),
        ("\u5206\u6570\u7ebf", f"{current_min_score:.2f} -> {next_min_score:.2f}"),
        ("\u5f31\u8d54\u7387\u6876", f"{', '.join(sorted(current_buckets)) or '-'} -> {', '.join(sorted(next_buckets)) or '-'}"),
        ("\u79fb\u9664\u6876", ", ".join(removed_buckets) or "-"),
        ("\u539f\u56e0", "\n".join(reasons) if reasons else "-"),
    ]
    return {
        "source": "draw_release_guard_tuning",
        "action": action,
        "label": label,
        "tone": tone,
        "current_policy": current_policy,
        "next_policy": next_policy,
        "policy_update": policy_update,
        "changed": bool(policy_update),
        "reasons": reasons,
        "rows": rows_out,
        "review": review,
        "summary_text": f"{label} | {review.get('summary_text', '-')}",
    }


def _draw_guard_policy_direction(item: Mapping[str, object]) -> str:
    policy = _draw_guard_policy_from_status(item.get("policy") if isinstance(item.get("policy"), Mapping) else item)
    previous = _draw_guard_policy_from_status(item.get("previous_policy") if isinstance(item.get("previous_policy"), Mapping) else {})
    policy_min = _safe_float(policy.get("min_score"), 0.58)
    previous_min = _safe_float(previous.get("min_score"), policy_min)
    policy_buckets = set((_as_mapping(policy.get("weak_odds_buckets"))).keys())
    previous_buckets = set((_as_mapping(previous.get("weak_odds_buckets"))).keys())
    if policy_min > previous_min or len(policy_buckets) < len(previous_buckets):
        return "loosen"
    if policy_min < previous_min or len(policy_buckets) > len(previous_buckets):
        return "tighten"
    return "hold"


def _draw_guard_effect_label(status: str) -> str:
    labels = {
        "effective": "\u5e73\u5c40\u8c03\u53c2\u751f\u6548",
        "negative": "\u5e73\u5c40\u8c03\u53c2\u56de\u9000",
        "watch": "\u5e73\u5c40\u8c03\u53c2\u89c2\u5bdf",
        "collecting": "\u5e73\u5c40\u8c03\u53c2\u6837\u672c\u79ef\u7d2f\u4e2d",
        "none": "\u6682\u65e0\u5e73\u5c40\u8c03\u53c2\u7248\u672c",
    }
    return labels.get(status, labels["watch"])


def _draw_guard_effect_tone(status: str) -> str:
    if status == "effective":
        return "good"
    if status == "negative":
        return "bad"
    if status == "watch":
        return "warning"
    return "neutral"


def _draw_guard_rollback_effect_label(status: str) -> str:
    labels = {
        "effective": "DrawGuard回滚修复生效",
        "negative": "DrawGuard回滚后仍回退",
        "watch": "DrawGuard回滚后观察",
        "collecting": "DrawGuard回滚样本积累中",
        "none": "暂无DrawGuard回滚版本",
    }
    return labels.get(status, labels["watch"])


def _draw_guard_rollback_source_version(source: object) -> str:
    text = _text(source, "").strip()
    if not text:
        return ""
    lowered = text.lower()
    for prefix in ("draw_guard_policy_rollback:", "draw_release_guard_policy_rollback:"):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return ""


def _draw_guard_freeze_override_source_version(source: object) -> str:
    text = _text(source, "").strip()
    if not text:
        return ""
    lowered = text.lower()
    for prefix in ("draw_guard_freeze_override:", "draw_release_guard_freeze_override:"):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return ""


def _draw_guard_is_rollback_source(source: object) -> bool:
    lowered = _text(source, "").strip().lower()
    return "draw_guard_policy_rollback" in lowered or "draw_release_guard_policy_rollback" in lowered


def _draw_guard_effect_row_by_version(rows: Sequence[Mapping[str, object]], version_id: object) -> dict[str, object]:
    key = _text(version_id, "")
    if not key:
        return {}
    for row in rows:
        if isinstance(row, Mapping) and _text(row.get("version_id"), "") == key:
            return dict(row)
    return {}


def build_draw_release_guard_tuning_effect_review(
    policy_history: Sequence[Mapping[str, object]] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    min_blocked_samples: int = 3,
    min_delta: float = 0.10,
    limit: int = 5,
) -> dict[str, object]:
    history_items = [item for item in policy_history if isinstance(item, Mapping)] if isinstance(policy_history, Sequence) else []
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    parsed_history: list[dict[str, object]] = []
    for item in history_items:
        updated_at = _parse_policy_review_time(item.get("updated_at"))
        if updated_at is None:
            continue
        parsed_history.append({**dict(item), "_updated_dt": updated_at})
    parsed_history.sort(key=lambda item: item["_updated_dt"])
    if not parsed_history:
        label = _draw_guard_effect_label("none")
        return {
            "status": "none",
            "label": label,
            "tone": "neutral",
            "history_count": 0,
            "summary_text": f"{label} | \u5c1a\u672a\u5e94\u7528 DrawGuard \u8c03\u53c2\u7248\u672c\u3002",
            "recommendation_text": "\u5148\u5e94\u7528\u5e73\u5c40\u62e6\u622a\u8c03\u53c2\uff0c\u518d\u7528\u540e\u7eed\u8d5b\u679c\u56de\u6536\u9a8c\u8bc1\u6548\u679c\u3002",
            "latest_version_id": "-",
            "latest_source": "-",
            "post_blocked_count": 0,
            "pre_blocked_count": 0,
            "avoid_rate_delta": None,
            "missed_rate_delta": None,
            "avoid_rate_delta_text": "-",
            "missed_rate_delta_text": "-",
            "metrics": [],
            "rows": [],
        }

    rows: list[dict[str, object]] = []
    previous_review: Mapping[str, object] | None = None
    for index, item in enumerate(parsed_history):
        start = item["_updated_dt"]
        end = parsed_history[index + 1]["_updated_dt"] if index + 1 < len(parsed_history) else None
        window_items = []
        for settlement in settlement_items:
            settled_at = _settlement_review_time(settlement)
            if settled_at is None or settled_at < start:
                continue
            if end is not None and settled_at >= end:
                continue
            window_items.append(settlement)
        review = build_draw_release_guard_review_summary(window_items)
        direction = _draw_guard_policy_direction(item)
        post_blocked = _safe_int(review.get("blocked_count"))
        post_avoid = review.get("avoid_rate")
        post_missed = review.get("missed_rate")
        pre_blocked = _safe_int(previous_review.get("blocked_count")) if isinstance(previous_review, Mapping) else 0
        pre_avoid = previous_review.get("avoid_rate") if isinstance(previous_review, Mapping) else None
        pre_missed = previous_review.get("missed_rate") if isinstance(previous_review, Mapping) else None
        avoid_delta = _safe_float(post_avoid) - _safe_float(pre_avoid) if post_avoid is not None and pre_avoid is not None else None
        missed_delta = _safe_float(post_missed) - _safe_float(pre_missed) if post_missed is not None and pre_missed is not None else None
        if post_blocked < max(1, int(min_blocked_samples)) or pre_blocked < max(1, int(min_blocked_samples)) or avoid_delta is None or missed_delta is None:
            status = "collecting"
        elif direction == "loosen":
            if missed_delta <= -abs(float(min_delta)):
                status = "effective"
            elif missed_delta >= abs(float(min_delta)) or avoid_delta <= -abs(float(min_delta)):
                status = "negative"
            else:
                status = "watch"
        elif direction == "tighten":
            if avoid_delta >= abs(float(min_delta)) and missed_delta <= 0.05:
                status = "effective"
            elif missed_delta >= abs(float(min_delta)) or avoid_delta <= -abs(float(min_delta)):
                status = "negative"
            else:
                status = "watch"
        else:
            if missed_delta <= -abs(float(min_delta)) or avoid_delta >= abs(float(min_delta)):
                status = "effective"
            elif missed_delta >= abs(float(min_delta)) or avoid_delta <= -abs(float(min_delta)):
                status = "negative"
            else:
                status = "watch"
        label = _draw_guard_effect_label(status)
        tone = _draw_guard_effect_tone(status)
        source = _text(item.get("source") or item.get("reason"), "-")
        version_id = _text(item.get("version_id"), "-")
        body = (
            f"\u7248\u672c {version_id} | \u65b9\u5411 {direction} | "
            f"\u62e6\u622a {post_blocked} | \u907f\u514d {review.get('avoid_rate_text', '-')} ({_pct(avoid_delta) if avoid_delta is not None else '-'}) | "
            f"\u9519\u8fc7 {review.get('missed_rate_text', '-')} ({_pct(missed_delta) if missed_delta is not None else '-'})"
        )
        rows.append(
            {
                "version_id": version_id,
                "updated_at": item.get("updated_at", "-"),
                "source": source,
                "direction": direction,
                "sample_count": _safe_int(review.get("sample_count")),
                "blocked_count": post_blocked,
                "avoid_rate": post_avoid,
                "avoid_rate_text": review.get("avoid_rate_text", "-"),
                "missed_rate": post_missed,
                "missed_rate_text": review.get("missed_rate_text", "-"),
                "pre_blocked_count": pre_blocked,
                "pre_avoid_rate": pre_avoid,
                "pre_avoid_rate_text": _pct(pre_avoid) if pre_avoid is not None else "-",
                "pre_missed_rate": pre_missed,
                "pre_missed_rate_text": _pct(pre_missed) if pre_missed is not None else "-",
                "avoid_rate_delta": avoid_delta,
                "avoid_rate_delta_text": _pct(avoid_delta) if avoid_delta is not None else "-",
                "missed_rate_delta": missed_delta,
                "missed_rate_delta_text": _pct(missed_delta) if missed_delta is not None else "-",
                "effect_status": status,
                "effect_label": label,
                "tone": tone,
                "title": f"{label} | {source} | {item.get('updated_at', '-')}",
                "body": body,
                "review": review,
            }
        )
        previous_review = review

    rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    latest = rows[0] if rows else {}
    latest_status = str(latest.get("effect_status") or "none")
    latest_label = str(latest.get("effect_label") or _draw_guard_effect_label(latest_status))
    if latest_status == "effective":
        recommendation = "\u5e73\u5c40\u62e6\u622a\u8c03\u53c2\u540e\u6838\u5fc3\u6307\u6807\u6539\u5584\uff0c\u7ee7\u7eed\u4fdd\u7559\u5f53\u524d\u7248\u672c\u5e76\u7d2f\u79ef\u6837\u672c\u3002"
    elif latest_status == "negative":
        recommendation = "\u5e73\u5c40\u62e6\u622a\u8c03\u53c2\u540e\u6307\u6807\u56de\u9000\uff0c\u4f18\u5148\u590d\u6838\u8be5\u7248\u672c\u7684\u9519\u8fc7\u771f\u5e73\u548c\u907f\u514d\u5047\u9633\u6837\u672c\u3002"
    elif latest_status == "watch":
        recommendation = "\u6682\u65e0\u660e\u786e\u6539\u5584\u6216\u56de\u9000\uff0c\u7ef4\u6301\u89c2\u5bdf\u3002"
    else:
        recommendation = "\u8c03\u53c2\u540e\u62e6\u622a\u6837\u672c\u6216\u5bf9\u7167\u6837\u672c\u4e0d\u8db3\uff0c\u6682\u4e0d\u5224\u5b9a\u6548\u679c\u3002"
    metrics = [
        {"label": "\u751f\u6548\u72b6\u6001", "value": latest_label, "tone": str(latest.get("tone") or "neutral")},
        {"label": "\u540e\u7eed\u62e6\u622a", "value": str(latest.get("blocked_count", 0)), "tone": "neutral"},
        {"label": "\u907f\u514d\u53d8\u5316", "value": str(latest.get("avoid_rate_delta_text") or "-"), "tone": "good" if _safe_float(latest.get("avoid_rate_delta"), 0.0) > 0 else "bad" if latest.get("avoid_rate_delta") is not None else "neutral"},
        {"label": "\u9519\u8fc7\u53d8\u5316", "value": str(latest.get("missed_rate_delta_text") or "-"), "tone": "good" if latest.get("missed_rate_delta") is not None and _safe_float(latest.get("missed_rate_delta"), 0.0) < 0 else "bad" if latest.get("missed_rate_delta") is not None else "neutral"},
    ]
    return {
        "status": latest_status,
        "label": latest_label,
        "tone": str(latest.get("tone") or "neutral"),
        "history_count": len(parsed_history),
        "rollback_recommended": latest_status == "negative",
        "rollback_candidate_version_id": latest.get("version_id", "-") if latest_status == "negative" else "-",
        "summary_text": (
            f"\u7248\u672c {len(parsed_history)} | \u6700\u65b0 {latest_label} | "
            f"\u907f\u514d\u53d8\u5316 {latest.get('avoid_rate_delta_text', '-') if latest else '-'} | "
            f"\u9519\u8fc7\u53d8\u5316 {latest.get('missed_rate_delta_text', '-') if latest else '-'}"
        ),
        "recommendation_text": recommendation,
        "latest_version_id": latest.get("version_id", "-") if latest else "-",
        "latest_source": latest.get("source", "-") if latest else "-",
        "post_blocked_count": _safe_int(latest.get("blocked_count")) if latest else 0,
        "pre_blocked_count": _safe_int(latest.get("pre_blocked_count")) if latest else 0,
        "avoid_rate_delta": latest.get("avoid_rate_delta") if latest else None,
        "missed_rate_delta": latest.get("missed_rate_delta") if latest else None,
        "avoid_rate_delta_text": latest.get("avoid_rate_delta_text", "-") if latest else "-",
        "missed_rate_delta_text": latest.get("missed_rate_delta_text", "-") if latest else "-",
        "metrics": metrics,
        "rows": rows[: max(0, int(limit))],
        "all_rows": rows,
    }


def build_draw_release_guard_rollback_effect_review(
    policy_history: Sequence[Mapping[str, object]] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    min_blocked_samples: int = 3,
    min_delta: float = 0.10,
    limit: int = 5,
) -> dict[str, object]:
    tuning_effect = build_draw_release_guard_tuning_effect_review(
        policy_history,
        settlements,
        min_blocked_samples=min_blocked_samples,
        min_delta=min_delta,
        limit=limit,
    )
    source_rows = _as_list(tuning_effect.get("all_rows")) or _as_list(tuning_effect.get("rows"))
    rows = [dict(row) for row in source_rows if isinstance(row, Mapping)]
    rows.sort(key=lambda row: (_parse_policy_review_time(row.get("updated_at")) or datetime.min, str(row.get("version_id") or "")))
    rollback_indexes = [
        (index, row)
        for index, row in enumerate(rows)
        if _draw_guard_is_rollback_source(row.get("source"))
    ]
    if not rollback_indexes:
        label = _draw_guard_rollback_effect_label("none")
        return {
            "status": "collecting",
            "label": label,
            "tone": "neutral",
            "summary_text": f"{label} | 尚未找到 DrawGuard 回滚版本。",
            "recommendation_text": "执行 DrawGuard 回滚并完成后续赛果回收后，再判断回滚是否修复调参回退。",
            "latest_version_id": "-",
            "latest_source": "-",
            "latest_updated_at": "-",
            "rolled_back_version_id": "-",
            "post_blocked_count": 0,
            "rolled_back_blocked_count": 0,
            "post_avoid_rate": None,
            "rolled_back_avoid_rate": None,
            "post_missed_rate": None,
            "rolled_back_missed_rate": None,
            "avoid_rate_delta": None,
            "missed_rate_delta": None,
            "avoid_rate_delta_text": "-",
            "missed_rate_delta_text": "-",
            "metrics": [],
            "rows": [],
        }

    latest_index, rollback_row = rollback_indexes[-1]
    rolled_back_version_id = _draw_guard_rollback_source_version(rollback_row.get("source"))
    rolled_back_row = _draw_guard_effect_row_by_version(rows, rolled_back_version_id)
    if not rolled_back_row and latest_index > 0:
        rolled_back_row = rows[latest_index - 1]

    post_blocked = _safe_int(rollback_row.get("blocked_count"))
    prior_blocked = _safe_int(rolled_back_row.get("blocked_count"))
    post_avoid = rollback_row.get("avoid_rate")
    prior_avoid = rolled_back_row.get("avoid_rate") if rolled_back_row else None
    post_missed = rollback_row.get("missed_rate")
    prior_missed = rolled_back_row.get("missed_rate") if rolled_back_row else None
    avoid_delta = _safe_float(post_avoid) - _safe_float(prior_avoid) if post_avoid is not None and prior_avoid is not None else None
    missed_delta = _safe_float(post_missed) - _safe_float(prior_missed) if post_missed is not None and prior_missed is not None else None

    sample_floor = max(1, int(min_blocked_samples))
    delta_floor = abs(float(min_delta))
    if post_blocked < sample_floor or prior_blocked < sample_floor or avoid_delta is None or missed_delta is None:
        status = "collecting"
    elif missed_delta <= -delta_floor or avoid_delta >= delta_floor:
        status = "effective"
    elif missed_delta >= delta_floor or avoid_delta <= -delta_floor:
        status = "negative"
    else:
        status = "watch"

    label = _draw_guard_rollback_effect_label(status)
    tone = _draw_guard_effect_tone(status)
    if status == "effective":
        recommendation = "回滚后错过真平下降或避免假阳恢复，继续按回滚后版本观察下一批回收样本。"
    elif status == "negative":
        recommendation = "回滚后仍未修复核心指标，暂停继续调参，优先复核回滚后的错过真平和赔率桶样本。"
    elif status == "watch":
        recommendation = "回滚后暂未出现足够明确修复或恶化，维持观察并继续回收样本。"
    else:
        recommendation = "回滚后可判断样本不足，暂不下修复结论。"

    detail_rows: list[dict[str, object]] = []
    for index, row in reversed(rollback_indexes[-max(1, int(limit)) :]):
        source_version = _draw_guard_rollback_source_version(row.get("source"))
        compare_row = _draw_guard_effect_row_by_version(rows, source_version)
        if not compare_row and index > 0:
            compare_row = rows[index - 1]
        row_avoid = row.get("avoid_rate")
        compare_avoid = compare_row.get("avoid_rate") if compare_row else None
        row_missed = row.get("missed_rate")
        compare_missed = compare_row.get("missed_rate") if compare_row else None
        row_avoid_delta = _safe_float(row_avoid) - _safe_float(compare_avoid) if row_avoid is not None and compare_avoid is not None else None
        row_missed_delta = _safe_float(row_missed) - _safe_float(compare_missed) if row_missed is not None and compare_missed is not None else None
        detail_rows.append(
            {
                "title": f"{row.get('updated_at', '-')} | 回滚 {row.get('version_id', '-')} -> 对照 {compare_row.get('version_id', source_version or '-')}",
                "body": (
                    f"回滚后拦截 {row.get('blocked_count', 0)} | 避免 {row.get('avoid_rate_text', '-')} ({_pct(row_avoid_delta) if row_avoid_delta is not None else '-'}) | "
                    f"错过 {row.get('missed_rate_text', '-')} ({_pct(row_missed_delta) if row_missed_delta is not None else '-'}) | "
                    f"被回滚版本拦截 {compare_row.get('blocked_count', 0)}"
                ),
                "version_id": row.get("version_id", "-"),
                "rolled_back_version_id": compare_row.get("version_id", source_version or "-"),
                "updated_at": row.get("updated_at", "-"),
                "post_blocked_count": _safe_int(row.get("blocked_count")),
                "rolled_back_blocked_count": _safe_int(compare_row.get("blocked_count")),
                "avoid_rate_delta": row_avoid_delta,
                "missed_rate_delta": row_missed_delta,
                "avoid_rate_delta_text": _pct(row_avoid_delta) if row_avoid_delta is not None else "-",
                "missed_rate_delta_text": _pct(row_missed_delta) if row_missed_delta is not None else "-",
            }
        )

    metrics = [
        {"label": "回滚修复", "value": label, "tone": tone},
        {"label": "回滚后拦截", "value": str(post_blocked), "tone": "neutral"},
        {"label": "避免变化", "value": _pct(avoid_delta) if avoid_delta is not None else "-", "tone": "good" if avoid_delta is not None and avoid_delta > 0 else "bad" if avoid_delta is not None else "neutral"},
        {"label": "错过变化", "value": _pct(missed_delta) if missed_delta is not None else "-", "tone": "good" if missed_delta is not None and missed_delta < 0 else "bad" if missed_delta is not None else "neutral"},
    ]
    summary_text = (
        f"{label} | 回滚 {rollback_row.get('version_id', '-')} | "
        f"被回滚 {rolled_back_row.get('version_id', rolled_back_version_id or '-')} | "
        f"避免变化 {_pct(avoid_delta) if avoid_delta is not None else '-'} | "
        f"错过变化 {_pct(missed_delta) if missed_delta is not None else '-'}"
    )
    return {
        "status": status,
        "label": label,
        "tone": tone,
        "summary_text": summary_text,
        "recommendation_text": recommendation,
        "latest_version_id": rollback_row.get("version_id", "-"),
        "latest_source": rollback_row.get("source", "-"),
        "latest_updated_at": rollback_row.get("updated_at", "-"),
        "rolled_back_version_id": rolled_back_row.get("version_id", rolled_back_version_id or "-"),
        "post_blocked_count": post_blocked,
        "rolled_back_blocked_count": prior_blocked,
        "post_avoid_rate": post_avoid,
        "rolled_back_avoid_rate": prior_avoid,
        "post_missed_rate": post_missed,
        "rolled_back_missed_rate": prior_missed,
        "avoid_rate_delta": avoid_delta,
        "missed_rate_delta": missed_delta,
        "avoid_rate_delta_text": _pct(avoid_delta) if avoid_delta is not None else "-",
        "missed_rate_delta_text": _pct(missed_delta) if missed_delta is not None else "-",
        "min_blocked_samples": sample_floor,
        "metrics": metrics,
        "rows": detail_rows,
    }


def build_draw_release_guard_freeze_override_status(
    policy_history: Sequence[Mapping[str, object]] | object,
    rollback_effect_review: Mapping[str, object] | object,
) -> dict[str, object]:
    rollback_effect = _as_mapping(rollback_effect_review)
    rollback_status = str(rollback_effect.get("status") or "")
    rollback_version = _text(rollback_effect.get("latest_version_id"), "")
    rollback_updated_at = _parse_policy_review_time(rollback_effect.get("latest_updated_at")) or datetime.min
    if rollback_status != "negative":
        return {
            "status": "inactive",
            "label": "无需解除DrawGuard冻结",
            "tone": "neutral",
            "override_active": False,
            "rollback_version_id": rollback_version or "-",
            "override_version_id": "-",
            "summary_text": "当前没有 DrawGuard 回滚失败导致的调参冻结。",
        }

    history_items = [dict(item) for item in policy_history if isinstance(item, Mapping)] if isinstance(policy_history, Sequence) else []
    overrides: list[dict[str, object]] = []
    for item in history_items:
        source = str(item.get("source") or "")
        source_lower = source.lower()
        if not (source_lower.startswith("draw_guard_freeze_override") or source_lower.startswith("draw_release_guard_freeze_override")):
            continue
        source_version = _draw_guard_freeze_override_source_version(source)
        updated_at = _parse_policy_review_time(item.get("updated_at")) or datetime.min
        if source_version and rollback_version and source_version != rollback_version:
            continue
        if updated_at < rollback_updated_at:
            continue
        overrides.append({**item, "_updated_dt": updated_at, "_source_version": source_version})
    overrides.sort(key=lambda item: (_parse_policy_review_time(item.get("updated_at")) or datetime.min, str(item.get("version_id") or "")), reverse=True)
    if overrides:
        latest = overrides[0]
        label = "DrawGuard冻结已人工解除"
        return {
            "status": "overridden",
            "label": label,
            "tone": "warning",
            "override_active": True,
            "rollback_version_id": rollback_version or "-",
            "override_version_id": latest.get("version_id", "-"),
            "override_source": latest.get("source", "-"),
            "override_updated_at": latest.get("updated_at", "-"),
            "summary_text": f"{label} | 回滚 {rollback_version or '-'} | 审计 {latest.get('version_id', '-')} | {latest.get('updated_at', '-')}",
        }

    label = "DrawGuard调参冻结中"
    return {
        "status": "frozen",
        "label": label,
        "tone": "bad",
        "override_active": False,
        "rollback_version_id": rollback_version or "-",
        "override_version_id": "-",
        "summary_text": f"{label} | 回滚 {rollback_version or '-'} 修复失败，需人工复核后解除。",
    }


def build_draw_release_guard_tuning_guard(
    tuning: Mapping[str, object] | object | None = None,
    *,
    rollback_effect_review: Mapping[str, object] | object | None = None,
    freeze_override_status: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    tuning_payload = _as_mapping(tuning)
    rollback_effect = _as_mapping(rollback_effect_review)
    freeze_override = _as_mapping(freeze_override_status)
    rollback_status = str(rollback_effect.get("status") or "")
    override_status = str(freeze_override.get("status") or "")
    action = str(tuning_payload.get("action") or "").strip()

    if rollback_status == "negative" and override_status == "overridden":
        decision = "confirm"
        label = "DrawGuard冻结已人工解除"
        tone = "warning"
        reasons = [
            f"回滚修复状态: {rollback_effect.get('label', '-')}",
            str(rollback_effect.get("summary_text") or "-"),
            f"解除冻结审计: {freeze_override.get('summary_text', '-')}",
            "回滚失败信号仍存在，继续应用 DrawGuard 调参前需要再次人工确认。",
        ]
    elif rollback_status == "negative":
        decision = "freeze"
        label = "DrawGuard回滚失败，冻结调参"
        tone = "bad"
        reasons = [
            f"回滚修复状态: {rollback_effect.get('label', '-')}",
            str(rollback_effect.get("summary_text") or "-"),
            "回滚后错过真平或避免假阳仍在恶化，继续写入新 DrawGuard 参数可能放大错误方向。",
            "先复核回滚后的赔率桶和错过真平样本，或由人工解除冻结后再调参。",
        ]
        recommendation = str(rollback_effect.get("recommendation_text") or "").strip()
        if recommendation:
            reasons.append(recommendation)
    elif rollback_status == "watch":
        decision = "confirm"
        label = "DrawGuard回滚后需确认"
        tone = "warning"
        reasons = [
            f"回滚修复状态: {rollback_effect.get('label', '-')}",
            str(rollback_effect.get("summary_text") or "-"),
            "回滚后还没有形成明确修复结论，应用新调参前需确认不是短期噪声。",
        ]
    else:
        decision = "allow"
        label = "允许DrawGuard调参"
        tone = "good" if rollback_status == "effective" else "neutral"
        reasons = [f"回滚修复状态: {rollback_effect.get('label', '暂无回滚风险')}"]

    if action:
        reasons.append(f"待应用动作: {action}")
    body = "\n".join(str(item) for item in reasons if item)
    return {
        "decision": decision,
        "allowed": decision in {"allow", "confirm"},
        "confirm_required": decision == "confirm",
        "label": label,
        "tone": tone,
        "source": "draw_release_guard_tuning",
        "source_label": "DrawGuard调参",
        "rollback_effect_status": rollback_status or "-",
        "rollback_effect_label": str(rollback_effect.get("label") or "-"),
        "rollback_effect_summary": str(rollback_effect.get("summary_text") or "-"),
        "freeze_override_status": override_status or "-",
        "freeze_override_label": str(freeze_override.get("label") or "-"),
        "freeze_override_summary": str(freeze_override.get("summary_text") or "-"),
        "rollback_recommended": rollback_status == "negative",
        "rollback_candidate_version_id": str(rollback_effect.get("rolled_back_version_id") or "-"),
        "freeze_active": decision == "freeze",
        "freeze_override_active": override_status == "overridden",
        "action": action or "-",
        "reasons": reasons,
        "body": body,
        "summary_text": f"DrawGuard调参: {label} | {rollback_effect.get('summary_text', '-')}",
    }


def build_handicap_margin_backtest_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if item.get("handicap_is_correct") is not None and item.get("handicap_margin_score") is not None
    ]
    buckets: dict[str, dict[str, object]] = {
        "low": {"bucket": "low", "count": 0, "hit_count": 0, "score_sum": 0.0, "signals": {}},
        "medium": {"bucket": "medium", "count": 0, "hit_count": 0, "score_sum": 0.0, "signals": {}},
        "high": {"bucket": "high", "count": 0, "hit_count": 0, "score_sum": 0.0, "signals": {}},
    }
    for item in known:
        bucket = _handicap_margin_bucket(item)
        row = buckets[bucket]
        row["count"] = _safe_int(row.get("count")) + 1
        row["hit_count"] = _safe_int(row.get("hit_count")) + (1 if item.get("handicap_is_correct") is True else 0)
        row["score_sum"] = _safe_float(row.get("score_sum")) + _safe_float(item.get("handicap_margin_score"))
        signal_counts = row.get("signals")
        if not isinstance(signal_counts, dict):
            signal_counts = {}
            row["signals"] = signal_counts
        signals = item.get("handicap_margin_signals") if isinstance(item.get("handicap_margin_signals"), list) else []
        for signal in signals:
            key = str(signal)
            signal_counts[key] = _safe_int(signal_counts.get(key)) + 1

    total = len(known)
    total_hits = sum(_safe_int(row.get("hit_count")) for row in buckets.values())
    overall_accuracy = total_hits / total if total else None
    rows: list[dict[str, object]] = []
    for bucket in ("high", "medium", "low"):
        row = buckets[bucket]
        count = _safe_int(row.get("count"))
        hit_count = _safe_int(row.get("hit_count"))
        miss_count = max(0, count - hit_count)
        hit_rate = hit_count / count if count else None
        avg_score = _safe_float(row.get("score_sum")) / count if count else None
        signal_counts = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        top_signal = "-"
        if signal_counts:
            top_signal = sorted(signal_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                "bucket": bucket,
                "label": _market_entropy_bucket_label(bucket),
                "count": count,
                "hit_count": hit_count,
                "miss_count": miss_count,
                "hit_rate": hit_rate,
                "hit_rate_text": _pct(hit_rate),
                "miss_rate_text": _pct(1.0 - hit_rate) if hit_rate is not None else "-",
                "avg_score": avg_score,
                "avg_score_text": _pct(avg_score),
                "top_signal": top_signal,
            }
        )
    high = next((row for row in rows if row.get("bucket") == "high"), {})
    medium = next((row for row in rows if row.get("bucket") == "medium"), {})
    low = next((row for row in rows if row.get("bucket") == "low"), {})
    high_count = _safe_int(high.get("count"))
    high_misses = _safe_int(high.get("miss_count"))
    high_hits = _safe_int(high.get("hit_count"))
    retained_count = _safe_int(medium.get("count")) + _safe_int(low.get("count"))
    retained_hits = _safe_int(medium.get("hit_count")) + _safe_int(low.get("hit_count"))
    retained_accuracy = retained_hits / retained_count if retained_count else None
    high_miss_rate = high_misses / high_count if high_count else None
    overall_miss_rate = 1.0 - overall_accuracy if overall_accuracy is not None else None
    if total < 5:
        recommendation = "collecting"
        recommendation_text = "样本不足，继续积累让球胜差一致性与让球赛果的联动。"
    elif high_count >= 3 and high_miss_rate is not None and overall_miss_rate is not None and high_miss_rate >= overall_miss_rate + 0.12:
        recommendation = "block_high_handicap_margin"
        recommendation_text = "HIGH 冲突场次让球失误明显更高，建议正式放行时过滤让球玩法。"
    elif high_count >= 3 and high_miss_rate is not None and high_miss_rate >= 0.45:
        recommendation = "observe_high_handicap_margin"
        recommendation_text = "HIGH 冲突场次让球失误偏高，建议降级为观察并增加人工复核。"
    else:
        recommendation = "monitor"
        recommendation_text = "暂未证明该过滤能稳定提升让球命中率，继续监控。"
    return {
        "sample_count": total,
        "overall_accuracy": overall_accuracy,
        "overall_accuracy_text": _pct(overall_accuracy),
        "retained_accuracy": retained_accuracy,
        "retained_accuracy_text": _pct(retained_accuracy),
        "avoidable_handicap_misses": high_misses,
        "opportunity_cost": high_hits,
        "high_bucket_count": high_count,
        "high_bucket_miss_rate": high_miss_rate,
        "high_bucket_miss_rate_text": _pct(high_miss_rate),
        "rows": rows,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "summary_text": (
            f"样本 {total} | 让球全量 {_pct(overall_accuracy)} | 过滤HIGH后 {_pct(retained_accuracy)} | "
            f"可避让球错 {high_misses} / 机会成本 {high_hits}"
        ),
    }


def build_market_entropy_backtest_summary(settlements: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    known = [
        item
        for item in settlement_items
        if item.get("is_correct") is not None and item.get("market_entropy_score") is not None
    ]
    buckets: dict[str, dict[str, object]] = {
        "low": {"bucket": "low", "count": 0, "hit_count": 0, "score_sum": 0.0, "risk_applied": 0, "signals": {}},
        "medium": {"bucket": "medium", "count": 0, "hit_count": 0, "score_sum": 0.0, "risk_applied": 0, "signals": {}},
        "high": {"bucket": "high", "count": 0, "hit_count": 0, "score_sum": 0.0, "risk_applied": 0, "signals": {}},
    }
    for item in known:
        bucket = _market_entropy_bucket(item)
        row = buckets[bucket]
        row["count"] = _safe_int(row.get("count")) + 1
        row["hit_count"] = _safe_int(row.get("hit_count")) + (1 if item.get("is_correct") is True else 0)
        row["score_sum"] = _safe_float(row.get("score_sum")) + _safe_float(item.get("market_entropy_score"))
        row["risk_applied"] = _safe_int(row.get("risk_applied")) + (1 if item.get("market_entropy_risk_applied") else 0)
        signal_counts = row.get("signals")
        if not isinstance(signal_counts, dict):
            signal_counts = {}
            row["signals"] = signal_counts
        signals = item.get("market_entropy_signals") if isinstance(item.get("market_entropy_signals"), list) else []
        for signal in signals:
            key = str(signal)
            signal_counts[key] = _safe_int(signal_counts.get(key)) + 1

    total = len(known)
    total_hits = sum(_safe_int(row.get("hit_count")) for row in buckets.values())
    overall_accuracy = total_hits / total if total else None
    rows: list[dict[str, object]] = []
    for bucket in ("high", "medium", "low"):
        row = buckets[bucket]
        count = _safe_int(row.get("count"))
        hit_count = _safe_int(row.get("hit_count"))
        miss_count = max(0, count - hit_count)
        hit_rate = hit_count / count if count else None
        avg_score = _safe_float(row.get("score_sum")) / count if count else None
        signal_counts = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        top_signal = "-"
        if signal_counts:
            top_signal = sorted(signal_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))[0][0]
        rows.append(
            {
                "bucket": bucket,
                "label": _market_entropy_bucket_label(bucket),
                "count": count,
                "hit_count": hit_count,
                "miss_count": miss_count,
                "hit_rate": hit_rate,
                "hit_rate_text": _pct(hit_rate),
                "miss_rate_text": _pct(1.0 - hit_rate) if hit_rate is not None else "-",
                "avg_score": avg_score,
                "avg_score_text": _pct(avg_score),
                "risk_applied_count": _safe_int(row.get("risk_applied")),
                "top_signal": top_signal,
            }
        )
    high = next((row for row in rows if row.get("bucket") == "high"), {})
    medium = next((row for row in rows if row.get("bucket") == "medium"), {})
    low = next((row for row in rows if row.get("bucket") == "low"), {})
    high_count = _safe_int(high.get("count"))
    high_misses = _safe_int(high.get("miss_count"))
    high_hits = _safe_int(high.get("hit_count"))
    retained_count = _safe_int(medium.get("count")) + _safe_int(low.get("count"))
    retained_hits = _safe_int(medium.get("hit_count")) + _safe_int(low.get("hit_count"))
    retained_accuracy = retained_hits / retained_count if retained_count else None
    high_miss_rate = high_misses / high_count if high_count else None
    overall_miss_rate = 1.0 - overall_accuracy if overall_accuracy is not None else None
    if total < 5:
        recommendation = "collecting"
        recommendation_text = "样本不足，继续记录 MarketEntropy 与赛果联动。"
    elif high_count >= 3 and high_miss_rate is not None and overall_miss_rate is not None and high_miss_rate >= overall_miss_rate + 0.12:
        recommendation = "block_high_entropy"
        recommendation_text = "高熵值场次显著更容易失误，建议正式放行时阻断 HIGH 桶。"
    elif high_count >= 3 and high_miss_rate is not None and high_miss_rate >= 0.45:
        recommendation = "observe_high_entropy"
        recommendation_text = "高熵值场次失误偏高，建议降级为观察并增加人工复核。"
    else:
        recommendation = "monitor"
        recommendation_text = "暂未证明高熵值过滤能显著提升命中率，继续监控。"
    return {
        "sample_count": total,
        "overall_accuracy": overall_accuracy,
        "overall_accuracy_text": _pct(overall_accuracy),
        "retained_accuracy": retained_accuracy,
        "retained_accuracy_text": _pct(retained_accuracy),
        "avoidable_misses": high_misses,
        "opportunity_cost": high_hits,
        "high_bucket_count": high_count,
        "high_bucket_miss_rate": high_miss_rate,
        "high_bucket_miss_rate_text": _pct(high_miss_rate),
        "rows": rows,
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "summary_text": (
            f"样本 {total} | 全量 {_pct(overall_accuracy)} | 过滤HIGH后 {_pct(retained_accuracy)} | "
            f"可避错 {high_misses} / 机会成本 {high_hits}"
        ),
    }


def build_strategy_allowlist_tuning_recommendation(
    settlements: Sequence[Mapping[str, object]] | object,
    *,
    base_min_confidence: float = 0.50,
    base_active_strategy_min: int = 1,
    historical_error_attribution: Mapping[str, object] | object | None = None,
    historical_replay: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    summary = build_strategy_allowlist_settlement_summary(settlements)
    historical_errors = _as_mapping(historical_error_attribution)
    historical_replay_summary = _as_mapping(historical_replay)
    historical_reason_counts = _as_mapping(historical_errors.get("reason_counts"))
    historical_sample_count = _safe_int(historical_replay_summary.get("sample_count"))
    historical_miss_count = _safe_int(historical_errors.get("miss_count") or historical_replay_summary.get("miss_count"))
    historical_hit_rate = historical_replay_summary.get("hit_rate")
    historical_hit_rate_value = _safe_float(historical_hit_rate, -1.0) if historical_hit_rate is not None else None
    historical_high_conf_misses = _safe_int(historical_reason_counts.get("high_confidence_miss"))
    historical_gap_misses = _safe_int(historical_reason_counts.get("historical_gap"))
    historical_ready = historical_sample_count >= 100 and historical_miss_count >= 10
    historical_weak = historical_hit_rate_value is not None and 0.0 <= historical_hit_rate_value < 0.65
    historical_pressure = bool(
        historical_ready
        and (
            historical_weak
            or historical_high_conf_misses >= max(12, int(historical_sample_count * 0.16))
            or historical_gap_misses >= max(12, int(historical_sample_count * 0.16))
        )
    )
    known_count = _safe_int(summary.get("known_count"))
    hit_rate = summary.get("hit_rate")
    hit_rate_value = _safe_float(hit_rate, 0.0) if hit_rate is not None else None
    high_strategy_rate = summary.get("high_strategy_hit_rate")
    high_strategy_value = _safe_float(high_strategy_rate, 0.0) if high_strategy_rate is not None else None
    high_conf_misses = _safe_int(summary.get("high_conf_misses"))
    reasons: list[str] = []
    next_min_confidence = _safe_float(base_min_confidence)
    next_active_strategy_min = max(1, _safe_int(base_active_strategy_min, 1))
    medium_risk_allowed = True
    risk_policy = "\u5141\u8bb8\u4f4e/\u4e2d\u98ce\u9669\uff0c\u9ad8\u98ce\u9669\u7ee7\u7eed\u963b\u65ad"
    action = "collect"
    label = "\u7ee7\u7eed\u79ef\u7d2f\u6837\u672c"
    tone = "neutral"

    if known_count < 5:
        if historical_ready:
            action = "history_watch"
            label = "\u53c2\u8003\u5386\u53f2\u56de\u653e"
            tone = "warning" if historical_pressure else "neutral"
            reasons.append(
                f"\u771f\u5b9e\u653e\u884c\u5df2\u7ed3\u7b97\u6837\u672c\u4ec5 {known_count} \u573a\uff0c\u4e0d\u76f4\u63a5\u6df7\u5165\u5386\u53f2\u56de\u653e\u547d\u4e2d\u7387\u3002"
            )
            reasons.append(
                f"\u5386\u53f2\u56de\u653e {historical_sample_count} \u9879 | \u547d\u4e2d {historical_replay_summary.get('hit_rate_text') or '-'} | "
                f"\u9ad8\u7f6e\u4fe1\u5931\u8bef {historical_high_conf_misses} | \u5386\u53f2\u80cc\u79bb {historical_gap_misses}\u3002"
            )
            if historical_pressure:
                reasons.append("\u5386\u53f2\u56de\u653e\u663e\u793a\u95e8\u69db\u5b58\u5728\u538b\u529b\uff0c\u5efa\u8bae\u5148\u4ee5\u89c2\u5bdf\u65b9\u5f0f\u6536\u7a84\u653e\u884c\u8303\u56f4\uff0c\u7b49\u771f\u5b9e\u7ed3\u7b97\u6837\u672c\u8fbe\u6807\u540e\u518d\u81ea\u52a8\u5e94\u7528\u3002")
                medium_risk_allowed = False
                risk_policy = "\u5386\u53f2\u56de\u653e\u627f\u538b\uff1a\u4e2d\u98ce\u9669\u5148\u964d\u4e3a\u89c2\u5bdf"
        else:
            reasons.append(f"\u653e\u884c\u5df2\u7ed3\u7b97\u6837\u672c\u4ec5 {known_count} \u573a\uff0c\u4e0d\u8db3\u4ee5\u81ea\u52a8\u6539\u95e8\u69db\u3002")
    elif (
        (hit_rate_value is not None and hit_rate_value < 0.55)
        or high_conf_misses >= max(2, known_count // 4)
        or (high_strategy_value is not None and high_strategy_value < 0.60)
    ):
        action = "tighten"
        label = "\u6536\u7d27\u6b63\u5f0f\u653e\u884c"
        tone = "warning"
        if hit_rate_value is not None and hit_rate_value < 0.55:
            reasons.append(f"\u653e\u884c 1X2 \u547d\u4e2d\u7387 {summary.get('hit_rate_text')}\uff0c\u4f4e\u4e8e 55% \u89c2\u5bdf\u7ebf\u3002")
            next_min_confidence += 0.05 if hit_rate_value >= 0.45 else 0.08
        if high_conf_misses >= max(2, known_count // 4):
            reasons.append(f"\u9ad8\u7f6e\u4fe1\u5931\u8bef {high_conf_misses} \u573a\uff0c\u8bf4\u660e\u5f53\u524d\u7f6e\u4fe1\u8fc7\u6ee4\u504f\u677e\u3002")
            next_min_confidence += 0.03
            medium_risk_allowed = False
            risk_policy = "\u4ec5\u5141\u8bb8\u4f4e\u98ce\u9669\uff0c\u4e2d\u98ce\u9669\u964d\u4e3a\u89c2\u5bdf"
        if high_strategy_value is not None and high_strategy_value < 0.60:
            reasons.append(f"\u9ad8\u51c6\u7b56\u7565\u547d\u4e2d {summary.get('high_strategy_summary')}\uff0c\u5efa\u8bae\u589e\u52a0\u6b63\u5f0f\u7b56\u7565\u6570\u8981\u6c42\u3002")
            next_active_strategy_min = max(next_active_strategy_min, 2)
        if historical_ready:
            reasons.append(
                f"\u5386\u53f2\u56de\u653e\u53c2\u8003\uff1a{historical_sample_count} \u9879 | \u547d\u4e2d {historical_replay_summary.get('hit_rate_text') or '-'} | "
                f"\u4e3b\u56e0 {historical_errors.get('top_reason') or '-'}\u3002"
            )
            if historical_high_conf_misses >= max(12, int(historical_sample_count * 0.12)) and not historical_weak:
                next_min_confidence += 0.02
                medium_risk_allowed = False
                risk_policy = "\u4ec5\u5141\u8bb8\u4f4e\u98ce\u9669\uff0c\u5386\u53f2\u9ad8\u7f6e\u4fe1\u5931\u8bef\u504f\u591a"
            if historical_gap_misses >= max(12, int(historical_sample_count * 0.12)):
                next_active_strategy_min = max(next_active_strategy_min, 2)
    elif hit_rate_value is not None and hit_rate_value >= 0.70 and (high_strategy_value is None or high_strategy_value >= 0.70):
        action = "hold"
        label = "\u7ef4\u6301\u95e8\u69db"
        tone = "good"
        reasons.append("\u653e\u884c\u547d\u4e2d\u548c\u9ad8\u51c6\u7b56\u7565\u8868\u73b0\u8fbe\u5230\u7a33\u5b9a\u533a\u95f4\uff0c\u6682\u4e0d\u653e\u5bbd\u8986\u76d6\u3002")
    else:
        action = "watch"
        label = "\u5c0f\u5e45\u89c2\u5bdf"
        tone = "neutral"
        reasons.append("\u653e\u884c\u8868\u73b0\u672a\u8fbe\u5230\u653e\u5bbd\u6761\u4ef6\uff0c\u4f46\u4e5f\u672a\u89e6\u53d1\u660e\u663e\u6536\u7d27\u6761\u4ef6\u3002")

    next_min_confidence = round(min(0.78, max(0.45, next_min_confidence)), 2)
    if action in {"collect", "hold", "watch", "history_watch"}:
        next_min_confidence = round(_safe_float(base_min_confidence), 2)

    rows = [
        ("\u52a8\u4f5c", label),
        ("\u6837\u672c", f"{known_count} \u573a | \u653e\u884c\u547d\u4e2d {summary.get('hit_rate_text', '-')}"),
        ("\u6700\u4f4e\u7f6e\u4fe1", f"{_safe_float(base_min_confidence):.2f} -> {next_min_confidence:.2f}"),
        ("\u9ad8\u51c6\u7b56\u7565\u6570", f"{max(1, _safe_int(base_active_strategy_min, 1))} -> {next_active_strategy_min}"),
        ("\u98ce\u9669\u9650\u5236", risk_policy),
        (
            "\u5386\u53f2\u56de\u653e",
            (
                f"{historical_sample_count} \u9879 | \u547d\u4e2d {historical_replay_summary.get('hit_rate_text') or '-'} | "
                f"\u9519\u56e0 {historical_errors.get('top_reason') or '-'}"
                if historical_sample_count
                else "-"
            ),
        ),
        ("\u89e6\u53d1\u539f\u56e0", "\n".join(reasons) if reasons else "-"),
    ]
    return {
        "action": action,
        "label": label,
        "tone": tone,
        "known_count": known_count,
        "next_min_confidence": next_min_confidence,
        "next_active_strategy_min": next_active_strategy_min,
        "medium_risk_allowed": medium_risk_allowed,
        "risk_policy": risk_policy,
        "historical_sample_count": historical_sample_count,
        "historical_miss_count": historical_miss_count,
        "historical_pressure": historical_pressure,
        "historical_error_attribution": dict(historical_errors),
        "historical_replay": dict(historical_replay_summary),
        "policy_update": {
            "min_confidence": next_min_confidence,
            "active_strategy_min": next_active_strategy_min,
            "medium_risk_allowed": medium_risk_allowed,
            "high_risk_allowed": False,
        },
        "reasons": reasons,
        "rows": rows,
        "summary": summary,
    }


def _strategy_release_loop_match_date(item: Mapping[str, object]) -> date | None:
    match = item.get("match")
    match_date = _parse_date_value(_field(match, "match_date", ""))
    if match_date is not None:
        return match_date
    kickoff = str(item.get("kickoff") or "").strip()
    return _parse_date_value(kickoff)


def _strategy_release_snapshot_row(
    match_id: str,
    record: Mapping[str, object],
    *,
    settled_ids: set[str],
) -> dict[str, object]:
    match = _as_mapping(record.get("match"))
    prediction = _as_mapping(record.get("prediction"))
    marker = _allowlist_marker(prediction, record)
    settled = bool(match_id and match_id in settled_ids)
    return {
        "match_id": match_id,
        "match": match,
        "prediction": prediction,
        "admission": _strategy_admission(prediction),
        "title": f"{_text(match.get('league'))} | {_text(match.get('home_team'))} vs {_text(match.get('away_team'))}",
        "kickoff": f"{_text(match.get('match_date'))} {_text(match.get('match_time'))}",
        "recommendation": _text(prediction.get("recommendation")),
        "confidence_text": _pct(prediction.get("confidence")),
        "risk_text": _risk_text(prediction.get("risk_level")),
        "candidate_text": format_strategy_admission_pick(marker if marker else _strategy_admission(prediction)),
        "reason_text": format_strategy_admission_reasons(marker if marker else _strategy_admission(prediction), limit=4),
        "export_status": "\u5df2\u5bfc\u51fa" if _text(marker.get("file"), "") else "\u672a\u5bfc\u51fa",
        "allowlist_file": _text(marker.get("file")),
        "exported_at": _text(marker.get("exported_at")),
        "snapshot_status": "\u5df2\u4fdd\u5b58",
        "settlement_status": "\u5df2\u56de\u6536" if settled else "\u5f85\u56de\u6536",
        "ready_for_recovery": not settled,
        "source": "snapshot",
    }


def _strategy_release_settlement_row(item: Mapping[str, object]) -> dict[str, object]:
    match_id = _settlement_match_id(item)
    match = {
        "match_id": match_id,
        "match_date": item.get("match_date"),
        "match_time": item.get("match_time"),
        "league": item.get("league"),
        "home_team": item.get("home_team"),
        "away_team": item.get("away_team"),
    }
    prediction = {
        "recommendation": item.get("predicted"),
        "confidence": item.get("prediction_confidence"),
        "risk_level": item.get("risk_level"),
    }
    return {
        "match_id": match_id,
        "match": match,
        "prediction": prediction,
        "admission": {"decision": "allow"},
        "title": f"{_text(item.get('league'))} | {_text(item.get('home_team'))} vs {_text(item.get('away_team'))}",
        "kickoff": f"{_text(item.get('match_date'))} {_text(item.get('match_time'))}",
        "recommendation": _text(item.get("predicted")),
        "confidence_text": _pct(item.get("prediction_confidence")),
        "risk_text": _risk_text(item.get("risk_level")),
        "candidate_text": _text(item.get("predicted")),
        "reason_text": "\u5df2\u901a\u8fc7\u7ed3\u7b97\u8bb0\u5f55\u56de\u586b",
        "export_status": "\u5df2\u5bfc\u51fa" if _text(item.get("strategy_allowlist_file"), "") else "\u672a\u5bfc\u51fa",
        "allowlist_file": _text(item.get("strategy_allowlist_file")),
        "exported_at": _text(item.get("strategy_allowlist_exported_at")),
        "snapshot_status": "\u7f3a\u5feb\u7167",
        "settlement_status": "\u5df2\u56de\u6536",
        "ready_for_recovery": False,
        "source": "settlement",
    }


def build_strategy_release_recovery_loop(
    rows: Sequence[object] | object,
    *,
    snapshots: Mapping[str, object] | object = None,
    settlements: Sequence[Mapping[str, object]] | object = None,
    now: datetime | None = None,
    stale_after_days: int = 1,
) -> dict[str, object]:
    snapshot_map = snapshots if isinstance(snapshots, Mapping) else {}
    settlement_items = _strategy_allowlist_settlements(settlements)
    settled_ids = {_settlement_match_id(item) for item in settlement_items if _settlement_match_id(item)}
    row_map: dict[str, dict[str, object]] = {}

    for item in build_strategy_release_pool_rows(rows, snapshots=snapshot_map, settlements=settlement_items):
        match_id = str(item.get("match_id") or "")
        if not match_id:
            continue
        enriched = dict(item)
        enriched["source"] = "current"
        row_map[match_id] = enriched

    for match_id, record in snapshot_map.items():
        if not isinstance(record, Mapping):
            continue
        prediction = _as_mapping(record.get("prediction"))
        marker = _allowlist_marker(prediction, record)
        if not marker:
            continue
        key = str(match_id)
        if key not in row_map:
            row_map[key] = _strategy_release_snapshot_row(key, record, settled_ids=settled_ids)

    for item in settlement_items:
        match_id = _settlement_match_id(item)
        if match_id and match_id not in row_map:
            row_map[match_id] = _strategy_release_settlement_row(item)

    current_date = (now or datetime.now()).date()
    stale_days = max(0, _safe_int(stale_after_days, 1))
    loop_rows: list[dict[str, object]] = []
    for item in row_map.values():
        row = dict(item)
        settled = str(row.get("settlement_status") or "") == "\u5df2\u56de\u6536"
        snapshot_saved = str(row.get("snapshot_status") or "") == "\u5df2\u4fdd\u5b58"
        exported = str(row.get("export_status") or "") == "\u5df2\u5bfc\u51fa"
        match_date = _strategy_release_loop_match_date(row)
        pending_days = max(0, (current_date - match_date).days) if match_date is not None and not settled else 0
        stale_pending = bool(not settled and match_date is not None and pending_days >= stale_days)
        if settled:
            loop_status = "\u5df2\u56de\u6536"
        elif not snapshot_saved:
            loop_status = "\u7f3a\u5feb\u7167"
        elif stale_pending:
            loop_status = "\u8d85\u671f\u5f85\u56de\u6536"
        else:
            loop_status = "\u5f85\u56de\u6536"
        row.update(
            {
                "exported": exported,
                "snapshot_saved": snapshot_saved,
                "settled": settled,
                "pending": not settled,
                "pending_days": pending_days,
                "stale_pending": stale_pending,
                "loop_status": loop_status,
            }
        )
        loop_rows.append(row)

    def sort_key(item: Mapping[str, object]) -> tuple[int, int, str, str]:
        status_rank = 0 if item.get("stale_pending") else 1 if item.get("ready_for_recovery") else 2 if item.get("pending") else 3
        match_date = _strategy_release_loop_match_date(item)
        return (
            status_rank,
            -_safe_int(item.get("pending_days")),
            match_date.isoformat() if match_date else "9999-99-99",
            str(item.get("match_id") or ""),
        )

    loop_rows = sorted(loop_rows, key=sort_key)
    total_count = len(loop_rows)
    exported_count = sum(1 for item in loop_rows if item.get("exported"))
    snapshot_saved_count = sum(1 for item in loop_rows if item.get("snapshot_saved"))
    settled_count = sum(1 for item in loop_rows if item.get("settled"))
    pending_count = sum(1 for item in loop_rows if item.get("pending"))
    ready_for_recovery_count = sum(1 for item in loop_rows if item.get("ready_for_recovery"))
    stale_pending_count = sum(1 for item in loop_rows if item.get("stale_pending"))
    missing_snapshot_count = sum(1 for item in loop_rows if item.get("pending") and not item.get("snapshot_saved"))
    settlement_summary = build_strategy_allowlist_settlement_summary(settlement_items)
    tuning = build_strategy_allowlist_tuning_recommendation(settlement_items)
    if stale_pending_count or missing_snapshot_count:
        health = "warning"
        health_text = "\u9700\u8865\u56de\u6536"
    elif pending_count:
        health = "watch"
        health_text = "\u7b49\u5f85\u8d5b\u679c"
    elif total_count:
        health = "good"
        health_text = "\u95ed\u73af\u5b8c\u6210"
    else:
        health = "collecting"
        health_text = "\u6682\u65e0\u653e\u884c"
    return {
        "total_release_count": total_count,
        "exported_count": exported_count,
        "snapshot_saved_count": snapshot_saved_count,
        "settled_count": settled_count,
        "pending_count": pending_count,
        "ready_for_recovery_count": ready_for_recovery_count,
        "stale_pending_count": stale_pending_count,
        "missing_snapshot_count": missing_snapshot_count,
        "hit_rate": settlement_summary.get("hit_rate"),
        "hit_rate_text": settlement_summary.get("hit_rate_text", "-"),
        "settlement_summary": settlement_summary,
        "tuning": tuning,
        "health": health,
        "health_text": health_text,
        "rows": loop_rows,
        "summary_text": (
            f"\u653e\u884c {total_count} | \u5df2\u56de\u6536 {settled_count} | \u5f85\u56de\u6536 {pending_count} | "
            f"\u7f3a\u5feb\u7167 {missing_snapshot_count} | \u8d85\u671f {stale_pending_count} | \u547d\u4e2d {settlement_summary.get('hit_rate_text', '-')}"
        ),
    }


def select_strategy_allowlist_rows(rows: Sequence[object] | object) -> list[object]:
    if not isinstance(rows, Sequence):
        return []
    allowed: list[object] = []
    for row in rows:
        admission = _strategy_admission(_row_prediction(row))
        if str(admission.get("decision") or "").strip() == "allow":
            allowed.append(row)
    return sorted(allowed, key=_allowlist_sort_key)


def build_strategy_allowlist_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"strategy_allowlist_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_strategy_policy_audit_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"strategy_policy_audit_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_strategy_policy_audit_csv_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"strategy_policy_audit_samples_{current.strftime('%Y%m%d_%H%M%S')}.csv"


def build_strategy_release_recovery_loop_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"strategy_release_recovery_loop_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_strategy_release_recovery_loop_report_lines(
    release_loop: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
) -> list[str]:
    loop = _as_mapping(release_loop)
    current = generated_at or datetime.now()
    settlement_summary = _as_mapping(loop.get("settlement_summary"))
    tuning = _as_mapping(loop.get("tuning"))
    rows = [item for item in _as_list(loop.get("rows")) if isinstance(item, Mapping)]
    lines = [
        "# \u7b56\u7565\u653e\u884c\u56de\u6536\u95ed\u73af\u62a5\u544a",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u95ed\u73af\u72b6\u6001: {loop.get('health_text', '-')}",
        f"- \u6458\u8981: {loop.get('summary_text', '-')}",
        f"- \u8c03\u53c2\u5efa\u8bae: {tuning.get('label', '-')}",
        "",
        "## \u95ed\u73af\u6307\u6807",
        "",
        "| \u6307\u6807 | \u6570\u503c |",
        "| --- | ---: |",
        f"| \u653e\u884c\u603b\u6570 | {_safe_int(loop.get('total_release_count'))} |",
        f"| \u5df2\u5bfc\u51fa | {_safe_int(loop.get('exported_count'))} |",
        f"| \u5df2\u7559\u5feb\u7167 | {_safe_int(loop.get('snapshot_saved_count'))} |",
        f"| \u5df2\u56de\u6536 | {_safe_int(loop.get('settled_count'))} |",
        f"| \u5f85\u56de\u6536 | {_safe_int(loop.get('pending_count'))} |",
        f"| \u7f3a\u5feb\u7167 | {_safe_int(loop.get('missing_snapshot_count'))} |",
        f"| \u8d85\u671f\u5f85\u56de\u6536 | {_safe_int(loop.get('stale_pending_count'))} |",
        f"| \u653e\u884c\u547d\u4e2d | {_text(loop.get('hit_rate_text'), '-')} |",
        "",
        "## \u7ed3\u7b97\u8d28\u91cf",
        "",
        f"- 1X2\u6837\u672c: {settlement_summary.get('known_count', 0)}",
        f"- 1X2\u547d\u4e2d: {settlement_summary.get('hit_rate_text', '-')}",
        f"- \u8ba9\u7403\u547d\u4e2d: {settlement_summary.get('handicap_hit_rate_text', '-')}",
        f"- \u5927\u5c0f\u7403\u547d\u4e2d: {settlement_summary.get('ou_hit_rate_text', '-')}",
        f"- \u9ad8\u51c6\u7b56\u7565: {settlement_summary.get('high_strategy_summary', '-')}",
        f"- \u4e3b\u8981\u504f\u5dee: {settlement_summary.get('top_failure', '-')}",
        "",
        "## \u8c03\u53c2\u4fe1\u53f7",
        "",
    ]
    tuning_rows = [item for item in _as_list(tuning.get("rows")) if isinstance(item, tuple) and len(item) >= 2]
    if tuning_rows:
        for label, value in tuning_rows:
            lines.append(f"- {label}: {value}")
    else:
        lines.append("- \u6682\u65e0\u8c03\u53c2\u4fe1\u53f7")
    lines.extend(
        [
            "",
            "## \u9010\u573a\u660e\u7ec6",
            "",
            "| \u95ed\u73af\u72b6\u6001 | \u5f00\u8d5b | \u8054\u8d5b | \u8d5b\u4e8b | \u63a8\u8350 | \u7f6e\u4fe1 | \u98ce\u9669 | \u5feb\u7167 | \u56de\u6536 | \u5f85\u56de\u6536 | \u6e05\u5355 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    if not rows:
        lines.append("| \u6682\u65e0\u653e\u884c\u8bb0\u5f55 | - | - | - | - | - | - | - | - | 0 | - |")
    for item in rows:
        match = item.get("match", {}) if isinstance(item.get("match"), Mapping) else {}
        match_text = f"{_text(match.get('home_team'))} vs {_text(match.get('away_team'))}"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("loop_status")),
                    _md_cell(item.get("kickoff")),
                    _md_cell(match.get("league")),
                    _md_cell(match_text),
                    _md_cell(item.get("recommendation")),
                    _md_cell(item.get("confidence_text")),
                    _md_cell(item.get("risk_text")),
                    _md_cell(item.get("snapshot_status")),
                    _md_cell(item.get("settlement_status")),
                    str(_safe_int(item.get("pending_days"))),
                    _md_cell(item.get("allowlist_file")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## \u5904\u7406\u5efa\u8bae",
            "",
        ]
    )
    if _safe_int(loop.get("missing_snapshot_count")):
        lines.append("- \u7f3a\u5feb\u7167\u573a\u6b21\u65e0\u6cd5\u5b8c\u6210\u6807\u51c6\u653e\u884c\u590d\u76d8\uff0c\u540e\u7eed\u9700\u786e\u4fdd\u5bfc\u51fa\u653e\u884c\u6e05\u5355\u65f6\u540c\u6b65\u6807\u8bb0\u5feb\u7167\u3002")
    if _safe_int(loop.get("stale_pending_count")):
        lines.append("- \u8d85\u671f\u5f85\u56de\u6536\u573a\u6b21\u9700\u4f18\u5148\u8fd0\u884c\u8d5b\u679c\u56de\u6536\uff0c\u5426\u5219\u653e\u884c\u547d\u4e2d\u7387\u4f1a\u6ede\u540e\u3002")
    if not _safe_int(loop.get("missing_snapshot_count")) and not _safe_int(loop.get("stale_pending_count")):
        lines.append("- \u5f53\u524d\u653e\u884c\u56de\u6536\u95ed\u73af\u6ca1\u6709\u660e\u663e\u963b\u65ad\u9879\uff0c\u7ee7\u7eed\u7b49\u5f85\u672a\u5f00\u8d5b\u573a\u6b21\u7ed3\u675f\u540e\u56de\u6536\u3002")
    return lines


def build_strategy_policy_audit_report_lines(
    policy_effect_review: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
    draw_release_guard_policy_history: Sequence[Mapping[str, object]] | object | None = None,
    draw_release_guard_tuning_effect_review: Mapping[str, object] | object | None = None,
    draw_release_guard_rollback_effect_review: Mapping[str, object] | object | None = None,
    draw_release_guard_freeze_override_status: Mapping[str, object] | object | None = None,
    draw_release_guard_tuning_guard: Mapping[str, object] | object | None = None,
) -> list[str]:
    review = _as_mapping(policy_effect_review)
    current = generated_at or datetime.now()
    rows = [row for row in _as_list(review.get("rows")) if isinstance(row, Mapping)]
    stability = _as_mapping(review.get("stability_monitor"))
    rollback_effect = build_strategy_policy_rollback_effect_review(review)
    freeze_override = build_strategy_policy_freeze_override_status(_as_list(review.get("all_rows")) or _as_list(review.get("rows")), rollback_effect)
    draw_guard_history = draw_release_guard_policy_history or []
    draw_guard_tuning_effect = _as_mapping(draw_release_guard_tuning_effect_review)
    if not draw_guard_tuning_effect and draw_guard_history:
        draw_guard_tuning_effect = build_draw_release_guard_tuning_effect_review(draw_guard_history, [])
    draw_guard_rollback_effect = _as_mapping(draw_release_guard_rollback_effect_review)
    if not draw_guard_rollback_effect and draw_guard_history:
        draw_guard_rollback_effect = build_draw_release_guard_rollback_effect_review(draw_guard_history, [])
    draw_guard_freeze_override = _as_mapping(draw_release_guard_freeze_override_status)
    if not draw_guard_freeze_override and draw_guard_history:
        draw_guard_freeze_override = build_draw_release_guard_freeze_override_status(draw_guard_history, draw_guard_rollback_effect)
    draw_guard_tuning_guard = _as_mapping(draw_release_guard_tuning_guard)
    if not draw_guard_tuning_guard and (draw_guard_history or draw_guard_rollback_effect):
        draw_guard_tuning_guard = build_draw_release_guard_tuning_guard(
            {},
            rollback_effect_review=draw_guard_rollback_effect,
            freeze_override_status=draw_guard_freeze_override,
        )
    governance = build_strategy_policy_governance_event_summary(
        review,
        draw_release_guard_policy_history=draw_guard_history,
        draw_release_guard_tuning_effect_review=draw_guard_tuning_effect,
        draw_release_guard_rollback_effect_review=draw_guard_rollback_effect,
        draw_release_guard_freeze_override_status=draw_guard_freeze_override,
        draw_release_guard_tuning_guard=draw_guard_tuning_guard,
    )
    tuning_guard = build_strategy_policy_tuning_guard(
        stability,
        source="audit",
        trend_tuning_effect_review=build_strategy_trend_tuning_effect_review(review),
        rollback_effect_review=rollback_effect,
        freeze_override_status=freeze_override,
    )
    lines = [
        "# \u7b56\u7565\u8c03\u53c2\u5ba1\u8ba1\u62a5\u544a",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u7248\u672c\u6570: {review.get('history_count', 0)}",
        f"- \u6700\u65b0\u72b6\u6001: {review.get('latest_label', '-')}",
        f"- \u7248\u672c\u7a33\u5b9a: {stability.get('summary_text', '-')}",
        f"- \u8c03\u53c2\u95e8\u63a7: {tuning_guard.get('summary_text', '-')}",
        f"- \u6cbb\u7406\u4e8b\u4ef6: {governance.get('summary_text', '-')}",
        f"- \u6458\u8981: {review.get('summary_text', '-')}",
        "",
        "## \u7b56\u7565\u6cbb\u7406\u4e8b\u4ef6",
        "",
        f"- \u6458\u8981: {governance.get('summary_text', '-')}",
        f"- \u56de\u6eda\u4fee\u590d: {rollback_effect.get('summary_text', '-')}",
        f"- \u51bb\u7ed3\u89e3\u9664: {freeze_override.get('summary_text', '-')}",
        f"- \u95e8\u63a7\u72b6\u6001: {tuning_guard.get('label', '-')} / {tuning_guard.get('body', '-')}",
        f"- DrawGuard\u56de\u6eda\u4fee\u590d: {draw_guard_rollback_effect.get('summary_text', '-') if draw_guard_rollback_effect else '-'}",
        f"- DrawGuard\u51bb\u7ed3\u89e3\u9664: {draw_guard_freeze_override.get('summary_text', '-') if draw_guard_freeze_override else '-'}",
        f"- DrawGuard\u95e8\u63a7: {draw_guard_tuning_guard.get('label', '-') if draw_guard_tuning_guard else '-'} / {draw_guard_tuning_guard.get('body', '-') if draw_guard_tuning_guard else '-'}",
        "",
        "| \u65f6\u95f4 | \u7248\u672c | \u4e8b\u4ef6 | \u6765\u6e90 | \u5173\u8054\u7248\u672c | \u6548\u679c | \u653e\u884c\u547d\u4e2d | Replay\u51c0\u503c | \u8bf4\u660e |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    governance_rows = [row for row in _as_list(governance.get("rows")) if isinstance(row, Mapping)]
    if governance_rows:
        for row in governance_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(row.get("updated_at")),
                        _md_cell(row.get("version_id")),
                        _md_cell(row.get("event_label")),
                        _md_cell(row.get("source")),
                        _md_cell(row.get("related_version_id")),
                        _md_cell(row.get("effect_label")),
                        _md_cell(row.get("allow_hit_rate_text")),
                        f"{_safe_int(row.get('replay_guard_net')):+d}",
                        _md_cell(row.get("description")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | - | \u6682\u65e0\u6cbb\u7406\u4e8b\u4ef6 | - | - | - | - | 0 | - |")
    lines.extend(
        [
            "",
            "## \u7248\u672c\u7a33\u5b9a\u76d1\u63a7",
            "",
            f"- \u72b6\u6001: {stability.get('label', '-')}",
            f"- \u8bc4\u4f30\u7248\u672c: {stability.get('evaluated_count', 0)} / {stability.get('version_count', 0)}",
            f"- \u6700\u65b0\u547d\u4e2d: {stability.get('latest_allow_hit_rate_text', '-')}",
            f"- \u6700\u65b0\u73af\u6bd4: {stability.get('latest_delta_text', '-')}",
            f"- \u5e73\u5747\u6ce2\u52a8: {stability.get('avg_abs_delta_text', '-')}",
            f"- Replay\u7d2f\u8ba1\u51c0\u503c: {stability.get('cumulative_replay_net', 0):+d}"
            if isinstance(stability.get("cumulative_replay_net"), int)
            else f"- Replay\u7d2f\u8ba1\u51c0\u503c: {stability.get('cumulative_replay_net', 0)}",
            f"- \u5efa\u8bae: {stability.get('recommendation_text', '-')}",
            f"- \u8c03\u53c2\u95e8\u63a7: {tuning_guard.get('label', '-')} / {tuning_guard.get('body', '-')}",
            "",
            "| \u5468\u671f | \u7248\u672c | \u6837\u672c | \u653e\u884c\u547d\u4e2d | Replay\u51c0\u503c | \u6b63\u5411 | \u8d1f\u5411 | \u79ef\u7d2f |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    weekly_rows = [row for row in _as_list(stability.get("weekly_rows")) if isinstance(row, Mapping)]
    if weekly_rows:
        for row in weekly_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _text(row.get("week"), "-"),
                        str(_safe_int(row.get("version_count"))),
                        str(_safe_int(row.get("sample_count"))),
                        _text(row.get("allow_hit_rate_text"), "-"),
                        f"{_safe_int(row.get('replay_guard_net')):+d}",
                        str(_safe_int(row.get("effective_count"))),
                        str(_safe_int(row.get("negative_count"))),
                        str(_safe_int(row.get("collecting_count"))),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | 0 | 0 | - | 0 | 0 | 0 | 0 |")
    lines.extend(
        [
            "",
            "## \u7248\u672c\u6548\u679c\u603b\u89c8",
            "",
            "| \u7248\u672c | \u65f6\u95f4 | \u6765\u6e90 | \u6548\u679c | \u6837\u672c | \u653e\u884c\u547d\u4e2d | Replay\u51c0\u503c | \u56de\u6eda\u5efa\u8bae |",
            "| --- | --- | --- | --- | ---: | --- | ---: | --- |",
        ]
    )
    if not rows:
        lines.extend(["| - | - | - | \u6682\u65e0\u7248\u672c | 0 | - | 0 | - |", ""])
        return lines
    for row in rows:
        diagnostics = _as_mapping(row.get("negative_diagnostics"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _text(row.get("version_id"), "-"),
                    _text(row.get("updated_at"), "-"),
                    _text(row.get("source"), "-"),
                    _text(row.get("effect_label"), "-"),
                    str(_safe_int(row.get("sample_count"))),
                    _text(row.get("allow_hit_rate_text"), "-"),
                    f"{_safe_int(row.get('replay_guard_net')):+d}",
                    _text(diagnostics.get("action_label"), "-"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## \u8d1f\u5411\u7248\u672c\u5b9a\u4f4d", ""])
    for row in rows:
        diagnostics = _as_mapping(row.get("negative_diagnostics"))
        negative_rows = [item for item in _as_list(diagnostics.get("top_negative_rows")) if isinstance(item, Mapping)]
        if not negative_rows and not bool(diagnostics.get("rollback_recommended")):
            continue
        lines.extend(
            [
                f"### {_text(row.get('version_id'), '-')} | {_text(row.get('effect_label'), '-')}",
                "",
                f"- \u8bca\u65ad: {diagnostics.get('summary_text', '-')}",
                f"- \u4e3b\u56e0: {diagnostics.get('top_negative_reason', '-')}",
                f"- \u662f\u5426\u5efa\u8bae\u56de\u6eda: {'YES' if diagnostics.get('rollback_recommended') else 'NO'}",
                "",
                "| \u65f6\u95f4 | \u8d5b\u4e8b | \u51c6\u5165 | 1X2 | \u8ba9\u7403 | Replay | Agent | \u51c0\u503c | \u62d6\u7d2f\u539f\u56e0 |",
                "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
            ]
        )
        for sample in negative_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _text(sample.get("time"), "-"),
                        _text(sample.get("title"), "-"),
                        _text(sample.get("decision"), "-"),
                        _text(sample.get("prediction_result"), "-"),
                        _text(sample.get("handicap_result"), "-"),
                        _text(sample.get("replay_guard"), "-"),
                        _text(sample.get("replay_agent"), "-"),
                        f"{_safe_int(sample.get('replay_net_hint')):+d}",
                        _text(sample.get("drag_reason_text"), "-"),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.extend(["## \u5168\u91cf\u6837\u672c\u660e\u7ec6", ""])
    for row in rows:
        sample_rows = [item for item in _as_list(row.get("sample_rows")) if isinstance(item, Mapping)]
        lines.extend(
            [
                f"### {_text(row.get('version_id'), '-')} | {_text(row.get('updated_at'), '-')}",
                "",
                "| \u65f6\u95f4 | \u8d5b\u4e8b | \u51c6\u5165 | 1X2 | \u8ba9\u7403 | Replay | Agent | \u51c0\u503c | \u5f71\u54cd\u539f\u56e0 |",
                "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
            ]
        )
        if not sample_rows:
            lines.append("| - | - | - | - | - | - | - | 0 | - |")
        for sample in sample_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _text(sample.get("time"), "-"),
                        _text(sample.get("title"), "-"),
                        _text(sample.get("decision"), "-"),
                        _text(sample.get("prediction_result"), "-"),
                        _text(sample.get("handicap_result"), "-"),
                        _text(sample.get("replay_guard"), "-"),
                        _text(sample.get("replay_agent"), "-"),
                        f"{_safe_int(sample.get('replay_net_hint')):+d}",
                        _text(sample.get("drag_reason_text"), "-"),
                    ]
                )
                + " |"
            )
        lines.append("")
    return lines


def build_strategy_policy_audit_csv_text(
    policy_effect_review: Mapping[str, object] | object,
    *,
    draw_release_guard_policy_history: Sequence[Mapping[str, object]] | object | None = None,
    draw_release_guard_tuning_effect_review: Mapping[str, object] | object | None = None,
    draw_release_guard_rollback_effect_review: Mapping[str, object] | object | None = None,
    draw_release_guard_freeze_override_status: Mapping[str, object] | object | None = None,
    draw_release_guard_tuning_guard: Mapping[str, object] | object | None = None,
) -> str:
    review = _as_mapping(policy_effect_review)
    rows = [row for row in (_as_list(review.get("all_rows")) or _as_list(review.get("rows"))) if isinstance(row, Mapping)]
    draw_guard_history = draw_release_guard_policy_history or []
    draw_guard_tuning_effect = _as_mapping(draw_release_guard_tuning_effect_review)
    if not draw_guard_tuning_effect and draw_guard_history:
        draw_guard_tuning_effect = build_draw_release_guard_tuning_effect_review(draw_guard_history, [])
    draw_guard_rollback_effect = _as_mapping(draw_release_guard_rollback_effect_review)
    if not draw_guard_rollback_effect and draw_guard_history:
        draw_guard_rollback_effect = build_draw_release_guard_rollback_effect_review(draw_guard_history, [])
    draw_guard_freeze_override = _as_mapping(draw_release_guard_freeze_override_status)
    if not draw_guard_freeze_override and draw_guard_history:
        draw_guard_freeze_override = build_draw_release_guard_freeze_override_status(draw_guard_history, draw_guard_rollback_effect)
    draw_guard_tuning_guard = _as_mapping(draw_release_guard_tuning_guard)
    if not draw_guard_tuning_guard and (draw_guard_history or draw_guard_rollback_effect):
        draw_guard_tuning_guard = build_draw_release_guard_tuning_guard(
            {},
            rollback_effect_review=draw_guard_rollback_effect,
            freeze_override_status=draw_guard_freeze_override,
        )
    governance = build_strategy_policy_governance_event_summary(
        review,
        draw_release_guard_policy_history=draw_guard_history,
        draw_release_guard_tuning_effect_review=draw_guard_tuning_effect,
        draw_release_guard_rollback_effect_review=draw_guard_rollback_effect,
        draw_release_guard_freeze_override_status=draw_guard_freeze_override,
        draw_release_guard_tuning_guard=draw_guard_tuning_guard,
    )
    governance_by_version = {
        str(row.get("version_id") or ""): row
        for row in _as_list(governance.get("rows"))
        if isinstance(row, Mapping) and str(row.get("domain") or "strategy") == "strategy"
    }
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "version_id",
            "updated_at",
            "source",
            "effect_label",
            "event_type",
            "event_label",
            "related_version_id",
            "governance_description",
            "governance_domain",
            "draw_guard_blocked_count",
            "draw_guard_avoid_rate",
            "draw_guard_missed_rate",
            "rollback_recommended",
            "match_id",
            "time",
            "match",
            "decision",
            "prediction_result",
            "handicap_result",
            "replay_guard",
            "replay_agent",
            "replay_net_hint",
            "drag_score",
            "drag_reason",
        ]
    )
    for row in rows:
        diagnostics = _as_mapping(row.get("negative_diagnostics"))
        version_id = _text(row.get("version_id"), "-")
        governance_row = _as_mapping(governance_by_version.get(str(row.get("version_id") or "")))
        sample_rows = [item for item in _as_list(row.get("sample_rows")) if isinstance(item, Mapping)]
        if not sample_rows:
            sample_rows = [{}]
        for sample in sample_rows:
            writer.writerow(
                [
                    version_id,
                    _text(row.get("updated_at"), "-"),
                    _text(row.get("source"), "-"),
                    _text(row.get("effect_label"), "-"),
                    _text(governance_row.get("event_type"), "-"),
                    _text(governance_row.get("event_label"), "-"),
                    _text(governance_row.get("related_version_id"), "-"),
                    _text(governance_row.get("description"), "-"),
                    _text(governance_row.get("domain"), "strategy"),
                    _safe_int(governance_row.get("draw_guard_blocked_count")),
                    _text(governance_row.get("draw_guard_avoid_rate_text"), "-"),
                    _text(governance_row.get("draw_guard_missed_rate_text"), "-"),
                    "YES" if diagnostics.get("rollback_recommended") else "NO",
                    _text(sample.get("match_id"), "-"),
                    _text(sample.get("time"), "-"),
                    _text(sample.get("title"), "-"),
                    _text(sample.get("decision"), "-"),
                    _text(sample.get("prediction_result"), "-"),
                    _text(sample.get("handicap_result"), "-"),
                    _text(sample.get("replay_guard"), "-"),
                    _text(sample.get("replay_agent"), "-"),
                    _safe_int(sample.get("replay_net_hint")),
                    _safe_int(sample.get("drag_score")),
                    _text(sample.get("drag_reason_text"), "-"),
                ]
            )
    for event in _as_list(governance.get("rows")):
        if not isinstance(event, Mapping) or str(event.get("domain") or "") != "draw_guard":
            continue
        writer.writerow(
            [
                _text(event.get("version_id"), "-"),
                _text(event.get("updated_at"), "-"),
                _text(event.get("source"), "-"),
                _text(event.get("effect_label"), "-"),
                _text(event.get("event_type"), "-"),
                _text(event.get("event_label"), "-"),
                _text(event.get("related_version_id"), "-"),
                _text(event.get("description"), "-"),
                _text(event.get("domain"), "draw_guard"),
                _safe_int(event.get("draw_guard_blocked_count")),
                _text(event.get("draw_guard_avoid_rate_text"), "-"),
                _text(event.get("draw_guard_missed_rate_text"), "-"),
                "YES" if str(event.get("effect_status") or "") == "negative" else "NO",
                "-",
                _text(event.get("updated_at"), "-"),
                _text(event.get("summary"), "-"),
                "-",
                "-",
                "-",
                "-",
                "-",
                0,
                0,
                _text(event.get("description"), "-"),
            ]
        )
    return output.getvalue()


def build_strategy_allowlist_report_lines(
    rows: Sequence[object] | object,
    *,
    generated_at: datetime | None = None,
    settlements: Sequence[Mapping[str, object]] | object | None = None,
) -> list[str]:
    current = generated_at or datetime.now()
    allowed = select_strategy_allowlist_rows(rows)
    lines = [
        "# \u7b56\u7565\u653e\u884c\u6e05\u5355",
        "",
        f"- \u751f\u6210\u65f6\u95f4: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- \u6b63\u5f0f\u653e\u884c\u573a\u6b21: {len(allowed)}",
        "",
    ]
    if not allowed:
        lines.extend(
            [
                "\u5f53\u524d\u6ca1\u6709\u7b56\u7565\u51c6\u5165\u4e3a\u6b63\u5f0f\u653e\u884c\u7684\u573a\u6b21\u3002",
                "",
                "## \u8d5b\u524d\u590d\u6838\u539f\u5219",
                "",
            ]
        )
        lines.extend(f"- [ ] {item}" for item in PRE_MATCH_REVIEW_CHECKLIST)
        return lines

    lines.extend(
        [
            "## \u653e\u884c\u573a\u6b21",
            "",
        ]
    )
    for index, row in enumerate(allowed, start=1):
        match = _row_match(row)
        prediction = _row_prediction(row)
        admission = _strategy_admission(prediction)
        home = _text(_field(match, "home_team"))
        away = _text(_field(match, "away_team"))
        league = _text(_field(match, "league"))
        title = f"### {index}. {league} | {home} vs {away}"
        lines.extend(
            [
                title,
                "",
                "| \u5b57\u6bb5 | \u5185\u5bb9 |",
                "|---|---|",
                f"| \u5f00\u8d5b\u65f6\u95f4 | {_md_cell(_field(match, 'match_date'))} {_md_cell(_field(match, 'match_time'))} |",
                f"| \u6570\u636e\u6e90 | {_md_cell(_field(match, 'source'))} / {_md_cell(_field(match, 'source_id'))} |",
                f"| \u51c6\u5165\u7ed3\u8bba | {_md_cell(_admission_label(admission))} |",
                f"| \u51c6\u5165\u52a8\u4f5c | {_md_cell(format_strategy_admission_action(admission))} |",
                f"| \u63a8\u8350 | {_md_cell(prediction.get('recommendation'))} |",
                f"| \u7f6e\u4fe1\u5ea6 | {_pct(prediction.get('confidence'))} |",
                f"| \u98ce\u9669\u7b49\u7ea7 | {_md_cell(_risk_text(prediction.get('risk_level')))} |",
                f"| \u9ad8\u51c6\u7b56\u7565 | \u6b63\u5f0f {_safe_int(admission.get('active_count'))} / \u89c2\u5bdf {_safe_int(admission.get('shadow_count'))} / \u5355\u73a9\u6cd5 {_safe_int(admission.get('single_play_count'))} |",
                f"| \u5019\u9009\u73a9\u6cd5 | {_md_cell(format_strategy_admission_pick(admission))} |",
                f"| \u51c6\u5165\u539f\u56e0 | {_md_cell(_admission_reasons(admission))} |",
                f"| \u51c6\u5165\u95e8\u69db | {_md_cell(format_strategy_admission_thresholds(admission))} |",
                f"| \u6458\u8981 | {_md_cell(admission.get('summary'))} |",
                "",
                "\u8d5b\u524d\u590d\u6838\u6e05\u5355",
                "",
            ]
        )
        lines.extend(f"- [ ] {item}" for item in PRE_MATCH_REVIEW_CHECKLIST)
        lines.append("")
    error_attribution = build_strategy_error_attribution_summary(settlements or [])
    if _safe_int(error_attribution.get("miss_count")) or _safe_int(error_attribution.get("unknown_count")):
        evaluation_agent = build_strategy_evaluation_agent_summary({}, settlements or [])
        statsbomb_review = build_statsbomb_event_review_summary(settlements or [])
        lines.extend(
            [
                "## \u6700\u8fd1\u590d\u76d8\u9519\u56e0",
                "",
                f"- Evaluation Agent: {evaluation_agent.get('status') or '-'} / {evaluation_agent.get('score') or '-'}",
                f"- \u8bc4\u4f30\u6458\u8981: {evaluation_agent.get('summary_text') or '-'}",
                f"- \u4e3b\u8981\u9519\u56e0: {error_attribution.get('top_reason') or '-'}",
                f"- \u9519\u56e0\u9879: {_safe_int(error_attribution.get('miss_count'))}",
                f"- \u5f85\u5224\u5b9a: {_safe_int(error_attribution.get('unknown_count'))}",
                "",
            ]
        )
        if _safe_int(statsbomb_review.get("sample_count")):
            lines.extend(
                [
                    "### StatsBomb \u8d5b\u540e\u4e8b\u4ef6\u590d\u76d8",
                    "",
                    f"- \u6458\u8981: {statsbomb_review.get('summary_text') or '-'}",
                    f"- xG\u5bf9\u9f50: {statsbomb_review.get('xg_alignment_rate_text') or '-'}",
                    f"- \u7ec8\u7ed3\u6ce2\u52a8: {statsbomb_review.get('finishing_variance_rate_text') or '-'}",
                    f"- \u6ce8\u610f: {statsbomb_review.get('leakage_note') or '-'}",
                    "",
                ]
            )
            for row in statsbomb_review.get("rows", []) if isinstance(statsbomb_review.get("rows"), list) else []:
                if isinstance(row, Mapping):
                    lines.extend([f"- {row.get('title') or '-'}: {_md_cell(row.get('body'))}", ""])
        recommendations = evaluation_agent.get("recommendations", []) if isinstance(evaluation_agent.get("recommendations"), list) else []
        if recommendations:
            lines.extend(["### Evaluation Agent \u5efa\u8bae", ""])
            for item in recommendations[:5]:
                if isinstance(item, Mapping):
                    lines.append(f"- {item.get('title') or '-'}: {item.get('body') or '-'}")
            lines.append("")
        rows_payload = error_attribution.get("rows", []) if isinstance(error_attribution.get("rows"), list) else []
        for row in rows_payload[:5]:
            if not isinstance(row, Mapping):
                continue
            lines.extend(
                [
                    f"### \u9519\u56e0\u6837\u672c: {row.get('title') or '-'}",
                    "",
                    str(row.get("body") or "-"),
                    "",
                ]
            )
    return lines


def build_high_accuracy_strategy_dashboard(
    status: Mapping[str, object] | object,
    settlements: Sequence[Mapping[str, object]] | object,
    policy_history: Sequence[Mapping[str, object]] | object | None = None,
    statsbomb_event_baseline: Mapping[str, object] | object | None = None,
    statsbomb_fewshot_memory: Mapping[str, object] | object | None = None,
    historical_replay: Mapping[str, object] | object | None = None,
    draw_release_guard_policy_status: Mapping[str, object] | object | None = None,
    draw_release_guard_policy_history: Sequence[Mapping[str, object]] | object | None = None,
    *,
    include_statsbomb_backfill_candidates: bool = False,
    video_review_fewshot_memory: Mapping[str, object] | object | None = None,
    statsbomb_review_training_samples: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    resolved = _as_mapping(status)
    settlement_items = [item for item in settlements if isinstance(item, Mapping)] if isinstance(settlements, Sequence) else []
    pool = _strategy_pool(resolved)
    validation = _as_mapping(resolved.get("validation"))
    breaker = _as_mapping(resolved.get("breaker"))
    settlement_summary = build_high_accuracy_strategy_settlement_summary(settlement_items)
    statsbomb_review_training_quality = build_statsbomb_review_training_quality_summary(statsbomb_review_training_samples or {})
    statsbomb_review_training_signal = _as_mapping(statsbomb_review_training_quality.get("signal"))
    statsbomb_review_training_weight_gate = _as_mapping(statsbomb_review_training_signal.get("weight_gate"))
    error_attribution = build_strategy_error_attribution_summary(
        settlement_items,
        error_weight_overrides=_as_mapping(statsbomb_review_training_signal.get("attribution_weights")),
    )
    historical_replay_summary = _as_mapping(historical_replay)
    formal_release_replay_summary = build_strategy_formal_release_settlement_summary(settlement_items)
    historical_replay_effective = (
        historical_replay_summary
        if _safe_int(historical_replay_summary.get("sample_count"))
        else formal_release_replay_summary
    )
    historical_replay_label = "历史回放" if _safe_int(historical_replay_summary.get("sample_count")) else "正式放行回放"
    historical_replay_settlements = [
        item
        for item in _as_list(historical_replay_effective.get("settlements"))
        if isinstance(item, Mapping)
    ]
    historical_error_attribution = build_strategy_error_attribution_summary(historical_replay_settlements)
    agent_trace_replay = build_agent_trace_replay_summary(settlement_items)
    agent_replay_downgrade = build_agent_replay_downgrade_backtest_summary(settlement_items)
    agent_replay_guard_tuning = build_agent_replay_guard_tuning_recommendation(settlement_items)
    allowlist_summary = build_strategy_allowlist_settlement_summary(settlement_items)
    allowlist_tuning = build_strategy_allowlist_tuning_recommendation(
        settlement_items,
        historical_error_attribution=historical_error_attribution,
        historical_replay=historical_replay_effective,
    )
    policy_effect_review = build_strategy_policy_effect_review(policy_history or [], settlement_items)
    policy_stability_monitor = _as_mapping(policy_effect_review.get("stability_monitor"))
    trend_tuning_effect_review = build_strategy_trend_tuning_effect_review(policy_effect_review)
    rollback_effect_review = build_strategy_policy_rollback_effect_review(policy_effect_review)
    freeze_override_status = build_strategy_policy_freeze_override_status(policy_history or [], rollback_effect_review)
    policy_tuning_guard = build_strategy_policy_tuning_guard(
        policy_stability_monitor,
        source="dashboard",
        trend_tuning_effect_review=trend_tuning_effect_review,
        rollback_effect_review=rollback_effect_review,
        freeze_override_status=freeze_override_status,
    )
    market_entropy_backtest = build_market_entropy_backtest_summary(settlement_items)
    handicap_margin_backtest = build_handicap_margin_backtest_summary(settlement_items)
    draw_release_guard_review = build_draw_release_guard_review_summary(settlement_items)
    draw_release_guard_tuning = build_draw_release_guard_policy_tuning_recommendation(
        settlement_items,
        draw_release_guard_policy_status,
    )
    draw_release_guard_tuning_effect = build_draw_release_guard_tuning_effect_review(
        draw_release_guard_policy_history or [],
        settlement_items,
    )
    draw_release_guard_rollback_effect = build_draw_release_guard_rollback_effect_review(
        draw_release_guard_policy_history or [],
        settlement_items,
    )
    draw_release_guard_freeze_override = build_draw_release_guard_freeze_override_status(
        draw_release_guard_policy_history or [],
        draw_release_guard_rollback_effect,
    )
    draw_release_guard_tuning_guard = build_draw_release_guard_tuning_guard(
        draw_release_guard_tuning,
        rollback_effect_review=draw_release_guard_rollback_effect,
        freeze_override_status=draw_release_guard_freeze_override,
    )
    policy_governance_event_summary = build_strategy_policy_governance_event_summary(
        policy_effect_review,
        draw_release_guard_policy_history=draw_release_guard_policy_history or [],
        draw_release_guard_tuning_effect_review=draw_release_guard_tuning_effect,
        draw_release_guard_rollback_effect_review=draw_release_guard_rollback_effect,
        draw_release_guard_freeze_override_status=draw_release_guard_freeze_override,
        draw_release_guard_tuning_guard=draw_release_guard_tuning_guard,
    )
    jc_bucket_feedback = build_jc_bucket_feedback_summary(resolved, settlement_items)
    live_feedback_loop = build_high_accuracy_live_feedback_summary(resolved)
    statsbomb_event_review = build_statsbomb_event_review_summary(settlement_items, statsbomb_event_baseline or {})
    video_review_memory = build_video_review_memory_summary(settlement_items)
    evaluation_agent = build_strategy_evaluation_agent_summary(
        resolved,
        settlement_items,
        statsbomb_event_baseline or {},
        statsbomb_fewshot_memory or {},
        settlement_summary=settlement_summary,
        error_attribution=error_attribution,
        allowlist_summary=allowlist_summary,
        jc_feedback=jc_bucket_feedback,
        event_review=statsbomb_event_review,
        video_review_memory=video_review_memory,
        video_review_fewshot_memory=video_review_fewshot_memory or {},
        statsbomb_review_training_samples=statsbomb_review_training_samples or {},
    )
    statsbomb_fewshot_monitor = _as_mapping(evaluation_agent.get("statsbomb_fewshot_monitor"))
    statsbomb_fewshot_quality = _as_mapping(evaluation_agent.get("statsbomb_fewshot_quality"))
    video_fewshot_memory = _as_mapping(evaluation_agent.get("video_review_fewshot_memory"))
    statsbomb_fewshot_health = build_statsbomb_fewshot_memory_health_summary(
        statsbomb_fewshot_monitor,
        statsbomb_fewshot_quality,
    )
    statsbomb_backfill_queue = build_statsbomb_fewshot_backfill_queue(
        statsbomb_fewshot_monitor,
        statsbomb_fewshot_quality,
        settlement_items,
        statsbomb_event_baseline or {},
        include_candidates=include_statsbomb_backfill_candidates,
    )
    statsbomb_health_drivers = build_statsbomb_fewshot_health_driver_summary(
        statsbomb_fewshot_health,
        statsbomb_backfill_queue,
        statsbomb_fewshot_memory or {},
    )
    stable_count = sum(1 for item in pool if bool(_strategy_stability(item).get("stable")))
    primary_count = sum(1 for item in pool if str(item.get("role") or "") == "primary")
    backup_count = sum(1 for item in pool if str(item.get("role") or "") == "backup")
    paused_count = _safe_int(breaker.get("paused_count"))
    runtime_active_count = _safe_int(resolved.get("runtime_active_count") or breaker.get("runtime_active_count"))
    live_feedback_active_count = _safe_int(resolved.get("live_feedback_active_count") or breaker.get("active_count"))
    live_feedback_pending_count = _safe_int(resolved.get("live_feedback_pending_count") or breaker.get("pending_count"))
    breaker_status = str(resolved.get("breaker_status") or breaker.get("status") or "-")
    recovery_status = str(resolved.get("recovery_status") or breaker.get("recovery_status") or "-")
    status_text = (
        f"{breaker_status} | 可用 {runtime_active_count}/{len(pool)} | 反馈 {live_feedback_active_count} / 待反馈 {live_feedback_pending_count}"
    )
    known_count = _safe_int(settlement_summary.get("known_count"))
    hit_rate = settlement_summary.get("hit_rate")
    hit_tone = "neutral"
    if known_count:
        hit_tone = "good" if _safe_float(hit_rate) >= 0.6 else "warning"

    metrics = [
        {
            "label": "\u7b56\u7565\u72b6\u6001",
            "value": status_text,
            "tone": "bad"
            if paused_count and runtime_active_count <= 0
            else "warning"
            if breaker_status in {"pending_live_feedback", "partial_paused", "recovering"}
            else "good"
            if bool(resolved.get("active"))
            else "neutral",
        },
        {
            "label": "\u6062\u590d\u72b6\u6001",
            "value": recovery_status,
            "tone": "warning" if recovery_status in {"in_progress", "pending_live_feedback", "watch"} else "bad" if recovery_status == "blocked" else "good",
        },
        {"label": "\u7b56\u7565\u6c60", "value": str(len(pool)), "tone": "info"},
        {"label": "\u7a33\u5b9a\u7b56\u7565", "value": f"{stable_count}/{len(pool)}", "tone": "good" if stable_count else "warning"},
        {"label": "\u65ad\u8def\u6682\u505c", "value": str(paused_count), "tone": "bad" if paused_count else "good"},
        {
            "label": "\u5b9e\u76d8\u53cd\u9988",
            "value": str(live_feedback_loop.get("summary_text") or "-"),
            "tone": str(live_feedback_loop.get("tone") or "neutral"),
        },
        {
            "label": "\u56de\u6d4b\u8bb0\u5f55",
            "value": str(_safe_int(validation.get("record_count"))),
            "tone": "neutral",
        },
        {"label": "\u771f\u5b9e\u547d\u4e2d", "value": str(settlement_summary.get("hit_rate_text") or "-"), "tone": hit_tone},
        {
            "label": "\u7b56\u7565\u9519\u56e0",
            "value": str(error_attribution.get("top_reason") or "-"),
            "tone": "warning" if _safe_int(error_attribution.get("miss_count")) else "good",
        },
        {
            "label": "StatsBomb\u6743\u91cd",
            "value": str(statsbomb_review_training_signal.get("summary_text") or "-"),
            "tone": "good"
            if bool(statsbomb_review_training_weight_gate.get("enabled"))
            else "warning"
            if str(statsbomb_review_training_weight_gate.get("mode") or "") == "report_only"
            else "neutral",
        },
        {
            "label": historical_replay_label,
            "value": (
                f"{_safe_int(historical_replay_effective.get('sample_count'))} | {historical_replay_effective.get('hit_rate_text') or '-'}"
                if _safe_int(historical_replay_effective.get("sample_count"))
                else "-"
            ),
            "tone": "warning"
            if _safe_int(historical_error_attribution.get("miss_count"))
            else "good"
            if _safe_int(historical_replay_effective.get("sample_count"))
            else "neutral",
        },
        {
            "label": "Agent Replay",
            "value": str(agent_trace_replay.get("top_agent") or "-"),
            "tone": "warning" if _safe_int(agent_trace_replay.get("agent_count")) else "neutral",
        },
        {
            "label": "Replay Guard",
            "value": str(agent_replay_downgrade.get("net", 0)),
            "tone": "good"
            if _safe_int(agent_replay_downgrade.get("net")) > 0
            else "bad"
            if _safe_int(agent_replay_downgrade.get("net")) < 0
            else "neutral",
        },
        {
            "label": "Replay Tuning",
            "value": str(agent_replay_guard_tuning.get("label") or "-"),
            "tone": str(agent_replay_guard_tuning.get("tone") or "neutral"),
        },
        {
            "label": "\u8c03\u53c2\u751f\u6548",
            "value": str(policy_effect_review.get("latest_label") or "-"),
            "tone": "good"
            if str(policy_effect_review.get("latest_status") or "") == "effective"
            else "bad"
            if str(policy_effect_review.get("latest_status") or "") == "negative"
            else "neutral",
        },
        {
            "label": "\u6cbb\u7406\u4e8b\u4ef6",
            "value": str(policy_governance_event_summary.get("summary_text") or "-"),
            "tone": "warning"
            if _safe_int(policy_governance_event_summary.get("rollback_count"))
            or _safe_int(policy_governance_event_summary.get("freeze_override_count"))
            or _safe_int(policy_governance_event_summary.get("trend_gate_count"))
            or _safe_int(policy_governance_event_summary.get("draw_guard_freeze_count"))
            or _safe_int(policy_governance_event_summary.get("draw_guard_freeze_override_count"))
            or _safe_int(policy_governance_event_summary.get("draw_guard_rollback_count"))
            else "neutral"
            if _safe_int(policy_governance_event_summary.get("event_count"))
            else "good",
        },
        {
            "label": "\u95e8\u63a7\u751f\u6548",
            "value": str(trend_tuning_effect_review.get("label") or "-"),
            "tone": str(trend_tuning_effect_review.get("tone") or "neutral"),
        },
        {
            "label": "\u56de\u6eda\u4fee\u590d",
            "value": str(rollback_effect_review.get("label") or "-"),
            "tone": str(rollback_effect_review.get("tone") or "neutral"),
        },
        {
            "label": "\u51bb\u7ed3\u89e3\u9664",
            "value": str(freeze_override_status.get("label") or "-"),
            "tone": str(freeze_override_status.get("tone") or "neutral"),
        },
        {
            "label": "\u7248\u672c\u7a33\u5b9a",
            "value": str(policy_stability_monitor.get("label") or "-"),
            "tone": str(policy_stability_monitor.get("tone") or "neutral"),
        },
        {
            "label": "\u8c03\u53c2\u95e8\u63a7",
            "value": str(policy_tuning_guard.get("label") or "-"),
            "tone": str(policy_tuning_guard.get("tone") or "neutral"),
        },
        {
            "label": "Evaluation",
            "value": f"{evaluation_agent.get('status', '-')} / {evaluation_agent.get('score', '-')}",
            "tone": "bad"
            if str(evaluation_agent.get("status") or "") == "tighten"
            else "warning"
            if str(evaluation_agent.get("status") or "") in {"watch", "collecting"}
            else "good",
        },
        {
            "label": "StatsBomb",
            "value": str(statsbomb_event_review.get("summary_text") or "-"),
            "tone": "warning"
            if str(statsbomb_event_review.get("status") or "") in {"variance_watch", "control_gap_watch"}
            else "good"
            if _safe_int(statsbomb_event_review.get("sample_count"))
            else "neutral",
        },
        {
            "label": "AI Video",
            "value": str(video_review_memory.get("summary_text") or "-"),
            "tone": "warning"
            if str(video_review_memory.get("status") or "") == "needs_more_evidence"
            else "good"
            if _safe_int(video_review_memory.get("actionable_count"))
            else "neutral",
        },
        {
            "label": "Video Memory",
            "value": str(video_fewshot_memory.get("summary_text") or "-"),
            "tone": "good"
            if _safe_int(video_fewshot_memory.get("matched_count"))
            else "neutral"
            if _safe_int(video_fewshot_memory.get("sample_count"))
            else "warning",
        },
        {
            "label": "SB Memory",
            "value": str(statsbomb_fewshot_monitor.get("summary_text") or "-"),
            "tone": "good"
            if _safe_int(statsbomb_fewshot_monitor.get("current_matched_count"))
            else "warning"
            if str(statsbomb_fewshot_monitor.get("status") or "") == "standby"
            else "neutral",
        },
        {
            "label": "SB Health",
            "value": str(statsbomb_fewshot_health.get("summary_text") or "-"),
            "tone": str(statsbomb_fewshot_health.get("tone") or "neutral"),
        },
        {
            "label": "SB Backfill",
            "value": str(statsbomb_backfill_queue.get("summary_text") or "-"),
            "tone": "warning" if _safe_int(statsbomb_backfill_queue.get("task_count")) else "good",
        },
        {
            "label": "SB Drivers",
            "value": str(statsbomb_health_drivers.get("summary_text") or "-"),
            "tone": str(statsbomb_health_drivers.get("tone") or "neutral"),
        },
        {
            "label": "JC\u7a33\u5b9a\u6876",
            "value": str(jc_bucket_feedback.get("summary_text") or "-"),
            "tone": "bad"
            if _safe_int(_as_mapping(jc_bucket_feedback.get("status_counts")).get("downgraded"))
            else "warning"
            if _safe_int(_as_mapping(jc_bucket_feedback.get("status_counts")).get("watch"))
            else "good"
            if _safe_int(jc_bucket_feedback.get("total"))
            else "neutral",
        },
        {
            "label": "\u653e\u884c\u547d\u4e2d",
            "value": str(allowlist_summary.get("hit_rate_text") or "-"),
            "tone": "good" if _safe_float(allowlist_summary.get("hit_rate")) >= 0.6 else "warning" if _safe_int(allowlist_summary.get("known_count")) else "neutral",
        },
        {
            "label": "Entropy避险",
            "value": str(market_entropy_backtest.get("retained_accuracy_text") or "-"),
            "tone": "good"
            if str(market_entropy_backtest.get("recommendation") or "") == "block_high_entropy"
            else "warning"
            if str(market_entropy_backtest.get("recommendation") or "") in {"observe_high_entropy", "collecting"}
            else "neutral",
        },
        {
            "label": "Handicap Margin",
            "value": str(handicap_margin_backtest.get("retained_accuracy_text") or "-"),
            "tone": "good"
            if str(handicap_margin_backtest.get("recommendation") or "") == "block_high_handicap_margin"
            else "warning"
            if str(handicap_margin_backtest.get("recommendation") or "") in {"observe_high_handicap_margin", "collecting"}
            else "neutral",
        },
        {
            "label": "\u5e73\u5c40\u62e6\u622a",
            "value": str(draw_release_guard_review.get("avoid_rate_text") or "-"),
            "tone": "good"
            if str(draw_release_guard_review.get("recommendation") or "") == "keep_draw_guard"
            else "bad"
            if str(draw_release_guard_review.get("recommendation") or "") == "loosen_draw_guard"
            else "warning"
            if str(draw_release_guard_review.get("recommendation") or "") == "collecting"
            else "neutral",
        },
        {
            "label": "\u5e73\u5c40\u8c03\u53c2",
            "value": str(draw_release_guard_tuning.get("label") or "-"),
            "tone": str(draw_release_guard_tuning.get("tone") or "neutral"),
        },
        {
            "label": "DrawGuard\u751f\u6548",
            "value": str(draw_release_guard_tuning_effect.get("label") or "-"),
            "tone": str(draw_release_guard_tuning_effect.get("tone") or "neutral"),
        },
        {
            "label": "DrawGuard\u56de\u6eda",
            "value": str(draw_release_guard_rollback_effect.get("label") or "-"),
            "tone": str(draw_release_guard_rollback_effect.get("tone") or "neutral"),
        },
        {
            "label": "DrawGuard\u95e8\u63a7",
            "value": str(draw_release_guard_tuning_guard.get("label") or "-"),
            "tone": str(draw_release_guard_tuning_guard.get("tone") or "neutral"),
        },
    ]
    validation_rows = [
        (
            "\u6837\u672c\u6765\u6e90",
            f"APP {_safe_int(validation.get('settlement_record_count'))} | \u5386\u53f2\u5e02\u573a {_safe_int(validation.get('historical_record_count'))}",
        ),
        (
            "\u5019\u9009\u7b56\u7565",
            f"{_safe_int(validation.get('candidate_count'))} | \u7a33\u5b9a {_safe_int(validation.get('stable_candidate_count'))}",
        ),
        ("\u65f6\u95f4\u8303\u56f4", f"{validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}"),
        (
            f"{historical_replay_label}\u6837\u672c",
            (
                f"{_safe_int(historical_replay_effective.get('sample_count'))} | "
                f"\u547d\u4e2d {historical_replay_effective.get('hit_rate_text') or '-'} | "
                f"\u4e3b\u56e0 {historical_error_attribution.get('top_reason') or '-'}"
            ),
        ),
        (
            "\u7ed3\u7b97\u547d\u4e2d",
            f"\u6b63\u5f0f {settlement_summary.get('official_summary_text')} | \u89c2\u5bdf {settlement_summary.get('shadow_summary_text')} | \u672a\u5224\u5b9a {_safe_int(settlement_summary.get('unknown_count'))}",
        ),
    ]
    if not bool(resolved.get("enabled")):
        guidance = [
            {
                "title": "\u7b56\u7565\u6c60\u672a\u542f\u7528",
                "body": "\u9700\u5148\u6267\u884c\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b\uff0c\u751f\u6210\u7b56\u7565\u6c60\u540e\u518d\u8fdb\u884c\u8d5b\u524d\u7b5b\u9009\u3002",
            }
        ]
    else:
        guidance = [
            {
                "title": "\u5206\u5c42\u4f7f\u7528",
                "body": f"\u4e3b\u7b56\u7565 {primary_count} \u6761\uff0c\u5907\u9009 {backup_count} \u6761\u3002\u4e3b\u7b56\u7565\u53ea\u5e94\u5728\u547d\u4e2d\u95e8\u69db\u548c\u98ce\u9669\u8fc7\u6ee4\u540c\u65f6\u901a\u8fc7\u65f6\u751f\u6548\u3002",
            },
            {
                "title": "\u590d\u76d8\u8981\u6c42",
                "body": "\u6bcf\u6b21\u8d5b\u679c\u56de\u6536\u540e\u8981\u89c2\u5bdf\u771f\u5b9e\u547d\u4e2d\u7387\u3002\u82e5\u8fde\u7eed\u672a\u547d\u4e2d\uff0c\u4e0b\u4e00\u6b65\u5e94\u52a0\u65ad\u8def\u5668\u800c\u4e0d\u662f\u7ee7\u7eed\u6269\u5927\u8986\u76d6\u3002",
            },
        ]
        if paused_count:
            guidance.insert(
                0,
                {
                    "title": "\u65ad\u8def\u5668\u5df2\u89e6\u53d1",
                    "body": f"{paused_count} \u6761\u7b56\u7565\u56e0\u771f\u5b9e\u7ed3\u7b97\u8fde\u9519\u5df2\u964d\u4e3a\u89c2\u5bdf\u3002\u7b56\u7565\u4ecd\u4f1a\u8bb0\u5f55\u5f71\u5b50\u7ed3\u7b97\uff0c\u8fde\u7eed\u8fbe\u5230\u6062\u590d\u547d\u4e2d\u8981\u6c42\u540e\u81ea\u52a8\u6062\u590d\u3002",
                },
            )
    return {
        "enabled": bool(resolved.get("enabled")),
        "updated_at": resolved.get("updated_at") or "-",
        "reason": resolved.get("reason") or "-",
        "metrics": metrics,
        "pool_rows": build_high_accuracy_strategy_pool_rows(resolved),
        "live_feedback_loop": live_feedback_loop,
        "settlement_rows": build_high_accuracy_strategy_settlement_rows(settlement_items),
        "error_attribution": error_attribution,
        "historical_strategy_replay": dict(historical_replay_effective),
        "formal_release_replay": dict(formal_release_replay_summary),
        "historical_error_attribution": historical_error_attribution,
        "agent_trace_replay": agent_trace_replay,
        "agent_replay_downgrade": agent_replay_downgrade,
        "agent_replay_guard_tuning": agent_replay_guard_tuning,
        "evaluation_agent": evaluation_agent,
        "statsbomb_review_training_quality": statsbomb_review_training_quality,
        "statsbomb_event_review": statsbomb_event_review,
        "video_review_memory": video_review_memory,
        "video_review_fewshot_memory": video_fewshot_memory,
        "statsbomb_fewshot_monitor": statsbomb_fewshot_monitor,
        "statsbomb_fewshot_health": statsbomb_fewshot_health,
        "statsbomb_fewshot_health_drivers": statsbomb_health_drivers,
        "statsbomb_backfill_queue": statsbomb_backfill_queue,
        "jc_bucket_feedback": jc_bucket_feedback,
        "allowlist_settlement_rows": build_strategy_allowlist_settlement_rows(settlement_items),
        "validation_rows": validation_rows,
        "guidance_rows": guidance,
        "settlement_summary": settlement_summary,
        "allowlist_settlement_summary": allowlist_summary,
        "allowlist_tuning": allowlist_tuning,
        "policy_effect_review": policy_effect_review,
        "policy_governance_event_summary": policy_governance_event_summary,
        "trend_tuning_effect_review": trend_tuning_effect_review,
        "rollback_effect_review": rollback_effect_review,
        "freeze_override_status": freeze_override_status,
        "policy_stability_monitor": policy_stability_monitor,
        "policy_tuning_guard": policy_tuning_guard,
        "market_entropy_backtest": market_entropy_backtest,
        "handicap_margin_backtest": handicap_margin_backtest,
        "draw_release_guard_review": draw_release_guard_review,
        "draw_release_guard_tuning": draw_release_guard_tuning,
        "draw_release_guard_tuning_effect": draw_release_guard_tuning_effect,
        "draw_release_guard_rollback_effect": draw_release_guard_rollback_effect,
        "draw_release_guard_freeze_override": draw_release_guard_freeze_override,
        "draw_release_guard_tuning_guard": draw_release_guard_tuning_guard,
    }
