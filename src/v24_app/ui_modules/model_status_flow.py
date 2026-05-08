from __future__ import annotations

from typing import Mapping


def build_bayes_calibration_status_text(status: Mapping[str, object] | object) -> str:
    resolved = status if isinstance(status, Mapping) else {}
    config = resolved.get("config", {}) if isinstance(resolved, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    baseline = metrics.get("baseline", {}) if isinstance(metrics, Mapping) else {}
    best = metrics.get("best", {}) if isinstance(metrics, Mapping) else {}
    improvement = metrics.get("improvement", {}) if isinstance(metrics, Mapping) else {}
    override_count = int(resolved.get("league_override_count", 0) or 0)
    return (
        "贝叶斯校准状态\n"
        + f"- 模式: {resolved.get('mode', '-')}\n"
        + f"- 更新时间: {resolved.get('updated_at') or '-'}\n"
        + f"- 联赛分层覆盖: {override_count}\n"
        + f"- prior={config.get('prior_source')} | prior_strength={float(config.get('prior_strength', 0) or 0):.1f} | model_strength={float(config.get('model_strength', 0) or 0):.1f}\n"
        + f"- uncertainty_gain={float(config.get('uncertainty_gain', 0) or 0):.2f} | draw_bias_scale={float(config.get('draw_bias_scale', 0) or 0):.2f} | min_prob={float(config.get('min_probability', 0) or 0):.3f}\n"
        + f"- 验证样本: {validation.get('sample_count', 0)} | 训练样本: {validation.get('train_sample_count', 0)}\n"
        + f"- 时间区间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}\n"
        + f"- baseline: logloss={float(baseline.get('logloss', 0) or 0):.6f}, brier={float(baseline.get('brier', 0) or 0):.6f}, acc={float(baseline.get('accuracy', 0) or 0):.2%}\n"
        + f"- current : logloss={float(best.get('logloss', 0) or 0):.6f}, brier={float(best.get('brier', 0) or 0):.6f}, acc={float(best.get('accuracy', 0) or 0):.2%}\n"
        + f"- 提升: logloss {float(improvement.get('logloss_delta', 0) or 0):+.6f}, brier {float(improvement.get('brier_delta', 0) or 0):+.6f}, acc {float(improvement.get('accuracy_delta', 0) or 0):+.2%}"
    )


def build_bayes_calibration_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    calibrated = bool(resolved.get("calibrated"))
    reason = str(resolved.get("reason", "-"))
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    improvement = metrics.get("improvement", {}) if isinstance(metrics, Mapping) else {}
    return (
        f"贝叶斯校准{'完成' if calibrated else '未更新'} | 原因: {reason} | "
        f"logloss {float(improvement.get('logloss_delta', 0) or 0):+.6f} | "
        f"acc {float(improvement.get('accuracy_delta', 0) or 0):+.2%}"
    )


def build_bayes_calibration_apply_message(result: Mapping[str, object] | object, status_text: str) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    return (
        "贝叶斯参数搜索完成\n"
        + f"- 是否更新: {bool(resolved.get('calibrated'))}\n"
        + f"- 原因: {resolved.get('reason', '-')}\n"
        + f"- 验证样本: {validation.get('sample_count', 0)}\n\n"
        + status_text
    )


def build_ensemble_weight_status_text(status: Mapping[str, object] | object) -> str:
    resolved = status if isinstance(status, Mapping) else {}
    weights = resolved.get("weights", {}) if isinstance(resolved, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    league_weights = resolved.get("league_weights", {}) if isinstance(resolved, Mapping) else {}
    parts = [
        "Ensemble 权重状态",
        f"- 模式: {resolved.get('mode')}",
        f"- 更新时间: {resolved.get('updated_at') or '-'}",
        f"- 当前权重: market={float(weights.get('market', 0) or 0):.1%}, elo={float(weights.get('elo', 0) or 0):.1%}, poisson={float(weights.get('poisson', 0) or 0):.1%}, xgboost={float(weights.get('xgboost', 0) or 0):.1%}",
    ]
    sample_count = validation.get("sample_count")
    train_count = validation.get("train_sample_count")
    if sample_count or train_count:
        parts.append(f"- 验证集/训练集: {sample_count or 0} / {train_count or 0}")
        parts.append(f"- 验证时间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}")
    if isinstance(league_weights, Mapping) and league_weights:
        sample_leagues = list(league_weights.keys())[:5]
        parts.append(f"- 联赛覆盖: {len(league_weights)} 个")
        parts.append(f"- 覆盖示例: {', '.join(sample_leagues)}")
    if isinstance(metrics, Mapping) and metrics:
        for key in ("market", "elo", "poisson", "xgboost"):
            item = metrics.get(key, {})
            if not isinstance(item, Mapping):
                continue
            parts.append(
                f"- {key}: logloss={float(item.get('logloss', 0) or 0):.4f}, brier={float(item.get('brier', 0) or 0):.4f}, acc={float(item.get('accuracy', 0) or 0):.1%}"
            )
    return "\n".join(parts)


def build_calibrate_ensemble_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    calibrated = bool(resolved.get("calibrated"))
    reason = resolved.get("reason", "-")
    weights = resolved.get("weights", {}) if isinstance(resolved, Mapping) else {}
    return (
        f"权重校准{'完成' if calibrated else '未执行'} | 原因 {reason} | "
        f"market {float(weights.get('market', 0) or 0):.1%} | xgb {float(weights.get('xgboost', 0) or 0):.1%}"
    )


def build_calibrate_ensemble_apply_message(result: Mapping[str, object] | object, ensemble_status_text: str) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    calibrated = bool(resolved.get("calibrated"))
    reason = resolved.get("reason", "-")
    return (
        f"校准结果: {'成功' if calibrated else '未执行'}\n"
        + f"原因: {reason}\n"
        + f"样本数: {resolved.get('sample_count', 0)}\n\n"
        + ensemble_status_text
    )


def build_ensemble_backtest_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    ok = bool(resolved.get("ok"))
    stage5_improvement = resolved.get("stage5_improvement", {}) if isinstance(resolved, Mapping) else {}
    return (
        f"回测{'完成' if ok else '失败'} | Stage5 acc {float(stage5_improvement.get('accuracy_delta', 0) or 0):+.2%} | "
        f"logloss {float(stage5_improvement.get('logloss_delta', 0) or 0):+.4f}"
    )


def build_ensemble_backtest_success_message(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    default_metrics = resolved.get("default", {})
    calibrated_metrics = resolved.get("calibrated", {})
    league_metrics = resolved.get("league_specific", {})
    stage4_metrics = resolved.get("stage4_runtime", {})
    stage5_metrics = resolved.get("stage5_specialist", {})
    validation = resolved.get("validation", {})
    report_path = resolved.get("report_path") or "-"
    improvement = resolved.get("improvement", {}) if isinstance(resolved, Mapping) else {}
    league_improvement = resolved.get("league_improvement", {}) if isinstance(resolved, Mapping) else {}
    stage5_improvement = resolved.get("stage5_improvement", {}) if isinstance(resolved, Mapping) else {}
    return (
        "Ensemble 回测完成\n"
        + f"验证样本: {validation.get('sample_count', 0)} | 训练样本: {validation.get('train_sample_count', 0)}\n"
        + f"时间区间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}\n\n"
        + f"默认权重: logloss={float(default_metrics.get('logloss', 0) or 0):.6f}, brier={float(default_metrics.get('brier', 0) or 0):.6f}, acc={float(default_metrics.get('accuracy', 0) or 0):.2%}\n"
        + f"校准权重: logloss={float(calibrated_metrics.get('logloss', 0) or 0):.6f}, brier={float(calibrated_metrics.get('brier', 0) or 0):.6f}, acc={float(calibrated_metrics.get('accuracy', 0) or 0):.2%}\n"
        + f"联赛分层: logloss={float(league_metrics.get('logloss', 0) or 0):.6f}, brier={float(league_metrics.get('brier', 0) or 0):.6f}, acc={float(league_metrics.get('accuracy', 0) or 0):.2%}\n"
        + f"Stage4运行态: logloss={float(stage4_metrics.get('logloss', 0) or 0):.6f}, brier={float(stage4_metrics.get('brier', 0) or 0):.6f}, acc={float(stage4_metrics.get('accuracy', 0) or 0):.2%}\n"
        + f"Stage5专家层: logloss={float(stage5_metrics.get('logloss', 0) or 0):.6f}, brier={float(stage5_metrics.get('brier', 0) or 0):.6f}, acc={float(stage5_metrics.get('accuracy', 0) or 0):.2%}\n\n"
        + f"校准提升: logloss {float(improvement.get('logloss_delta', 0) or 0):+.6f}, brier {float(improvement.get('brier_delta', 0) or 0):+.6f}, acc {float(improvement.get('accuracy_delta', 0) or 0):+.2%}\n"
        + f"联赛提升: logloss {float(league_improvement.get('logloss_delta', 0) or 0):+.6f}, brier {float(league_improvement.get('brier_delta', 0) or 0):+.6f}, acc {float(league_improvement.get('accuracy_delta', 0) or 0):+.2%}\n"
        + f"Stage5提升: logloss {float(stage5_improvement.get('logloss_delta', 0) or 0):+.6f}, brier {float(stage5_improvement.get('brier_delta', 0) or 0):+.6f}, acc {float(stage5_improvement.get('accuracy_delta', 0) or 0):+.2%}\n"
        + f"平局行为: Stage4 {int(stage4_metrics.get('draw_picks', 0) or 0)}场/{float(stage4_metrics.get('draw_hit_rate', 0) or 0):.2%} | Stage5 {int(stage5_metrics.get('draw_picks', 0) or 0)}场/{float(stage5_metrics.get('draw_hit_rate', 0) or 0):.2%}\n"
        + f"报告: {report_path}"
    )


def build_play_threshold_status_text(status: Mapping[str, object] | object) -> str:
    resolved = status if isinstance(status, Mapping) else {}
    thresholds = resolved.get("thresholds", {}) if isinstance(resolved, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    parts = [
        "玩法阈值状态",
        f"- 模式: {resolved.get('mode')}",
        f"- 更新时间: {resolved.get('updated_at') or '-'}",
    ]
    if validation.get("sample_count") or validation.get("train_sample_count"):
        parts.append(f"- 验证集/训练集: {validation.get('sample_count', 0)} / {validation.get('train_sample_count', 0)}")
        parts.append(f"- 验证时间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}")
    for play_name in ("1x2", "handicap", "total_goals", "htft", "score"):
        metric = metrics.get(play_name, {}) if isinstance(metrics, Mapping) else {}
        parts.append(
            f"- {play_name}: threshold={float(thresholds.get(play_name, 0) or 0):.2f}, acc={float(metric.get('accuracy', 0) or 0):.2%}, coverage={float(metric.get('coverage', 0) or 0):.2%}"
        )
    return "\n".join(parts)


def build_play_threshold_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    calibrated = bool(resolved.get("calibrated"))
    reason = resolved.get("reason", "-")
    return f"玩法阈值校准{'完成' if calibrated else '失败'} | 原因 {reason}"


def build_play_threshold_apply_success_message(result: Mapping[str, object] | object, threshold_status_text: str) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    return (
        "玩法阈值校准完成\n"
        + f"验证样本: {validation.get('sample_count', 0)}\n"
        + f"报告: {resolved.get('report_path') or '-'}\n\n"
        + threshold_status_text
    )


def build_play_model_policy_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    calibrated = bool(resolved.get("calibrated"))
    reason = resolved.get("reason", "-")
    return f"玩法接管策略{'完成' if calibrated else '失败'} | 原因 {reason}"


def build_play_model_policy_apply_success_message(result: Mapping[str, object] | object, policy_status_text: str) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    return (
        "玩法接管策略已校准\n"
        + f"验证样本: {validation.get('sample_count', 0)}\n\n"
        + policy_status_text
    )


def build_train_play_models_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    trained = bool(resolved.get("trained"))
    total_result = resolved.get("total_goals", {}) if isinstance(resolved, Mapping) else {}
    score_result = resolved.get("scoreline", {}) if isinstance(resolved, Mapping) else {}
    volatile_result = resolved.get("volatile_scoreline", {}) if isinstance(resolved, Mapping) else {}
    return (
        f"玩法模型{'完成' if trained else '未执行'} | 总进球={total_result.get('reason', '-')} | "
        f"比分={score_result.get('reason', '-')} | 高波动={volatile_result.get('reason', '-')}"
    )


def build_train_play_models_apply_message(result: Mapping[str, object] | object, model_status_text: str) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    trained = bool(resolved.get("trained"))
    total_result = resolved.get("total_goals", {}) if isinstance(resolved, Mapping) else {}
    score_result = resolved.get("scoreline", {}) if isinstance(resolved, Mapping) else {}
    volatile_result = resolved.get("volatile_scoreline", {}) if isinstance(resolved, Mapping) else {}
    return (
        f"玩法模型训练: {'完成' if trained else '未执行'}\n"
        + f"- 总进球: {total_result.get('reason', '-')} | 可用样本={total_result.get('usable_count', 0)} | 更新时间={total_result.get('updated_at') or '-'}\n"
        + f"- 比分: {score_result.get('reason', '-')} | 可用样本={score_result.get('usable_count', 0)} | 更新时间={score_result.get('updated_at') or '-'}\n"
        + f"- 高波动比分: {volatile_result.get('reason', '-')} | 可用样本={volatile_result.get('usable_count', 0)} | 更新时间={volatile_result.get('updated_at') or '-'}\n\n"
        + model_status_text
    )


def build_play_model_backtest_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    ok = bool(resolved.get("ok"))
    improvement = resolved.get("improvement", {}) if isinstance(resolved, Mapping) else {}
    return (
        f"玩法回测{'完成' if ok else '失败'} | 让球 {float(improvement.get('handicap_shadow_delta', 0) or 0):+.2%} | "
        f"总进球 {float(improvement.get('total_goals_model_delta', 0) or 0):+.2%} | 比分 {float(improvement.get('score_model_delta', 0) or 0):+.2%}"
    )


def build_play_model_backtest_success_message(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    report_path = resolved.get("report_path") or "-"
    return (
        "玩法回测完成\n"
        + f"验证样本: {validation.get('sample_count', 0)}\n"
        + f"时间区间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}\n\n"
        + f"让球: baseline {float(metrics.get('handicap_baseline', {}).get('accuracy', 0) or 0):.2%} | current {float(metrics.get('handicap_current', {}).get('accuracy', 0) or 0):.2%} | shadow {float(metrics.get('handicap_shadow', {}).get('accuracy', 0) or 0):.2%}\n"
        + f"总进球: baseline {float(metrics.get('total_goals_baseline', {}).get('accuracy', 0) or 0):.2%} | current {float(metrics.get('total_goals_current', {}).get('accuracy', 0) or 0):.2%} | model {float(metrics.get('total_goals_model', {}).get('accuracy', 0) or 0):.2%}\n"
        + f"比分: baseline {float(metrics.get('score_baseline', {}).get('accuracy', 0) or 0):.2%} | current {float(metrics.get('score_current', {}).get('accuracy', 0) or 0):.2%} | model {float(metrics.get('score_model', {}).get('accuracy', 0) or 0):.2%}\n"
        + f"高波动专用: {float(metrics.get('score_volatile_model_volatile', {}).get('accuracy', 0) or 0):.2%} ({int(metrics.get('score_volatile_model_volatile', {}).get('hits', 0) or 0)}/{int(metrics.get('score_volatile_model_volatile', {}).get('total', 0) or 0)})\n\n"
        + f"报告: {report_path}"
    )


def build_play_model_training_status_text(status: Mapping[str, object] | object) -> str:
    resolved = status if isinstance(status, Mapping) else {}
    total_goals = resolved.get("total_goals", {}) if isinstance(resolved, Mapping) else {}
    scoreline = resolved.get("scoreline", {}) if isinstance(resolved, Mapping) else {}
    volatile_scoreline = resolved.get("volatile_scoreline", {}) if isinstance(resolved, Mapping) else {}
    return (
        "玩法模型状态\n"
        + f"- 总进球: ready={total_goals.get('model_ready')} | usable={total_goals.get('usable_count', 0)} | updated={total_goals.get('model_updated_at') or '-'}\n"
        + f"- 比分: ready={scoreline.get('model_ready')} | usable={scoreline.get('usable_count', 0)} | updated={scoreline.get('model_updated_at') or '-'}\n"
        + f"- 高波动比分: ready={volatile_scoreline.get('model_ready')} | usable={volatile_scoreline.get('usable_count', 0)} | updated={volatile_scoreline.get('model_updated_at') or '-'}\n"
        + f"- 总进球类别数: {len(total_goals.get('class_names', []) or [])}\n"
        + f"- 比分类别数: {len(scoreline.get('class_names', []) or [])}\n"
        + f"- 高波动类别数: {len(volatile_scoreline.get('class_names', []) or [])}"
    )


def build_play_model_policy_status_text(status: Mapping[str, object] | object) -> str:
    resolved = status if isinstance(status, Mapping) else {}
    policy = resolved.get("policy", {}) if isinstance(resolved, Mapping) else {}
    scoreline = policy.get("scoreline", {}) if isinstance(policy, Mapping) else {}
    total_goals = policy.get("total_goals", {}) if isinstance(policy, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    best = metrics.get("scoreline_best", {}) if isinstance(metrics, Mapping) else {}
    return (
        "玩法接管策略\n"
        + f"- 更新时间: {resolved.get('updated_at') or '-'}\n"
        + f"- 比分接管: enabled={scoreline.get('takeover_enabled')} | 常规同向={float(scoreline.get('regular_same_outcome_min_confidence', 0) or 0):.2f} | 常规跨向={scoreline.get('regular_cross_outcome_enabled')}@{float(scoreline.get('regular_cross_outcome_min_confidence', 0) or 0):.2f}\n"
        + f"- 高波动确认: 同向={float(scoreline.get('volatile_same_outcome_min_confidence', 0) or 0):.2f} | 跨向={scoreline.get('volatile_cross_outcome_enabled')}@{float(scoreline.get('volatile_cross_outcome_min_confidence', 0) or 0):.2f}\n"
        + f"- 总进球接管: enabled={total_goals.get('takeover_enabled')} | min_conf={float(total_goals.get('min_confidence', 0) or 0):.2f}\n"
        + f"- 联合最优: 比分={int(best.get('score_hits', 0) or 0)}/{int(best.get('score_covered', 0) or 0)} ({float(best.get('score_accuracy', 0) or 0):.2%}) | 总进球={int(best.get('total_goals_hits', 0) or 0)}/{int(best.get('total_goals_covered', 0) or 0)} ({float(best.get('total_goals_accuracy', 0) or 0):.2%}) | combined={int(best.get('combined_hits', 0) or 0)}"
    )
