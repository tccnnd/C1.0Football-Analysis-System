from __future__ import annotations

from typing import Mapping


def _ready_text(value: object) -> str:
    return "就绪" if bool(value) else "未就绪"


def build_model_training_overview_text(
    *,
    xgb_status: Mapping[str, object] | object,
    play_model_status: Mapping[str, object] | object,
    ensemble_status: Mapping[str, object] | object,
    bayes_status: Mapping[str, object] | object,
    threshold_status: Mapping[str, object] | object,
    policy_status: Mapping[str, object] | object,
    coverage_status: Mapping[str, object] | object,
) -> str:
    xgb = xgb_status if isinstance(xgb_status, Mapping) else {}
    play = play_model_status if isinstance(play_model_status, Mapping) else {}
    ensemble = ensemble_status if isinstance(ensemble_status, Mapping) else {}
    bayes = bayes_status if isinstance(bayes_status, Mapping) else {}
    thresholds = threshold_status if isinstance(threshold_status, Mapping) else {}
    policy = policy_status if isinstance(policy_status, Mapping) else {}
    coverage = coverage_status if isinstance(coverage_status, Mapping) else {}

    total_goals = play.get("total_goals", {}) if isinstance(play, Mapping) else {}
    scoreline = play.get("scoreline", {}) if isinstance(play, Mapping) else {}
    volatile_scoreline = play.get("volatile_scoreline", {}) if isinstance(play, Mapping) else {}
    weights = ensemble.get("weights", {}) if isinstance(ensemble, Mapping) else {}
    ensemble_validation = ensemble.get("validation", {}) if isinstance(ensemble, Mapping) else {}
    bayes_config = bayes.get("config", {}) if isinstance(bayes, Mapping) else {}
    threshold_values = thresholds.get("thresholds", {}) if isinstance(thresholds, Mapping) else {}
    policy_config = policy.get("policy", {}) if isinstance(policy, Mapping) else {}
    scoreline_policy = policy_config.get("scoreline", {}) if isinstance(policy_config, Mapping) else {}
    total_goals_policy = policy_config.get("total_goals", {}) if isinstance(policy_config, Mapping) else {}
    policy_validation = policy.get("validation", {}) if isinstance(policy, Mapping) else {}
    samples = coverage.get("xgb_samples", {}) if isinstance(coverage, Mapping) else {}
    club_history = coverage.get("club_history", {}) if isinstance(coverage, Mapping) else {}
    world_cup = coverage.get("world_cup_history", {}) if isinstance(coverage, Mapping) else {}
    rating_pools = coverage.get("rating_pools", {}) if isinstance(coverage, Mapping) else {}

    lines = [
        "模型训练状态总览",
        "",
        "训练数据",
        f"- XGB样本: {samples.get('sample_count', 0)} | 有效特征: {samples.get('valid_feature_count', 0)} | 联赛覆盖: {samples.get('league_count', 0)}",
        f"- 样本时间: {samples.get('date_start') or '-'} -> {samples.get('date_end') or '-'}",
        f"- 联赛样例: {', '.join(samples.get('league_examples', []) or []) or '-'}",
        f"- 联赛历史: {club_history.get('match_count', 0)} 场 | {club_history.get('date_start') or '-'} -> {club_history.get('date_end') or '-'} | profile={club_history.get('league_profile_count', 0)}",
        f"- 世界杯历史: {world_cup.get('match_count', 0)} 场 | {world_cup.get('year_start') or '-'}-{world_cup.get('year_end') or '-'} | 届数={world_cup.get('year_count', 0)}",
        f"- ELO评分池: 俱乐部 {rating_pools.get('club_team_count', 0)} 队 | 国家队 {rating_pools.get('national_team_count', 0)} 队",
        "",
        "模型就绪",
        f"- 主胜平负 XGB: {_ready_text(xgb.get('model_ready'))} | 样本={xgb.get('sample_count', 0)} | updated={xgb.get('model_updated_at') or '-'}",
        f"- 总进球模型: {_ready_text(total_goals.get('model_ready'))} | usable={total_goals.get('usable_count', 0)} | updated={total_goals.get('model_updated_at') or '-'}",
        f"- 比分模型: {_ready_text(scoreline.get('model_ready'))} | usable={scoreline.get('usable_count', 0)} | updated={scoreline.get('model_updated_at') or '-'}",
        f"- 高波动比分: {_ready_text(volatile_scoreline.get('model_ready'))} | usable={volatile_scoreline.get('usable_count', 0)} | updated={volatile_scoreline.get('model_updated_at') or '-'}",
        "",
        "校准参数",
        f"- Ensemble: updated={ensemble.get('updated_at') or '-'} | market={float(weights.get('market', 0) or 0):.1%} | elo={float(weights.get('elo', 0) or 0):.1%} | poisson={float(weights.get('poisson', 0) or 0):.1%} | xgb={float(weights.get('xgboost', 0) or 0):.1%}",
        f"- Ensemble验证: {ensemble_validation.get('sample_count', 0)} 场 | 联赛分层={ensemble_validation.get('league_override_count', 0)}",
        f"- Bayes: updated={bayes.get('updated_at') or '-'} | prior={bayes_config.get('prior_source', '-')} | prior_strength={float(bayes_config.get('prior_strength', 0) or 0):.1f} | model_strength={float(bayes_config.get('model_strength', 0) or 0):.1f}",
        f"- 玩法阈值: 1x2={float(threshold_values.get('1x2', 0) or 0):.2f} | handicap={float(threshold_values.get('handicap', 0) or 0):.2f} | total={float(threshold_values.get('total_goals', 0) or 0):.2f} | score={float(threshold_values.get('score', 0) or 0):.2f}",
        f"- 接管策略: updated={policy.get('updated_at') or '-'} | 验证={policy_validation.get('sample_count', 0)} | 搜索={policy_validation.get('search_profile', '-')}/{policy_validation.get('candidate_count', 0)}",
        f"- 比分接管: enabled={scoreline_policy.get('takeover_enabled')} | 同向={float(scoreline_policy.get('regular_same_outcome_min_confidence', 0) or 0):.2f} | 跨向={scoreline_policy.get('regular_cross_outcome_enabled')}@{float(scoreline_policy.get('regular_cross_outcome_min_confidence', 0) or 0):.2f}",
        f"- 总进球接管: enabled={total_goals_policy.get('takeover_enabled')} | min_conf={float(total_goals_policy.get('min_confidence', 0) or 0):.2f}",
    ]
    return "\n".join(lines)


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
    layered = resolved.get("layered_filter", {}) if isinstance(resolved, Mapping) else {}
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
    if isinstance(layered, Mapping) and layered.get("enabled"):
        global_play = layered.get("global_play", {}) if isinstance(layered.get("global_play"), Mapping) else {}
        league_play = layered.get("league_play", {}) if isinstance(layered.get("league_play"), Mapping) else {}
        league_rule_count = sum(len(item) for item in league_play.values() if isinstance(item, Mapping))
        parts.append(
            f"- 分层过滤: enabled=True | updated={layered.get('updated_at') or '-'} | global={len(global_play)} | league={league_rule_count}"
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


def _policy_reason_label(reason: object) -> str:
    reason_key = str(reason or "-")
    labels = {
        "joint_best": "joint_best",
        "candidate_disabled": "candidate_disabled",
        "calibration_uplift_passed": "calibration_uplift_passed",
        "insufficient_calibration_uplift": "insufficient_calibration_uplift",
    }
    return labels.get(reason_key, reason_key)


def build_play_model_policy_decision_rows(status: Mapping[str, object] | object) -> list[dict[str, str]]:
    resolved = status if isinstance(status, Mapping) else {}
    policy = resolved.get("policy", {}) if isinstance(resolved, Mapping) else {}
    scoreline_policy = policy.get("scoreline", {}) if isinstance(policy, Mapping) else {}
    total_goals_policy = policy.get("total_goals", {}) if isinstance(policy, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    total_goals_metrics = metrics.get("total_goals", {}) if isinstance(metrics, Mapping) else {}
    total_goals_best = total_goals_metrics.get("best", {}) if isinstance(total_goals_metrics, Mapping) else {}
    scoreline_best = metrics.get("scoreline_best", {}) if isinstance(metrics, Mapping) else {}

    total_goals_enabled = bool(total_goals_policy.get("takeover_enabled"))
    total_goals_reason = _policy_reason_label(total_goals_metrics.get("reason"))
    total_goals_current = float(total_goals_metrics.get("current_accuracy", 0) or 0)
    total_goals_candidate = float(total_goals_best.get("accuracy", 0) or 0)
    total_goals_uplift = float(total_goals_metrics.get("uplift", total_goals_candidate - total_goals_current) or 0)
    total_goals_required = float(total_goals_metrics.get("min_required_uplift", 0) or 0)
    total_goals_holdout_uplift = total_goals_metrics.get("holdout_uplift")
    total_goals_holdout_text = (
        f" | holdout {float(total_goals_holdout_uplift):+.2%}"
        if total_goals_holdout_uplift is not None
        else ""
    )
    total_goals_body = (
        f"current {total_goals_current:.2%} | candidate {total_goals_candidate:.2%} | "
        f"uplift {total_goals_uplift:+.2%} / required {total_goals_required:+.2%}{total_goals_holdout_text}\n"
        f"reason: {total_goals_reason} | min_conf {float(total_goals_policy.get('min_confidence', 0) or 0):.2f} | "
        f"hits {int(total_goals_best.get('hits', 0) or 0)}/{int(total_goals_best.get('covered', 0) or 0)}"
    )

    scoreline_enabled = bool(scoreline_policy.get("takeover_enabled"))
    scoreline_metrics = metrics.get("scoreline", {}) if isinstance(metrics, Mapping) else {}
    scoreline_reason = _policy_reason_label(scoreline_metrics.get("reason"))
    scoreline_holdout_delta = scoreline_metrics.get("holdout_delta")
    scoreline_holdout_text = (
        f" | holdout {float(scoreline_holdout_delta):+.2%}"
        if scoreline_holdout_delta is not None
        else ""
    )
    score_accuracy = float(scoreline_best.get("score_accuracy", 0) or 0)
    score_hits = int(scoreline_best.get("score_hits", 0) or 0)
    score_covered = int(scoreline_best.get("score_covered", 0) or 0)
    scoreline_body = (
        f"score {score_hits}/{score_covered} ({score_accuracy:.2%}) | combined {int(scoreline_best.get('combined_hits', 0) or 0)}{scoreline_holdout_text}\n"
        f"reason: {scoreline_reason}\n"
        f"regular same {float(scoreline_policy.get('regular_same_outcome_min_confidence', 0) or 0):.2f} | "
        f"regular cross {scoreline_policy.get('regular_cross_outcome_enabled')}@{float(scoreline_policy.get('regular_cross_outcome_min_confidence', 0) or 0):.2f}\n"
        f"volatile same {float(scoreline_policy.get('volatile_same_outcome_min_confidence', 0) or 0):.2f} | "
        f"volatile cross {scoreline_policy.get('volatile_cross_outcome_enabled')}@{float(scoreline_policy.get('volatile_cross_outcome_min_confidence', 0) or 0):.2f}"
    )

    return [
        {
            "title": f"Total Goals takeover: {'ON' if total_goals_enabled else 'SHADOW'}",
            "body": total_goals_body,
            "tone": "good" if total_goals_enabled else "warning",
        },
        {
            "title": f"Scoreline takeover: {'ON' if scoreline_enabled else 'OFF'}",
            "body": scoreline_body,
            "tone": "good" if scoreline_enabled else "warning",
        },
    ]


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


def build_high_accuracy_strategy_backtest_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    ok = bool(resolved.get("ok"))
    strategy = resolved.get("strategy", {}) if isinstance(resolved, Mapping) else {}
    return (
        f"高准确率策略{'完成' if ok else '失败'} | "
        f"{strategy.get('play_type', '-')}@{float(strategy.get('min_confidence', 0) or 0):.2f} | "
        f"acc {float(strategy.get('accuracy', 0) or 0):.2%}"
    )


def build_high_accuracy_strategy_backtest_message(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    strategy = resolved.get("strategy", {}) if isinstance(resolved, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    strategy_pool = resolved.get("strategy_pool", []) if isinstance(resolved, Mapping) else []
    report_path = resolved.get("report_path") or "-"
    return (
        "高准确率策略回测完成\n"
        + f"历史结算: {validation.get('settlement_count', 0)}\n"
        + f"策略记录: {validation.get('record_count', 0)}\n"
        + f"结算记录: {validation.get('settlement_record_count', 0)}\n"
        + f"历史市场记录: {validation.get('historical_record_count', 0)}\n"
        + f"候选策略: {validation.get('candidate_count', 0)}\n"
        + f"时间区间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}\n\n"
        + f"选中玩法: {strategy.get('play_type', '-')}\n"
        + f"适用范围: {strategy.get('scope', '-')} / {strategy.get('scope_value', '-')}\n"
        + f"最低置信度: {float(strategy.get('min_confidence', 0) or 0):.2f}\n"
        + f"回测命中率: {float(strategy.get('accuracy', 0) or 0):.2%} ({int(strategy.get('hit_count', 0) or 0)}/{int(strategy.get('sample_count', 0) or 0)})\n"
        + f"覆盖率: {float(strategy.get('coverage', 0) or 0):.2%}\n"
        + f"保守下界: {float(strategy.get('wilson_lower', 0) or 0):.2%}\n"
        + f"历史优势: {float(strategy.get('edge', 0) or 0):+.2%}\n\n"
        + f"策略池数量: {len(strategy_pool) if isinstance(strategy_pool, list) else 0}\n"
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
    decision_rows = build_play_model_policy_decision_rows(resolved)
    decision_text = "\n".join(
        f"- {row.get('title', '-')}: {row.get('body', '-')}" for row in decision_rows
    )
    return (
        "玩法接管策略\n"
        + f"- 更新时间: {resolved.get('updated_at') or '-'}\n"
        + f"- 版本: {resolved.get('version_id') or '-'}\n"
        + f"- 比分接管: enabled={scoreline.get('takeover_enabled')} | 常规同向={float(scoreline.get('regular_same_outcome_min_confidence', 0) or 0):.2f} | 常规跨向={scoreline.get('regular_cross_outcome_enabled')}@{float(scoreline.get('regular_cross_outcome_min_confidence', 0) or 0):.2f}\n"
        + f"- 高波动确认: 同向={float(scoreline.get('volatile_same_outcome_min_confidence', 0) or 0):.2f} | 跨向={scoreline.get('volatile_cross_outcome_enabled')}@{float(scoreline.get('volatile_cross_outcome_min_confidence', 0) or 0):.2f}\n"
        + f"- 总进球接管: enabled={total_goals.get('takeover_enabled')} | min_conf={float(total_goals.get('min_confidence', 0) or 0):.2f}\n"
        + f"- 联合最优: 比分={int(best.get('score_hits', 0) or 0)}/{int(best.get('score_covered', 0) or 0)} ({float(best.get('score_accuracy', 0) or 0):.2%}) | 总进球={int(best.get('total_goals_hits', 0) or 0)}/{int(best.get('total_goals_covered', 0) or 0)} ({float(best.get('total_goals_accuracy', 0) or 0):.2%}) | combined={int(best.get('combined_hits', 0) or 0)}\n"
        + "\nTakeover decisions\n"
        + decision_text
    )
