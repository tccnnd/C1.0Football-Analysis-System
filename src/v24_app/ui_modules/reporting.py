from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


def build_export_report_lines(
    *,
    matches: list[Any],
    all_match_count: int,
    predictions: dict[str, dict],
    c1_marks: dict[str, dict],
    release_gate_pick_fn: Callable[[str, dict], str],
    predict_match_fn: Callable[[Any], dict],
    current_filter: str,
    scope_label: str,
    generated_at: datetime | None = None,
) -> list[str]:
    now = generated_at or datetime.now()
    counts: dict[str, int] = {}
    for item in c1_marks.values():
        if not isinstance(item, dict):
            continue
        action = str(item.get("suggested_action", "-"))
        counts[action] = counts.get(action, 0) + 1

    lines = [
        "# V24 Recommendation Report With C1 Governance",
        "",
        f"- Generated At: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Match Count: {all_match_count}",
        f"- Export Scope: {scope_label}",
        f"- Current Filter: {current_filter}",
        f"- Visible Matches: {len(matches)}",
        f"- C1 Marks: {counts}",
        "",
        "| Date | Time | League | Match | 1X2 | Handicap | Total Goals | HT/FT | Score | Confidence | C1 Action | Governance | Primary Reason |",
        "|---|---|---|---|---|---|---|---|---|---:|---|---|---|",
    ]

    for match in matches:
        prediction = predictions.get(match.match_id) or predict_match_fn(match)
        handicap_pick = prediction.get("handicap_display") or prediction.get("handicap_recommendation") or "-"
        total_goals_pick = str(prediction.get("total_goals_recommendation") or prediction.get("ou_recommendation") or "-")
        score_pick = str(prediction.get("score_recommendation") or "-")
        htft_pick = str(prediction.get("htft_recommendation") or "-")
        gated_pick = release_gate_pick_fn(match.match_id, prediction)
        mark = c1_marks.get(match.match_id, {}) if isinstance(c1_marks, dict) else {}
        suggested_action = str(mark.get("suggested_action", "-")) if isinstance(mark, dict) else "-"
        governance_action = str(mark.get("governance_action", "-")) if isinstance(mark, dict) else "-"
        primary_reason = str(mark.get("primary_reason_code", "-")) if isinstance(mark, dict) else "-"
        lines.append(
            f"| {match.match_date} | {match.match_time} | {match.league} | "
            f"{match.home_team} vs {match.away_team} | {gated_pick} | "
            f"{handicap_pick} | {total_goals_pick} | {htft_pick} | {score_pick} | "
            f"{prediction['confidence']:.1%} | {suggested_action} | {governance_action} | {primary_reason} |"
        )
    return lines
