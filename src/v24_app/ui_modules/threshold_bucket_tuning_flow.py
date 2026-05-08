from __future__ import annotations

from typing import Mapping


def build_threshold_bucket_tuning_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    calibrated = bool(resolved.get("calibrated"))
    reason = str(resolved.get("reason", "-"))
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    changed = int(validation.get("changed_play_count", 0) or 0)
    return f"弱分桶校准{'完成' if calibrated else '未更新'} | 变更玩法 {changed} | 原因 {reason}"


def build_threshold_bucket_tuning_apply_message(
    result: Mapping[str, object] | object,
    threshold_status_text: str,
) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    report_path = str(resolved.get("report_path") or "-")
    return (
        "弱分桶阈值校准已执行\n"
        + f"- 结算样本: {int(validation.get('sample_count', 0) or 0)}\n"
        + f"- 变更玩法: {int(validation.get('changed_play_count', 0) or 0)}\n"
        + f"- 报告: {report_path}\n\n"
        + threshold_status_text
    )
