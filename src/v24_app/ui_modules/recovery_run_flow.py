from __future__ import annotations

from typing import Mapping, Sequence


STATUS_LABELS = {
    "running": "\u8fd0\u884c\u4e2d",
    "success": "\u6210\u529f",
    "failed": "\u5931\u8d25",
}


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _status_label(status: object) -> str:
    key = str(status or "").strip().lower()
    return STATUS_LABELS.get(key, key or "-")


def _elapsed_text(value: object) -> str:
    seconds = _safe_float(value, default=-1.0)
    if seconds < 0:
        return "-"
    return f"{seconds:.2f}s"


def _run_items(records: Sequence[Mapping[str, object]] | object) -> list[Mapping[str, object]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []
    return [item for item in records if isinstance(item, Mapping)]


def build_result_recovery_run_summary(records: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    rows = _run_items(records)
    completed = [item for item in rows if str(item.get("status") or "").lower() in {"success", "failed"}]
    success = [item for item in completed if str(item.get("status") or "").lower() == "success"]
    failed = [item for item in completed if str(item.get("status") or "").lower() == "failed"]
    running = [item for item in rows if str(item.get("status") or "").lower() == "running"]
    recent_completed = completed[-10:]
    recent_success = [item for item in recent_completed if str(item.get("status") or "").lower() == "success"]
    elapsed_values = [
        _safe_float(item.get("elapsed_seconds"), default=-1.0)
        for item in completed[-20:]
        if _safe_float(item.get("elapsed_seconds"), default=-1.0) >= 0
    ]
    avg_elapsed = sum(elapsed_values) / len(elapsed_values) if elapsed_values else None
    latest = rows[-1] if rows else {}
    total_new_settled = sum(_safe_int(item.get("new_settled"), 0) for item in completed)
    success_rate = (len(recent_success) / len(recent_completed)) if recent_completed else None
    latest_status = str(latest.get("status") or "-") if latest else "-"
    return {
        "total": len(rows),
        "completed_count": len(completed),
        "success_count": len(success),
        "failed_count": len(failed),
        "running_count": len(running),
        "recent_success_rate": success_rate,
        "recent_success_rate_text": f"{success_rate:.0%}" if success_rate is not None else "-",
        "avg_elapsed_seconds": avg_elapsed,
        "avg_elapsed_text": _elapsed_text(avg_elapsed) if avg_elapsed is not None else "-",
        "total_new_settled": total_new_settled,
        "latest_status": latest_status,
        "latest_status_label": _status_label(latest_status),
        "latest_started_at": str(latest.get("started_at") or "-") if latest else "-",
        "latest_finished_at": str(latest.get("finished_at") or "-") if latest else "-",
        "latest_new_settled": _safe_int(latest.get("new_settled"), 0) if latest else 0,
        "latest_error": str(latest.get("error") or "-") if latest else "-",
    }


def build_result_recovery_run_rows(
    records: Sequence[Mapping[str, object]] | object,
    *,
    limit: int = 30,
) -> list[dict[str, object]]:
    rows = list(reversed(_run_items(records)))[0 : max(0, int(limit))]
    result: list[dict[str, object]] = []
    for item in rows:
        status = str(item.get("status") or "-").lower()
        title = (
            f"{_status_label(status)} | {item.get('started_at') or '-'} | "
            f"\u65b0\u589e\u7ed3\u7b97 {_safe_int(item.get('new_settled'), 0)}"
        )
        body = (
            f"\u8017\u65f6: {_elapsed_text(item.get('elapsed_seconds'))} | "
            f"\u5b8c\u573a: {_safe_int(item.get('fetched_finished'), 0)} | "
            f"\u4fee\u590d\u5feb\u7167: {_safe_int(item.get('restored_snapshots'), 0)} | "
            f"\u6765\u6e90: {item.get('source') or '-'}"
        )
        if status == "failed":
            body = f"{body}\n\u9519\u8bef: {item.get('error') or '-'}"
        result.append({"title": title, "body": body, "status": status, "record": dict(item)})
    return result


def build_result_recovery_run_detail(record: Mapping[str, object] | object) -> str:
    item = _as_mapping(record)
    result = _as_mapping(item.get("result"))
    messages = item.get("messages")
    if not isinstance(messages, list):
        messages = result.get("messages") if isinstance(result.get("messages"), list) else []
    message_text = "\n".join(f"- {message}" for message in messages if message) or "- \u65e0"
    return (
        f"\u8fd0\u884c ID: {item.get('run_id') or '-'}\n"
        f"\u72b6\u6001: {_status_label(item.get('status'))}\n"
        f"\u89e6\u53d1: {item.get('trigger') or '-'} / {item.get('source_view') or '-'}\n"
        f"\u5f00\u59cb: {item.get('started_at') or '-'}\n"
        f"\u7ed3\u675f: {item.get('finished_at') or '-'}\n"
        f"\u8017\u65f6: {_elapsed_text(item.get('elapsed_seconds'))}\n"
        f"\u6570\u636e\u6e90: {item.get('source') or result.get('source') or '-'}\n\n"
        f"\u6838\u5fc3\u6307\u6807:\n"
        f"- \u56de\u770b\u5929\u6570: {_safe_int(item.get('lookback_days') or result.get('lookback_days'), 0)}\n"
        f"- \u5b8c\u573a\u573a\u6b21: {_safe_int(item.get('fetched_finished') or result.get('fetched_finished'), 0)}\n"
        f"- \u4fee\u590d\u5feb\u7167: {_safe_int(item.get('restored_snapshots') or result.get('restored_snapshots'), 0)}\n"
        f"- \u65b0\u589e\u7ed3\u7b97: {_safe_int(item.get('new_settled') or result.get('new_settled'), 0)}\n"
        f"- \u65b0\u589e\u4e8c\u4e32\u4e00\u7ed3\u7b97: {_safe_int(item.get('new_parlay_settled') or result.get('new_parlay_settled'), 0)}\n"
        f"- \u5df2\u7ed3\u7b97\u8df3\u8fc7: {_safe_int(item.get('already_settled') or result.get('already_settled'), 0)}\n"
        f"- \u5176\u4ed6\u8df3\u8fc7: {_safe_int(item.get('skipped') or result.get('skipped'), 0)}\n"
        f"- \u5feb\u7167\u56de\u67e5: {_safe_int(item.get('snapshot_checked') or result.get('snapshot_checked'), 0)} / "
        f"{_safe_int(item.get('snapshot_result_hits') or result.get('snapshot_result_hits'), 0)}\n"
        f"- \u9884\u6d4b\u5feb\u7167\u547d\u4e2d: {_safe_int(item.get('snapshot_predictions') or result.get('snapshot_predictions'), 0)}\n\n"
        f"\u9519\u8bef:\n- {item.get('error') or '-'}\n\n"
        f"\u6d88\u606f:\n{message_text}"
    )
