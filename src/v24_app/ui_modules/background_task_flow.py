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

GROUP_LABELS = {
    "default": "默认",
    "recovery": "赛果回收",
    "backtest": "历史回测",
    "model": "模型任务",
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
        group = str(item.get("group") or "default")
        priority = item.get("priority", 100)
        elapsed = item.get("elapsed_seconds")
        elapsed_text = f"{_safe_float(elapsed):.2f}s" if elapsed is not None else "-"
        detail = str(item.get("error") or item.get("result_summary") or "-")
        rows.append(
            {
                "title": f"{STATUS_LABELS.get(status, status)} | {item.get('label', '-')}",
                "body": (
                    f"ID {item.get('task_id', '-')} | {MODE_LABELS.get(mode, mode)} | "
                    f"{GROUP_LABELS.get(group, group)} | P{priority} | "
                    f"开始 {item.get('started_at', '-') or '-'} | 耗时 {elapsed_text}\n{detail}"
                ),
                "task_id": str(item.get("task_id") or ""),
                "status": status,
                "mode": mode,
                "can_cancel": status in {"queued", "running"},
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
    queued = sum(1 for item in items if str(item.get("status") or "") == "queued")
    return {
        "total": len(items),
        "running": running,
        "queued": queued,
        "success": success,
        "failed": failed,
        "process_running": process_running,
        "summary_text": f"活跃 {running} | 排队 {queued} | 已完成 {success} | 失败 {failed} | 进程 {process_running}",
    }


def build_background_task_detail_lines(task: Mapping[str, object] | object) -> list[str]:
    item = _as_mapping(task)
    metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
    status = str(item.get("status") or "queued")
    mode = str(item.get("mode") or "thread")
    group = str(item.get("group") or "default")
    priority = item.get("priority", 100)
    elapsed = item.get("elapsed_seconds")
    elapsed_text = f"{_safe_float(elapsed):.2f}s" if elapsed is not None else "-"
    lines = [
        "后台任务详情",
        "",
        f"任务ID: {item.get('task_id', '-')}",
        f"任务键: {item.get('key', '-')}",
        f"任务名称: {item.get('label', '-')}",
        f"执行模式: {MODE_LABELS.get(mode, mode)}",
        f"任务分组: {GROUP_LABELS.get(group, group)}",
        f"优先级: P{priority}",
        f"状态: {STATUS_LABELS.get(status, status)}",
        f"入队时间: {item.get('queued_at', '-') or '-'}",
        f"开始时间: {item.get('started_at', '-') or '-'}",
        f"结束时间: {item.get('finished_at', '-') or '-'}",
        f"耗时: {elapsed_text}",
    ]
    if isinstance(metadata, Mapping) and metadata.get("cancel_requested"):
        lines.extend(
            [
                "",
                "取消请求",
                f"已请求取消: {metadata.get('cancel_requested_at', '-')}",
                "说明: 任务已经开始运行时不会被强制终止，系统只记录取消请求并等待任务自然结束。",
            ]
        )
    lines.extend(
        [
            "",
            "结果摘要",
            str(item.get("result_summary") or "-"),
            "",
            "错误信息",
            str(item.get("error") or "-"),
            "",
            "Metadata",
        ]
    )
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
