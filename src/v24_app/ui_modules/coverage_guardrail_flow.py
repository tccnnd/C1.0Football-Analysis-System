from __future__ import annotations

from typing import Mapping


def build_coverage_guardrail_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    calibrated = bool(resolved.get("calibrated"))
    reason = str(resolved.get("reason", "-"))
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    final_cov = float(validation.get("final_single_coverage", 0.0) or 0.0)
    return f"覆盖率保护{'完成' if calibrated else '未调整'} | 覆盖率 {final_cov:.0%} | 原因 {reason}"


def build_coverage_guardrail_apply_message(
    result: Mapping[str, object] | object,
    threshold_status_text: str,
) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    report_path = str(resolved.get("report_path") or "-")
    return (
        "覆盖率保护器执行完成\n"
        + f"- 预测样本: {int(validation.get('prediction_count', 0) or 0)}\n"
        + f"- 基线覆盖率: {float(validation.get('base_single_coverage', 0.0) or 0.0):.1%}\n"
        + f"- 调整后覆盖率: {float(validation.get('final_single_coverage', 0.0) or 0.0):.1%}\n"
        + f"- 报告: {report_path}\n\n"
        + threshold_status_text
    )
