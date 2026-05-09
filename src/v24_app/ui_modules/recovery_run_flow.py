from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence


STATUS_LABELS = {
    "running": "\u8fd0\u884c\u4e2d",
    "success": "\u6210\u529f",
    "failed": "\u5931\u8d25",
    "interrupted": "\u4e2d\u65ad",
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


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _run_items(records: Sequence[Mapping[str, object]] | object) -> list[Mapping[str, object]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return []
    return [item for item in records if isinstance(item, Mapping)]


def mark_stale_result_recovery_runs(
    records: Sequence[Mapping[str, object]] | object,
    *,
    now: datetime | None = None,
    stale_after_minutes: int = 60,
) -> dict[str, object]:
    rows = _run_items(records)
    current = now or datetime.now()
    threshold_seconds = max(1, int(stale_after_minutes)) * 60
    normalized: list[dict[str, object]] = []
    updated: list[dict[str, object]] = []
    for item in rows:
        record = dict(item)
        if str(record.get("status") or "").lower() == "running":
            started_at = _parse_timestamp(record.get("started_at"))
            if started_at is not None:
                elapsed = max(0.0, (current - started_at).total_seconds())
                if elapsed >= threshold_seconds:
                    record.update(
                        {
                            "status": "interrupted",
                            "finished_at": current.strftime("%Y-%m-%d %H:%M:%S"),
                            "elapsed_seconds": round(elapsed, 4),
                            "error": "\u4e0a\u6b21\u56de\u6536\u672a\u6b63\u5e38\u5b8c\u6210\uff0c\u53ef\u80fd\u662f APP \u5173\u95ed\u6216\u4efb\u52a1\u4e2d\u65ad",
                        }
                    )
                    messages = record.get("messages")
                    if not isinstance(messages, list):
                        messages = []
                    record["messages"] = [*messages, "\u8fd0\u884c\u8bb0\u5f55\u5df2\u81ea\u52a8\u6807\u8bb0\u4e3a\u4e2d\u65ad"]
                    updated.append(dict(record))
        normalized.append(record)
    return {"items": normalized, "updated": updated, "updated_count": len(updated)}


def build_result_recovery_run_summary(records: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    rows = _run_items(records)
    completed = [item for item in rows if str(item.get("status") or "").lower() in {"success", "failed", "interrupted"}]
    success = [item for item in completed if str(item.get("status") or "").lower() == "success"]
    failed = [item for item in completed if str(item.get("status") or "").lower() in {"failed", "interrupted"}]
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


def build_result_recovery_quality_alerts(
    records: Sequence[Mapping[str, object]] | object,
    *,
    failure_streak_threshold: int = 2,
    no_settlement_window: int = 3,
    elapsed_multiplier: float = 2.0,
    min_elapsed_seconds: float = 10.0,
) -> list[dict[str, str]]:
    rows = _run_items(records)
    completed = [item for item in rows if str(item.get("status") or "").lower() in {"success", "failed", "interrupted"}]
    if not completed and rows and str(rows[-1].get("status") or "").lower() == "running":
        return [
            {
                "severity": "info",
                "title": "\u56de\u6536\u4efb\u52a1\u6b63\u5728\u8fd0\u884c",
                "body": f"\u5f00\u59cb\u65f6\u95f4: {rows[-1].get('started_at') or '-'}",
                "tone": "info",
            }
        ]
    if not completed:
        return []

    alerts: list[dict[str, str]] = []
    latest_completed = completed[-1]
    if str(latest_completed.get("status") or "").lower() == "interrupted":
        alerts.append(
            {
                "severity": "high",
                "title": "\u4e0a\u6b21\u56de\u6536\u4efb\u52a1\u4e2d\u65ad",
                "body": str(latest_completed.get("error") or "\u56de\u6536\u672a\u6b63\u5e38\u5b8c\u6210\uff0c\u5efa\u8bae\u91cd\u65b0\u6267\u884c\u56de\u6536\u5e76\u68c0\u67e5\u5feb\u7167\u72b6\u6001\u3002"),
                "tone": "bad",
            }
        )
    failure_streak = 0
    for item in reversed(completed):
        if str(item.get("status") or "").lower() in {"failed", "interrupted"}:
            failure_streak += 1
        else:
            break
    if failure_streak >= max(1, int(failure_streak_threshold)):
        latest = completed[-1]
        alerts.append(
            {
                "severity": "high",
                "title": f"\u8fde\u7eed\u56de\u6536\u5931\u8d25/\u4e2d\u65ad {failure_streak} \u6b21",
                "body": f"\u6700\u8fd1\u9519\u8bef: {latest.get('error') or '-'}",
                "tone": "bad",
            }
        )

    success_runs = [item for item in completed if str(item.get("status") or "").lower() == "success"]
    recent_success = success_runs[-max(1, int(no_settlement_window)) :]
    if len(recent_success) >= max(1, int(no_settlement_window)) and all(_safe_int(item.get("new_settled"), 0) == 0 for item in recent_success):
        total_finished = sum(_safe_int(item.get("fetched_finished"), 0) for item in recent_success)
        total_restored = sum(_safe_int(item.get("restored_snapshots"), 0) for item in recent_success)
        alerts.append(
            {
                "severity": "medium",
                "title": f"\u8fd1 {len(recent_success)} \u6b21\u56de\u6536\u65e0\u65b0\u7ed3\u7b97",
                "body": f"\u671f\u95f4\u5b8c\u573a {total_finished} \u573a\uff0c\u4fee\u590d\u5feb\u7167 {total_restored} \u573a\u3002\u5efa\u8bae\u68c0\u67e5\u5feb\u7167\u7ed1\u5b9a\u548c\u8d5b\u679c\u6e90\u547d\u4e2d\u7387\u3002",
                "tone": "warning",
            }
        )

    elapsed_runs = [item for item in success_runs if _safe_float(item.get("elapsed_seconds"), default=-1.0) >= 0]
    if len(elapsed_runs) >= 4:
        latest = elapsed_runs[-1]
        previous = elapsed_runs[-4:-1]
        baseline = sum(_safe_float(item.get("elapsed_seconds"), 0.0) for item in previous) / len(previous)
        latest_elapsed = _safe_float(latest.get("elapsed_seconds"), 0.0)
        if baseline > 0 and latest_elapsed >= max(float(min_elapsed_seconds), baseline * float(elapsed_multiplier)):
            alerts.append(
                {
                    "severity": "medium",
                    "title": "\u56de\u6536\u8017\u65f6\u5f02\u5e38\u5347\u9ad8",
                    "body": f"\u6700\u8fd1\u8017\u65f6 {_elapsed_text(latest_elapsed)}\uff0c\u524d 3 \u6b21\u5e73\u5747 {_elapsed_text(baseline)}\u3002\u5efa\u8bae\u68c0\u67e5\u8d5b\u679c\u6e90\u54cd\u5e94\u548c\u672c\u5730\u72b6\u6001\u6587\u4ef6\u3002",
                    "tone": "warning",
                }
            )

    if not alerts and str(rows[-1].get("status") or "").lower() == "running":
        alerts.append(
            {
                "severity": "info",
                "title": "\u56de\u6536\u4efb\u52a1\u6b63\u5728\u8fd0\u884c",
                "body": f"\u5f00\u59cb\u65f6\u95f4: {rows[-1].get('started_at') or '-'}",
                "tone": "info",
            }
        )
    return alerts


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
        f"\u5feb\u7167\u53ef\u56de\u6536\u6027:\n"
        f"- \u53ef\u81ea\u52a8\u56de\u67e5: {_safe_int(item.get('snapshot_recoverable') or result.get('snapshot_recoverable'), 0)}\n"
        f"- \u7f3a source_id: {_safe_int(item.get('snapshot_missing_source_id') or result.get('snapshot_missing_source_id'), 0)}\n"
        f"- \u975e Titan \u5feb\u7167: {_safe_int(item.get('snapshot_non_titan_source') or result.get('snapshot_non_titan_source'), 0)}\n"
        f"- \u8d85\u51fa\u56de\u770b\u7a97\u53e3: {_safe_int(item.get('snapshot_out_of_window') or result.get('snapshot_out_of_window'), 0)}\n\n"
        f"\u9519\u8bef:\n- {item.get('error') or '-'}\n\n"
        f"\u6d88\u606f:\n{message_text}"
    )
