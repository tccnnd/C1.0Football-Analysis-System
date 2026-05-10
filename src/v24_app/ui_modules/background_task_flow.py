from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
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

FAILURE_REASON_LABELS = {
    "data_source_error": "数据源异常",
    "model_error": "模型异常",
    "timeout": "执行超时",
    "process_error": "进程异常",
    "cancelled": "任务取消",
    "unknown": "未知异常",
}


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_dt(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text or text == "-":
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def classify_background_task_failure(task: Mapping[str, object] | object) -> str:
    item = _as_mapping(task)
    status = str(item.get("status") or "")
    if status == "cancelled":
        return "cancelled"
    metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
    text = " ".join(
        [
            str(item.get("error") or ""),
            str(item.get("label") or ""),
            str(item.get("key") or ""),
            str(metadata.get("traceback") or "") if isinstance(metadata, Mapping) else "",
        ]
    ).lower()
    if any(token in text for token in ("timeout", "timed out", "超时")):
        return "timeout"
    if any(token in text for token in ("process", "brokenprocesspool", "进程", "pickle", "subprocess")):
        return "process_error"
    if any(token in text for token in ("model", "xgb", "训练", "推理", "predict", "calibration")):
        return "model_error"
    if any(token in text for token in ("source", "api", "http", "network", "fetch", "数据源", "接口", "连接")):
        return "data_source_error"
    return "unknown"


def build_background_task_stability_summary(
    tasks: Sequence[Mapping[str, object]] | object,
    *,
    now: datetime | None = None,
    window_hours: int = 24,
) -> dict[str, object]:
    items = [item for item in tasks if isinstance(item, Mapping)] if isinstance(tasks, Sequence) else []
    reference_time = now or datetime.now()
    cutoff = reference_time - timedelta(hours=max(1, int(window_hours)))
    recent: list[Mapping[str, object]] = []
    for item in items:
        stamp = _parse_dt(item.get("finished_at")) or _parse_dt(item.get("started_at")) or _parse_dt(item.get("queued_at"))
        if stamp is None or stamp >= cutoff:
            recent.append(item)
    success = sum(1 for item in recent if str(item.get("status") or "") == "success")
    failed_items = [item for item in recent if str(item.get("status") or "") == "failed"]
    cancelled = sum(1 for item in recent if str(item.get("status") or "") == "cancelled")
    active = sum(1 for item in recent if str(item.get("status") or "") in {"queued", "running"})
    completed = success + len(failed_items)
    failure_rate = (len(failed_items) / completed) if completed else 0.0
    elapsed_values = [
        _safe_float(item.get("elapsed_seconds"))
        for item in recent
        if item.get("elapsed_seconds") is not None and _safe_float(item.get("elapsed_seconds")) >= 0
    ]
    avg_elapsed = sum(elapsed_values) / len(elapsed_values) if elapsed_values else 0.0
    slowest = max(
        (item for item in recent if item.get("elapsed_seconds") is not None),
        key=lambda item: _safe_float(item.get("elapsed_seconds")),
        default=None,
    )
    reason_counts = Counter(classify_background_task_failure(item) for item in failed_items)
    group_failures = Counter(str(item.get("group") or "default") for item in failed_items)
    latest_failure = failed_items[0] if failed_items else None
    if failure_rate >= 0.25 or len(failed_items) >= 3:
        health = "abnormal"
        tone = "bad"
        recommendation = "优先查看失败分组和最近一次失败，必要时暂停低优先级模型任务。"
    elif len(failed_items) > 0 or active >= 4:
        health = "watch"
        tone = "warning"
        recommendation = "继续观察失败原因，若同类错误重复出现再增加重试或降级规则。"
    else:
        health = "normal"
        tone = "good"
        recommendation = "后台任务稳定，可继续推进批量回测和自动复盘。"
    return {
        "window_hours": max(1, int(window_hours)),
        "total": len(recent),
        "active": active,
        "success": success,
        "failed": len(failed_items),
        "cancelled": cancelled,
        "failure_rate": round(failure_rate, 4),
        "avg_elapsed_seconds": round(avg_elapsed, 2),
        "slowest_label": str(slowest.get("label") or "-") if isinstance(slowest, Mapping) else "-",
        "slowest_elapsed_seconds": round(_safe_float(slowest.get("elapsed_seconds")), 2) if isinstance(slowest, Mapping) else 0.0,
        "failure_reasons": dict(reason_counts),
        "top_failure_reason": reason_counts.most_common(1)[0][0] if reason_counts else "-",
        "top_failure_group": group_failures.most_common(1)[0][0] if group_failures else "-",
        "latest_failure_label": str(latest_failure.get("label") or "-") if isinstance(latest_failure, Mapping) else "-",
        "latest_failure_error": str(latest_failure.get("error") or "-") if isinstance(latest_failure, Mapping) else "-",
        "health": health,
        "tone": tone,
        "recommendation": recommendation,
    }


def build_background_task_stability_cards(summary: Mapping[str, object] | object) -> list[dict[str, object]]:
    item = _as_mapping(summary)
    health_labels = {"normal": "正常", "watch": "观察", "abnormal": "异常"}
    top_reason = str(item.get("top_failure_reason") or "-")
    top_group = str(item.get("top_failure_group") or "-")
    cards = [
        {
            "title": f"后台健康: {health_labels.get(str(item.get('health') or ''), item.get('health', '-'))}",
            "body": (
                f"窗口 {item.get('window_hours', 24)}h | 任务 {item.get('total', 0)} | "
                f"失败率 {_safe_float(item.get('failure_rate')) * 100:.1f}% | "
                f"平均耗时 {_safe_float(item.get('avg_elapsed_seconds')):.2f}s"
            ),
            "tone": str(item.get("tone") or "neutral"),
        },
        {
            "title": "失败归因",
            "body": (
                f"主要原因: {FAILURE_REASON_LABELS.get(top_reason, top_reason)}\n"
                f"失败最多分组: {GROUP_LABELS.get(top_group, top_group)} | "
                f"最近失败: {item.get('latest_failure_label', '-')}"
            ),
            "tone": "warning" if int(_safe_float(item.get("failed"), 0)) else "good",
        },
        {
            "title": "耗时与建议",
            "body": (
                f"最慢任务: {item.get('slowest_label', '-')} / {_safe_float(item.get('slowest_elapsed_seconds')):.2f}s\n"
                f"{item.get('recommendation', '-')}"
            ),
            "tone": str(item.get("tone") or "neutral"),
        },
    ]
    return cards


def build_background_task_rows(tasks: Sequence[Mapping[str, object]] | object, *, limit: int = 8) -> list[dict[str, object]]:
    items = [item for item in tasks if isinstance(item, Mapping)] if isinstance(tasks, Sequence) else []
    rows: list[dict[str, object]] = []
    for item in items[: max(0, int(limit))]:
        status = str(item.get("status") or "queued")
        mode = str(item.get("mode") or "thread")
        group = str(item.get("group") or "default")
        priority = item.get("priority", 100)
        metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
        retry_count = int(_safe_float(metadata.get("retry_count") if isinstance(metadata, Mapping) else 0))
        max_retries = int(_safe_float(metadata.get("max_retries") if isinstance(metadata, Mapping) else 0))
        retry_text = f" | 重试 {retry_count}/{max_retries}" if max_retries else ""
        elapsed = item.get("elapsed_seconds")
        elapsed_text = f"{_safe_float(elapsed):.2f}s" if elapsed is not None else "-"
        detail = str(item.get("error") or item.get("result_summary") or "-")
        rows.append(
            {
                "title": f"{STATUS_LABELS.get(status, status)} | {item.get('label', '-')}",
                "body": (
                    f"ID {item.get('task_id', '-')} | {MODE_LABELS.get(mode, mode)} | "
                    f"{GROUP_LABELS.get(group, group)} | P{priority} | "
                    f"开始 {item.get('started_at', '-') or '-'} | 耗时 {elapsed_text}{retry_text}\n{detail}"
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


def build_background_task_group_rows(queue_state: Mapping[str, object] | object, *, limit: int = 6) -> list[dict[str, object]]:
    state = _as_mapping(queue_state)
    groups = state.get("groups")
    items = [item for item in groups if isinstance(item, Mapping)] if isinstance(groups, Sequence) else []
    rows: list[dict[str, object]] = []
    for item in items[: max(0, int(limit))]:
        group = str(item.get("group") or "default")
        running = int(_safe_float(item.get("running"), 0))
        queued = int(_safe_float(item.get("queued"), 0))
        limit_value = int(_safe_float(item.get("limit"), 0))
        failed = int(_safe_float(item.get("failed"), 0))
        latest_status = str(item.get("latest_status") or "-")
        tone = "bad" if failed else "warning" if queued else "good" if running else "neutral"
        rows.append(
            {
                "title": f"{GROUP_LABELS.get(group, group)} | {running}/{limit_value} 运行 | {queued} 排队",
                "body": (
                    f"最新任务: {item.get('latest_label', '-')}\n"
                    f"状态: {STATUS_LABELS.get(latest_status, latest_status)} | "
                    f"完成 {int(_safe_float(item.get('success'), 0))} | "
                    f"失败 {failed} | 已取消 {int(_safe_float(item.get('cancelled'), 0))}"
                ),
                "tone": tone,
                "group": group,
            }
        )
    return rows


def build_background_task_detail_lines(task: Mapping[str, object] | object) -> list[str]:
    item = _as_mapping(task)
    metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
    status = str(item.get("status") or "queued")
    mode = str(item.get("mode") or "thread")
    group = str(item.get("group") or "default")
    priority = item.get("priority", 100)
    retry_count = int(_safe_float(metadata.get("retry_count") if isinstance(metadata, Mapping) else 0))
    max_retries = int(_safe_float(metadata.get("max_retries") if isinstance(metadata, Mapping) else 0))
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
        f"重试: {retry_count}/{max_retries}",
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
