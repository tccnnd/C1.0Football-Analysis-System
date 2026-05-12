from __future__ import annotations

from typing import Mapping


def build_xgb_status_text(status: Mapping[str, object] | object) -> str:
    resolved = status if isinstance(status, Mapping) else {}
    label_counts = resolved.get("label_counts", {}) if isinstance(resolved, Mapping) else {}
    home_n = int(label_counts.get(0, 0))
    draw_n = int(label_counts.get(1, 0))
    away_n = int(label_counts.get(2, 0))
    return (
        "XGBoost v0 状态\n"
        + f"- xgboost可用: {resolved.get('xgboost_available')}\n"
        + f"- 样本总数: {resolved.get('sample_count', 0)}\n"
        + f"- 有效特征样本: {resolved.get('valid_feature_count', 0)}\n"
        + f"- 标签分布(主/平/客): {home_n} / {draw_n} / {away_n}\n"
        + f"- 训练阈值: {resolved.get('min_train_samples', 0)}\n"
        + f"- 模型文件存在: {resolved.get('model_exists')}\n"
        + f"- 模型已就绪: {resolved.get('model_ready')}\n"
        + f"- 模型兼容: {resolved.get('model_compatible')}\n"
        + f"- 最近模型更新时间: {resolved.get('model_updated_at') or '-'}\n"
        + f"- 最近训练尝试: {resolved.get('last_train_attempt') or '-'}"
    )


def build_train_xgb_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    trained = bool(resolved.get("trained"))
    reason = resolved.get("reason", "-")
    sample_count = resolved.get("sample_count", 0)
    postcheck = resolved.get("postcheck", {}) if isinstance(resolved.get("postcheck"), Mapping) else {}
    suffix = f" | 复检 {postcheck.get('status')}" if postcheck else ""
    return f"XGB训练{'成功' if trained else '未执行'} | 样本 {sample_count} | 原因 {reason}{suffix}"


def build_train_xgb_apply_message(result: Mapping[str, object] | object, xgb_status_text: str) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    trained = bool(resolved.get("trained"))
    reason = resolved.get("reason", "-")
    sample_count = resolved.get("sample_count", 0)
    updated_at = resolved.get("updated_at") or "-"
    postcheck = resolved.get("postcheck", {}) if isinstance(resolved.get("postcheck"), Mapping) else {}
    auto_backtest = resolved.get("auto_backtest", {}) if isinstance(resolved.get("auto_backtest"), Mapping) else {}
    postcheck_text = ""
    if postcheck:
        postcheck_text = (
            "\n\n训练后复检\n"
            + f"- 状态: {postcheck.get('status') or '-'}\n"
            + f"- 建议: {postcheck.get('recommendation') or '-'}\n"
            + f"- 自动回测: {'已执行' if bool(auto_backtest.get('executed')) else '未执行'} | {auto_backtest.get('reason') or '-'}\n"
            + f"- 闭环报告: {postcheck.get('report_path') or '-'}"
        )
    return (
        f"训练结果: {'成功' if trained else '未执行'}\n"
        + f"原因: {reason}\n"
        + f"样本数: {sample_count}\n"
        + f"更新时间: {updated_at}"
        + postcheck_text
        + "\n\n"
        + xgb_status_text
    )
