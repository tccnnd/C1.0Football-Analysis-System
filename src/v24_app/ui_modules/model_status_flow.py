from __future__ import annotations

from typing import Mapping


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _draw_guard_policy_text(result: Mapping[str, object]) -> str:
    policy = result.get("draw_release_guard_policy")
    if not isinstance(policy, Mapping):
        summary = result.get("summary", {}) if isinstance(result.get("summary"), Mapping) else {}
        policy = summary.get("draw_release_guard_policy") if isinstance(summary.get("draw_release_guard_policy"), Mapping) else {}
    if not isinstance(policy, Mapping) or not policy:
        return "Draw release guard (watch-only): -"
    weak_buckets = policy.get("weak_odds_buckets") if isinstance(policy.get("weak_odds_buckets"), Mapping) else {}
    bucket_text = ", ".join(sorted(str(key) for key in weak_buckets)) if weak_buckets else "-"
    return (
        f"Draw release guard (watch-only): active={bool(policy.get('enabled', True))} | "
        f"score_floor={_safe_float(policy.get('min_score'), 0.0):.2f} | blocked_odds={bucket_text}"
    )


def _ready_text(value: object) -> str:
    return "就绪" if bool(value) else "未就绪"


def _health_tone(status: object) -> str:
    value = str(status or "").strip().lower()
    if value == "blocked":
        return "danger"
    if value == "attention":
        return "warning"
    if value == "healthy":
        return "success"
    return "neutral"


def _health_status_title(status: object) -> str:
    value = str(status or "").strip().lower()
    if value == "blocked":
        return "训练阻塞"
    if value == "attention":
        return "需要关注"
    if value == "healthy":
        return "可训练"
    return "-"


def _metric_tone(value: int, target: int, *, status: str = "") -> str:
    if target <= 0:
        return "neutral"
    if value < target:
        return "danger" if status == "blocked" else "warning"
    return "success"


def _feature_ratio_tone(value: float, target: float) -> str:
    if target <= 0:
        return "neutral"
    return "success" if value >= target else "warning"


def _training_health_action_for_issue(code: object, fallback: object = "") -> str:
    actions = {
        "xgb_sample_count_low": "扩大历史赛果样本，优先最近4年主流联赛",
        "xgb_valid_feature_count_low": "重建特征或清理无特征样本",
        "xgb_valid_feature_ratio_low": "重建特征或清理无特征样本",
        "xgb_label_class_missing": "补平局/客胜等弱类别样本",
        "xgb_class_balance_low": "补平局/客胜等弱类别样本",
        "xgb_league_coverage_low": "补不同联赛样本",
        "xgb_date_range_missing": "修复样本日期字段",
        "league_profiles_missing": "生成联赛画像",
        "statsbomb_date_overlap_missing": "执行StatsBomb覆盖计划；若仍无交集，补重叠历史赛果或当前事件源",
        "statsbomb_review_samples_missing": "将事件摘要转为复盘训练样本",
    }
    actions.update(
        {
            "fact_match_coverage_low": "Materialize MatchFact rows for history/XGB samples",
            "fact_action_coverage_low": "Build canonical ActionFact sidecars from event summaries",
            "fact_source_provenance_low": "Backfill provider/source metadata for fact rows",
        }
    )
    return actions.get(str(code or ""), str(fallback or "按健康问题补齐训练数据"))


def _training_health_action_key_for_issue(code: object) -> str:
    action_keys = {
        "xgb_sample_count_low": "import_historical_samples",
        "xgb_valid_feature_count_low": "rebuild_xgb_from_club_history",
        "xgb_valid_feature_ratio_low": "rebuild_xgb_from_club_history",
        "xgb_label_class_missing": "import_historical_samples",
        "xgb_class_balance_low": "import_historical_samples",
        "xgb_league_coverage_low": "import_historical_samples",
        "xgb_date_range_missing": "rebuild_xgb_from_club_history",
        "league_profiles_missing": "build_league_profiles",
        "statsbomb_date_overlap_missing": "execute_statsbomb_coverage_import_plan",
        "statsbomb_review_samples_missing": "build_statsbomb_review_samples",
    }
    action_keys.update(
        {
            "fact_match_coverage_low": "refresh_training_health",
            "fact_action_coverage_low": "build_statsbomb_review_samples",
            "fact_source_provenance_low": "refresh_training_health",
        }
    )
    return action_keys.get(str(code or ""), "refresh_training_health")


def training_health_action_button_text(action_key: object) -> str:
    labels = {
        "import_historical_samples": "导入历史样本",
        "rebuild_xgb_from_club_history": "重建XGB样本",
        "build_league_profiles": "生成联赛画像",
        "build_statsbomb_coverage_import_plan": "生成覆盖计划",
        "execute_statsbomb_coverage_import_plan": "执行覆盖计划",
        "build_statsbomb_review_samples": "生成复盘样本",
        "train_xgb": "训练XGB",
        "train_play_models": "训练玩法模型",
        "run_play_model_backtest": "运行稳定性回测",
        "refresh_training_health": "刷新诊断",
    }
    labels["export_play_model_takeover_gate_audit_report"] = "导出守门审计报告"
    return labels.get(str(action_key or ""), "刷新诊断")


def build_training_health_card_rows(coverage_status: Mapping[str, object] | object, *, limit: int = 8) -> list[dict[str, str]]:
    coverage = coverage_status if isinstance(coverage_status, Mapping) else {}
    samples = coverage.get("xgb_samples", {}) if isinstance(coverage.get("xgb_samples"), Mapping) else {}
    health = coverage.get("training_health", {}) if isinstance(coverage.get("training_health"), Mapping) else {}
    trainability = health.get("xgb_trainability", {}) if isinstance(health.get("xgb_trainability"), Mapping) else {}
    history = health.get("history_readiness", {}) if isinstance(health.get("history_readiness"), Mapping) else {}
    rating = health.get("rating_readiness", {}) if isinstance(health.get("rating_readiness"), Mapping) else {}
    fact = health.get("fact_readiness", {}) if isinstance(health.get("fact_readiness"), Mapping) else {}

    status = str(health.get("status") or "-")
    sample_count = _safe_int(trainability.get("sample_count", samples.get("sample_count", 0)))
    min_sample_count = _safe_int(trainability.get("min_sample_count", 300))
    valid_feature_count = _safe_int(trainability.get("valid_feature_count", samples.get("valid_feature_count", 0)))
    min_valid_feature_count = _safe_int(trainability.get("min_valid_feature_count", 300))
    valid_feature_ratio = _safe_float(trainability.get("valid_feature_ratio"), 0.0)
    min_valid_feature_ratio = _safe_float(trainability.get("min_valid_feature_ratio"), 0.95)
    label_class_count = _safe_int(trainability.get("label_class_count", 0))
    min_label_classes = _safe_int(trainability.get("min_label_classes", 3))
    min_class_count = _safe_int(trainability.get("min_class_count", 0))
    min_required_class_count = _safe_int(trainability.get("min_required_class_count", 30))
    league_count = _safe_int(trainability.get("league_count", samples.get("league_count", 0)))
    min_league_count = _safe_int(trainability.get("min_league_count", 5))
    club_match_count = _safe_int(history.get("club_match_count", 0))
    min_club_match_count = _safe_int(history.get("min_club_match_count", 100))
    league_profile_count = _safe_int(history.get("league_profile_count", 0))
    statsbomb = coverage.get("statsbomb_events", {}) if isinstance(coverage.get("statsbomb_events"), Mapping) else {}
    statsbomb_match_count = _safe_int(history.get("statsbomb_match_count", 0))
    statsbomb_review_sample_count = _safe_int(history.get("statsbomb_review_sample_count", 0))
    statsbomb_review_feature_count = _safe_int(history.get("statsbomb_review_feature_count", 0))
    statsbomb_coverage_plan = statsbomb.get("coverage_import_plan", {}) if isinstance(statsbomb.get("coverage_import_plan"), Mapping) else {}
    club_team_count = _safe_int(rating.get("club_team_count", 0))
    national_team_count = _safe_int(rating.get("national_team_count", 0))
    match_fact_available_count = _safe_int(fact.get("match_fact_available_count", 0))
    match_fact_target_count = _safe_int(fact.get("match_fact_target_count", 0))
    match_fact_coverage_ratio = _safe_float(fact.get("match_fact_coverage_ratio"), 0.0)
    min_match_fact_coverage_ratio = _safe_float(fact.get("min_match_fact_coverage_ratio"), 0.80)
    action_fact_match_count = _safe_int(fact.get("action_fact_match_count", 0))
    action_fact_target_match_count = _safe_int(fact.get("action_fact_target_match_count", 0))
    action_fact_event_count = _safe_int(fact.get("action_fact_event_count", 0))
    source_provenance_ratio = _safe_float(fact.get("source_provenance_ratio"), 0.0)

    rows = [
        {
            "label": "整体状态",
            "value": status,
            "tone": _health_tone(status),
            "detail": f"{_health_status_title(status)} | blocking={health.get('blocking_count', 0)} | warning={health.get('warning_count', 0)}",
        },
        {
            "label": "XGB样本",
            "value": f"{sample_count} / {min_sample_count}",
            "tone": _metric_tone(sample_count, min_sample_count, status=status),
            "detail": f"有效特征 {valid_feature_count}",
        },
        {
            "label": "有效特征",
            "value": f"{valid_feature_count} / {min_valid_feature_count}",
            "tone": _metric_tone(valid_feature_count, min_valid_feature_count, status=status),
            "detail": f"比例 {valid_feature_ratio:.1%} / {min_valid_feature_ratio:.1%}",
        },
        {
            "label": "标签类别",
            "value": f"{label_class_count} / {min_label_classes}",
            "tone": _metric_tone(label_class_count, min_label_classes),
            "detail": f"最小类别 {min_class_count} / {min_required_class_count}",
        },
        {
            "label": "联赛覆盖",
            "value": f"{league_count} / {min_league_count}",
            "tone": _metric_tone(league_count, min_league_count),
            "detail": f"日期 {trainability.get('date_start') or '-'} -> {trainability.get('date_end') or '-'}",
        },
        {
            "label": "历史样本",
            "value": f"{club_match_count} / {min_club_match_count}",
            "tone": _metric_tone(club_match_count, min_club_match_count),
            "detail": f"联赛画像 {league_profile_count} | 世界杯 {history.get('world_cup_match_count', 0)}",
        },
        {
            "label": "StatsBomb复盘",
            "value": str(statsbomb_review_sample_count),
            "tone": "warning" if statsbomb_match_count > 0 and statsbomb_review_sample_count <= 0 else "success" if statsbomb_review_sample_count > 0 else "neutral",
            "detail": f"事件 {statsbomb_match_count} | 特征 {statsbomb_review_feature_count} | 计划 {statsbomb_coverage_plan.get('status', '-')}",
        },
        {
            "label": "Fact Layer",
            "value": f"{match_fact_available_count} / {match_fact_target_count}",
            "tone": "success" if match_fact_target_count <= 0 or match_fact_coverage_ratio >= min_match_fact_coverage_ratio else "warning",
            "detail": f"MatchFact {match_fact_coverage_ratio:.1%} | ActionFact {action_fact_match_count}/{action_fact_target_match_count} ({action_fact_event_count} events) | Source {source_provenance_ratio:.1%}",
        },
        {
            "label": "ELO评分池",
            "value": f"{club_team_count} / {national_team_count}",
            "tone": "success" if club_team_count > 0 or national_team_count > 0 else "neutral",
            "detail": "俱乐部 / 国家队",
        },
    ]
    return rows[: max(0, int(limit))]


def build_training_health_action_rows(coverage_status: Mapping[str, object] | object, *, limit: int = 5) -> list[dict[str, str]]:
    coverage = coverage_status if isinstance(coverage_status, Mapping) else {}
    health = coverage.get("training_health", {}) if isinstance(coverage.get("training_health"), Mapping) else {}
    issues = [row for row in health.get("issues", []) if isinstance(row, Mapping)] if isinstance(health.get("issues"), list) else []
    if not issues:
        return [
            {
                "label": "下一步",
                "value": "进入回测/训练稳定性验证",
                "tone": "success" if str(health.get("status") or "") == "healthy" else "neutral",
                "detail": "训练数据当前无阻塞问题",
                "action_key": "run_play_model_backtest",
            }
        ][: max(0, int(limit))]

    severity_order = {"blocking": 0, "warning": 1}
    ordered = sorted(
        issues,
        key=lambda issue: (
            severity_order.get(str(issue.get("severity") or ""), 2),
            str(issue.get("code") or ""),
        ),
    )
    rows = []
    for index, issue in enumerate(ordered[: max(0, int(limit))], start=1):
        severity = str(issue.get("severity") or "-")
        rows.append(
            {
                "label": f"建议{index}",
                "value": _training_health_action_for_issue(issue.get("code"), issue.get("recommendation")),
                "tone": "danger" if severity == "blocking" else "warning",
                "detail": f"{severity} | {issue.get('code', '-')} | {issue.get('message', '-')}",
                "action_key": _training_health_action_key_for_issue(issue.get("code")),
            }
        )
    return rows


def build_training_model_gate_rows(gate_status: Mapping[str, object] | object, *, limit: int = 6) -> list[dict[str, str]]:
    gate = gate_status if isinstance(gate_status, Mapping) else {}
    xgb = gate.get("xgb", {}) if isinstance(gate.get("xgb"), Mapping) else {}
    play = gate.get("play_models", {}) if isinstance(gate.get("play_models"), Mapping) else {}
    recommended_action = str(gate.get("recommended_action") or "-")
    status = str(gate.get("status") or "-")
    rows = [
        {
            "label": "门槛状态",
            "value": status,
            "tone": "danger" if status == "blocked" else "success" if status in {"ready_to_train_xgb", "ready_to_train_play_models", "ready_for_backtest"} else "warning",
            "detail": str(gate.get("recommendation") or "-"),
            "action_key": recommended_action,
        },
        {
            "label": "XGB训练门槛",
            "value": "可训练" if bool(xgb.get("trainable")) else "未达标",
            "tone": "success" if bool(xgb.get("trainable")) else "danger",
            "detail": f"样本 {xgb.get('sample_count', 0)}/{xgb.get('min_sample_count', 0)} | 特征 {xgb.get('valid_feature_count', 0)}/{xgb.get('min_valid_feature_count', 0)} | ready={bool(xgb.get('model_ready'))}",
            "action_key": "train_xgb" if bool(xgb.get("trainable")) and not bool(xgb.get("model_ready")) else "",
        },
        {
            "label": "玩法训练门槛",
            "value": f"{play.get('trainable_count', 0)}/{play.get('total_count', 0)}",
            "tone": "success" if bool(play.get("all_trainable")) else "warning",
            "detail": f"ready={play.get('ready_count', 0)}/{play.get('total_count', 0)}",
            "action_key": "train_play_models" if bool(play.get("all_trainable")) and not bool(play.get("all_ready")) else "",
        },
    ]
    items = play.get("items", []) if isinstance(play.get("items"), list) else []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        rows.append(
            {
                "label": str(item.get("label") or item.get("key") or "-"),
                "value": "可训练" if bool(item.get("trainable")) else "未达标",
                "tone": "success" if bool(item.get("trainable")) else "warning",
                "detail": f"usable={item.get('usable_count', 0)}/{item.get('min_train_samples', 0)} | ready={bool(item.get('model_ready'))}",
                "action_key": "",
            }
        )
    return rows[: max(0, int(limit))]


def _statsbomb_no_overlap_fallback_lines(plan: Mapping[str, object] | object, *, limit: int = 3) -> list[str]:
    resolved = plan if isinstance(plan, Mapping) else {}
    fallback = resolved.get("no_overlap_fallback") if isinstance(resolved.get("no_overlap_fallback"), Mapping) else {}
    if not isinstance(fallback, Mapping) or not fallback:
        return []
    lines = [
        "StatsBomb无重叠兜底",
        f"- 状态: {fallback.get('status', '-')} | reason={fallback.get('reason', '-')}",
        f"- 说明: {fallback.get('message', '-')}",
        f"- 可安全使用: {fallback.get('safe_use', '-')}",
    ]
    actions = [row for row in fallback.get("actions", []) if isinstance(row, Mapping)] if isinstance(fallback.get("actions"), list) else []
    for row in actions[: max(0, int(limit))]:
        lines.append(f"- {row.get('label', '-')}: {row.get('detail', '-')}")
    return lines


def build_training_health_repair_result_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    payload = resolved.get("result", {}) if isinstance(resolved.get("result"), Mapping) else {}
    gate = resolved.get("training_gate", {}) if isinstance(resolved.get("training_gate"), Mapping) else {}
    action_key = str(resolved.get("action_key") or "")
    plan_line = ""
    import_line = ""
    review_line = ""
    if action_key in {"build_statsbomb_coverage_import_plan", "execute_statsbomb_coverage_import_plan"} and isinstance(payload, Mapping):
        plan_line = (
            f"- 计划: {payload.get('target_date_start', '-')} -> {payload.get('target_date_end', '-')} | "
            f"next={payload.get('next_step', payload.get('plan_next_step', '-'))}\n"
        )
    if action_key == "execute_statsbomb_coverage_import_plan" and isinstance(payload, Mapping):
        import_line = (
            f"- 导入: competitions={len(payload.get('import_runs', []) if isinstance(payload.get('import_runs'), list) else [])} | "
            f"records={payload.get('imported_records', '-')} | output={payload.get('output_records', '-')}\n"
        )
        review_line = (
            f"- 复盘: samples={payload.get('sample_count', '-')} | missing={payload.get('skipped_missing_statsbomb', '-')} | "
            f"unknown={payload.get('skipped_unknown_label', '-')}\n"
        )
    return (
        f"训练健康修复: {'完成' if bool(resolved.get('ok', True)) else '未完成'}\n"
        + f"- 动作: {training_health_action_button_text(resolved.get('action_key'))}\n"
        + f"- 状态: {resolved.get('before_status') or '-'} -> {resolved.get('after_status') or '-'}\n"
        + f"- 结果: {resolved.get('message') or '-'}\n"
        + f"- 样本: imported={payload.get('imported_samples', '-')} | saved={payload.get('saved_total', '-')} | profiles={payload.get('league_profile_count', '-')}\n"
        + plan_line
        + import_line
        + review_line
        + f"- 复检: {gate.get('status', '-')} | 建议: {gate.get('recommendation', '-')}"
    )


def build_model_training_overview_text(
    *,
    xgb_status: Mapping[str, object] | object,
    play_model_status: Mapping[str, object] | object,
    ensemble_status: Mapping[str, object] | object,
    bayes_status: Mapping[str, object] | object,
    threshold_status: Mapping[str, object] | object,
    policy_status: Mapping[str, object] | object,
    coverage_status: Mapping[str, object] | object,
    training_gate_status: Mapping[str, object] | object | None = None,
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
    statsbomb = coverage.get("statsbomb_events", {}) if isinstance(coverage, Mapping) else {}
    statsbomb_coverage_plan = statsbomb.get("coverage_import_plan", {}) if isinstance(statsbomb.get("coverage_import_plan"), Mapping) else {}
    rating_pools = coverage.get("rating_pools", {}) if isinstance(coverage, Mapping) else {}
    fact_coverage = coverage.get("fact_coverage", {}) if isinstance(coverage.get("fact_coverage"), Mapping) else {}
    match_fact = fact_coverage.get("match_fact", {}) if isinstance(fact_coverage.get("match_fact"), Mapping) else {}
    action_fact = fact_coverage.get("action_fact", {}) if isinstance(fact_coverage.get("action_fact"), Mapping) else {}
    source_provenance = fact_coverage.get("source_provenance", {}) if isinstance(fact_coverage.get("source_provenance"), Mapping) else {}
    trace_fact_refs = fact_coverage.get("trace_fact_refs", {}) if isinstance(fact_coverage.get("trace_fact_refs"), Mapping) else {}
    training_health = coverage.get("training_health", {}) if isinstance(coverage.get("training_health"), Mapping) else {}
    health_issues = training_health.get("issues", []) if isinstance(training_health.get("issues"), list) else []
    health_issue_lines = []
    for index, issue in enumerate([row for row in health_issues if isinstance(row, Mapping)][:3], start=1):
        health_issue_lines.append(
            f"- 健康问题{index}: [{issue.get('severity', '-')}] {issue.get('message', '-')} | 建议: {issue.get('recommendation', '-')}"
        )
    if not health_issue_lines:
        health_issue_lines.append("- 健康问题: -")
    health_card_lines = [
        f"- {row.get('label', '-')}: {row.get('value', '-')} | {row.get('detail', '-')}"
        for row in build_training_health_card_rows(coverage)
    ]
    health_action_lines = [
        f"- {row.get('label', '-')}: {row.get('value', '-')} | {row.get('detail', '-')}"
        for row in build_training_health_action_rows(coverage)
    ]
    statsbomb_fallback_lines = _statsbomb_no_overlap_fallback_lines(statsbomb_coverage_plan)
    training_gate_lines = [
        f"- {row.get('label', '-')}: {row.get('value', '-')} | {row.get('detail', '-')}"
        for row in build_training_model_gate_rows(training_gate_status)
    ] if isinstance(training_gate_status, Mapping) else ["- 门槛状态: -"]

    lines = [
        "模型训练状态总览",
        "",
        "训练数据",
        f"- XGB样本: {samples.get('sample_count', 0)} | 有效特征: {samples.get('valid_feature_count', 0)} | 联赛覆盖: {samples.get('league_count', 0)}",
        f"- 样本时间: {samples.get('date_start') or '-'} -> {samples.get('date_end') or '-'}",
        f"- 联赛样例: {', '.join(samples.get('league_examples', []) or []) or '-'}",
        f"- 联赛历史: {club_history.get('match_count', 0)} 场 | {club_history.get('date_start') or '-'} -> {club_history.get('date_end') or '-'} | profile={club_history.get('league_profile_count', 0)}",
        f"- 世界杯历史: {world_cup.get('match_count', 0)} 场 | {world_cup.get('year_start') or '-'}-{world_cup.get('year_end') or '-'} | 届数={world_cup.get('year_count', 0)}",
        f"- StatsBomb事件: {statsbomb.get('match_count', 0)} 场 | 复盘样本={statsbomb.get('review_sample_count', 0)} | 特征={statsbomb.get('review_feature_count', 0)} | 覆盖缺口={statsbomb.get('coverage_gap_count', 0)} | 候选={statsbomb.get('coverage_candidate_count', 0)}",
        f"- StatsBomb覆盖计划: {statsbomb_coverage_plan.get('status', '-')}",
        *statsbomb_fallback_lines,
        f"- Fact Layer: MatchFact={match_fact.get('available_count', 0)}/{match_fact.get('target_count', 0)} ({_safe_float(match_fact.get('coverage_ratio'), 0.0):.1%}) | ActionFact={action_fact.get('available_match_count', 0)}/{action_fact.get('target_match_count', 0)} ({action_fact.get('event_count', 0)} events) | SourceProvenance={_safe_float(source_provenance.get('coverage_ratio'), 0.0):.1%} | TraceRefs={_safe_float(trace_fact_refs.get('trace_fact_ref_coverage_ratio'), 0.0):.1%}",
        f"- ELO评分池: 俱乐部 {rating_pools.get('club_team_count', 0)} 队 | 国家队 {rating_pools.get('national_team_count', 0)} 队",
        f"- 训练健康: {training_health.get('status', '-')} | blocking={training_health.get('blocking_count', 0)} | warning={training_health.get('warning_count', 0)}",
        *health_issue_lines,
        "",
        "训练健康卡片",
        *health_card_lines,
        "",
        "优先补数建议",
        *health_action_lines,
        "",
        "训练门槛联动",
        *training_gate_lines,
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
    effective_policy = resolved.get("effective_policy", {}) if isinstance(resolved, Mapping) else {}
    display_policy = effective_policy if isinstance(effective_policy, Mapping) and effective_policy else policy
    scoreline_policy = display_policy.get("scoreline", {}) if isinstance(display_policy, Mapping) else {}
    total_goals_policy = display_policy.get("total_goals", {}) if isinstance(display_policy, Mapping) else {}
    raw_scoreline_policy = policy.get("scoreline", {}) if isinstance(policy, Mapping) else {}
    raw_total_goals_policy = policy.get("total_goals", {}) if isinstance(policy, Mapping) else {}
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
        f"raw takeover {bool(raw_total_goals_policy.get('takeover_enabled'))} | effective takeover {total_goals_enabled}\n"
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
        f"raw takeover {bool(raw_scoreline_policy.get('takeover_enabled'))} | effective takeover {scoreline_enabled}\n"
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


def _takeover_gate_from_status(status: Mapping[str, object] | object) -> Mapping[str, object]:
    resolved = status if isinstance(status, Mapping) else {}
    if isinstance(resolved.get("takeover_gate"), Mapping):
        return resolved.get("takeover_gate", {})  # type: ignore[return-value]
    if str(resolved.get("mode") or "") == "watch_only" and "metrics" in resolved:
        return resolved
    return {}


def _takeover_gate_tone(status: object) -> str:
    value = str(status or "").strip().lower()
    if value == "allow":
        return "good"
    if value == "watch":
        return "warning"
    if value == "block":
        return "danger"
    return "neutral"


def build_play_model_takeover_gate_rows(status: Mapping[str, object] | object) -> list[dict[str, str]]:
    gate = _takeover_gate_from_status(status)
    if not gate:
        return [
            {
                "title": "Takeover gate: not evaluated",
                "body": "Run play-model backtest to produce allow/watch/block takeover governance.",
                "tone": "neutral",
            }
        ]
    metrics = gate.get("metrics", {}) if isinstance(gate.get("metrics"), Mapping) else {}
    issues = gate.get("issues", []) if isinstance(gate.get("issues"), list) else []
    status_text = str(gate.get("status") or "-")
    rows = [
        {
            "title": f"Takeover gate: {status_text.upper()}",
            "body": (
                f"mode {gate.get('mode') or '-'} | policy_impact {gate.get('policy_impact') or '-'}\n"
                f"training_gate {metrics.get('training_gate_status') or '-'} | "
                f"samples {metrics.get('validation_sample_count', 0)}/{metrics.get('min_validation_samples', 0)}\n"
                f"total_goals_delta {_safe_float(metrics.get('total_goals_model_delta'), 0.0):+.2%} | "
                f"score_delta {_safe_float(metrics.get('score_model_delta'), 0.0):+.2%}\n"
                f"recommendation: {gate.get('recommendation') or '-'}"
            ),
            "tone": _takeover_gate_tone(status_text),
        }
    ]
    for item in issues[:3]:
        if not isinstance(item, Mapping):
            continue
        severity = str(item.get("severity") or "-")
        rows.append(
            {
                "title": f"{severity}: {item.get('code') or '-'}",
                "body": f"{item.get('message') or '-'}\nrecommendation: {item.get('recommendation') or '-'}",
                "tone": "danger" if severity == "blocking" else "warning" if severity == "warning" else "neutral",
            }
        )
    return rows


def build_play_model_takeover_gate_action_rows(
    status: Mapping[str, object] | object,
    *,
    limit: int = 5,
) -> list[dict[str, str]]:
    gate = _takeover_gate_from_status(status)
    if not gate:
        return [
            {
                "title": "Run play-model backtest",
                "body": "No takeover gate result yet. Generate allow/watch/block decision first.",
                "action_key": "run_play_model_backtest",
                "tone": "neutral",
            }
        ][: max(0, int(limit))]

    gate_status = str(gate.get("status") or "").strip().lower()
    issues = gate.get("issues", []) if isinstance(gate.get("issues"), list) else []
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def _append_action(title: str, body: str, action_key: str, tone: str) -> None:
        if action_key in seen:
            return
        seen.add(action_key)
        rows.append(
            {
                "title": title,
                "body": body,
                "action_key": action_key,
                "tone": tone,
            }
        )

    issue_map = {
        "validation_sample_count_low": [
            ("Expand validation samples", "Increase validation horizon to improve takeover confidence.", "run_play_model_backtest", "warning"),
            ("Import historical samples", "Import and merge historical samples, then rerun backtest.", "import_historical_samples", "warning"),
        ],
        "score_model_regression": [
            ("Retrain scoreline model", "Score model regressed; retrain and verify holdout stability.", "train_play_models", "danger"),
            ("Pause scoreline takeover", "Keep scoreline model in shadow/watch until regression is resolved.", "pause_scoreline_takeover", "danger"),
        ],
        "total_goals_model_no_uplift": [
            ("Continue shadow mode", "Keep total-goals model as shadow evidence until uplift is positive.", "continue_shadow_watch", "warning"),
            ("Recalibrate total goals policy", "Rerun total-goals calibration and compare against current policy.", "calibrate_play_model_policy", "warning"),
        ],
        "training_gate_not_ready": [
            ("Fix training gate first", "Resolve training gate blockers before formal takeover review.", "refresh_training_health", "danger"),
        ],
    }

    for item in issues:
        if not isinstance(item, Mapping):
            continue
        issue_code = str(item.get("code") or "")
        for action in issue_map.get(issue_code, []):
            _append_action(*action)

    if gate_status == "allow":
        _append_action(
            "Calibrate takeover policy",
            "Gate is allow. Run policy calibration to update takeover thresholds.",
            "calibrate_play_model_policy",
            "good",
        )
        _append_action(
            "Start formal takeover review",
            "Proceed with guarded formal takeover review and monitor audit transitions.",
            "review_formal_takeover",
            "good",
        )
        _append_action(
            "Export gate audit report",
            "Export markdown/csv audit report for long-horizon stability review.",
            "export_play_model_takeover_gate_audit_report",
            "good",
        )
    elif gate_status == "watch":
        _append_action(
            "Continue shadow observation",
            "Keep formal takeover disabled and collect another stable backtest window.",
            "continue_shadow_watch",
            "warning",
        )
        _append_action(
            "Retrain play models",
            "Retrain play models before next takeover decision checkpoint.",
            "train_play_models",
            "warning",
        )
    elif gate_status == "block":
        _append_action(
            "Keep takeover blocked",
            "Do not enter formal takeover until blocking issues are closed.",
            "continue_shadow_watch",
            "danger",
        )

    if not rows:
        _append_action(
            "Run play-model backtest",
            "No specific issue mapping found. Re-run backtest and review gate details.",
            "run_play_model_backtest",
            "neutral",
        )
    _append_action(
        "Export gate audit report",
        "Export markdown/csv audit report for long-horizon stability review.",
        "export_play_model_takeover_gate_audit_report",
        "neutral",
    )
    return rows[: max(0, int(limit))]


def build_play_model_takeover_gate_audit_rows(status: Mapping[str, object] | object) -> list[dict[str, str]]:
    resolved = status if isinstance(status, Mapping) else {}
    history = resolved.get("takeover_gate_history", []) if isinstance(resolved, Mapping) else []
    audit = resolved.get("takeover_gate_audit", {}) if isinstance(resolved.get("takeover_gate_audit"), Mapping) else {}
    history_items = [item for item in history if isinstance(item, Mapping)] if isinstance(history, list) else []
    history_count = _safe_int(resolved.get("takeover_gate_history_count"), _safe_int(audit.get("history_count"), len(history_items)))
    if not history_items:
        return [
            {
                "title": "Takeover gate audit: no transitions",
                "body": f"history_source {resolved.get('takeover_gate_history_source') or '-'}",
                "tone": "neutral",
            }
        ]
    latest = history_items[0]
    latest_metrics = latest.get("metrics", {}) if isinstance(latest.get("metrics"), Mapping) else {}
    latest_validation = latest.get("validation", {}) if isinstance(latest.get("validation"), Mapping) else {}
    latest_status = str(latest.get("status") or audit.get("latest_status") or "-")
    latest_samples = _safe_int(
        latest_metrics.get("validation_sample_count"),
        _safe_int(latest_validation.get("sample_count"), _safe_int(audit.get("latest_validation_sample_count"))),
    )
    latest_total_delta = _safe_float(
        latest_metrics.get("total_goals_model_delta"),
        _safe_float(audit.get("latest_total_goals_model_delta"), 0.0),
    )
    latest_score_delta = _safe_float(
        latest_metrics.get("score_model_delta"),
        _safe_float(audit.get("latest_score_model_delta"), 0.0),
    )
    rows = [
        {
            "title": f"Takeover gate audit: {history_count} transition(s)",
            "body": (
                f"latest {latest.get('transition') or audit.get('latest_transition') or '-'} | "
                f"reason {latest.get('reason') or audit.get('latest_reason') or '-'} | updated {latest.get('updated_at') or audit.get('latest_updated_at') or '-'}\n"
                f"samples {latest_samples} | total_goals_delta {latest_total_delta:+.2%} | score_delta {latest_score_delta:+.2%}\n"
                f"policy_impact {latest.get('policy_impact') or audit.get('latest_policy_impact') or '-'} | report {latest.get('report_path') or audit.get('latest_report_path') or '-'}"
            ),
            "tone": _takeover_gate_tone(latest_status),
        }
    ]
    for item in history_items[1:3]:
        status_text = str(item.get("status") or "-")
        rows.append(
            {
                "title": f"Previous gate transition: {item.get('transition') or '-'}",
                "body": f"reason {item.get('reason') or '-'} | updated {item.get('updated_at') or '-'} | impact {item.get('policy_impact') or '-'}",
                "tone": _takeover_gate_tone(status_text),
            }
        )
    return rows


def build_play_model_takeover_gate_audit_overview_text(status: Mapping[str, object] | object) -> str:
    resolved = status if isinstance(status, Mapping) else {}
    history = resolved.get("takeover_gate_history", []) if isinstance(resolved, Mapping) else []
    audit = resolved.get("takeover_gate_audit", {}) if isinstance(resolved.get("takeover_gate_audit"), Mapping) else {}
    report = resolved.get("takeover_gate_audit_report", {}) if isinstance(resolved.get("takeover_gate_audit_report"), Mapping) else {}
    history_items = [item for item in history if isinstance(item, Mapping)] if isinstance(history, list) else []
    latest_history = history_items[0] if history_items else {}
    history_count = _safe_int(
        resolved.get("takeover_gate_history_count"),
        _safe_int(audit.get("history_count"), _safe_int(report.get("history_count"), len(history_items))),
    )
    latest_transition = str(report.get("latest_transition") or audit.get("latest_transition") or latest_history.get("transition") or "-")
    latest_status = str(audit.get("latest_status") or report.get("latest_status") or latest_history.get("status") or "-")
    latest_reason = str(report.get("latest_reason") or audit.get("latest_reason") or latest_history.get("reason") or "-")
    latest_updated_at = str(report.get("updated_at") or audit.get("latest_updated_at") or latest_history.get("updated_at") or "-")
    markdown_path = str(report.get("markdown_path") or audit.get("latest_report_path") or latest_history.get("report_path") or "-")
    csv_path = str(report.get("csv_path") or audit.get("latest_csv_path") or "-")
    history_source = str(resolved.get("takeover_gate_history_source") or resolved.get("history_source") or "-")
    return (
        "接管审计概览\n"
        + f"- 历史转场: {history_count}\n"
        + f"- 最新转场: {latest_transition}\n"
        + f"- 最新状态: {latest_status}\n"
        + f"- 最新原因: {latest_reason}\n"
        + f"- 更新时间: {latest_updated_at}\n"
        + f"- Markdown: {markdown_path}\n"
        + f"- CSV: {csv_path}\n"
        + f"- 历史源: {history_source}"
    )


def build_play_model_takeover_gate_audit_export_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    if not bool(resolved.get("ok")):
        return f"接管守门审计导出失败 | {resolved.get('reason') or '-'}"
    return (
        f"接管守门审计已导出 | transitions {int(resolved.get('history_count', 0) or 0)} | "
        f"{resolved.get('markdown_path') or '-'}"
    )


def build_play_model_takeover_gate_audit_export_message(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    if not bool(resolved.get("ok")):
        return f"接管守门审计报告导出未完成\n原因: {resolved.get('reason') or '-'}"
    summary = resolved.get("summary", {}) if isinstance(resolved.get("summary"), Mapping) else {}
    return (
        "接管守门审计报告已导出\n"
        + f"- Transitions: {int(resolved.get('history_count', 0) or 0)}\n"
        + f"- Latest: {summary.get('latest_transition') or '-'} | {summary.get('latest_status') or '-'}\n"
        + f"- Reason: {summary.get('latest_reason') or '-'}\n\n"
        + f"Markdown:\n{resolved.get('markdown_path') or '-'}\n\n"
        + f"CSV:\n{resolved.get('csv_path') or '-'}"
    )


def build_train_play_models_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    trained = bool(resolved.get("trained"))
    total_result = resolved.get("total_goals", {}) if isinstance(resolved, Mapping) else {}
    score_result = resolved.get("scoreline", {}) if isinstance(resolved, Mapping) else {}
    volatile_result = resolved.get("volatile_scoreline", {}) if isinstance(resolved, Mapping) else {}
    auto_backtest = resolved.get("auto_backtest", {}) if isinstance(resolved.get("auto_backtest"), Mapping) else {}
    backtest_text = ""
    if auto_backtest:
        takeover_gate = auto_backtest.get("takeover_gate", {}) if isinstance(auto_backtest.get("takeover_gate"), Mapping) else {}
        backtest_text = f" | 自动回测={'完成' if bool(auto_backtest.get('ok')) else '未完成'}"
        if takeover_gate.get("status"):
            backtest_text += f" | gate={takeover_gate.get('status')}"
    return (
        f"玩法模型{'完成' if trained else '未执行'} | 总进球={total_result.get('reason', '-')} | "
        f"比分={score_result.get('reason', '-')} | 高波动={volatile_result.get('reason', '-')}{backtest_text}"
    )


def build_train_play_models_apply_message(result: Mapping[str, object] | object, model_status_text: str) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    trained = bool(resolved.get("trained"))
    total_result = resolved.get("total_goals", {}) if isinstance(resolved, Mapping) else {}
    score_result = resolved.get("scoreline", {}) if isinstance(resolved, Mapping) else {}
    volatile_result = resolved.get("volatile_scoreline", {}) if isinstance(resolved, Mapping) else {}
    auto_backtest = resolved.get("auto_backtest", {}) if isinstance(resolved.get("auto_backtest"), Mapping) else {}
    postcheck = resolved.get("postcheck", {}) if isinstance(resolved.get("postcheck"), Mapping) else {}
    auto_backtest_text = ""
    if auto_backtest or postcheck:
        takeover_gate = auto_backtest.get("takeover_gate", {}) if isinstance(auto_backtest.get("takeover_gate"), Mapping) else {}
        takeover_gate_text = ""
        if takeover_gate:
            takeover_gate_text = (
                f"- Takeover gate: {takeover_gate.get('status') or '-'} | "
                f"{takeover_gate.get('recommendation') or '-'}\n"
            )
        auto_backtest_text = (
            "\n训练后复检\n"
            + f"- 状态: {postcheck.get('status') or '-'}\n"
            + f"- 建议: {postcheck.get('recommendation') or '-'}\n"
            + f"- 自动回测: {'已执行' if bool(auto_backtest.get('executed')) else '未执行'} | ok={bool(auto_backtest.get('ok'))} | {auto_backtest.get('reason') or '-'}\n"
            + takeover_gate_text
            + f"- 回测报告: {auto_backtest.get('report_path') or '-'}\n"
            + f"- 闭环报告: {postcheck.get('report_path') or '-'}\n\n"
        )
    return (
        f"玩法模型训练: {'完成' if trained else '未执行'}\n"
        + f"- 总进球: {total_result.get('reason', '-')} | 可用样本={total_result.get('usable_count', 0)} | 更新时间={total_result.get('updated_at') or '-'}\n"
        + f"- 比分: {score_result.get('reason', '-')} | 可用样本={score_result.get('usable_count', 0)} | 更新时间={score_result.get('updated_at') or '-'}\n"
        + f"- 高波动比分: {volatile_result.get('reason', '-')} | 可用样本={volatile_result.get('usable_count', 0)} | 更新时间={volatile_result.get('updated_at') or '-'}\n\n"
        + auto_backtest_text
        + model_status_text
    )


def build_play_model_backtest_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    ok = bool(resolved.get("ok"))
    improvement = resolved.get("improvement", {}) if isinstance(resolved, Mapping) else {}
    takeover_gate = resolved.get("takeover_gate", {}) if isinstance(resolved.get("takeover_gate"), Mapping) else {}
    gate_text = f" | gate {takeover_gate.get('status')}" if takeover_gate.get("status") else ""
    return (
        f"玩法回测{'完成' if ok else '失败'} | 让球 {float(improvement.get('handicap_shadow_delta', 0) or 0):+.2%} | "
        f"总进球 {float(improvement.get('total_goals_model_delta', 0) or 0):+.2%} | 比分 {float(improvement.get('score_model_delta', 0) or 0):+.2%}{gate_text}"
    )


def build_play_model_backtest_success_message(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved, Mapping) else {}
    report_path = resolved.get("report_path") or "-"
    takeover_gate = resolved.get("takeover_gate", {}) if isinstance(resolved.get("takeover_gate"), Mapping) else {}
    takeover_gate_text = ""
    if takeover_gate:
        takeover_gate_text = (
            "\n\nTakeover gate\n"
            + f"- Status: {takeover_gate.get('status') or '-'}\n"
            + f"- Mode: {takeover_gate.get('mode') or '-'}\n"
            + f"- Recommendation: {takeover_gate.get('recommendation') or '-'}"
        )
    return (
        "玩法回测完成\n"
        + f"验证样本: {validation.get('sample_count', 0)}\n"
        + f"时间区间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}\n\n"
        + f"让球: baseline {float(metrics.get('handicap_baseline', {}).get('accuracy', 0) or 0):.2%} | current {float(metrics.get('handicap_current', {}).get('accuracy', 0) or 0):.2%} | shadow {float(metrics.get('handicap_shadow', {}).get('accuracy', 0) or 0):.2%}\n"
        + f"总进球: baseline {float(metrics.get('total_goals_baseline', {}).get('accuracy', 0) or 0):.2%} | current {float(metrics.get('total_goals_current', {}).get('accuracy', 0) or 0):.2%} | model {float(metrics.get('total_goals_model', {}).get('accuracy', 0) or 0):.2%}\n"
        + f"比分: baseline {float(metrics.get('score_baseline', {}).get('accuracy', 0) or 0):.2%} | current {float(metrics.get('score_current', {}).get('accuracy', 0) or 0):.2%} | model {float(metrics.get('score_model', {}).get('accuracy', 0) or 0):.2%}\n"
        + f"高波动专用: {float(metrics.get('score_volatile_model_volatile', {}).get('accuracy', 0) or 0):.2%} ({int(metrics.get('score_volatile_model_volatile', {}).get('hits', 0) or 0)}/{int(metrics.get('score_volatile_model_volatile', {}).get('total', 0) or 0)})\n\n"
        + f"报告: {report_path}"
        + takeover_gate_text
    )


def build_draw_specialist_backtest_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    summary = resolved.get("summary", {}) if isinstance(resolved.get("summary"), Mapping) else {}
    validation = resolved.get("validation", {}) if isinstance(resolved.get("validation"), Mapping) else {}
    guard = summary.get("guard", {}) if isinstance(summary.get("guard"), Mapping) else {}
    takeover = summary.get("takeover", {}) if isinstance(summary.get("takeover"), Mapping) else {}
    guard_policy_text = _draw_guard_policy_text(resolved)
    policy = resolved.get("draw_release_guard_policy")
    if not isinstance(policy, Mapping):
        policy = summary.get("draw_release_guard_policy") if isinstance(summary.get("draw_release_guard_policy"), Mapping) else {}
    min_score = _safe_float(policy.get("min_score"), 0.58) if isinstance(policy, Mapping) else 0.58
    if not bool(resolved.get("ok")):
        return (
            "平局专项诊断\n"
            + f"- 状态: {resolved.get('reason', 'not_run')}\n"
            + "- 建议: 先运行一次平局专项回测，生成平局召回、误报和分层表现。"
        )
    return (
        "平局专项诊断\n"
        + f"- 更新时间: {resolved.get('updated_at') or '-'}\n"
        + f"- 验证样本: {validation.get('sample_count', 0)} | 时间: {validation.get('date_start') or '-'} -> {validation.get('date_end') or '-'}\n"
        + f"- 真实平局: {summary.get('actual_draw_count', 0)} ({summary.get('actual_draw_rate_text', '-')})\n"
        + f"- 正式博平: {summary.get('draw_hit_count', 0)}/{summary.get('predicted_draw_count', 0)} | 精确率 {summary.get('precision_text', '-')} | 召回 {summary.get('recall_text', '-')}\n"
        + f"- 防平信号(draw_score>={min_score:.2f}): 样本 {guard.get('sample_count', 0)} | 平局率 {guard.get('draw_rate_text', '-')} | lift {guard.get('lift_text', '-')}\n"
        + f"- draw_takeover: 样本 {takeover.get('sample_count', 0)} | 精确率 {takeover.get('precision_text', '-')} | 召回 {takeover.get('recall_text', '-')}\n"
        + f"- 漏判平局: {summary.get('missed_draw_count', 0)} | 误报平局: {summary.get('false_positive_count', 0)}\n"
        + f"- 建议: {summary.get('recommendation_text') or summary.get('recommendation') or '-'}\n"
        + f"- {guard_policy_text}\n"
        + f"- 报告: {resolved.get('report_path') or '-'}"
    )


def build_draw_specialist_backtest_apply_status_text(result: Mapping[str, object] | object) -> str:
    resolved = result if isinstance(result, Mapping) else {}
    summary = resolved.get("summary", {}) if isinstance(resolved.get("summary"), Mapping) else {}
    return (
        f"平局专项回测{'完成' if bool(resolved.get('ok')) else '失败'} | "
        f"样本 {summary.get('sample_count', 0)} | 精确 {summary.get('precision_text', '-')} | 召回 {summary.get('recall_text', '-')}"
    )


def build_draw_specialist_backtest_success_message(result: Mapping[str, object] | object) -> str:
    return build_draw_specialist_backtest_status_text(result)


def build_draw_specialist_backtest_card_rows(result: Mapping[str, object] | object) -> list[dict[str, str]]:
    resolved = result if isinstance(result, Mapping) else {}
    summary = resolved.get("summary", {}) if isinstance(resolved.get("summary"), Mapping) else {}
    guard = summary.get("guard", {}) if isinstance(summary.get("guard"), Mapping) else {}
    takeover = summary.get("takeover", {}) if isinstance(summary.get("takeover"), Mapping) else {}
    if not bool(resolved.get("ok")):
        return [
            {
                "title": "平局专项诊断: 未运行",
                "body": "点击平局诊断运行历史回测，生成平局精确率、召回率、漏判和误报分层。",
                "tone": "neutral",
            }
        ]
    recommendation = str(summary.get("recommendation") or "")
    tone = "good" if recommendation == "enable_draw_watch" else "warning" if recommendation in {"watch_draw_guard", "tighten_draw_takeover"} else "neutral"
    policy = resolved.get("draw_release_guard_policy")
    if not isinstance(policy, Mapping):
        policy = summary.get("draw_release_guard_policy") if isinstance(summary.get("draw_release_guard_policy"), Mapping) else {}
    min_score = _safe_float(policy.get("min_score"), 0.58) if isinstance(policy, Mapping) else 0.58
    return [
        {
            "title": f"平局识别: 精确 {summary.get('precision_text', '-')} / 召回 {summary.get('recall_text', '-')}",
            "body": (
                f"样本 {_safe_int(summary.get('sample_count'))} | 真实平局 {summary.get('actual_draw_count', 0)}"
                f"({summary.get('actual_draw_rate_text', '-')}) | 博平 {summary.get('draw_hit_count', 0)}/{summary.get('predicted_draw_count', 0)}\n"
                f"漏判 {summary.get('missed_draw_count', 0)} | 误报 {summary.get('false_positive_count', 0)} | 建议 {summary.get('recommendation', '-')}"
            ),
            "tone": tone,
        },
        {
            "title": f"防平信号: {guard.get('draw_rate_text', '-')} / lift {guard.get('lift_text', '-')}",
            "body": (
                f"draw_score>={min_score:.2f} 样本 {guard.get('sample_count', 0)} | 真实平局 {guard.get('actual_draw_count', 0)} | "
                f"正式博平 {takeover.get('sample_count', 0)}样本，精确 {takeover.get('precision_text', '-')}"
            ),
            "tone": "good" if _safe_float(guard.get("lift"), 0.0) > 0.03 else "warning" if _safe_int(guard.get("sample_count")) else "neutral",
        },
        {
            "title": "Draw release guard (watch-only)",
            "body": _draw_guard_policy_text(resolved),
            "tone": "warning" if "blocked_odds=-" not in _draw_guard_policy_text(resolved) else "neutral",
        },
    ]


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
    effective_policy = resolved.get("effective_policy", {}) if isinstance(resolved, Mapping) else {}
    if not isinstance(effective_policy, Mapping) or not effective_policy:
        effective_policy = policy
    scoreline = policy.get("scoreline", {}) if isinstance(policy, Mapping) else {}
    total_goals = policy.get("total_goals", {}) if isinstance(policy, Mapping) else {}
    effective_scoreline = effective_policy.get("scoreline", {}) if isinstance(effective_policy, Mapping) else {}
    effective_total_goals = effective_policy.get("total_goals", {}) if isinstance(effective_policy, Mapping) else {}
    metrics = resolved.get("metrics", {}) if isinstance(resolved, Mapping) else {}
    best = metrics.get("scoreline_best", {}) if isinstance(metrics, Mapping) else {}
    gate_status = str(_takeover_gate_from_status(resolved).get("status") or "").strip().lower()
    gate_blocked_text = (
        "- 当前接管被守门策略阻断\n"
        if bool(resolved.get("policy_blocked_by_gate")) or gate_status in {"block", "watch"}
        else ""
    )
    decision_rows = build_play_model_policy_decision_rows(resolved)
    decision_text = "\n".join(
        f"- {row.get('title', '-')}: {row.get('body', '-')}" for row in decision_rows
    )
    takeover_gate_rows = build_play_model_takeover_gate_rows(resolved)
    takeover_gate_text = "\n".join(
        f"- {row.get('title', '-')}: {row.get('body', '-')}" for row in takeover_gate_rows
    )
    takeover_gate_audit_rows = build_play_model_takeover_gate_audit_rows(resolved)
    takeover_gate_audit_text = "\n".join(
        f"- {row.get('title', '-')}: {row.get('body', '-')}" for row in takeover_gate_audit_rows
    )
    takeover_gate_action_rows = build_play_model_takeover_gate_action_rows(resolved, limit=5)
    takeover_gate_action_text = "\n".join(
        f"- {row.get('title', '-')}: {row.get('body', '-')} | action_key={row.get('action_key', '-')}"
        for row in takeover_gate_action_rows
    )
    takeover_gate_export = resolved.get("takeover_gate_audit_report", {}) if isinstance(resolved.get("takeover_gate_audit_report"), Mapping) else {}
    takeover_gate_export_text = (
        "\n\nTakeover gate exported report\n"
        + f"- Updated: {takeover_gate_export.get('updated_at') or '-'}\n"
        + f"- History count: {takeover_gate_export.get('history_count', 0)}\n"
        + f"- Latest transition: {takeover_gate_export.get('latest_transition') or '-'}\n"
        + f"- Markdown: {takeover_gate_export.get('markdown_path') or '-'}\n"
        + f"- CSV: {takeover_gate_export.get('csv_path') or '-'}"
        if takeover_gate_export
        else ""
    )
    return (
        "玩法接管策略\n"
        + f"- 更新时间: {resolved.get('updated_at') or '-'}\n"
        + f"- 版本: {resolved.get('version_id') or '-'}\n"
        + f"- 比分接管: enabled={scoreline.get('takeover_enabled')} | 常规同向={float(scoreline.get('regular_same_outcome_min_confidence', 0) or 0):.2f} | 常规跨向={scoreline.get('regular_cross_outcome_enabled')}@{float(scoreline.get('regular_cross_outcome_min_confidence', 0) or 0):.2f}\n"
        + f"- 高波动确认: 同向={float(scoreline.get('volatile_same_outcome_min_confidence', 0) or 0):.2f} | 跨向={scoreline.get('volatile_cross_outcome_enabled')}@{float(scoreline.get('volatile_cross_outcome_min_confidence', 0) or 0):.2f}\n"
        + f"- 总进球接管: enabled={total_goals.get('takeover_enabled')} | min_conf={float(total_goals.get('min_confidence', 0) or 0):.2f}\n"
        + f"- 联合最优: 比分={int(best.get('score_hits', 0) or 0)}/{int(best.get('score_covered', 0) or 0)} ({float(best.get('score_accuracy', 0) or 0):.2%}) | 总进球={int(best.get('total_goals_hits', 0) or 0)}/{int(best.get('total_goals_covered', 0) or 0)} ({float(best.get('total_goals_accuracy', 0) or 0):.2%}) | combined={int(best.get('combined_hits', 0) or 0)}\n"
        + "\nPolicy gate execution\n"
        + gate_blocked_text
        + f"- Raw scoreline takeover: enabled={scoreline.get('takeover_enabled')}\n"
        + f"- Effective scoreline takeover: enabled={effective_scoreline.get('takeover_enabled')}\n"
        + f"- Raw total goals takeover: enabled={total_goals.get('takeover_enabled')} | min_conf={float(total_goals.get('min_confidence', 0) or 0):.2f}\n"
        + f"- Effective total goals takeover: enabled={effective_total_goals.get('takeover_enabled')} | min_conf={float(effective_total_goals.get('min_confidence', 0) or 0):.2f}\n"
        + "\nTakeover decisions\n"
        + decision_text
        + "\n\nTakeover gate\n"
        + takeover_gate_text
        + "\n\nTakeover gate audit\n"
        + takeover_gate_audit_text
        + "\n\nTakeover gate actions\n"
        + takeover_gate_action_text
        + takeover_gate_export_text
    )
