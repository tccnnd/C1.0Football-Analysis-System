from __future__ import annotations

from typing import Any, Callable, Mapping

from .main_list_sync import replace_tree_action_value


def sync_tree_c1_action_column(
    *,
    tree: Any,
    matches: list[Any],
    action_text_by_match_id: Callable[[str], str],
    action_col_index: int = 6,
) -> int:
    updated_count = 0
    for match in matches:
        match_id = str(getattr(match, "match_id", ""))
        if not match_id or not tree.exists(match_id):
            continue
        updated_values = replace_tree_action_value(
            tree.item(match_id, "values"),
            action_text_by_match_id(match_id),
            action_col_index=action_col_index,
        )
        if updated_values is None:
            continue
        tree.item(match_id, values=updated_values)
        updated_count += 1
    return updated_count


def resolve_selected_prediction_for_details(
    *,
    selected_match: Any | None,
    predictions: Mapping[str, object],
) -> tuple[Any, dict] | None:
    if selected_match is None:
        return None
    match_id = str(getattr(selected_match, "match_id", ""))
    if not match_id:
        return None
    prediction = predictions.get(match_id)
    if not isinstance(prediction, dict):
        return None
    return selected_match, prediction
