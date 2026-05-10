from __future__ import annotations

from typing import Mapping, Sequence


STATUS_LABELS = {
    "queued": "排队中",
    "running": "运行中",
    "success": "完成",
    "failed": "失败",
    "cancelled": "已取消",
}

MODE_LABELS = {
    "thread": "线程",
    "process": "进程",
}


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_background_task_rows(tasks: Sequence[Mapping[str, object]] | object, *, limit: int = 8) -> list[dict[str, str]]:
    items = [item for item in tasks if isinstance(item, Mapping)] if isinstance(tasks, Sequence) else []
    rows: list[dict[str, str]] = []
    for item in items[: max(0, int(limit))]:
        status = str(item.get("status") or "queued")
        mode = str(item.get("mode") or "thread")
        elapsed = item.get("elapsed_seconds")
        elapsed_text = f"{_safe_float(elapsed):.2f}s" if elapsed is not None else "-"
        detail = str(item.get("error") or item.get("result_summary") or "-")
        rows.append(
            {
                "title": f"{STATUS_LABELS.get(status, status)} | {item.get('label', '-')}",
                "body": (
                    f"ID {item.get('task_id', '-')} | {MODE_LABELS.get(mode, mode)} | "
                    f"开始 {item.get('started_at', '-') or '-'} | 耗时 {elapsed_text}\n{detail}"
                ),
                "status": status,
                "mode": mode,
            }
        )
    return rows


def build_background_task_summary(tasks: Sequence[Mapping[str, object]] | object) -> dict[str, object]:
    items = [item for item in tasks if isinstance(item, Mapping)] if isinstance(tasks, Sequence) else []
    running = sum(1 for item in items if str(item.get("status") or "") in {"queued", "running"})
    success = sum(1 for item in items if str(item.get("status") or "") == "success")
    failed = sum(1 for item in items if str(item.get("status") or "") == "failed")
    process_running = sum(
        1
        for item in items
        if str(item.get("status") or "") in {"queued", "running"} and str(item.get("mode") or "") == "process"
    )
    return {
        "total": len(items),
        "running": running,
        "success": success,
        "failed": failed,
        "process_running": process_running,
        "summary_text": f"运行中 {running} | 已完成 {success} | 失败 {failed} | 进程 {process_running}",
    }
