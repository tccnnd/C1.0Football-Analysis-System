from __future__ import annotations

import json
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


def build_background_task_rows(tasks: Sequence[Mapping[str, object]] | object, *, limit: int = 8) -> list[dict[str, object]]:
    items = [item for item in tasks if isinstance(item, Mapping)] if isinstance(tasks, Sequence) else []
    rows: list[dict[str, object]] = []
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
                "task_id": str(item.get("task_id") or ""),
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


def build_background_task_detail_lines(task: Mapping[str, object] | object) -> list[str]:
    item = _as_mapping(task)
    metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
    status = str(item.get("status") or "queued")
    mode = str(item.get("mode") or "thread")
    elapsed = item.get("elapsed_seconds")
    elapsed_text = f"{_safe_float(elapsed):.2f}s" if elapsed is not None else "-"
    lines = [
        "后台任务详情",
        "",
        f"任务ID: {item.get('task_id', '-')}",
        f"任务键: {item.get('key', '-')}",
        f"任务名称: {item.get('label', '-')}",
        f"执行模式: {MODE_LABELS.get(mode, mode)}",
        f"状态: {STATUS_LABELS.get(status, status)}",
        f"开始时间: {item.get('started_at', '-') or '-'}",
        f"结束时间: {item.get('finished_at', '-') or '-'}",
        f"耗时: {elapsed_text}",
        "",
        "结果摘要",
        str(item.get("result_summary") or "-"),
        "",
        "错误信息",
        str(item.get("error") or "-"),
        "",
        "Metadata",
    ]
    if metadata:
        try:
            lines.append(json.dumps(dict(metadata), ensure_ascii=False, indent=2))
        except Exception:
            lines.append(str(metadata))
    else:
        lines.append("-")
    traceback_text = ""
    if isinstance(metadata, Mapping):
        traceback_text = str(metadata.get("traceback") or "")
    if traceback_text:
        lines.extend(["", "Traceback", traceback_text])
    return lines
