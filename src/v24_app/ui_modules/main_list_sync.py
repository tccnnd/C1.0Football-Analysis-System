from __future__ import annotations

from typing import Any, Mapping


C1_TREE_TAG_STYLES: Mapping[str, str] = {
    "c1_pass": "#e8f7ee",
    "c1_pending": "#fff7db",
    "c1_observe": "#eef4ff",
    "c1_block": "#fdecec",
}


def configure_c1_tree_tags(tree: Any) -> None:
    for tag, color in C1_TREE_TAG_STYLES.items():
        tree.tag_configure(tag, background=color)


def build_c1_apply_status_text(*, applied: int, buckets: Mapping[str, int]) -> str:
    return (
        f"C1 标记已应用 | 共 {applied} 场 | 放行 {int(buckets.get('可放行', 0))} | "
        f"待处理 {int(buckets.get('待处理', 0))} | 观察 {int(buckets.get('观察', 0))} | 阻断 {int(buckets.get('阻断', 0))}"
    )


def build_c1_apply_dialog_text(*, applied: int, buckets: Mapping[str, int]) -> str:
    return (
        f"已应用 {applied} 场\n"
        f"可放行: {int(buckets.get('可放行', 0))}\n"
        f"待处理: {int(buckets.get('待处理', 0))}\n"
        f"观察: {int(buckets.get('观察', 0))}\n"
        f"阻断: {int(buckets.get('阻断', 0))}"
    )


def replace_tree_action_value(current_values: object, action_text: str, *, action_col_index: int = 6) -> tuple | None:
    if not isinstance(current_values, (list, tuple)):
        return None
    mutable = list(current_values)
    if len(mutable) <= action_col_index:
        return None
    mutable[action_col_index] = action_text
    return tuple(mutable)
