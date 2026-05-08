from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping


def build_c1_rows_from_marks(
    *,
    matches: list[Any],
    marks: Mapping[str, dict] | None,
    predictions: Mapping[str, dict],
    action_priority_fn: Callable[[str], int],
) -> list[dict]:
    rows: list[dict] = []
    resolved_marks = marks if isinstance(marks, Mapping) else {}
    for match in matches:
        item = resolved_marks.get(match.match_id)
        if not isinstance(item, dict):
            continue
        prediction = predictions.get(match.match_id) or {}
        row = dict(item)
        row.setdefault("match_id", match.match_id)
        row.setdefault("match_label", f"{match.home_team} vs {match.away_team}")
        row.setdefault("v24_recommendation", prediction.get("recommendation", "-"))
        row.setdefault("v24_confidence", float(prediction.get("confidence", 0) or 0))
        row.setdefault("c1_predicted_side", "-")
        row.setdefault("c1_confidence", 0.0)
        row.setdefault("governance_action", "-")
        row.setdefault("suggested_action", "-")
        row.setdefault("primary_reason_code", "-")
        row.setdefault("governance_reason_codes", [])
        row.setdefault("side_diverged", False)
        row.setdefault("near_block", False)
        row.setdefault("confidence_gap", 0.0)
        rows.append(row)
    rows.sort(
        key=lambda item: (
            action_priority_fn(str(item.get("suggested_action", "-"))),
            str(item.get("match_label", "")),
        )
    )
    return rows


def summarize_c1_rows(rows: list[dict]) -> dict:
    governance_counts: dict[str, int] = {}
    reason_code_counts: dict[str, int] = {}
    side_divergence_count = 0
    blocked_count = 0
    near_block_count = 0
    for item in rows:
        governance = str(item.get("governance_action", "-"))
        governance_counts[governance] = governance_counts.get(governance, 0) + 1
        for code in item.get("governance_reason_codes", []) or []:
            code_text = str(code)
            reason_code_counts[code_text] = reason_code_counts.get(code_text, 0) + 1
        if item.get("side_diverged"):
            side_divergence_count += 1
        if governance == "BLOCK" or str(item.get("suggested_action", "")) == "阻断":
            blocked_count += 1
        if item.get("near_block"):
            near_block_count += 1
    return {
        "governance_counts": governance_counts,
        "reason_code_counts": reason_code_counts,
        "side_divergence_count": side_divergence_count,
        "blocked_count": blocked_count,
        "near_block_count": near_block_count,
    }


def find_release_row(rows: list[dict] | object, match_id: str) -> dict:
    if not isinstance(rows, list):
        return {}
    for item in rows:
        if isinstance(item, dict) and str(item.get("match_id", "")) == str(match_id):
            return item
    return {}


def collect_release_allowed_match_ids(rows: list[dict] | object) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {
        str(item.get("match_id", "")).strip()
        for item in rows
        if isinstance(item, dict) and item.get("release_allowed") and str(item.get("match_id", "")).strip()
    }


def resolve_release_gate_pick(*, gate_active: bool, prediction: dict, row: dict | None) -> str:
    recommendation = str(prediction.get("recommendation", "-"))
    if not gate_active:
        return recommendation
    if not isinstance(row, dict) or not row:
        return recommendation
    if row.get("release_allowed"):
        return recommendation
    if str(row.get("governance_action", "")).upper() == "BLOCK":
        return "阻断"
    reason = str(row.get("primary_reason_code") or "")
    if any(token in reason for token in ("LINEUP", "INFO_QUALITY")):
        return "待补阵容"
    return "观察"


def format_release_candidate_text(row: dict, prediction: dict | None = None) -> str:
    play = str(row.get("top_play") or "-")
    selection = str(row.get("top_selection") or "-")
    line = row.get("top_line")
    if play == "1x2":
        mapping = {
            "HOME_WIN": "主胜",
            "DRAW": "平局",
            "AWAY_WIN": "客胜",
        }
        return mapping.get(selection, selection)
    if play == "totals":
        base_line = line
        if base_line in (None, "") and isinstance(prediction, dict):
            base_line = prediction.get("total_goals_value")
        if base_line not in (None, ""):
            return f"{selection} {base_line}"
        return selection
    if play == "handicap":
        if line not in (None, ""):
            return f"{selection} {line}"
        return selection
    return selection


def build_formal_release_rows(*, rows: list[dict], predictions: Mapping[str, dict]) -> list[dict]:
    if not rows:
        return []
    formal_rows: list[dict] = []
    for item in rows:
        if not isinstance(item, dict) or not item.get("release_allowed"):
            continue
        match_id = str(item.get("match_id", "")).strip()
        prediction = predictions.get(match_id, {})
        formal_rows.append(
            {
                "match_id": match_id,
                "match_label": item.get("match_label", "-"),
                "official_pick": format_release_candidate_text(item, prediction if isinstance(prediction, dict) else None),
                "play": item.get("top_play") or "-",
                "selection": item.get("top_selection") or "-",
                "line": item.get("top_line"),
                "confidence": float(item.get("top_confidence", 0) or 0),
                "provider_name": item.get("provider_name", "-"),
                "primary_reason_code": item.get("primary_reason_code") or "-",
                "governance_action": item.get("governance_action", "-"),
                "release_action": item.get("release_action", "-"),
            }
        )
    formal_rows.sort(
        key=lambda item: (
            -float(item.get("confidence", 0) or 0),
            str(item.get("match_label", "")),
        )
    )
    return formal_rows


def build_release_allowlist_lines(
    *,
    allow_rows: list[dict],
    summary: Mapping[str, object] | object,
    generated_at: datetime | None = None,
) -> list[str]:
    now = generated_at or datetime.now()
    resolved_summary = summary if isinstance(summary, Mapping) else {}
    lines = [
        "# C1 Controlled Release Allowlist",
        "",
        f"- Generated At: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Allowed Count: {len(allow_rows)}",
        f"- Governance Counts: {resolved_summary.get('governance_counts', {})}",
        f"- Release Counts: {resolved_summary.get('release_counts', {})}",
        f"- Provider Counts: {resolved_summary.get('provider_counts', {})}",
        "",
        "| Match | Governance | Release | Play | Selection | Confidence | Provider | Reason |",
        "|---|---|---|---|---|---:|---|---|",
    ]
    for item in allow_rows:
        lines.append(
            f"| {item.get('match_label', '-')} | {item.get('governance_action', '-')} | {item.get('release_action', '-')} | "
            f"{item.get('top_play') or '-'} | {item.get('top_selection') or '-'} | "
            f"{float(item.get('top_confidence', 0) or 0):.2%} | {item.get('provider_name', '-')} | {item.get('primary_reason_code') or '-'} |"
        )
    return lines


def filter_release_rows(rows: list[dict], selected: str) -> list[dict]:
    if selected == "可放行":
        return [item for item in rows if item.get("release_allowed")]
    if selected == "保留":
        return [item for item in rows if not item.get("release_allowed")]
    return list(rows)


def release_window_row_values(item: Mapping[str, object]) -> tuple[object, ...]:
    return (
        item.get("match_label", "-"),
        item.get("governance_action", "-"),
        item.get("release_action", "-"),
        item.get("top_play") or "-",
        item.get("top_selection") or "-",
        f"{float(item.get('top_confidence', 0) or 0):.2%}",
        item.get("provider_name", "-"),
        item.get("primary_reason_code") or "-",
    )


def filter_comparison_rows(rows: list[dict], selected: str) -> list[dict]:
    if selected == "全部":
        return list(rows)
    if selected == "待处理":
        return [
            item
            for item in rows
            if item.get("suggested_action") in {"补阵容", "接近阻断", "阻断"}
        ]
    return [item for item in rows if str(item.get("suggested_action", "")) == selected]


def comparison_window_row_values(item: Mapping[str, object]) -> tuple[object, ...]:
    return (
        item.get("match_label", "-"),
        f"{item.get('v24_recommendation', '-')} ({float(item.get('v24_confidence', 0) or 0):.2%})",
        f"{item.get('c1_predicted_side', '-')} ({float(item.get('c1_confidence', 0) or 0):.2%})",
        item.get("governance_action", "-"),
        item.get("suggested_action", "-"),
        item.get("primary_reason_code") or "-",
        ", ".join(item.get("governance_reason_codes", []) or []) or "-",
        "Y" if item.get("side_diverged") else "N",
        "Y" if item.get("near_block") else "N",
        f"{float(item.get('confidence_gap', 0) or 0):+.3f}",
    )


def compute_pending_match_ids(rows: list[dict]) -> set[str]:
    pending_actions = {"补阵容", "接近阻断", "阻断"}
    return {
        str(item.get("match_id", "")).strip()
        for item in rows
        if str(item.get("suggested_action", "")).strip() in pending_actions
        and str(item.get("match_id", "")).strip()
    }


def classify_suggested_action_for_tree(suggested_action: str) -> tuple[str, str]:
    suggested = str(suggested_action or "").strip()
    if suggested == "可放行":
        return "c1_pass", "可放行"
    if suggested in {"补阵容", "接近阻断"}:
        return "c1_pending", "待处理"
    if suggested == "阻断":
        return "c1_block", "阻断"
    return "c1_observe", "观察"


def build_c1_mark_apply_plan(
    *,
    rows: list[dict],
    exists_fn: Callable[[str], bool],
) -> tuple[dict[str, dict], dict[str, str], dict[str, int], int]:
    marks_by_match_id: dict[str, dict] = {}
    tags_by_match_id: dict[str, str] = {}
    buckets = {"可放行": 0, "待处理": 0, "观察": 0, "阻断": 0}
    applied = 0
    for item in rows:
        match_id = str(item.get("match_id", "")).strip()
        if not match_id or not exists_fn(match_id):
            continue
        tag, bucket = classify_suggested_action_for_tree(str(item.get("suggested_action", "")))
        marks_by_match_id[match_id] = dict(item)
        tags_by_match_id[match_id] = tag
        buckets[bucket] += 1
        applied += 1
    return marks_by_match_id, tags_by_match_id, buckets, applied
