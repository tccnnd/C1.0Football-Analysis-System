from __future__ import annotations

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
    return {
        "schema_version": 1,
        "generated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "report_path": str(report_path) if report_path else "",
        "source": str(source or "-"),
        "summary": summary,
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
    return "\n".join(
        [
            "每日二串一报告已导出",
            "",
            f"文件: {path}",
            f"当前组合: {summary.get('active_count', 0)}",
            f"近期结算: {summary.get('settled_count', 0)}",
            f"快照签名: {payload.get('snapshot_signature') or '-'}",
            "",
            "已同步写入快照留痕，便于后续赛果回收和复盘对照。",
        ]
    )
