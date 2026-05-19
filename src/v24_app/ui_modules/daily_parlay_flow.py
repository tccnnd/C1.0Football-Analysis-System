from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any


def _as_items(items: Sequence[Any] | object) -> list[Mapping[str, Any]]:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return default
    if resolved != resolved:
        return default
    return resolved


def _safe_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "mixed"}
    return bool(value)


def _safe_limit(limit: int) -> int:
    try:
        return max(0, int(limit))
    except (TypeError, ValueError):
        return 0


def _ticket_time(ticket: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = ticket.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return ""


def _md_cell(value: Any) -> str:
    return str(value if value is not None else "-").replace("|", "/").replace("\n", " ")


def _csv_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    if any(char in text for char in [",", '"', "\n", "\r"]):
        return '"' + text.replace('"', '""') + '"'
    return text


def _pct_text(value: Any) -> str:
    return f"{_safe_float(value) * 100:.1f}%"


def _safe_json(value: Any) -> Any:
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        return value if value == value else 0.0
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_safe_json(item) for item in value]
    return str(value)


def _leg_label(leg: Any) -> str:
    if not isinstance(leg, Mapping):
        return "-"
    teams = str(leg.get("display") or "").strip()
    if not teams:
        home = str(leg.get("home_team") or "").strip()
        away = str(leg.get("away_team") or "").strip()
        teams = f"{home} vs {away}".strip() if home or away else str(leg.get("match_id") or "").strip()
    play_type = str(leg.get("play_type") or "").strip()
    pick = str(leg.get("pick") or "").strip()
    pieces = [piece for piece in (play_type, teams, pick) if piece]
    return " ".join(pieces) if pieces else "-"


def _leg_labels(ticket: Mapping[str, Any]) -> list[str]:
    legs = ticket.get("legs", [])
    if not isinstance(legs, Sequence) or isinstance(legs, (str, bytes, bytearray)):
        return []
    return [_leg_label(leg) for leg in legs if isinstance(leg, Mapping)]


def _status(ticket: Mapping[str, Any], default: str) -> str:
    value = str(ticket.get("status") or default).strip().lower()
    return value or default


def _active_sort_key(ticket: Mapping[str, Any]) -> tuple[int, float, float, str, str]:
    return (
        0 if _safe_bool(ticket.get("mixed")) else 1,
        -_safe_float(ticket.get("rank_score"), _safe_float(ticket.get("expected_hit"))),
        -_safe_float(ticket.get("expected_hit")),
        _ticket_time(ticket, "created_at"),
        str(ticket.get("ticket_id") or ""),
    )


def _settled_sort_key(ticket: Mapping[str, Any]) -> tuple[str, str]:
    return (
        _ticket_time(ticket, "settled_at", "created_at", "timestamp"),
        str(ticket.get("ticket_id") or ""),
    )


def _expected_tone(expected_hit: float) -> str:
    if expected_hit >= 0.4:
        return "success"
    if expected_hit >= 0.25:
        return "info"
    return "muted"


def _settlement_tone(status: str) -> str:
    if status == "won":
        return "success"
    if status == "lost":
        return "danger"
    return "muted"


def _settled_result(ticket: Mapping[str, Any]) -> bool | None:
    is_hit = ticket.get("is_hit")
    if isinstance(is_hit, bool):
        return is_hit
    status = _status(ticket, "")
    if status == "won":
        return True
    if status == "lost":
        return False
    return None


def _row_body(ticket: Mapping[str, Any], labels: list[str]) -> str:
    display = str(ticket.get("display") or "").strip()
    if display:
        return display
    return " + ".join(labels) if labels else "-"


def build_daily_parlay_summary(active_tickets: Sequence[Any] | object, settled_tickets: Sequence[Any] | object) -> dict[str, Any]:
    active = _as_items(active_tickets)
    settled = _as_items(settled_tickets)
    settled_results = [_settled_result(item) for item in settled]
    won_count = sum(1 for result in settled_results if result is True)
    lost_count = sum(1 for result in settled_results if result is False)
    expected_values = [_safe_float(item.get("expected_hit")) for item in active if _safe_float(item.get("expected_hit")) > 0.0]
    hit_samples = won_count + lost_count
    return {
        "active_count": len(active),
        "settled_count": len(settled),
        "won_count": won_count,
        "lost_count": lost_count,
        "pending_count": sum(1 for item in active if _status(item, "pending") == "pending"),
        "mixed_count": sum(1 for item in active if _safe_bool(item.get("mixed"))),
        "avg_expected_hit": round(sum(expected_values) / len(expected_values), 4) if expected_values else 0.0,
        "hit_rate": round(won_count / hit_samples, 4) if hit_samples else 0.0,
        "has_active": bool(active),
        "has_settled": bool(settled),
    }


def build_daily_parlay_ticket_rows(active_tickets: Sequence[Any] | object, limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered = sorted(_as_items(active_tickets), key=_active_sort_key)
    for ticket in ordered[: _safe_limit(limit)]:
        expected_hit = round(_safe_float(ticket.get("expected_hit")), 4)
        labels = _leg_labels(ticket)
        ticket_id = str(ticket.get("ticket_id") or "").strip()
        source_text, source_id_text = _ticket_source_summary(ticket)
        rows.append(
            {
                "title": ticket_id or _ticket_time(ticket, "created_at") or "pending",
                "body": _row_body(ticket, labels),
                "tone": _expected_tone(expected_hit),
                "ticket_id": ticket_id,
                "source": source_text,
                "source_id": source_id_text,
                "expected_hit": expected_hit,
                "mixed": _safe_bool(ticket.get("mixed")),
                "status": _status(ticket, "pending"),
                "legs": labels,
                "created_at": _ticket_time(ticket, "created_at"),
            }
        )
    return rows


def build_daily_parlay_settlement_rows(settled_tickets: Sequence[Any] | object, limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered = sorted(_as_items(settled_tickets), key=_settled_sort_key, reverse=True)
    for ticket in ordered[: _safe_limit(limit)]:
        status = _status(ticket, "settled")
        expected_hit = round(_safe_float(ticket.get("expected_hit")), 4)
        labels = _leg_labels(ticket)
        ticket_id = str(ticket.get("ticket_id") or "").strip()
        source_text, source_id_text = _ticket_source_summary(ticket)
        rows.append(
            {
                "title": ticket_id or _ticket_time(ticket, "settled_at", "created_at") or status,
                "body": _row_body(ticket, labels),
                "tone": _settlement_tone(status),
                "ticket_id": ticket_id,
                "source": source_text,
                "source_id": source_id_text,
                "expected_hit": expected_hit,
                "mixed": _safe_bool(ticket.get("mixed")),
                "status": status,
                "legs": labels,
                "settled_at": _ticket_time(ticket, "settled_at"),
                "is_hit": ticket.get("is_hit") if isinstance(ticket.get("is_hit"), bool) else status == "won",
            }
        )
    return rows


def _parlay_repair_gate(ticket: Mapping[str, Any]) -> dict[str, Any]:
    gate = ticket.get("settlement_recovery_gate")
    resolved_gate = dict(gate) if isinstance(gate, Mapping) else {}
    legs = ticket.get("legs", [])
    if not isinstance(legs, Sequence) or isinstance(legs, (str, bytes, bytearray)):
        legs = []
    source_names: list[str] = []
    source_ids: list[str] = []
    missing_source_count = 0
    missing_source_id_count = 0
    invalid_leg_count = 0
    for leg in legs:
        if not isinstance(leg, Mapping):
            invalid_leg_count += 1
            continue
        source = str(leg.get("source") or ticket.get("source") or "").strip()
        source_id = str(leg.get("source_id") or ticket.get("source_id") or "").strip()
        if source:
            if source not in source_names:
                source_names.append(source)
        else:
            missing_source_count += 1
        if source_id:
            if source_id not in source_ids:
                source_ids.append(source_id)
        else:
            missing_source_id_count += 1

    resolved_gate.setdefault("status", "blocked" if invalid_leg_count or not legs or missing_source_count or missing_source_id_count or len(source_names) > 1 else "ready")
    resolved_gate.setdefault(
        "code",
        "parlay_invalid_legs"
        if invalid_leg_count or not legs
        else "parlay_source_traceability_missing"
        if missing_source_count or missing_source_id_count
        else "parlay_mixed_sources"
        if len(source_names) > 1
        else "ready",
    )
    resolved_gate.setdefault(
        "message",
        "来源追溯完整" if str(resolved_gate.get("status") or "") == "ready" else "二串一票据仍需人工修复",
    )
    resolved_gate.setdefault(
        "recommendation",
        "可以进入自动回收" if str(resolved_gate.get("status") or "") == "ready" else "请补齐 source / source_id 后再回收",
    )
    resolved_gate["ticket_id"] = str(ticket.get("ticket_id") or "").strip() or "-"
    resolved_gate["source"] = str(resolved_gate.get("source") or " / ".join(source_names) or "-")
    resolved_gate["source_id"] = str(resolved_gate.get("source_id") or " / ".join(source_ids) or "-")
    resolved_gate["leg_count"] = int(resolved_gate.get("leg_count", len(legs)) or len(legs))
    resolved_gate["missing_source_count"] = int(resolved_gate.get("missing_source_count", missing_source_count) or missing_source_count)
    resolved_gate["missing_source_id_count"] = int(resolved_gate.get("missing_source_id_count", missing_source_id_count) or missing_source_id_count)
    resolved_gate["invalid_leg_count"] = int(resolved_gate.get("invalid_leg_count", invalid_leg_count) or invalid_leg_count)
    resolved_gate["mixed_source_count"] = max(0, len(source_names) - 1)
    resolved_gate["created_at"] = str(ticket.get("created_at") or "")
    resolved_gate["settled_at"] = str(ticket.get("settled_at") or "")
    resolved_gate["legs"] = _leg_labels(ticket)
    return resolved_gate


def _parlay_manual_review_queue_items(parlay_tickets: Sequence[Any] | object) -> list[dict[str, Any]]:
    tickets = _as_items(parlay_tickets)
    items: list[dict[str, Any]] = []
    for ticket in tickets:
        if _status(ticket, "pending") != "pending":
            continue
        gate = _parlay_repair_gate(ticket)
        if str(gate.get("status") or "").strip().lower() == "ready":
            continue
        items.append(
            {
                "ticket_id": str(gate.get("ticket_id") or ticket.get("ticket_id") or "-"),
                "status": str(gate.get("status") or "blocked"),
                "code": str(gate.get("code") or "-"),
                "message": str(gate.get("message") or "-"),
                "recommendation": str(gate.get("recommendation") or "-"),
                "source": str(gate.get("source") or "-"),
                "source_id": str(gate.get("source_id") or "-"),
                "leg_count": int(gate.get("leg_count", 0) or 0),
                "missing_source_count": int(gate.get("missing_source_count", 0) or 0),
                "missing_source_id_count": int(gate.get("missing_source_id_count", 0) or 0),
                "invalid_leg_count": int(gate.get("invalid_leg_count", 0) or 0),
                "mixed_source_count": int(gate.get("mixed_source_count", 0) or 0),
                "created_at": str(gate.get("created_at") or ticket.get("created_at") or ""),
                "settled_at": str(gate.get("settled_at") or ticket.get("settled_at") or ""),
                "title": str(gate.get("ticket_id") or ticket.get("ticket_id") or ticket.get("created_at") or "parlay_review"),
                "body": (
                    f"{str(gate.get('code') or '-')} | {str(gate.get('message') or '-')}\n"
                    f"建议: {str(gate.get('recommendation') or '-')}\n"
                    f"来源: {str(gate.get('source') or '-')} | source_id: {str(gate.get('source_id') or '-')}"
                ),
                "tone": "danger" if str(gate.get("status") or "") == "blocked" else "warning",
                "gate": _safe_json(gate),
                "legs": list(gate.get("legs", [])) if isinstance(gate.get("legs"), Sequence) and not isinstance(gate.get("legs"), (str, bytes, bytearray)) else [],
            }
        )
        priority = build_daily_parlay_repair_queue_priority(items[-1])
        items[-1].update(
            {
                "route_type": priority["route_key"],
                "priority_score": priority["priority_score"],
                "priority_bucket": priority["priority_bucket"],
                "priority_label": priority["priority_label"],
                "priority_reason": priority["priority_reason"],
                "auto_recoverable": priority["auto_recoverable"],
            }
        )
    items.sort(
        key=lambda item: (
            -int(item.get("priority_score", 0) or 0),
            0 if bool(item.get("auto_recoverable")) else 1,
            str(item.get("created_at") or ""),
            str(item.get("ticket_id") or ""),
        )
    )
    return items


def build_daily_parlay_repair_queue_summary(parlay_tickets: Sequence[Any] | object) -> dict[str, Any]:
    tickets = _as_items(parlay_tickets)
    items = _parlay_manual_review_queue_items(tickets)
    priority_counts = build_daily_parlay_repair_queue_priority_counts(items)
    pending_count = sum(1 for ticket in tickets if _status(ticket, "pending") == "pending")
    blocked_count = len(items)
    ready_count = sum(
        1
        for ticket in tickets
        if _status(ticket, "pending") == "pending" and str(_parlay_repair_gate(ticket).get("status") or "").strip().lower() == "ready"
    )
    source_issue_count = sum(1 for item in items if str(item.get("code") or "") in {"parlay_source_traceability_missing", "parlay_invalid_legs"})
    mixed_source_count = sum(1 for item in items if str(item.get("code") or "") == "parlay_mixed_sources")
    if pending_count <= 0:
        status = "empty"
    elif blocked_count <= 0:
        status = "healthy"
    elif ready_count > 0:
        status = "attention"
    else:
        status = "blocked"
    tone = "good" if status == "healthy" else "warning" if status == "attention" else "bad"
    return {
        "status": status,
        "tone": tone,
        "pending_count": pending_count,
        "blocked_count": blocked_count,
        "ready_count": ready_count,
        "source_issue_count": source_issue_count,
        "mixed_source_count": mixed_source_count,
        "priority_counts": priority_counts,
        "queue_items": items,
        "priority_summary_text": (
            f"最高 {priority_counts.get('critical', 0)} | 高 {priority_counts.get('high', 0)} | "
            f"中 {priority_counts.get('medium', 0)} | 低 {priority_counts.get('low', 0)} | "
            f"可自动回填 {priority_counts.get('auto_recoverable', 0)}"
        ),
        "summary_text": (
            f"二串一修复队列 {status} | 待检查 {pending_count} | 待修复 {blocked_count} | "
            f"可自动回收 {ready_count} | 源问题 {source_issue_count} | 混源 {mixed_source_count}"
        ),
    }


def build_daily_parlay_repair_queue_rows(parlay_tickets: Sequence[Any] | object, limit: int = 20) -> list[dict[str, Any]]:
    items = _parlay_manual_review_queue_items(parlay_tickets)
    return [dict(item) for item in items[: _safe_limit(limit)]]


def daily_parlay_repair_queue_route_label(route_key: str | None) -> str:
    normalized = str(route_key or "").strip().lower()
    return {
        "source_backfill": "来源回填",
        "mixed_source_split": "混源拆票",
        "recovery_failure": "复跑失败",
    }.get(normalized, "全部")


def _daily_parlay_repair_queue_row_route(row: Mapping[str, Any]) -> str:
    code = str(row.get("code") or "").strip()
    mixed_source_count = _safe_limit(row.get("mixed_source_count", 0))
    missing_source_count = _safe_limit(row.get("missing_source_count", 0))
    missing_source_id_count = _safe_limit(row.get("missing_source_id_count", 0))
    invalid_leg_count = _safe_limit(row.get("invalid_leg_count", 0))
    if code == "parlay_mixed_sources" or mixed_source_count > 0:
        return "mixed_source_split"
    if code in {"parlay_source_traceability_missing", "parlay_invalid_legs"}:
        return "source_backfill"
    if missing_source_count > 0 or missing_source_id_count > 0 or invalid_leg_count > 0:
        return "source_backfill"
    return "manual_review"


def build_daily_parlay_repair_queue_route_counts(rows: Sequence[Any] | object) -> dict[str, int]:
    items = _as_items(rows)
    source_count = sum(1 for row in items if _daily_parlay_repair_queue_row_route(row) == "source_backfill")
    mixed_count = sum(1 for row in items if _daily_parlay_repair_queue_row_route(row) == "mixed_source_split")
    manual_count = sum(1 for row in items if _daily_parlay_repair_queue_row_route(row) == "manual_review")
    return {
        "all": len(items),
        "source_backfill": source_count,
        "mixed_source_split": mixed_count,
        "manual_review": manual_count,
    }


def filter_daily_parlay_repair_queue_rows(rows: Sequence[Any] | object, route_key: str | None = None) -> list[dict[str, Any]]:
    items = [dict(item) for item in _as_items(rows)]
    normalized = str(route_key or "").strip().lower()
    if normalized in {"", "all", "watch", "recovery_failure"}:
        return items
    return [item for item in items if _daily_parlay_repair_queue_row_route(item) == normalized]


def _daily_parlay_repair_queue_route_summary_text(rows: Sequence[Any] | object) -> str:
    counts = build_daily_parlay_repair_queue_route_counts(rows)
    return (
        f"{daily_parlay_repair_queue_route_label('source_backfill')}(source_backfill) {counts.get('source_backfill', 0)} | "
        f"{daily_parlay_repair_queue_route_label('mixed_source_split')}(mixed_source_split) {counts.get('mixed_source_split', 0)} | "
        f"其他(manual_review) {counts.get('manual_review', 0)}"
    )


def build_daily_parlay_repair_queue_action_hint(row: Mapping[str, Any] | object) -> dict[str, Any]:
    item = row if isinstance(row, Mapping) else {}
    route_key = str(item.get("route_type") or _daily_parlay_repair_queue_row_route(item)).strip().lower()
    if route_key == "source_backfill":
        return {
            "route_key": "source_backfill",
            "route_label": daily_parlay_repair_queue_route_label("source_backfill"),
            "tone": "warning",
            "action_key": "source_backfill",
            "primary_action": "从快照回填选中",
            "secondary_action": "回填全部",
            "message": "该票据存在 source/source_id 或腿信息缺口，优先用赛前快照索引补齐来源。",
            "recommendation": "先执行“从快照回填选中”；若同类票据很多，再执行“回填全部”。",
            "done_when": "回填后该票据不再进入来源回填分流，并在修复审计中产生记录。",
        }
    if route_key == "mixed_source_split":
        return {
            "route_key": "mixed_source_split",
            "route_label": daily_parlay_repair_queue_route_label("mixed_source_split"),
            "tone": "danger",
            "action_key": "mixed_source_split",
            "primary_action": "标记需拆票",
            "secondary_action": "重新生成票据",
            "message": "该票据包含多个来源，直接回收容易造成赛果错配。",
            "recommendation": "先执行“标记需拆票”，再回到二串一窗口重建单源票据。",
            "done_when": "票据被标记为 split_required，后续回收不再把混源票据当作可自动处理对象。",
        }
    return {
        "route_key": "manual_review",
        "route_label": "人工复查",
        "tone": "neutral",
        "action_key": "manual_review",
        "primary_action": "查看门禁原文",
        "secondary_action": "导出闭环报告",
        "message": "该票据不属于来源回填或混源拆票，需要按门禁原文人工判断。",
        "recommendation": "先查看门禁原文和腿概览，再决定是否重建票据或补充来源快照。",
        "done_when": "人工确认后通过回填、拆票或重新生成票据消除阻塞。",
    }


def build_daily_parlay_repair_queue_priority(row: Mapping[str, Any] | object) -> dict[str, Any]:
    item = row if isinstance(row, Mapping) else {}
    route_key = str(item.get("route_type") or _daily_parlay_repair_queue_row_route(item)).strip().lower()
    code = str(item.get("code") or "").strip()
    status = str(item.get("status") or "").strip().lower()
    missing_source_count = _safe_limit(item.get("missing_source_count", 0))
    missing_source_id_count = _safe_limit(item.get("missing_source_id_count", 0))
    invalid_leg_count = _safe_limit(item.get("invalid_leg_count", 0))
    mixed_source_count = _safe_limit(item.get("mixed_source_count", 0))
    route_base = {
        "mixed_source_split": 300,
        "source_backfill": 200,
    }.get(route_key, 100)
    issue_bonus = (
        missing_source_count * 20
        + missing_source_id_count * 18
        + invalid_leg_count * 24
        + mixed_source_count * 30
    )
    status_bonus = 30 if status == "blocked" else 12 if status == "warning" else 0
    code_bonus = 0
    if code == "parlay_mixed_sources":
        code_bonus += 24
    elif code == "parlay_source_traceability_missing":
        code_bonus += 16
    elif code == "parlay_invalid_legs":
        code_bonus += 20
    priority_score = route_base + issue_bonus + status_bonus + code_bonus
    if priority_score >= 320:
        priority_bucket = "critical"
        priority_label = "最高"
    elif priority_score >= 220:
        priority_bucket = "high"
        priority_label = "高"
    elif priority_score >= 120:
        priority_bucket = "medium"
        priority_label = "中"
    else:
        priority_bucket = "low"
        priority_label = "低"
    if route_key == "mixed_source_split":
        reason = "混源票据会影响回收准确性，优先拆票。"
    elif route_key == "source_backfill":
        reason = "该票据可通过来源回填快速恢复自动回收能力。"
    else:
        reason = "该票据需要人工复查门禁原文后再处理。"
    if missing_source_count > 0:
        reason += f" 缺 source {missing_source_count}。"
    if missing_source_id_count > 0:
        reason += f" 缺 source_id {missing_source_id_count}。"
    if invalid_leg_count > 0:
        reason += f" 非法腿 {invalid_leg_count}。"
    if mixed_source_count > 0:
        reason += f" 混源腿 {mixed_source_count}。"
    return {
        "route_key": route_key or "manual_review",
        "priority_score": priority_score,
        "priority_bucket": priority_bucket,
        "priority_label": priority_label,
        "priority_reason": reason,
        "auto_recoverable": route_key == "source_backfill",
    }


def build_daily_parlay_repair_queue_priority_counts(rows: Sequence[Any] | object) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "auto_recoverable": 0}
    for row in _as_items(rows):
        priority = build_daily_parlay_repair_queue_priority(row)
        bucket = str(priority.get("priority_bucket") or "low")
        if bucket in counts:
            counts[bucket] += 1
        if bool(priority.get("auto_recoverable")):
            counts["auto_recoverable"] += 1
    return counts


def _source_ref_match_id(ref: Mapping[str, Any]) -> str:
    match_id = str(ref.get("match_id") or "").strip()
    if match_id:
        return match_id
    match = ref.get("match") if isinstance(ref.get("match"), Mapping) else {}
    if isinstance(match, Mapping):
        match_id = str(match.get("match_id") or "").strip()
        if match_id:
            return match_id
        pieces = [
            str(match.get("match_date") or "").strip(),
            str(match.get("league") or "").strip(),
            str(match.get("home_team") or "").strip(),
            str(match.get("away_team") or "").strip(),
        ]
        if all(pieces):
            return "|".join(pieces)
    pieces = [
        str(ref.get("match_date") or "").strip(),
        str(ref.get("league") or "").strip(),
        str(ref.get("home_team") or "").strip(),
        str(ref.get("away_team") or "").strip(),
    ]
    return "|".join(pieces) if all(pieces) else ""


def _source_ref_value(ref: Mapping[str, Any], key: str) -> str:
    value = str(ref.get(key) or "").strip()
    if value:
        return value
    match = ref.get("match") if isinstance(ref.get("match"), Mapping) else {}
    if isinstance(match, Mapping):
        value = str(match.get(key) or "").strip()
        if value:
            return value
    return ""


def build_daily_parlay_source_backfill_index(source_refs: Sequence[Any] | object) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for ref in _as_items(source_refs):
        match_id = _source_ref_match_id(ref)
        if not match_id:
            continue
        source = _source_ref_value(ref, "source")
        source_id = _source_ref_value(ref, "source_id")
        if not source and not source_id:
            continue
        current = index.setdefault(match_id, {"source": "", "source_id": ""})
        if source and not current.get("source"):
            current["source"] = source
        if source_id and not current.get("source_id"):
            current["source_id"] = source_id
    return index


def _fresh_parlay_gate(ticket: dict[str, Any], checked_at: datetime | None = None) -> dict[str, Any]:
    temporary = dict(ticket)
    temporary.pop("settlement_recovery_gate", None)
    gate = _parlay_repair_gate(temporary)
    gate["checked_at"] = (checked_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    return gate


def apply_daily_parlay_source_backfill(
    parlay_tickets: Sequence[Any] | object,
    source_refs: Sequence[Any] | object,
    *,
    ticket_id: str | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    source_index = build_daily_parlay_source_backfill_index(source_refs)
    target_ticket_id = str(ticket_id or "").strip()
    updated_tickets = [deepcopy(dict(item)) for item in _as_items(parlay_tickets)]
    checked_at = generated_at or datetime.now()
    updated_ticket_count = 0
    updated_leg_count = 0
    missing_ref_count = 0
    checked_ticket_count = 0

    for ticket in updated_tickets:
        if target_ticket_id and str(ticket.get("ticket_id") or "").strip() != target_ticket_id:
            continue
        if _status(ticket, "pending") != "pending":
            continue
        checked_ticket_count += 1
        legs = ticket.get("legs")
        if not isinstance(legs, list):
            continue
        ticket_changed = False
        ticket_updated_leg_count = 0
        for leg in legs:
            if not isinstance(leg, dict):
                continue
            match_id = str(leg.get("match_id") or "").strip()
            if not match_id:
                continue
            ref = source_index.get(match_id, {})
            source = str(leg.get("source") or ticket.get("source") or "").strip()
            source_id = str(leg.get("source_id") or ticket.get("source_id") or "").strip()
            if (source and source_id) or not ref:
                if not source or not source_id:
                    missing_ref_count += 1
                continue
            leg_changed = False
            if not source and ref.get("source"):
                leg["source"] = str(ref.get("source") or "")
                leg_changed = True
            if not source_id and ref.get("source_id"):
                leg["source_id"] = str(ref.get("source_id") or "")
                leg_changed = True
            if leg_changed:
                ticket_changed = True
                ticket_updated_leg_count += 1
                updated_leg_count += 1
        if ticket_changed:
            updated_ticket_count += 1
            ticket["repair_queue_last_action"] = {
                "action": "source_backfill",
                "updated_at": checked_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_leg_count": ticket_updated_leg_count,
            }
            gate = _fresh_parlay_gate(ticket, checked_at)
            if str(gate.get("status") or "") == "ready":
                ticket.pop("settlement_recovery_gate", None)
            else:
                ticket["settlement_recovery_gate"] = gate

    summary = build_daily_parlay_repair_queue_summary(updated_tickets)
    return {
        "action": "source_backfill",
        "changed": updated_ticket_count > 0,
        "tickets": updated_tickets,
        "checked_ticket_count": checked_ticket_count,
        "updated_ticket_count": updated_ticket_count,
        "updated_leg_count": updated_leg_count,
        "missing_ref_count": missing_ref_count,
        "source_ref_count": len(source_index),
        "target_ticket_id": target_ticket_id or "-",
        "queue_summary": summary,
        "summary_text": (
            f"source backfill checked {checked_ticket_count} ticket(s), "
            f"updated {updated_ticket_count} ticket(s) / {updated_leg_count} leg(s), "
            f"remaining blocked {summary.get('blocked_count', 0)}"
        ),
    }


def mark_daily_parlay_split_required(
    parlay_tickets: Sequence[Any] | object,
    ticket_id: str,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    target_ticket_id = str(ticket_id or "").strip()
    updated_tickets = [deepcopy(dict(item)) for item in _as_items(parlay_tickets)]
    checked_at = generated_at or datetime.now()
    changed = False
    for ticket in updated_tickets:
        if str(ticket.get("ticket_id") or "").strip() != target_ticket_id:
            continue
        if _status(ticket, "pending") != "pending":
            continue
        gate = _fresh_parlay_gate(ticket, checked_at)
        ticket["manual_review_status"] = "split_required"
        ticket["manual_review_note"] = "Mixed-source or invalid parlay ticket should be split/regenerated before settlement recovery."
        ticket["repair_queue_last_action"] = {
            "action": "mark_split_required",
            "updated_at": checked_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        ticket["settlement_recovery_gate"] = {
            **gate,
            "status": "blocked",
            "code": str(gate.get("code") or "parlay_split_required"),
            "message": str(gate.get("message") or "Parlay ticket requires manual split/regeneration."),
            "recommendation": "Split or regenerate this ticket before rerunning result recovery.",
        }
        changed = True
        break
    summary = build_daily_parlay_repair_queue_summary(updated_tickets)
    return {
        "action": "mark_split_required",
        "changed": changed,
        "tickets": updated_tickets,
        "target_ticket_id": target_ticket_id or "-",
        "queue_summary": summary,
        "summary_text": (
            f"split mark {'updated' if changed else 'not_found'} for {target_ticket_id or '-'} | "
            f"remaining blocked {summary.get('blocked_count', 0)}"
        ),
    }


def build_daily_parlay_repair_audit_record(
    repair_result: Mapping[str, Any] | object,
    recovery_result: Mapping[str, Any] | object | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    repair = repair_result if isinstance(repair_result, Mapping) else {}
    recovery = recovery_result if isinstance(recovery_result, Mapping) else {}
    queue_summary = repair.get("queue_summary") if isinstance(repair.get("queue_summary"), Mapping) else {}
    gate = recovery.get("gate") if isinstance(recovery.get("gate"), Mapping) else {}
    manual_review = recovery.get("manual_review_items") if isinstance(recovery.get("manual_review_items"), list) else []
    recovery_error = str(recovery.get("error") or "").strip()
    changed = bool(repair.get("changed"))
    new_settled = int(_safe_float(recovery.get("new_settled"), 0.0))
    if recovery_error:
        status = "error"
    elif new_settled > 0:
        status = "settled"
    elif changed:
        status = "rechecked"
    else:
        status = "no_change"
    return {
        "schema_version": 1,
        "generated_at": (generated_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "action": str(repair.get("action") or "-"),
        "target_ticket_id": str(repair.get("target_ticket_id") or "-"),
        "changed": changed,
        "updated_ticket_count": int(_safe_float(repair.get("updated_ticket_count"), 0.0)),
        "updated_leg_count": int(_safe_float(repair.get("updated_leg_count"), 0.0)),
        "missing_ref_count": int(_safe_float(repair.get("missing_ref_count"), 0.0)),
        "queue_status_after_repair": str(queue_summary.get("status") or "-"),
        "queue_blocked_after_repair": int(_safe_float(queue_summary.get("blocked_count"), 0.0)),
        "queue_ready_after_repair": int(_safe_float(queue_summary.get("ready_count"), 0.0)),
        "recovery_status": "error" if recovery_error else "ok" if recovery else "not_run",
        "recovery_new_settled": new_settled,
        "recovery_won": int(_safe_float(recovery.get("won"), 0.0)),
        "recovery_lost": int(_safe_float(recovery.get("lost"), 0.0)),
        "recovery_skipped_source_health": int(_safe_float(recovery.get("skipped_source_health"), 0.0)),
        "recovery_manual_review_count": len(manual_review),
        "recovery_gate_status": str(gate.get("status") or "-"),
        "recovery_gate_ready": int(_safe_float(gate.get("ready_ticket_count"), 0.0)),
        "recovery_gate_blocked": int(_safe_float(gate.get("blocked_ticket_count"), 0.0)),
        "error": recovery_error,
        "repair_summary_text": str(repair.get("summary_text") or "-"),
        "recovery_summary_text": str(gate.get("summary_text") or "-"),
    }


def build_daily_parlay_repair_audit_summary(records: Sequence[Any] | object) -> dict[str, Any]:
    items = _as_items(records)
    total = len(items)
    status_counts: dict[str, int] = {}
    recovery_settled = 0
    updated_tickets = 0
    updated_legs = 0
    latest = items[0] if items else {}
    for item in items:
        status = str(item.get("status") or "unknown").strip() or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        recovery_settled += int(_safe_float(item.get("recovery_new_settled"), 0.0))
        updated_tickets += int(_safe_float(item.get("updated_ticket_count"), 0.0))
        updated_legs += int(_safe_float(item.get("updated_leg_count"), 0.0))
    latest_blocked = int(_safe_float(latest.get("queue_blocked_after_repair"), 0.0)) if isinstance(latest, Mapping) else 0
    latest_status = str(latest.get("status") or "-") if isinstance(latest, Mapping) else "-"
    tone = "bad" if status_counts.get("error", 0) else "warning" if latest_blocked > 0 else "good" if total else "neutral"
    return {
        "total": total,
        "status": "empty" if total <= 0 else "attention" if latest_blocked > 0 or status_counts.get("error", 0) else "healthy",
        "tone": tone,
        "status_counts": status_counts,
        "settled_count": int(status_counts.get("settled", 0)),
        "rechecked_count": int(status_counts.get("rechecked", 0)),
        "error_count": int(status_counts.get("error", 0)),
        "no_change_count": int(status_counts.get("no_change", 0)),
        "recovery_new_settled": recovery_settled,
        "updated_ticket_count": updated_tickets,
        "updated_leg_count": updated_legs,
        "latest_status": latest_status,
        "latest_generated_at": str(latest.get("generated_at") or "-") if isinstance(latest, Mapping) else "-",
        "latest_blocked_count": latest_blocked,
        "summary_text": (
            f"二串一修复审计 {total} 条 | settled {status_counts.get('settled', 0)} | "
            f"rechecked {status_counts.get('rechecked', 0)} | error {status_counts.get('error', 0)} | "
            f"累计新结算 {recovery_settled} | 最新待人工 {latest_blocked}"
        ),
    }


def build_daily_parlay_repair_audit_card_rows(records: Sequence[Any] | object) -> list[dict[str, Any]]:
    summary = build_daily_parlay_repair_audit_summary(records)
    total = int(_safe_float(summary.get("total"), 0.0))
    latest_blocked = int(_safe_float(summary.get("latest_blocked_count"), 0.0))
    error_count = int(_safe_float(summary.get("error_count"), 0.0))
    updated_legs = int(_safe_float(summary.get("updated_leg_count"), 0.0))
    recovery_new_settled = int(_safe_float(summary.get("recovery_new_settled"), 0.0))
    latest_status = str(summary.get("latest_status") or "-")
    return [
        {
            "label": "最新修复状态",
            "value": latest_status if total else "-",
            "tone": "bad" if error_count else "warning" if latest_blocked else "good" if total else "neutral",
            "detail": f"latest_at={summary.get('latest_generated_at') or '-'} | records={total}",
        },
        {
            "label": "复跑结算",
            "value": str(recovery_new_settled),
            "tone": "good" if recovery_new_settled > 0 else "neutral",
            "detail": f"settled_records={summary.get('settled_count', 0)}",
        },
        {
            "label": "已修复腿数",
            "value": str(updated_legs),
            "tone": "good" if updated_legs > 0 else "neutral",
            "detail": f"tickets={summary.get('updated_ticket_count', 0)}",
        },
        {
            "label": "最新待人工",
            "value": str(latest_blocked),
            "tone": "bad" if latest_blocked > 0 else "good" if total else "neutral",
            "detail": f"errors={error_count} | no_change={summary.get('no_change_count', 0)}",
        },
    ]


def _daily_parlay_repair_audit_tone(status: str, blocked_count: int) -> str:
    if status == "error":
        return "danger"
    if blocked_count > 0:
        return "warning"
    if status == "settled":
        return "success"
    if status == "rechecked":
        return "info"
    return "muted"


def build_daily_parlay_repair_audit_rows(records: Sequence[Any] | object, limit: int = 50) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _as_items(records)[: _safe_limit(limit)]:
        status = str(item.get("status") or "-")
        blocked = int(_safe_float(item.get("queue_blocked_after_repair"), 0.0))
        generated_at = str(item.get("generated_at") or "-")
        target = str(item.get("target_ticket_id") or "-")
        title = f"{generated_at} | {status} | {target}"
        body = (
            f"action={item.get('action') or '-'} | updated={int(_safe_float(item.get('updated_ticket_count'), 0.0))}/"
            f"{int(_safe_float(item.get('updated_leg_count'), 0.0))} | "
            f"settled={int(_safe_float(item.get('recovery_new_settled'), 0.0))} | "
            f"gate={item.get('recovery_gate_status') or '-'} | blocked={blocked}"
        )
        rows.append(
            {
                "title": title,
                "body": body,
                "tone": _daily_parlay_repair_audit_tone(status, blocked),
                "record": _safe_json(item),
                "generated_at": generated_at,
                "status": status,
                "target_ticket_id": target,
            }
        )
    return rows


def build_daily_parlay_repair_audit_detail(record: Mapping[str, Any] | object) -> str:
    item = record if isinstance(record, Mapping) else {}
    if not item:
        return "暂无二串一修复审计记录。"
    lines = [
        f"时间: {item.get('generated_at') or '-'}",
        f"状态: {item.get('status') or '-'}",
        f"动作: {item.get('action') or '-'}",
        f"目标票据: {item.get('target_ticket_id') or '-'}",
        "",
        "修复结果",
        f"- changed: {item.get('changed')}",
        f"- updated_ticket_count: {item.get('updated_ticket_count', 0)}",
        f"- updated_leg_count: {item.get('updated_leg_count', 0)}",
        f"- missing_ref_count: {item.get('missing_ref_count', 0)}",
        f"- queue_status_after_repair: {item.get('queue_status_after_repair') or '-'}",
        f"- queue_blocked_after_repair: {item.get('queue_blocked_after_repair', 0)}",
        f"- queue_ready_after_repair: {item.get('queue_ready_after_repair', 0)}",
        "",
        "复跑结果",
        f"- recovery_status: {item.get('recovery_status') or '-'}",
        f"- recovery_new_settled: {item.get('recovery_new_settled', 0)}",
        f"- recovery_won/lost: {item.get('recovery_won', 0)} / {item.get('recovery_lost', 0)}",
        f"- recovery_skipped_source_health: {item.get('recovery_skipped_source_health', 0)}",
        f"- recovery_manual_review_count: {item.get('recovery_manual_review_count', 0)}",
        f"- recovery_gate_status: {item.get('recovery_gate_status') or '-'}",
        f"- recovery_gate_ready/blocked: {item.get('recovery_gate_ready', 0)} / {item.get('recovery_gate_blocked', 0)}",
        "",
        f"修复摘要: {item.get('repair_summary_text') or '-'}",
        f"复跑摘要: {item.get('recovery_summary_text') or '-'}",
    ]
    if item.get("error"):
        lines.extend(["", f"错误: {item.get('error')}"])
    lines.extend(["", "原始记录", str(_safe_json(item))])
    return "\n".join(lines)


def build_daily_parlay_repair_loop_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"daily_parlay_repair_loop_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_daily_parlay_repair_loop_csv_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"daily_parlay_repair_loop_{current.strftime('%Y%m%d_%H%M%S')}.csv"


def build_daily_parlay_repair_loop_report_lines(
    snapshot: Mapping[str, Any] | object,
    *,
    generated_at: datetime | None = None,
) -> list[str]:
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    queue_summary = payload.get("repair_queue_summary") if isinstance(payload.get("repair_queue_summary"), Mapping) else {}
    queue_rows = [item for item in _as_items(payload.get("repair_queue_rows")) if isinstance(item, Mapping)]
    audit_summary = payload.get("repair_audit_summary") if isinstance(payload.get("repair_audit_summary"), Mapping) else {}
    audit_rows = [item for item in _as_items(payload.get("repair_audit_rows")) if isinstance(item, Mapping)]
    audit_card_rows = build_daily_parlay_repair_audit_card_rows(payload.get("repair_audit_records"))
    route_summary = _daily_parlay_repair_queue_route_summary_text(queue_rows)
    priority_summary_text = str(queue_summary.get("priority_summary_text") or "").strip()
    if not priority_summary_text:
        priority_counts = build_daily_parlay_repair_queue_priority_counts(queue_rows)
        priority_summary_text = (
            f"最高 {priority_counts.get('critical', 0)} | 高 {priority_counts.get('high', 0)} | "
            f"中 {priority_counts.get('medium', 0)} | 低 {priority_counts.get('low', 0)} | "
            f"可自动回填 {priority_counts.get('auto_recoverable', 0)}"
        )
    current = generated_at or datetime.now()
    lines = [
        "# 二串一修复闭环报告",
        "",
        f"- 生成时间: {current.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 修复队列: 待检查 {queue_summary.get('pending_count', 0)} | 待修复 {queue_summary.get('blocked_count', 0)} | 可自动回收 {queue_summary.get('ready_count', 0)}",
        f"- 审计摘要: {audit_summary.get('summary_text') or '-'}",
        "",
        "## 审计健康卡片",
        "",
        "| 指标 | 数值 | 说明 |",
        "| --- | ---: | --- |",
    ]
    lines.insert(4, f"- 自动分流: {route_summary}")
    lines.insert(5, f"- 优先级概览: {priority_summary_text}")
    if not audit_card_rows:
        lines.append("| - | - | - |")
    for row in audit_card_rows:
        if isinstance(row, Mapping):
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(row.get("label")),
                        _md_cell(row.get("value")),
                        _md_cell(row.get("detail")),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## 最近修复审计",
            "",
            "| # | 时间 | 状态 | 动作 | 票据 | 摘要 |",
            "| ---: | --- | --- | --- | --- | --- |",
        ]
    )
    if not audit_rows:
        lines.append("| - | - | - | - | - | 暂无修复审计记录 |")
    for index, row in enumerate(audit_rows[:20], start=1):
        record = row.get("record") if isinstance(row.get("record"), Mapping) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    _md_cell(row.get("generated_at") or record.get("generated_at")),
                    _md_cell(row.get("status") or record.get("status")),
                    _md_cell(record.get("action") or "-"),
                    _md_cell(row.get("target_ticket_id") or record.get("target_ticket_id")),
                    _md_cell(row.get("body") or record.get("repair_summary_text") or "-"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 当前待人工修复队列",
            "",
            "| # | 优先级 | 分流 | ticket_id | 状态 | 代码 | 时间 | 来源 | source_id | 建议 |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if not queue_rows:
        lines.append("| - | - | - | - | - | - | - | - | - | 当前没有待人工修复的二串一票据 |")
    for index, row in enumerate(queue_rows[:50], start=1):
        priority = build_daily_parlay_repair_queue_priority(row)
        route_type = row.get("route_type") or priority.get("route_key") or _daily_parlay_repair_queue_row_route(row)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    _md_cell(f"{row.get('priority_label') or priority.get('priority_label') or '-'} {row.get('priority_score') or priority.get('priority_score') or 0}"),
                    _md_cell(route_type),
                    _md_cell(row.get("ticket_id")),
                    _md_cell(row.get("status")),
                    _md_cell(row.get("code")),
                    _md_cell(row.get("created_at")),
                    _md_cell(row.get("source")),
                    _md_cell(row.get("source_id")),
                    _md_cell(row.get("recommendation")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 复盘关注点",
            "",
            f"- 来源缺口票据: {queue_summary.get('source_issue_count', 0)}",
            f"- 混源票据: {queue_summary.get('mixed_source_count', 0)}",
            f"- 最新待人工: {audit_summary.get('latest_blocked_count', 0)}",
            f"- 累计复跑新结算: {audit_summary.get('recovery_new_settled', 0)}",
            "",
            "## 边界",
            "",
            "- 本报告只汇总二串一修复闭环，不改写预测样本或赛前特征。",
            "- CSV 附件用于筛选反复出现的来源缺口、混源和复跑失败问题。",
        ]
    )
    return lines


def build_daily_parlay_repair_loop_csv_text(snapshot: Mapping[str, Any] | object) -> str:
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    audit_rows = [item for item in _as_items(payload.get("repair_audit_rows")) if isinstance(item, Mapping)]
    queue_rows = [item for item in _as_items(payload.get("repair_queue_rows")) if isinstance(item, Mapping)]
    headers = [
        "record_type",
        "generated_at",
        "status",
        "action",
        "ticket_id",
        "code",
        "updated_ticket_count",
        "updated_leg_count",
        "recovery_new_settled",
        "recovery_gate_status",
        "queue_blocked_after_repair",
        "route_type",
        "priority_bucket",
        "priority_score",
        "auto_recoverable",
        "message",
        "recommendation",
    ]
    lines = [",".join(headers)]
    for row in audit_rows:
        record = row.get("record") if isinstance(row.get("record"), Mapping) else {}
        values = [
            "audit",
            record.get("generated_at") or row.get("generated_at") or "",
            record.get("status") or row.get("status") or "",
            record.get("action") or "",
            record.get("target_ticket_id") or row.get("target_ticket_id") or "",
            "",
            record.get("updated_ticket_count", 0),
            record.get("updated_leg_count", 0),
            record.get("recovery_new_settled", 0),
            record.get("recovery_gate_status") or "",
            record.get("queue_blocked_after_repair", 0),
            record.get("route_type") or "",
            record.get("priority_bucket") or "",
            record.get("priority_score") or "",
            record.get("auto_recoverable") or "",
            record.get("repair_summary_text") or row.get("body") or "",
            record.get("recovery_summary_text") or "",
        ]
        lines.append(",".join(_csv_cell(value) for value in values))
    for row in queue_rows:
        priority = build_daily_parlay_repair_queue_priority(row)
        route_type = row.get("route_type") or priority.get("route_key") or _daily_parlay_repair_queue_row_route(row)
        values = [
            "queue",
            row.get("created_at") or "",
            row.get("status") or "",
            "",
            row.get("ticket_id") or "",
            row.get("code") or "",
            "",
            "",
            "",
            "",
            "",
            route_type,
            row.get("priority_bucket") or priority.get("priority_bucket") or "",
            row.get("priority_score") or priority.get("priority_score") or "",
            row.get("auto_recoverable") if "auto_recoverable" in row else priority.get("auto_recoverable") or "",
            row.get("message") or "",
            row.get("recommendation") or "",
        ]
        lines.append(",".join(_csv_cell(value) for value in values))
    return "\n".join(lines) + "\n"


def build_daily_parlay_repair_loop_export_message(
    md_path: Path | str,
    csv_path: Path | str,
    snapshot: Mapping[str, Any] | object,
) -> str:
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    queue_summary = payload.get("repair_queue_summary") if isinstance(payload.get("repair_queue_summary"), Mapping) else {}
    queue_rows = [item for item in _as_items(payload.get("repair_queue_rows")) if isinstance(item, Mapping)]
    audit_summary = payload.get("repair_audit_summary") if isinstance(payload.get("repair_audit_summary"), Mapping) else {}
    route_summary = _daily_parlay_repair_queue_route_summary_text(queue_rows)
    priority_summary_text = str(queue_summary.get("priority_summary_text") or "").strip()
    if not priority_summary_text:
        priority_counts = build_daily_parlay_repair_queue_priority_counts(queue_rows)
        priority_summary_text = (
            f"最高 {priority_counts.get('critical', 0)} | 高 {priority_counts.get('high', 0)} | "
            f"中 {priority_counts.get('medium', 0)} | 低 {priority_counts.get('low', 0)} | "
            f"可自动回填 {priority_counts.get('auto_recoverable', 0)}"
        )
    return "\n".join(
        [
            "二串一修复闭环报告已导出",
            "",
            f"Markdown: {md_path}",
            f"CSV: {csv_path}",
            f"优先级概览: {priority_summary_text}",
            f"自动分流: {route_summary}",
            f"待修复: {queue_summary.get('blocked_count', 0)}",
            f"审计记录: {audit_summary.get('total', 0)}",
            f"累计复跑新结算: {audit_summary.get('recovery_new_settled', 0)}",
        ]
    )


def build_daily_parlay_empty_state(summary: Mapping[str, Any] | object) -> str:
    resolved = summary if isinstance(summary, Mapping) else {}
    active_count = int(_safe_float(resolved.get("active_count"), 0.0))
    settled_count = int(_safe_float(resolved.get("settled_count"), 0.0))
    if active_count > 0:
        return ""
    if settled_count > 0:
        return "当前没有 active 二串一组合；近期结算在下方可查看。"
    return "尚未生成每日二串一；请先刷新并分析今日赛事。"


def build_daily_parlay_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"daily_parlay_recommendations_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_daily_parlay_snapshot(
    active_tickets: Sequence[Any] | object,
    settled_tickets: Sequence[Any] | object,
    selector_metrics: Mapping[str, Any] | object,
    *,
    generated_at: datetime | None = None,
    report_path: Path | str | None = None,
    source: str = "-",
) -> dict[str, Any]:
    active = _as_items(active_tickets)
    settled = _as_items(settled_tickets)
    metrics = selector_metrics if isinstance(selector_metrics, Mapping) else {}
    summary = build_daily_parlay_summary(active, settled)
    source_health = build_daily_parlay_source_health_summary(active, settled)
    current = generated_at or datetime.now()
    ticket_rows = build_daily_parlay_ticket_rows(active, limit=20)
    settlement_rows = build_daily_parlay_settlement_rows(settled, limit=20)
    source_names: list[str] = []
    source_ids: list[str] = []
    for ticket in [*active, *settled]:
        source_text, source_id_text = _ticket_source_summary(ticket)
        if source_text != "-" and source_text not in source_names:
            source_names.append(source_text)
        if source_id_text != "-" and source_id_text not in source_ids:
            source_ids.append(source_id_text)
    summary["source"] = " / ".join(source_names) if source_names else "-"
    summary["source_id"] = " / ".join(source_ids) if source_ids else "-"
    summary["source_summary_text"] = f"{summary['source']} | {summary['source_id']}"
    summary["source_health_status"] = str(source_health.get("status") or "healthy")
    summary["source_health_issue_count"] = int(_safe_float(source_health.get("issue_count"), 0.0))
    summary["source_health_tone"] = str(source_health.get("tone") or "neutral")
    summary["source_health_summary_text"] = str(source_health.get("summary_text") or "-")
    return {
        "schema_version": 1,
        "generated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "report_path": str(report_path) if report_path else "",
        "source": str(source or "-"),
        "summary": summary,
        "source_health": _safe_json(source_health),
        "source_health_card_rows": _safe_json(build_daily_parlay_source_health_card_rows(source_health)),
        "source_health_issue_rows": _safe_json(build_daily_parlay_source_health_issue_rows(source_health)),
        "selector_metrics": _safe_json(metrics),
        "active_tickets": _safe_json(active),
        "settled_tickets": _safe_json(settled),
        "ticket_rows": _safe_json(ticket_rows),
        "settlement_rows": _safe_json(settlement_rows),
        "empty_state": build_daily_parlay_empty_state(summary),
        "snapshot_signature": (
            f"active={summary.get('active_count', 0)} | settled={summary.get('settled_count', 0)} | "
            f"avg_hit={_pct_text(summary.get('avg_expected_hit'))} | hit_rate={_pct_text(summary.get('hit_rate'))}"
        ),
        "boundary": "每日二串一导出仅做赛前推荐快照和赛后结算留痕，不自动调整策略门槛。",
    }


def _ticket_id(item: Mapping[str, Any] | object) -> str:
    return str(item.get("ticket_id") or "").strip() if isinstance(item, Mapping) else ""


def _snapshot_tickets(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    tickets = _as_items(record.get("active_tickets"))
    if tickets:
        return tickets
    return _as_items(record.get("ticket_rows"))


def _ticket_source_summary(ticket: Mapping[str, Any] | object) -> tuple[str, str]:
    if not isinstance(ticket, Mapping):
        return "-", "-"
    legs = ticket.get("legs", [])
    if not isinstance(legs, Sequence) or isinstance(legs, (str, bytes, bytearray)):
        return "-", "-"
    sources: list[str] = []
    source_ids: list[str] = []
    for leg in legs:
        if not isinstance(leg, Mapping):
            continue
        source = str(leg.get("source") or "").strip()
        source_id = str(leg.get("source_id") or "").strip()
        if source and source not in sources:
            sources.append(source)
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)
    return (" / ".join(sources) if sources else "-", " / ".join(source_ids) if source_ids else "-")


def _source_issue_tone(severity: str) -> str:
    normalized = str(severity or "").strip().lower()
    if normalized in {"blocking", "high"}:
        return "bad"
    if normalized in {"warning", "medium"}:
        return "warning"
    if normalized in {"info", "low"}:
        return "info"
    return "neutral"


def _source_issue_sort_key(issue: Mapping[str, Any]) -> tuple[int, str, str]:
    severity = str(issue.get("severity") or "").strip().lower()
    order = {"blocking": 0, "high": 0, "warning": 1, "medium": 1, "info": 2, "low": 2}
    return (order.get(severity, 3), str(issue.get("code") or ""), str(issue.get("target") or ""))


def build_daily_parlay_source_health_summary(
    active_tickets: Sequence[Any] | object,
    settled_tickets: Sequence[Any] | object,
) -> dict[str, Any]:
    active = _as_items(active_tickets)
    settled = _as_items(settled_tickets)
    tickets = [*active, *settled]
    issue_map: dict[str, dict[str, Any]] = {}
    ticket_count = len(tickets)
    leg_count = 0
    traceable_leg_count = 0
    source_id_leg_count = 0
    missing_traceability_leg_count = 0
    mixed_ticket_count = 0
    full_traceable_ticket_count = 0
    partial_traceable_ticket_count = 0
    untraceable_ticket_count = 0
    source_family_names: list[str] = []
    traceable_ticket_ids: list[str] = []
    trace_gap_ticket_ids: list[str] = []
    mixed_ticket_ids: list[str] = []
    untraceable_ticket_ids: list[str] = []
    missing_source_id_ticket_ids: list[str] = []

    for ticket in tickets:
        ticket_id = str(ticket.get("ticket_id") or "").strip()
        ticket_source = str(ticket.get("source") or "").strip()
        ticket_source_id = str(ticket.get("source_id") or "").strip()
        legs = ticket.get("legs", [])
        if not isinstance(legs, Sequence) or isinstance(legs, (str, bytes, bytearray)):
            legs = []

        resolved_sources: list[str] = []
        ticket_leg_count = 0
        ticket_traceable_leg_count = 0
        ticket_source_id_count = 0
        ticket_missing_traceability_count = 0
        ticket_missing_source_id_count = 0
        ticket_mixed_sources = False

        for leg in legs:
            if not isinstance(leg, Mapping):
                continue
            leg_count += 1
            ticket_leg_count += 1
            leg_source = str(leg.get("source") or ticket_source or "").strip()
            leg_source_id = str(leg.get("source_id") or ticket_source_id or "").strip()
            if leg_source or leg_source_id:
                traceable_leg_count += 1
                ticket_traceable_leg_count += 1
            if leg_source:
                if leg_source not in resolved_sources:
                    resolved_sources.append(leg_source)
                if leg_source not in source_family_names:
                    source_family_names.append(leg_source)
            if leg_source_id:
                source_id_leg_count += 1
                ticket_source_id_count += 1
            else:
                ticket_missing_source_id_count += 1
            if not leg_source and not leg_source_id:
                missing_traceability_leg_count += 1
                ticket_missing_traceability_count += 1

        if ticket_leg_count <= 0:
            ticket_missing_traceability_count += 1
            missing_traceability_leg_count += 1

        if len(resolved_sources) > 1:
            mixed_ticket_count += 1
            ticket_mixed_sources = True
            if ticket_id and ticket_id not in mixed_ticket_ids:
                mixed_ticket_ids.append(ticket_id)

        if ticket_leg_count > 0 and ticket_traceable_leg_count == ticket_leg_count:
            full_traceable_ticket_count += 1
            if ticket_id and ticket_id not in traceable_ticket_ids:
                traceable_ticket_ids.append(ticket_id)
        elif ticket_traceable_leg_count > 0:
            partial_traceable_ticket_count += 1
            if ticket_id and ticket_id not in traceable_ticket_ids:
                traceable_ticket_ids.append(ticket_id)
        else:
            untraceable_ticket_count += 1
            if ticket_id and ticket_id not in untraceable_ticket_ids:
                untraceable_ticket_ids.append(ticket_id)

        if ticket_missing_source_id_count > 0:
            if ticket_id and ticket_id not in missing_source_id_ticket_ids:
                missing_source_id_ticket_ids.append(ticket_id)
            issue = issue_map.setdefault(
                "parlay_source_id_missing",
                {
                    "code": "parlay_source_id_missing",
                    "severity": "warning",
                    "message": "",
                    "recommendation": "回填 source_id 并在导出前重新生成快照，确保回收闭环能按场次回溯。",
                    "target": "",
                },
            )
            issue["message"] = (
                f"{ticket_missing_source_id_count}/{ticket_leg_count or 1} 条腿缺少 source_id"
                if ticket_missing_source_id_count > 0
                else "串关腿缺少 source_id"
            )
            issue["target"] = ticket_id or issue.get("target") or "-"

        if ticket_missing_traceability_count > 0:
            if ticket_id and ticket_id not in trace_gap_ticket_ids:
                trace_gap_ticket_ids.append(ticket_id)
            issue = issue_map.setdefault(
                "parlay_traceability_gap",
                {
                    "code": "parlay_traceability_gap",
                    "severity": "warning",
                    "message": "",
                    "recommendation": "补齐 source/source_id 后再生成串关快照，避免后续回收和复盘无法对账。",
                    "target": "",
                },
            )
            issue["message"] = "串关票据存在 source/source_id 追溯缺口"
            issue["target"] = " / ".join(trace_gap_ticket_ids[:5]) or "-"

        if ticket_mixed_sources:
            issue = issue_map.setdefault(
                "parlay_mixed_sources",
                {
                    "code": "parlay_mixed_sources",
                    "severity": "warning",
                    "message": "",
                    "recommendation": "尽量让同一串关票据的腿保持同源，若必须混源则拆分为单源票据后再导出。",
                    "target": "",
                },
            )
            issue["message"] = f"{mixed_ticket_count} 张票据含多来源腿"
            issue["target"] = " / ".join(mixed_ticket_ids[:5]) or "-"

    if ticket_count > 0 and traceable_leg_count <= 0:
        blocked_targets = [
            str(item.get("ticket_id") or "").strip()
            for item in tickets[:3]
            if isinstance(item, Mapping) and str(item.get("ticket_id") or "").strip()
        ]
        issue_map["parlay_traceability_blocked"] = {
            "code": "parlay_traceability_blocked",
            "severity": "blocking",
            "message": "当前串关票据没有任何可追溯来源腿",
            "recommendation": "先补齐 source/source_id，再生成或导出串关快照，否则回收闭环无法对账。",
            "target": " / ".join(blocked_targets) or "-",
        }

    if "parlay_source_id_missing" in issue_map:
        issue_map["parlay_source_id_missing"]["message"] = (
            f"{len(missing_source_id_ticket_ids)} 张票据存在 source_id 缺口 | "
            f"source_id {source_id_leg_count}/{leg_count or 0}"
        )
        issue_map["parlay_source_id_missing"]["target"] = " / ".join(missing_source_id_ticket_ids[:5]) or "-"
    if "parlay_traceability_gap" in issue_map:
        issue_map["parlay_traceability_gap"]["target"] = " / ".join(trace_gap_ticket_ids[:5]) or "-"
    if "parlay_mixed_sources" in issue_map:
        issue_map["parlay_mixed_sources"]["message"] = f"{mixed_ticket_count} 张票据含多来源腿"
        issue_map["parlay_mixed_sources"]["target"] = " / ".join(mixed_ticket_ids[:5]) or "-"

    issues = sorted(issue_map.values(), key=_source_issue_sort_key)
    blocking_count = sum(1 for item in issues if str(item.get("severity") or "").strip().lower() in {"blocking", "high"})
    warning_count = sum(1 for item in issues if str(item.get("severity") or "").strip().lower() in {"warning", "medium"})
    if blocking_count:
        status = "blocked"
    elif issues:
        status = "attention"
    else:
        status = "healthy"
    tone = "bad" if status == "blocked" else "warning" if status == "attention" else "good"
    source_coverage = round(traceable_leg_count / leg_count, 4) if leg_count else 1.0
    source_id_coverage = round(source_id_leg_count / leg_count, 4) if leg_count else 1.0
    ticket_traceability_ratio = round((full_traceable_ticket_count + partial_traceable_ticket_count) / ticket_count, 4) if ticket_count else 1.0
    issue_rows = [
        {
            "code": str(issue.get("code") or "-"),
            "severity": str(issue.get("severity") or "-"),
            "message": str(issue.get("message") or "-"),
            "recommendation": str(issue.get("recommendation") or "-"),
            "target": str(issue.get("target") or "-"),
            "tone": _source_issue_tone(str(issue.get("severity") or "")),
            "title": f"{str(issue.get('code') or '-')} | {str(issue.get('severity') or '-')}",
            "body": (
                f"{str(issue.get('message') or '-')}\n"
                f"建议: {str(issue.get('recommendation') or '-')}"
                + (f"\n范围: {str(issue.get('target') or '-')}" if str(issue.get("target") or "-") != "-" else "")
            ),
        }
        for issue in issues
    ]
    card_rows = [
        {
            "label": "整体状态",
            "value": status,
            "tone": tone,
            "detail": f"issues={len(issues)} | blocking={blocking_count} | warning={warning_count}",
        },
        {
            "label": "完整追溯票据",
            "value": f"{full_traceable_ticket_count}/{ticket_count}" if ticket_count else "0/0",
            "tone": "neutral" if ticket_count <= 0 else "good" if full_traceable_ticket_count == ticket_count else "warning" if full_traceable_ticket_count > 0 else "bad",
            "detail": f"partial={partial_traceable_ticket_count} | missing={untraceable_ticket_count}",
        },
        {
            "label": "来源腿覆盖",
            "value": f"{traceable_leg_count}/{leg_count}" if leg_count else "0/0",
            "tone": "neutral" if leg_count <= 0 else "good" if traceable_leg_count == leg_count else "warning" if traceable_leg_count > 0 else "bad",
            "detail": f"traceable_ratio={traceable_leg_count}/{leg_count or 1}",
        },
        {
            "label": "source_id覆盖",
            "value": f"{source_id_leg_count}/{leg_count}" if leg_count else "0/0",
            "tone": "neutral" if leg_count <= 0 else "good" if source_id_leg_count == leg_count else "warning" if source_id_leg_count > 0 else "bad",
            "detail": f"missing={max(0, leg_count - source_id_leg_count)}",
        },
        {
            "label": "混合来源票据",
            "value": str(mixed_ticket_count),
            "tone": "warning" if mixed_ticket_count > 0 else "good",
            "detail": f"ticket_ids={', '.join(mixed_ticket_ids[:3]) or '-'}",
        },
        {
            "label": "问题数",
            "value": str(len(issues)),
            "tone": "bad" if status == "blocked" else "warning" if status == "attention" else "good",
            "detail": f"traceability_ratio={ticket_traceability_ratio:.2f} | source_families={len(source_family_names)}",
        },
    ]
    return {
        "status": status,
        "tone": tone,
        "issue_count": len(issues),
        "issues": issues,
        "issue_rows": issue_rows,
        "card_rows": card_rows,
        "metrics": {
            "ticket_count": ticket_count,
            "leg_count": leg_count,
            "full_traceable_ticket_count": full_traceable_ticket_count,
            "partial_traceable_ticket_count": partial_traceable_ticket_count,
            "untraceable_ticket_count": untraceable_ticket_count,
            "traceable_leg_count": traceable_leg_count,
            "source_id_leg_count": source_id_leg_count,
            "missing_traceability_leg_count": missing_traceability_leg_count,
            "mixed_ticket_count": mixed_ticket_count,
            "traceable_ticket_ratio": ticket_traceability_ratio,
            "source_coverage": source_coverage,
            "source_id_coverage": source_id_coverage,
        },
        "source_family_count": len(source_family_names),
        "source_families": source_family_names,
        "traceable_ticket_ids": traceable_ticket_ids,
        "mixed_ticket_ids": mixed_ticket_ids,
        "untraceable_ticket_ids": untraceable_ticket_ids,
        "missing_source_id_ticket_ids": missing_source_id_ticket_ids,
        "summary_text": (
            f"来源健康 {status} | 完整票据 {full_traceable_ticket_count}/{ticket_count or 0} | "
            f"来源腿 {traceable_leg_count}/{leg_count or 0} | source_id {source_id_leg_count}/{leg_count or 0} | "
            f"问题 {len(issues)}"
        ),
    }


def build_daily_parlay_source_health_card_rows(source_health: Mapping[str, Any] | object) -> list[dict[str, Any]]:
    resolved = source_health if isinstance(source_health, Mapping) else {}
    rows = resolved.get("card_rows")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
        return [row for row in rows if isinstance(row, Mapping)]
    metrics = resolved.get("metrics") if isinstance(resolved.get("metrics"), Mapping) else {}
    status = str(resolved.get("status") or "healthy")
    tone = str(resolved.get("tone") or "neutral")
    ticket_count = _safe_float(metrics.get("ticket_count"), 0.0)
    leg_count = _safe_float(metrics.get("leg_count"), 0.0)
    traceable_leg_count = _safe_float(metrics.get("traceable_leg_count"), 0.0)
    source_id_leg_count = _safe_float(metrics.get("source_id_leg_count"), 0.0)
    mixed_ticket_count = _safe_float(metrics.get("mixed_ticket_count"), 0.0)
    return [
        {
            "label": "整体状态",
            "value": status,
            "tone": tone,
            "detail": str(resolved.get("summary_text") or "-"),
        },
        {
            "label": "完整追溯票据",
            "value": f"{int(_safe_float(metrics.get('full_traceable_ticket_count'), 0.0))}/{int(ticket_count)}",
            "tone": "neutral" if ticket_count <= 0 else "good" if _safe_float(metrics.get("full_traceable_ticket_count"), 0.0) >= ticket_count else "warning" if _safe_float(metrics.get("full_traceable_ticket_count"), 0.0) > 0 else "bad",
            "detail": f"partial={int(_safe_float(metrics.get('partial_traceable_ticket_count'), 0.0))} | missing={int(_safe_float(metrics.get('untraceable_ticket_count'), 0.0))}",
        },
        {
            "label": "来源腿覆盖",
            "value": f"{int(traceable_leg_count)}/{int(leg_count)}",
            "tone": "neutral" if leg_count <= 0 else "good" if traceable_leg_count >= leg_count else "warning" if traceable_leg_count > 0 else "bad",
            "detail": f"source_coverage={_safe_float(metrics.get('source_coverage'), 0.0):.2f}",
        },
        {
            "label": "source_id覆盖",
            "value": f"{int(source_id_leg_count)}/{int(leg_count)}",
            "tone": "neutral" if leg_count <= 0 else "good" if source_id_leg_count >= leg_count else "warning" if source_id_leg_count > 0 else "bad",
            "detail": f"source_id_ratio={_safe_float(metrics.get('source_id_coverage'), 0.0):.2f}",
        },
        {
            "label": "混合来源票据",
            "value": str(int(mixed_ticket_count)),
            "tone": "warning" if mixed_ticket_count > 0 else "good",
            "detail": f"source_families={int(_safe_float(resolved.get('source_family_count'), 0.0))}",
        },
        {
            "label": "问题数",
            "value": str(int(_safe_float(resolved.get("issue_count"), 0.0))),
            "tone": "bad" if status == "blocked" else "warning" if status == "attention" else "good",
            "detail": f"blocking={sum(1 for item in _as_items(resolved.get('issues')) if str(item.get('severity') or '').lower() in {'blocking', 'high'})}",
        },
    ]


def build_daily_parlay_source_health_issue_rows(source_health: Mapping[str, Any] | object, limit: int = 5) -> list[dict[str, Any]]:
    resolved = source_health if isinstance(source_health, Mapping) else {}
    issues = [item for item in _as_items(resolved.get("issues")) if isinstance(item, Mapping)]
    ordered = sorted(issues, key=_source_issue_sort_key)
    rows: list[dict[str, Any]] = []
    for issue in ordered[: _safe_limit(limit)]:
        rows.append(
            {
                "code": str(issue.get("code") or "-"),
                "severity": str(issue.get("severity") or "-"),
                "message": str(issue.get("message") or "-"),
                "recommendation": str(issue.get("recommendation") or "-"),
                "target": str(issue.get("target") or "-"),
                "tone": _source_issue_tone(str(issue.get("severity") or "")),
                "title": f"{str(issue.get('code') or '-')} | {str(issue.get('severity') or '-')}",
                "body": (
                    f"{str(issue.get('message') or '-')}\n"
                    f"建议: {str(issue.get('recommendation') or '-')}"
                    + (f"\n范围: {str(issue.get('target') or '-')}" if str(issue.get("target") or "-") != "-" else "")
                ),
            }
        )
    return rows


def build_daily_parlay_snapshot_settlement_closure(
    records: Sequence[Any] | object,
    settled_tickets: Sequence[Any] | object,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    snapshot_records = _as_items(records)
    settlements = [item for item in _as_items(settled_tickets) if _status(item, "") in {"won", "lost"}]
    settlement_by_id = {_ticket_id(item): item for item in settlements if _ticket_id(item)}
    current = generated_at or datetime.now()
    updated_records: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    summary_source_names: list[str] = []
    summary_source_ids: list[str] = []
    summary = {
        "status": "empty" if not snapshot_records else "pending",
        "snapshot_count": len(snapshot_records),
        "updated_snapshot_count": 0,
        "checked_ticket_count": 0,
        "settled_ticket_count": 0,
        "newly_settled_ticket_count": 0,
        "pending_ticket_count": 0,
        "won_count": 0,
        "lost_count": 0,
        "status_counts": status_counts,
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "changed": False,
        "summary_text": "暂无每日二串一导出快照。",
    }

    for record in snapshot_records:
        next_record = dict(record)
        tickets = _snapshot_tickets(record)
        ticket_ids = [_ticket_id(item) for item in tickets if _ticket_id(item)]
        source_names: list[str] = []
        source_ids_list: list[str] = []
        for ticket in tickets:
            source_text, source_id_text = _ticket_source_summary(ticket)
            if source_text != "-" and source_text not in source_names:
                source_names.append(source_text)
            if source_id_text != "-" and source_id_text not in source_ids_list:
                source_ids_list.append(source_id_text)
        matched = [settlement_by_id[ticket_id] for ticket_id in ticket_ids if ticket_id in settlement_by_id]
        matched_ids = [_ticket_id(item) for item in matched if _ticket_id(item)]
        previous = record.get("parlay_recovery") if isinstance(record.get("parlay_recovery"), Mapping) else {}
        previous_matched_ids = previous.get("matched_ticket_ids") if isinstance(previous, Mapping) else []
        previous_ids = (
            {str(item) for item in previous_matched_ids if str(item).strip()}
            if isinstance(previous_matched_ids, Sequence) and not isinstance(previous_matched_ids, (str, bytes, bytearray))
            else set()
        )
        matched_id_set = set(matched_ids)
        newly_settled = len(matched_id_set - previous_ids)
        won = sum(1 for item in matched if _status(item, "") == "won")
        lost = sum(1 for item in matched if _status(item, "") == "lost")
        pending = max(0, len(ticket_ids) - len(set(matched_ids)))
        if not ticket_ids:
            status = "empty"
        elif pending == 0:
            status = "settled"
        elif matched_ids:
            status = "partial"
        else:
            status = "pending"
        recovery = {
            "status": status,
            "checked_ticket_count": len(ticket_ids),
            "settled_ticket_count": len(set(matched_ids)),
            "newly_settled_ticket_count": newly_settled,
            "pending_ticket_count": pending,
            "won_count": won,
            "lost_count": lost,
            "source": " / ".join(source_names) if source_names else "-",
            "source_id": " / ".join(source_ids_list) if source_ids_list else "-",
            "source_summary_text": (
                f"{' / '.join(source_names) if source_names else '-'} | "
                f"{' / '.join(source_ids_list) if source_ids_list else '-'}"
            ),
            "matched_ticket_ids": sorted(matched_id_set),
            "pending_ticket_ids": [ticket_id for ticket_id in ticket_ids if ticket_id not in matched_id_set],
            "settled_rows": _safe_json(build_daily_parlay_settlement_rows(matched, limit=20)),
            "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        }
        compare_keys = (
            "status",
            "checked_ticket_count",
            "settled_ticket_count",
            "pending_ticket_count",
            "won_count",
            "lost_count",
            "matched_ticket_ids",
            "pending_ticket_ids",
        )
        previous_compare = {key: previous.get(key) for key in compare_keys} if isinstance(previous, Mapping) else {}
        recovery_compare = {key: recovery.get(key) for key in compare_keys}
        if previous_compare != recovery_compare:
            next_record["parlay_recovery"] = recovery
            summary["updated_snapshot_count"] += 1
            summary["changed"] = True
        updated_records.append(next_record)
        status_counts[status] = int(status_counts.get(status, 0) or 0) + 1
        for source in source_names:
            if source not in summary_source_names:
                summary_source_names.append(source)
        for source_id in source_ids_list:
            if source_id not in summary_source_ids:
                summary_source_ids.append(source_id)
        summary["checked_ticket_count"] += len(ticket_ids)
        summary["settled_ticket_count"] += len(set(matched_ids))
        summary["newly_settled_ticket_count"] += newly_settled
        summary["pending_ticket_count"] += pending
        summary["won_count"] += won
        summary["lost_count"] += lost

    if status_counts:
        if int(status_counts.get("pending", 0) or 0) == len(snapshot_records):
            summary["status"] = "pending"
        elif int(status_counts.get("settled", 0) or 0) == len(snapshot_records):
            summary["status"] = "settled"
        elif int(status_counts.get("partial", 0) or 0) or int(status_counts.get("settled", 0) or 0):
            summary["status"] = "partial"
        else:
            summary["status"] = "empty"
    summary["summary_text"] = (
        f"快照 {summary['snapshot_count']} | 已结算 {summary['settled_ticket_count']}/"
        f"{summary['checked_ticket_count']} | 新增闭环 {summary['newly_settled_ticket_count']} | "
        f"命中 {summary['won_count']} | 未中 {summary['lost_count']} | 待回收 {summary['pending_ticket_count']}"
    )
    summary["source"] = " / ".join(summary_source_names) if summary_source_names else "-"
    summary["source_id"] = " / ".join(summary_source_ids) if summary_source_ids else "-"
    summary["source_summary_text"] = f"{summary['source']} | {summary['source_id']}"
    return {"records": updated_records, "summary": summary}


def build_daily_parlay_report_lines(snapshot: Mapping[str, Any] | object) -> list[str]:
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    source_health = payload.get("source_health") if isinstance(payload.get("source_health"), Mapping) else {}
    source_health_card_rows = payload.get("source_health_card_rows") if isinstance(payload.get("source_health_card_rows"), list) else []
    source_health_issue_rows = payload.get("source_health_issue_rows") if isinstance(payload.get("source_health_issue_rows"), list) else []
    metrics = payload.get("selector_metrics") if isinstance(payload.get("selector_metrics"), Mapping) else {}
    ticket_rows = payload.get("ticket_rows") if isinstance(payload.get("ticket_rows"), list) else []
    settlement_rows = payload.get("settlement_rows") if isinstance(payload.get("settlement_rows"), list) else []
    lines = [
        "# 每日二串一推荐报告",
        "",
        f"- 生成时间: {payload.get('generated_at') or '-'}",
        f"- 来源: {payload.get('source') or '-'}",
        f"- 快照签名: {payload.get('snapshot_signature') or '-'}",
        f"- 当前组合: {summary.get('active_count', 0)}",
        f"- 平均命中: {_pct_text(summary.get('avg_expected_hit'))}",
        f"- 近期结算: {summary.get('settled_count', 0)}",
        f"- 近期命中: {_pct_text(summary.get('hit_rate'))}",
        f"- 票据来源: {summary.get('source') or '-'} | {summary.get('source_id') or '-'}",
        "",
        "## 来源健康审计",
        "",
        f"- 状态: {source_health.get('status') or '-'} | 问题数: {source_health.get('issue_count', 0)} | 来源家族: {source_health.get('source_family_count', 0)}",
        f"- 摘要: {source_health.get('summary_text') or '-'}",
        "",
        "| 指标 | 数值 | 说明 |",
        "| --- | ---: | --- |",
    ]
    visible_source_cards = [item for item in source_health_card_rows if isinstance(item, Mapping)]
    if not visible_source_cards:
        lines.append("| - | - | - |")
    for row in visible_source_cards[:8]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("label")),
                    _md_cell(row.get("value")),
                    _md_cell(row.get("detail")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 来源问题与建议",
            "",
            "| 问题代码 | 严重级别 | 说明 | 建议 | 范围 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    visible_source_issues = [item for item in source_health_issue_rows if isinstance(item, Mapping)]
    if not visible_source_issues:
        lines.append("| - | - | - | - | - |")
    for row in visible_source_issues[:5]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("code")),
                    _md_cell(row.get("severity")),
                    _md_cell(row.get("message")),
                    _md_cell(row.get("recommendation")),
                    _md_cell(row.get("target")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 组合健康",
            "",
            "| 指标 | 数值 |",
            "| --- | ---: |",
            f"| 当前票据 | {_md_cell(metrics.get('ticket_count', summary.get('active_count', 0)))} |",
            f"| 唯一场次 | {_md_cell(metrics.get('unique_match_count', 0))} |",
            f"| 最大场次暴露 | {_md_cell(metrics.get('max_match_exposure', 0))} |",
            f"| 混合比例 | {_pct_text(metrics.get('mixed_ratio', 0))} |",
            f"| 最高组合命中 | {_pct_text(metrics.get('max_expected_hit', 0))} |",
            f"| 低折扣组合 | {_md_cell(metrics.get('low_discount_count', 0))} |",
            f"| 高爆冷腿 | {_md_cell(metrics.get('high_upset_leg_count', 0))} |",
            "",
            "## 今日推荐组合",
            "",
            "| # | ticket_id | 来源 | 来源ID | 类型 | 预期命中 | 状态 | 创建时间 | 组合腿 |",
            "| ---: | --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    visible_tickets = [item for item in ticket_rows if isinstance(item, Mapping)]
    if not visible_tickets:
        lines.append(f"| - | - | - | - | - | - | {_md_cell(payload.get('empty_state') or '当前没有可展示的二串一组合。')} |")
    for index, row in enumerate(visible_tickets, start=1):
        legs = row.get("legs") if isinstance(row.get("legs"), list) else []
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    _md_cell(row.get("ticket_id") or row.get("title") or "-"),
                    _md_cell(row.get("source") or "-"),
                    _md_cell(row.get("source_id") or "-"),
                    "混合玩法" if _safe_bool(row.get("mixed")) else "同类玩法",
                    _pct_text(row.get("expected_hit")),
                    _md_cell(row.get("status") or "-"),
                    _md_cell(row.get("created_at") or "-"),
                    _md_cell(" + ".join(str(item) for item in legs) or row.get("body") or "-"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 近期二串一结算",
            "",
            "| # | ticket_id | 来源 | 来源ID | 结果 | 预期命中 | 结算时间 | 组合腿 |",
            "| ---: | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    visible_settlements = [item for item in settlement_rows if isinstance(item, Mapping)]
    if not visible_settlements:
        lines.append("| - | - | - | - | - | 暂无二串一结算记录 |")
    for index, row in enumerate(visible_settlements, start=1):
        status = str(row.get("status") or "-")
        status_text = "命中" if status == "won" else "未中" if status == "lost" else status
        legs = row.get("legs") if isinstance(row.get("legs"), list) else []
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    _md_cell(row.get("ticket_id") or row.get("title") or "-"),
                    _md_cell(row.get("source") or "-"),
                    _md_cell(row.get("source_id") or "-"),
                    _md_cell(status_text),
                    _pct_text(row.get("expected_hit")),
                    _md_cell(row.get("settled_at") or "-"),
                    _md_cell(" + ".join(str(item) for item in legs) or row.get("body") or "-"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 边界",
            "",
            f"- {payload.get('boundary') or '每日二串一导出仅做推荐快照留痕。'}",
            "- 推荐组合需要在赛前信息、盘口变化和策略准入状态更新后重新生成。",
            "- 结算记录只用于复盘，不应反向写入赛前预测特征。",
        ]
    )
    return lines


def build_daily_parlay_export_message(path: Path | str, snapshot: Mapping[str, Any] | object) -> str:
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    source_health = payload.get("source_health") if isinstance(payload.get("source_health"), Mapping) else {}
    return "\n".join(
        [
            "每日二串一报告已导出",
            "",
            f"文件: {path}",
            f"当前组合: {summary.get('active_count', 0)}",
            f"近期结算: {summary.get('settled_count', 0)}",
            f"快照签名: {payload.get('snapshot_signature') or '-'}",
            f"来源健康: {source_health.get('status') or summary.get('source_health_status') or '-'} | 问题 {source_health.get('issue_count', summary.get('source_health_issue_count', 0))}",
            f"健康摘要: {source_health.get('summary_text') or summary.get('source_health_summary_text') or '-'}",
            "",
            "已同步写入快照留痕，便于后续赛果回收和复盘对照。",
        ]
    )


def build_daily_parlay_export_guard_text(snapshot: Mapping[str, Any] | object) -> str:
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    source_health = payload.get("source_health") if isinstance(payload.get("source_health"), Mapping) else {}
    source_health_issue_rows = payload.get("source_health_issue_rows") if isinstance(payload.get("source_health_issue_rows"), list) else []
    issue_rows = [item for item in source_health_issue_rows if isinstance(item, Mapping)]
    status = str(source_health.get("status") or summary.get("source_health_status") or "healthy")
    issue_count = int(_safe_float(source_health.get("issue_count"), _safe_float(summary.get("source_health_issue_count"), 0.0)))
    lines = [
        "每日二串一导出前的来源健康审计",
        "",
        f"状态: {status}",
        f"问题数: {issue_count}",
        f"摘要: {source_health.get('summary_text') or summary.get('source_health_summary_text') or '-'}",
    ]
    for row in issue_rows[:3]:
        lines.append(
            f"- {str(row.get('code') or '-')}: {str(row.get('message') or '-')} | {str(row.get('recommendation') or '-')}"
        )
    if status == "blocked":
        lines.append("")
        lines.append("当前来源健康已阻断，建议先补齐 source_id / source 留痕后再导出。")
    elif status == "attention":
        lines.append("")
        lines.append("当前来源健康需要关注，建议确认是否继续导出，并尽快补齐缺口。")
    else:
        lines.append("")
        lines.append("当前来源健康可用，可以继续导出。")
    return "\n".join(lines)
