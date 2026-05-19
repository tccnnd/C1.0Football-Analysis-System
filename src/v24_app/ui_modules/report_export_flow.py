from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


REPORT_TYPE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("ai_match_report_", "\u5355\u573a\u5206\u6790"),
    ("strategy_release_recovery_loop_", "\u653e\u884c\u95ed\u73af"),
    ("daily_parlay_repair_loop_", "二串一修复闭环"),
    ("strategy_allowlist_", "\u653e\u884c\u6e05\u5355"),
    ("strategy_policy_audit_", "\u8c03\u53c2\u5ba1\u8ba1"),
    ("statsbomb_event_sandbox_", "StatsBomb\u590d\u76d8"),
    ("statsbomb_fewshot_backfill_", "StatsBomb\u8865\u6837"),
    ("statsbomb_fewshot_draft_review_", "StatsBomb\u8349\u7a3f"),
    ("statsbomb_fewshot_merge_plan_", "StatsBomb\u5408\u5e76"),
    ("statsbomb_fewshot_merge_bundle_review_", "StatsBomb\u5408\u5e76"),
    ("statsbomb_fewshot_merge_apply_preview_", "StatsBomb\u5e94\u7528"),
    ("statsbomb_fewshot_merge_applied_", "StatsBomb\u5e94\u7528"),
    ("statsbomb_fewshot_memory_rollback_", "StatsBomb\u56de\u6eda"),
    ("statsbomb_fewshot_memory_audit_", "StatsBomb\u5ba1\u8ba1"),
    ("video_review_fewshot_draft_review_", "AI\u89c6\u9891\u8349\u7a3f"),
    ("video_review_fewshot_merge_plan_", "AI\u89c6\u9891\u5408\u5e76"),
    ("video_review_fewshot_merge_bundle_review_", "AI\u89c6\u9891\u5408\u5e76"),
    ("video_review_fewshot_merge_apply_preview_", "AI\u89c6\u9891\u5e94\u7528"),
    ("video_review_fewshot_merge_applied_", "AI\u89c6\u9891\u5e94\u7528"),
    ("video_review_fewshot_memory_rollback_", "AI\u89c6\u9891\u56de\u6eda"),
    ("video_review_fewshot_memory_audit_", "AI\u89c6\u9891\u5ba1\u8ba1"),
)


def should_run_pre_export_analysis(predictions: Mapping[str, object] | None) -> bool:
    return not bool(predictions)


def collect_visible_match_ids(tree: Any | None) -> set[str]:
    if tree is None:
        return set()
    get_children = getattr(tree, "get_children", None)
    if not callable(get_children):
        return set()
    return {str(item) for item in get_children("")}


def select_matches_for_export(matches: list[Any], visible_ids: set[str]) -> list[Any]:
    if visible_ids:
        return [match for match in matches if str(getattr(match, "match_id", "")) in visible_ids]
    return list(matches)


def ensure_report_dir(project_root: Path) -> Path:
    report_dir = project_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def build_report_filename(scope_slug: str, generated_at: datetime | None = None) -> str:
    now = generated_at or datetime.now()
    return f"recommendation_report_c1_{scope_slug}_{now.strftime('%Y%m%d_%H%M%S')}.md"


def resolve_current_filter(filter_var: Any | None, default: str = "\u5168\u90e8") -> str:
    if filter_var is None:
        return default
    getter = getattr(filter_var, "get", None)
    if not callable(getter):
        return default
    value = getter()
    text = str(value).strip()
    return text or default


def build_export_status_text(report_name: str) -> str:
    return f"\u62a5\u544a\u5df2\u5bfc\u51fa | {report_name}"


def classify_dashboard_report_file(path: Path) -> str:
    name = path.name
    for prefix, label in REPORT_TYPE_PREFIXES:
        if name.startswith(prefix):
            return label
    return "\u5176\u4ed6\u62a5\u544a"


def list_dashboard_report_files(
    report_dir: Path,
    *,
    limit: int = 100,
    include_csv: bool = False,
) -> list[dict[str, object]]:
    if not report_dir.exists():
        return []
    files = [path for path in report_dir.glob("*.md") if path.is_file()]
    if include_csv:
        files.extend(path for path in report_dir.glob("*.csv") if path.is_file())
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    rows: list[dict[str, object]] = []
    for path in files[: max(0, int(limit))]:
        stat = path.stat()
        rows.append(
            {
                "path": path,
                "name": path.name,
                "label": classify_dashboard_report_file(path),
                "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "mtime": stat.st_mtime,
                "size_bytes": stat.st_size,
            }
        )
    return rows


def summarize_dashboard_report_types(rows: list[Mapping[str, object]] | object) -> dict[str, int]:
    if not isinstance(rows, list):
        return {}
    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("label") or "\u5176\u4ed6\u62a5\u544a").strip() or "\u5176\u4ed6\u62a5\u544a"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def dashboard_report_type_options(rows: list[Mapping[str, object]] | object) -> list[str]:
    return ["\u5168\u90e8", *summarize_dashboard_report_types(rows).keys()]


def _size_text(value: object) -> str:
    try:
        size = int(value or 0)
    except (TypeError, ValueError):
        return "-"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _csv_rows(content: str) -> list[dict[str, str]]:
    try:
        reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
        return [dict(row) for row in reader]
    except csv.Error:
        return []


def _safe_int(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _daily_parlay_repair_loop_csv_metrics(row: Mapping[str, object]) -> dict[str, object] | None:
    path = row.get("path")
    if not isinstance(path, Path) or path.suffix.lower() != ".csv" or not path.name.startswith("daily_parlay_repair_loop_"):
        return None
    try:
        content = path.read_text(encoding="utf-8-sig")
    except Exception:
        return None
    records = _csv_rows(content)
    if not records:
        return None
    audit_rows = [item for item in records if item.get("record_type") == "audit"]
    queue_rows = [item for item in records if item.get("record_type") == "queue"]
    queue_blocked = sum(1 for item in queue_rows if str(item.get("status") or "").strip().lower() == "blocked")
    source_issue_count = sum(1 for item in queue_rows if "source" in str(item.get("code") or "").lower())
    mixed_source_count = sum(1 for item in queue_rows if "mixed" in str(item.get("code") or "").lower())
    recovery_error_count = sum(1 for item in audit_rows if str(item.get("status") or "").strip().lower() == "error")
    recovery_new_settled = sum(_safe_int(item.get("recovery_new_settled")) for item in audit_rows)
    recovery_rechecked_count = sum(1 for item in audit_rows if str(item.get("status") or "").strip().lower() == "rechecked")
    recovery_no_change_count = sum(1 for item in audit_rows if str(item.get("status") or "").strip().lower() == "no_change")
    ticket_ids = {str(item.get("ticket_id") or "").strip() for item in records if str(item.get("ticket_id") or "").strip()}
    return {
        "name": row.get("name") or path.name,
        "updated_at": row.get("updated_at") or "-",
        "mtime": float(row.get("mtime") or 0.0),
        "audit_count": len(audit_rows),
        "queue_count": len(queue_rows),
        "queue_blocked": queue_blocked,
        "source_issue_count": source_issue_count,
        "mixed_source_count": mixed_source_count,
        "recovery_error_count": recovery_error_count,
        "recovery_new_settled": recovery_new_settled,
        "recovery_rechecked_count": recovery_rechecked_count,
        "recovery_no_change_count": recovery_no_change_count,
        "ticket_count": len(ticket_ids),
    }


def build_daily_parlay_repair_loop_trend_routes(trend: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(trend, list):
        metrics = [item for item in trend if isinstance(item, Mapping)]
    else:
        resolved = trend if isinstance(trend, Mapping) else {}
        metrics = [item for item in resolved.get("metrics", []) if isinstance(item, Mapping)] if isinstance(resolved.get("metrics"), list) else []
    latest = metrics[0] if metrics else {}
    latest_blocked = _safe_int(latest.get("queue_blocked"))
    latest_source = _safe_int(latest.get("source_issue_count"))
    latest_mixed = _safe_int(latest.get("mixed_source_count"))
    latest_error = _safe_int(latest.get("recovery_error_count"))
    latest_recovery = _safe_int(latest.get("recovery_new_settled"))

    if latest_error <= 0 and latest_blocked > 0 and latest_source <= 0 and latest_mixed <= 0 and latest_recovery <= 0:
        latest_error = latest_blocked

    route_rows = [
        {
            "key": "source_backfill",
            "label": "来源回填",
            "count": latest_source,
            "detail": "补 source / source_id 后再回收",
            "tone": "danger" if latest_source >= max(latest_mixed, latest_error) and latest_source > 0 else "neutral",
            "action": "打开修复队列，优先回填缺失来源。",
            "target": "repair_queue",
        },
        {
            "key": "mixed_source_split",
            "label": "混源拆票",
            "count": latest_mixed,
            "detail": "优先标记拆票或重建票据",
            "tone": "danger" if latest_mixed > latest_source and latest_mixed >= latest_error and latest_mixed > 0 else "neutral",
            "action": "打开修复队列，优先处理混源票据。",
            "target": "repair_queue",
        },
        {
            "key": "recovery_failure",
            "label": "复跑失败",
            "count": latest_error,
            "detail": "优先检查复跑链路和回收中心",
            "tone": "danger" if latest_error > 0 else "neutral",
            "action": "打开回收中心，优先复查复跑链路。",
            "target": "recovery_center",
        },
    ]
    route_rows.sort(key=lambda item: (-_safe_int(item.get("count")), {"source_backfill": 0, "mixed_source_split": 1, "recovery_failure": 2}.get(str(item.get("key") or ""), 9)))
    primary = route_rows[0] if route_rows and _safe_int(route_rows[0].get("count")) > 0 else {}
    route_summary = " | ".join(f"{item.get('label') or '-'} {_safe_int(item.get('count'))}" for item in route_rows)
    return {
        "primary_route": str(primary.get("key") or "watch"),
        "primary_label": str(primary.get("label") or "观察"),
        "route_rows": route_rows,
        "route_summary": route_summary,
    }


def build_daily_parlay_repair_loop_trend(
    rows: list[Mapping[str, object]] | object,
    *,
    limit: int = 8,
) -> dict[str, object]:
    if not isinstance(rows, list):
        return {
            "status": "empty",
            "summary": "暂无二串一修复闭环趋势数据。",
            "metrics": [],
            "recommendation": "先导出至少 2 份二串一修复闭环 CSV 报告。",
        }
    metrics = [
        item
        for item in (_daily_parlay_repair_loop_csv_metrics(row) for row in rows if isinstance(row, Mapping))
        if isinstance(item, dict)
    ]
    metrics.sort(key=lambda item: float(item.get("mtime") or 0.0), reverse=True)
    metrics = metrics[: max(1, int(limit))]
    if not metrics:
        return {
            "status": "empty",
            "summary": "暂无二串一修复闭环趋势数据。",
            "metrics": [],
            "recommendation": "先导出至少 1 份带 CSV 的二串一修复闭环报告。",
        }
    latest = metrics[0]
    previous = metrics[1] if len(metrics) > 1 else None
    latest_blocked = _safe_int(latest.get("queue_blocked"))
    latest_source = _safe_int(latest.get("source_issue_count"))
    latest_recovery = _safe_int(latest.get("recovery_new_settled"))
    routes = build_daily_parlay_repair_loop_trend_routes(metrics)
    if latest_blocked == 0 and latest_source == 0:
        status = "healthy"
        recommendation = "当前修复闭环没有阻塞票据，继续保持导出和回收节奏。"
    elif previous is None:
        status = "watch"
        recommendation = "样本不足，至少保留 2 份历史 CSV 后再判断趋势。"
    else:
        previous_blocked = _safe_int(previous.get("queue_blocked"))
        previous_source = _safe_int(previous.get("source_issue_count"))
        if latest_blocked < previous_blocked and latest_source <= previous_source:
            status = "improving"
            recommendation = "待修复票据正在减少，继续优先处理来源缺口和复跑结算。"
        elif latest_blocked > previous_blocked or latest_source > previous_source:
            status = "regressing"
            recommendation = "修复问题在反复出现，优先排查来源回填和混源票据生成链路。"
        else:
            status = "watch"
            recommendation = "趋势暂未明显改善，继续观察下一轮导出后的阻塞变化。"
    summary = (
        f"最近 {len(metrics)} 份 | 最新待修复 {latest_blocked} | 来源缺口 {latest_source} | "
        f"复跑新结算 {latest_recovery} | 状态 {status}"
    )
    return {
        "status": status,
        "summary": summary,
        "metrics": metrics,
        "recommendation": recommendation,
        "routes": routes,
    }


def build_daily_parlay_repair_loop_trend_text(trend: Mapping[str, object] | object) -> str:
    resolved = trend if isinstance(trend, Mapping) else {}
    metrics = [item for item in resolved.get("metrics", []) if isinstance(item, Mapping)] if isinstance(resolved.get("metrics"), list) else []
    routes = resolved.get("routes") if isinstance(resolved.get("routes"), Mapping) else {}
    route_summary = str(routes.get("route_summary") or "").strip() if isinstance(routes, Mapping) else ""
    lines = [
        "二串一修复闭环健康趋势",
        f"- 摘要: {resolved.get('summary') or '-'}",
        f"- 建议: {resolved.get('recommendation') or '-'}",
    ]
    if route_summary:
        lines.append(f"- 分流: {route_summary}")
    if metrics:
        lines.append("- 最近记录:")
        for item in metrics[:5]:
            lines.append(
                "  "
                + f"{item.get('updated_at') or '-'} | 待修复 {_safe_int(item.get('queue_blocked'))} | "
                + f"来源 {_safe_int(item.get('source_issue_count'))} | 混源 {_safe_int(item.get('mixed_source_count'))} | "
                + f"复跑 {_safe_int(item.get('recovery_new_settled'))}"
            )
    else:
        lines.append("- 最近记录: 暂无")
    return "\n".join(lines)


def build_daily_parlay_repair_loop_trend_alert(trend: Mapping[str, object] | object) -> dict[str, object]:
    resolved = trend if isinstance(trend, Mapping) else {}
    status = str(resolved.get("status") or "empty").strip().lower()
    metrics = [item for item in resolved.get("metrics", []) if isinstance(item, Mapping)] if isinstance(resolved.get("metrics"), list) else []
    latest = metrics[0] if metrics else {}
    routes = resolved.get("routes") if isinstance(resolved.get("routes"), Mapping) else {}
    if not routes:
        routes = build_daily_parlay_repair_loop_trend_routes(resolved)
    route_rows = [item for item in routes.get("route_rows", []) if isinstance(item, Mapping)] if isinstance(routes, Mapping) else []
    visible = status == "regressing"
    return {
        "visible": visible,
        "status": status,
        "tone": "danger" if visible else "neutral",
        "title": "二串一修复趋势异常" if visible else "二串一修复趋势正常",
        "message": (
            f"最新待修复 {_safe_int(latest.get('queue_blocked'))} | "
            f"来源缺口 {_safe_int(latest.get('source_issue_count'))} | "
            f"混源 {_safe_int(latest.get('mixed_source_count'))} | "
            f"复跑新结算 {_safe_int(latest.get('recovery_new_settled'))}"
            if latest
            else "暂无可用趋势指标。"
        ),
        "recommendation": resolved.get("recommendation") or "继续观察下一轮闭环导出结果。",
        "summary": resolved.get("summary") or "-",
        "primary_route": str(routes.get("primary_route") or "watch") if isinstance(routes, Mapping) else "watch",
        "primary_label": str(routes.get("primary_label") or "观察") if isinstance(routes, Mapping) else "观察",
        "route_summary": str(routes.get("route_summary") or "") if isinstance(routes, Mapping) else "",
        "route_rows": route_rows,
    }


def _daily_parlay_repair_csv_summary(row: Mapping[str, object], content: str) -> list[str]:
    records = _csv_rows(content)
    audit_rows = [item for item in records if item.get("record_type") == "audit"]
    queue_rows = [item for item in records if item.get("record_type") == "queue"]
    ticket_ids = {str(item.get("ticket_id") or "").strip() for item in records if str(item.get("ticket_id") or "").strip()}
    queue_blocked = sum(1 for item in queue_rows if str(item.get("status") or "").strip().lower() == "blocked")
    recovery_new_settled = sum(_safe_int(item.get("recovery_new_settled")) for item in audit_rows)
    latest_queue_blocked_after = max([_safe_int(item.get("queue_blocked_after_repair")) for item in audit_rows] or [0])
    actions = sorted({str(item.get("action") or "").strip() for item in audit_rows if str(item.get("action") or "").strip()})
    action_text = " / ".join(actions[:3]) if actions else "-"
    if len(actions) > 3:
        action_text += f" / +{len(actions) - 3}"
    focus = "优先处理 queue 记录中的 blocked 票据" if queue_blocked else "优先复核最近 audit 记录和复跑结果"
    return [
        "报告摘要",
        f"- 文件: {row.get('name') or '-'}",
        f"- 类型: {row.get('label') or '-'} / CSV",
        f"- 审计记录: {len(audit_rows)} | 队列记录: {len(queue_rows)} | 涉及票据: {len(ticket_ids)}",
        f"- 当前待修复: {queue_blocked} | 最新复跑后待人工: {latest_queue_blocked_after}",
        f"- 累计复跑新结算: {recovery_new_settled} | 动作: {action_text}",
        f"- 建议: {focus}",
    ]


def _daily_parlay_repair_md_summary(row: Mapping[str, object], content: str) -> list[str]:
    extracted: dict[str, str] = {}
    for line in content.splitlines():
        text = line.strip()
        if not text.startswith("- ") or ":" not in text:
            continue
        label, value = text[2:].split(":", 1)
        extracted[label.strip()] = value.strip()
    queue_text = extracted.get("修复队列") or "-"
    audit_text = extracted.get("审计摘要") or "-"
    source_text = extracted.get("来源缺口票据") or "-"
    mixed_text = extracted.get("混源票据") or "-"
    latest_text = extracted.get("最新待人工") or "-"
    recovery_text = extracted.get("累计复跑新结算") or "-"
    return [
        "报告摘要",
        f"- 文件: {row.get('name') or '-'}",
        f"- 类型: {row.get('label') or '-'} / Markdown",
        f"- 修复队列: {queue_text}",
        f"- 审计摘要: {audit_text}",
        f"- 缺口/混源: {source_text} / {mixed_text}",
        f"- 待人工/复跑: {latest_text} / {recovery_text}",
    ]


def build_dashboard_report_preview_summary(row: Mapping[str, object] | object, content: str) -> str:
    resolved = row if isinstance(row, Mapping) else {}
    name = str(resolved.get("name") or "")
    suffix = Path(name).suffix.lower()
    line_count = len(content.splitlines())
    if name.startswith("daily_parlay_repair_loop_"):
        lines = (
            _daily_parlay_repair_csv_summary(resolved, content)
            if suffix == ".csv"
            else _daily_parlay_repair_md_summary(resolved, content)
        )
    else:
        lines = [
            "报告摘要",
            f"- 文件: {resolved.get('name') or '-'}",
            f"- 类型: {resolved.get('label') or '-'} / {suffix.lstrip('.').upper() or '-'}",
            f"- 更新时间: {resolved.get('updated_at') or '-'}",
            f"- 大小: {_size_text(resolved.get('size_bytes'))} | 行数: {line_count}",
            "- 建议: 查看下方原文确认细节。",
        ]
    return "\n".join(lines)


def filter_dashboard_report_rows(
    rows: list[Mapping[str, object]] | object,
    *,
    selected_type: object = "\u5168\u90e8",
    query: object = "",
) -> list[dict[str, object]]:
    if not isinstance(rows, list):
        return []
    type_text = str(selected_type or "\u5168\u90e8").strip() or "\u5168\u90e8"
    query_text = str(query or "").strip().lower()
    filtered: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("label") or "")
        name = str(row.get("name") or "")
        path = str(row.get("path") or "")
        if type_text != "\u5168\u90e8" and label != type_text:
            continue
        if query_text and query_text not in name.lower() and query_text not in label.lower() and query_text not in path.lower():
            continue
        filtered.append(dict(row))
    return filtered


def build_export_message_text(*, scope_label: str, match_count: int, report_path: Path) -> str:
    return f"\u62a5\u544a\u5df2\u751f\u6210\n\u8303\u56f4: {scope_label}\n\u573a\u6b21: {match_count}\n{report_path}"
