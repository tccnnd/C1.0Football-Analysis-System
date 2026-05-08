from __future__ import annotations

from typing import Any


def adapt_shadow_comparison_result(result: Any) -> dict:
    return {
        "total_matches": result.total_matches,
        "summary": dict(result.summary),
        "markdown_report": result.markdown_report,
        "json_report": result.json_report,
        "rows": [
            {
                "match_id": row.match_id,
                "match_label": row.match_label,
                "v24_recommendation": row.v24_recommendation,
                "v24_confidence": row.v24_confidence,
                "c1_predicted_side": row.c1_predicted_side,
                "c1_confidence": row.c1_confidence,
                "governance_action": row.governance_action,
                "suggested_action": row.suggested_action,
                "primary_reason_code": row.primary_reason_code,
                "governance_reason_codes": list(row.governance_reason_codes),
                "side_diverged": row.side_diverged,
                "near_block": row.near_block,
                "confidence_gap": row.confidence_gap,
            }
            for row in result.rows
        ],
    }


def adapt_release_review_result(result: Any) -> dict:
    return {
        "total_matches": result.total_matches,
        "summary": dict(result.summary),
        "rows": [
            {
                "match_id": row.match_id,
                "match_label": row.match_label,
                "governance_action": row.governance_action,
                "release_action": row.release_action,
                "release_allowed": row.release_allowed,
                "primary_reason_code": row.primary_reason_code,
                "candidate_count": row.candidate_count,
                "top_play": row.top_play,
                "top_selection": row.top_selection,
                "top_line": row.top_line,
                "top_confidence": row.top_confidence,
                "provider_name": row.provider_name,
            }
            for row in result.rows
        ],
    }


def build_shadow_comparison_status_text(total_matches: int, governance_counts: dict) -> str:
    return f"C1 对照完成 | 场次 {int(total_matches)} | 治理 {governance_counts}"


def build_release_review_status_text(total_matches: int, release_allowed_count: int) -> str:
    return f"C1 放行评估完成 | 场次 {int(total_matches)} | 可放行 {int(release_allowed_count)}"
