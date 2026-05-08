from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


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


def resolve_current_filter(filter_var: Any | None, default: str = "全部") -> str:
    if filter_var is None:
        return default
    getter = getattr(filter_var, "get", None)
    if not callable(getter):
        return default
    value = getter()
    text = str(value).strip()
    return text or default


def build_export_status_text(report_name: str) -> str:
    return f"报告已导出 | {report_name}"


def build_export_message_text(*, scope_label: str, match_count: int, report_path: Path) -> str:
    return f"报告已生成\n范围: {scope_label}\n场次: {match_count}\n{report_path}"
