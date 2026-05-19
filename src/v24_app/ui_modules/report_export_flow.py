from __future__ import annotations

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
