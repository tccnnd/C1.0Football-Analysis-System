from __future__ import annotations

from typing import Mapping


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
    return (
        f"数据源: {resolved.get('source')}\n"
        + f"回看天数: {int(resolved.get('lookback_days', 2) or 2)}\n"
        + f"完场场次: {int(resolved.get('fetched_finished', 0) or 0)}\n"
        + f"修复快照: {int(resolved.get('restored_snapshots', 0) or 0)}"
        + f" / 检查分析历史 {int(repair.get('checked', 0) or 0)}\n"
        + f"新增结算: {int(resolved.get('new_settled', 0) or 0)}\n"
        + f"已结算跳过: {int(resolved.get('already_settled', 0) or 0)}\n"
        + f"其他跳过: {int(resolved.get('skipped', 0) or 0)}\n\n"
        + f"赛果回查: 检查 {int(resolved.get('snapshot_checked', 0) or 0)} / 命中 {int(resolved.get('snapshot_result_hits', 0) or 0)}\n"
        + f"预测快照命中: {int(resolved.get('snapshot_predictions', 0) or 0)}\n\n"
        + "消息:\n"
        + details
    )


def should_refresh_after_auto_settle(*, new_settled: int, has_matches: bool) -> bool:
    return int(new_settled) > 0 and bool(has_matches)
