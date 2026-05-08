from __future__ import annotations

from typing import Any, Callable, Mapping

from c1.runtime import is_release_gate_active

from .c1_release import classify_suggested_action_for_tree
from .main_list_sync import configure_c1_tree_tags, replace_tree_action_value


def should_show_match_for_filter(*, selected_filter: str, action: str, release_allowed: bool) -> bool:
    if selected_filter == "正式建议":
        return bool(release_allowed)
    if selected_filter == "待处理":
        return action in {"补阵容", "接近阻断", "阻断"}
    if selected_filter != "全部":
        return action == selected_filter
    return True


def build_main_list_sort_key(
    *,
    selected_filter: str,
    action: str,
    release_confidence: float,
    match: Any,
    action_priority_fn: Callable[[str], int],
) -> tuple:
    return (
        0 if selected_filter == "正式建议" else action_priority_fn(action),
        -float(release_confidence),
        getattr(match, "match_date", ""),
        getattr(match, "match_time", ""),
        getattr(match, "league", ""),
        getattr(match, "home_team", ""),
        getattr(match, "away_team", ""),
    )


def compute_c1_action_counts(
    *,
    matches: list[Any],
    action_text_by_match_id: Callable[[str], str],
    release_allowed_ids: set[str],
) -> tuple[dict[str, int], int, int, int]:
    counts = {
        "正式建议": 0,
        "补阵容": 0,
        "观察": 0,
        "可放行": 0,
        "接近阻断": 0,
        "阻断": 0,
    }
    total = len(matches)
    for match in matches:
        match_id = str(getattr(match, "match_id", ""))
        action = action_text_by_match_id(match_id)
        if match_id in release_allowed_ids:
            counts["正式建议"] += 1
        if action in counts:
            counts[action] += 1
    pending_count = counts["补阵容"] + counts["接近阻断"] + counts["阻断"]
    formal_count = counts["正式建议"]
    return counts, pending_count, formal_count, total


def build_c1_mode_status_text(
    *,
    runtime_mode: str,
    active_allowed_count: int,
    release_allowed_count: int,
) -> str:
    if is_release_gate_active(runtime_mode):
        return f"C1模式: {runtime_mode} | 生效放行 {int(active_allowed_count)} 场"
    return f"C1模式: {runtime_mode} | 仅影子评估 {int(release_allowed_count)} 场"


def restore_c1_marks_for_matches(
    *,
    tree: Any,
    matches: list[Any],
    c1_comparison_marks: Mapping[str, object],
    action_text_by_match_id: Callable[[str], str],
    action_col_index: int = 6,
) -> int:
    configure_c1_tree_tags(tree)
    restored = 0
    for match in matches:
        match_id = str(getattr(match, "match_id", ""))
        if not match_id or not tree.exists(match_id):
            continue
        item = c1_comparison_marks.get(match_id)
        if not isinstance(item, Mapping):
            continue
        tag, _bucket = classify_suggested_action_for_tree(str(item.get("suggested_action", "")))
        tree.item(match_id, tags=(tag,))
        updated_values = replace_tree_action_value(
            tree.item(match_id, "values"),
            action_text_by_match_id(match_id),
            action_col_index=action_col_index,
        )
        if updated_values is not None:
            tree.item(match_id, values=updated_values)
        restored += 1
    return restored
