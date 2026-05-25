from __future__ import annotations

from typing import Mapping


def _format_backfill_report_lines(title: str, report: Mapping[str, object] | object) -> list[str]:
    resolved = report if isinstance(report, Mapping) else {}
    if not resolved:
        return []
    lines = [title]
    for key in ("checked", "updated", "restored", "already_ready", "missing_prediction", "invalid_match", "skipped_limit", "backfilled"):
        if key in resolved:
            lines.append(f"- {key}: {resolved.get(key, 0)}")
    fact_ref_kinds = resolved.get("fact_ref_kinds")
    if isinstance(fact_ref_kinds, Mapping) and fact_ref_kinds:
        counts = ", ".join(f"{key}={int(value or 0)}" for key, value in sorted(fact_ref_kinds.items()))
        lines.append(f"- fact_ref_kinds: {counts}")
    return lines


def build_auto_settle_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    return (
        f"自动回收: 回看{int(resolved.get('lookback_days', 2) or 2)}天 | "
        f"完场{int(resolved.get('fetched_finished', 0) or 0)} | "
        f"修复快照 {int(resolved.get('restored_snapshots', 0) or 0)} | "
        f"新增结算 {int(resolved.get('new_settled', 0) or 0)}"
    )


def build_auto_settle_popup_message(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    messages = resolved.get("messages", [])
    details = "\n".join(f"- {item}" for item in messages) if isinstance(messages, list) and messages else "- 无"
    repair = resolved.get("snapshot_repair", {}) if isinstance(resolved, Mapping) else {}
    history_backfill = resolved.get("analysis_history_backfill", {}) if isinstance(resolved, Mapping) else {}
    history_trace_backfill = resolved.get("analysis_history_trace_fact_ref_backfill", {}) if isinstance(resolved, Mapping) else {}
    miss_reasons = resolved.get("snapshot_result_miss_reasons", {})
    if isinstance(miss_reasons, Mapping) and miss_reasons:
        miss_reason_text = ", ".join(
            f"{key}={int(value or 0)}" for key, value in sorted(miss_reasons.items()) if int(value or 0) > 0
        )
    else:
        miss_reason_text = "-"
    return (
        f"数据源: {resolved.get('source')}\n"
        + f"回看天数: {int(resolved.get('lookback_days', 2) or 2)}\n"
        + f"完场场次: {int(resolved.get('fetched_finished', 0) or 0)}\n"
        + f"修复快照: {int(resolved.get('restored_snapshots', 0) or 0)}"
        + f" / 检查分析历史 {int(repair.get('checked', 0) or 0)}\n"
        + f"新增结算: {int(resolved.get('new_settled', 0) or 0)}\n"
        + f"已结算跳过: {int(resolved.get('already_settled', 0) or 0)}\n"
        + f"其他跳过: {int(resolved.get('skipped', 0) or 0)}\n\n"
        + f"赛果回查: 检查 {int(resolved.get('snapshot_checked', 0) or 0)} / 命中 {int(resolved.get('snapshot_result_hits', 0) or 0)} / 未命中 {int(resolved.get('snapshot_result_misses', 0) or 0)}\n"
        + f"Snapshot lookup queue: candidates {int(resolved.get('snapshot_lookup_candidates', 0) or 0)} / limit {int(resolved.get('snapshot_lookup_limit', 0) or 0)} / skipped {int(resolved.get('snapshot_lookup_skipped_by_limit', 0) or 0)} / cache_hits {int(resolved.get('snapshot_lookup_cache_hits', 0) or 0)}\n"
        + f"未命中原因: {miss_reason_text}\n"
        + f"预测快照命中: {int(resolved.get('snapshot_predictions', 0) or 0)}\n\n"
        + ("\n".join(_format_backfill_report_lines("历史快照回填", history_backfill)) + "\n\n" if isinstance(history_backfill, Mapping) and history_backfill else "")
        + ("\n".join(_format_backfill_report_lines("历史 Trace 回填", history_trace_backfill)) + "\n\n" if isinstance(history_trace_backfill, Mapping) and history_trace_backfill else "")
        + "消息:\n"
        + details
    )


def should_refresh_after_auto_settle(*, new_settled: int, has_matches: bool) -> bool:
    return int(new_settled) > 0 and bool(has_matches)
