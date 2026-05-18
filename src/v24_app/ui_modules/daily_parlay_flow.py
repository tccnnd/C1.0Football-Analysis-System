from __future__ import annotations

from collections.abc import Mapping, Sequence
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
        rows.append(
            {
                "title": ticket_id or _ticket_time(ticket, "created_at") or "pending",
                "body": _row_body(ticket, labels),
                "tone": _expected_tone(expected_hit),
                "ticket_id": ticket_id,
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
        rows.append(
            {
                "title": ticket_id or _ticket_time(ticket, "settled_at", "created_at") or status,
                "body": _row_body(ticket, labels),
                "tone": _settlement_tone(status),
                "ticket_id": ticket_id,
                "expected_hit": expected_hit,
                "mixed": _safe_bool(ticket.get("mixed")),
                "status": status,
                "legs": labels,
                "settled_at": _ticket_time(ticket, "settled_at"),
                "is_hit": ticket.get("is_hit") if isinstance(ticket.get("is_hit"), bool) else status == "won",
            }
        )
    return rows


def build_daily_parlay_empty_state(summary: Mapping[str, Any] | object) -> str:
    resolved = summary if isinstance(summary, Mapping) else {}
    active_count = int(_safe_float(resolved.get("active_count"), 0.0))
    settled_count = int(_safe_float(resolved.get("settled_count"), 0.0))
    if active_count > 0:
        return ""
    if settled_count > 0:
        return "当前没有 active 二串一组合；近期结算在下方可查看。"
    return "尚未生成每日二串一；请先刷新并分析今日赛事。"
