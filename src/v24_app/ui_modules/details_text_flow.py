from __future__ import annotations

from typing import Any, Callable, Mapping


def build_diagnostics_text(
    *,
    diagnostics: Any,
    snapshot_migration_report: Mapping[str, object] | object,
    xgb_status: Mapping[str, object] | object,
) -> str:
    source_guard = "通过" if getattr(diagnostics, "fixture_source_guard", False) else "未通过"
    page_guard = "通过" if getattr(diagnostics, "fixture_page_guard", False) else "未通过"
    cache_fresh = "是" if getattr(diagnostics, "cache_fresh", False) else "否"
    lines = [
        "V24 取数诊断",
        f"- 时间: {getattr(diagnostics, 'fetched_at', None) or '未知'}",
        f"- 数据源: {getattr(diagnostics, 'source', '-')}",
        f"- fixture_source_guard: {source_guard}",
        f"- fixture_page_guard: {page_guard}",
        f"- cache_fresh: {cache_fresh}",
        "",
        "诊断消息",
    ]
    messages = getattr(diagnostics, "messages", None) or []
    if messages:
        lines.extend(f"- {message}" for message in messages)
    else:
        lines.append("- 暂无诊断信息")

    migration = snapshot_migration_report if isinstance(snapshot_migration_report, Mapping) else {}
    if migration:
        lines.extend(
            [
                "",
                "快照迁移",
                f"- total_snapshots: {migration.get('total_snapshots', 0)}",
                f"- already_bound: {migration.get('already_bound', 0)}",
                f"- resolved: {migration.get('resolved', 0)}",
                f"- unresolved: {migration.get('unresolved', 0)}",
            ]
        )

    status = xgb_status if isinstance(xgb_status, Mapping) else {}
    label_counts = status.get("label_counts", {}) if isinstance(status, Mapping) else {}
    lines.extend(
        [
            "",
            "XGBoost样本状态",
            f"- sample_count: {status.get('sample_count', 0)}",
            f"- valid_feature_count: {status.get('valid_feature_count', 0)}",
            f"- labels(主/平/客): {label_counts.get(0, 0)}/{label_counts.get(1, 0)}/{label_counts.get(2, 0)}",
            f"- model_ready: {status.get('model_ready')}",
            f"- model_updated_at: {status.get('model_updated_at') or '-'}",
        ]
    )
    return "\n".join(lines)


def build_pending_match_details_text(*, diagnostics_text: str, match: Any) -> str:
    return (
        diagnostics_text
        + "\n\n"
        + "当前选中赛事\n"
        + f"- 对阵: {getattr(match, 'home_team', '-')} vs {getattr(match, 'away_team', '-')}\n"
        + f"- 联赛: {getattr(match, 'league', '-')}\n"
        + f"- 时间: {getattr(match, 'match_date', '-')} {getattr(match, 'match_time', '-')}\n"
        + f"- 赔率: 主胜 {float(getattr(match, 'odds_home', 0) or 0):.2f} / 平局 {float(getattr(match, 'odds_draw', 0) or 0):.2f} / 客胜 {float(getattr(match, 'odds_away', 0) or 0):.2f}\n\n"
        + "点击“分析选中”即可生成预测。"
    )


def build_poisson_block(poisson: Mapping[str, object] | object) -> str:
    resolved = poisson if isinstance(poisson, Mapping) else {}
    top_scores = resolved.get("top_scores", [])
    top_total_goals = resolved.get("top_total_goals", [])
    htft_top = resolved.get("htft_top", [])
    halftime = resolved.get("halftime_probabilities", {}) if isinstance(resolved, Mapping) else {}

    score_lines = [f"  - {item.get('score', '-')} ({item.get('probability', 0):.1%})" for item in top_scores[:3]]
    goal_lines = [f"  - {item.get('goals', '-')}球 ({item.get('probability', 0):.1%})" for item in top_total_goals[:3]]
    htft_lines = [f"  - {item.get('label', '-')} ({item.get('probability', 0):.1%})" for item in htft_top[:3]]

    score_text = "\n".join(score_lines) if score_lines else "  - -"
    goal_text = "\n".join(goal_lines) if goal_lines else "  - -"
    htft_text = "\n".join(htft_lines) if htft_lines else "  - -"

    return (
        "Poisson 分布预测\n"
        + f"- 主队进球均值: {resolved.get('home_lambda', 0):.3f}\n"
        + f"- 客队进球均值: {resolved.get('away_lambda', 0):.3f}\n"
        + f"- 半场主/平/客: {halftime.get('home', 0):.1%} / {halftime.get('draw', 0):.1%} / {halftime.get('away', 0):.1%}\n"
        + f"- BTTS(是): {resolved.get('btts_yes', 0):.1%}\n"
        + f"- BTTS(否): {resolved.get('btts_no', 0):.1%}\n"
        + "- 最可能总进球:\n"
        + goal_text
        + "\n- 最可能比分:\n"
        + score_text
        + "\n- 最可能半全场:\n"
        + htft_text
    )


def _format_play_items(items: object) -> str:
    if not isinstance(items, list) or not items:
        return "-"
    parts: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        play_type = str(item.get("play_type") or "-")
        pick = str(item.get("pick") or "-")
        confidence = float(item.get("confidence", 0) or 0)
        parts.append(f"{play_type}:{pick}({confidence:.1%})")
    return " / ".join(parts) if parts else "-"


def _build_confidence_calibration_block(prediction: Mapping[str, object]) -> str:
    calibration = prediction.get("confidence_calibration")
    if not isinstance(calibration, Mapping):
        return ""
    raw = float(calibration.get("raw_confidence", prediction.get("confidence_raw", prediction.get("confidence", 0))) or 0)
    calibrated = float(calibration.get("calibrated_confidence", prediction.get("confidence", 0)) or 0)
    scale = float(calibration.get("scale", 1.0) or 1.0)
    bucket = str(calibration.get("bin", "-"))
    bin_samples = int(calibration.get("bin_sample_count", 0) or 0)
    return (
        "\n\nConfidence Calibration\n"
        + f"- raw={raw:.1%} | calibrated={calibrated:.1%} | scale={scale:.2f}\n"
        + f"- bin={bucket} | bin_samples={bin_samples}"
    )


def _build_runtime_threshold_block(prediction: Mapping[str, object]) -> str:
    adjustment = prediction.get("play_threshold_adjustment")
    if not isinstance(adjustment, Mapping):
        return ""
    gate = adjustment.get("single_gate", {})
    per_play = adjustment.get("per_play", {})
    if not isinstance(gate, Mapping):
        gate = {}
    if not isinstance(per_play, Mapping):
        per_play = {}
    window = int(adjustment.get("window", 0) or 0)
    sample_count = int(adjustment.get("settlement_sample_count", 0) or 0)
    lines = [
        "",
        "Runtime Threshold Guard",
        f"- window={window} | settlements={sample_count}",
        (
            "- gate: "
            + f"hit={float(gate.get('hit_rate', 0) or 0):.1%}, "
            + f"expected={float(gate.get('expected_hit_rate', 0) or 0):.1%}, "
            + f"ev_bias={float(gate.get('ev_bias', 0) or 0):+.1%}, "
            + f"losing_streak={int(gate.get('losing_streak', 0) or 0)}, "
            + f"breaker={'ON' if bool(gate.get('breaker_on')) else 'OFF'}"
        ),
    ]
    for play_name in ("1x2", "handicap", "total_goals", "score", "htft"):
        item = per_play.get(play_name)
        if not isinstance(item, Mapping):
            continue
        old_thr = float(item.get("old", 0) or 0)
        new_thr = float(item.get("new", old_thr) or old_thr)
        delta = float(item.get("delta", new_thr - old_thr) or 0)
        reasons_raw = item.get("reasons", [])
        reasons = ",".join(str(x) for x in reasons_raw) if isinstance(reasons_raw, list) and reasons_raw else "-"
        marker = "*" if abs(delta) >= 1e-9 else " "
        lines.append(f"- {marker} {play_name}: {old_thr:.2f} -> {new_thr:.2f} ({delta:+.2f}) | reasons={reasons}")
    return "\n".join(lines)


def build_match_details_text(
    *,
    diagnostics_text: str,
    match: Any,
    prediction: Mapping[str, object],
    total_goals_pick: str,
    total_goals_conf: float,
    htft_pick: str,
    htft_conf: float,
    score_pick: str,
    score_conf: float,
    gated_recommendation: str,
    release_row: Mapping[str, object] | object,
    settlement: Mapping[str, object] | None,
    mark_text_fn: Callable[[object], str],
    poisson_block_text: str,
) -> str:
    probs = prediction.get("probabilities", {})
    market_probs = prediction.get("market_probabilities", {})
    elo_probs = prediction.get("elo_probabilities", {})
    poisson_probs = prediction.get("poisson_probabilities", {})
    xgb_probs = prediction.get("xgb_probabilities", {})
    handicap_pick = str(prediction.get("handicap_display") or prediction.get("handicap_recommendation") or "-")
    handicap_conf = float(prediction.get("handicap_confidence", 0) or 0)
    xgb_fallback = bool(prediction.get("xgb_fallback", True))
    xgb_ready = bool(prediction.get("xgb_model_ready", False))
    strength = prediction.get("elo", {})
    indices = prediction.get("indices", {})
    draw_score = float(prediction.get("draw_score", indices.get("draw_index", 0)) or 0)
    draw_grade = str(prediction.get("draw_grade") or "-")
    play_strategy = prediction.get("play_strategy", {}) if isinstance(prediction.get("play_strategy"), Mapping) else {}
    single_plays = play_strategy.get("single", [])
    parlay_plays = play_strategy.get("parlay", [])
    display_only_plays = play_strategy.get("display_only", [])
    high_strategy = prediction.get("high_accuracy_strategy", {}) if isinstance(prediction.get("high_accuracy_strategy"), Mapping) else {}

    settlement_block = ""
    if settlement is not None:
        settlement_block = (
            "\n赛果结算\n"
            + f"- 比分: {settlement.get('home_goals', 0)}-{settlement.get('away_goals', 0)}\n"
            + f"- 实际赛果: {settlement.get('result', '-')}\n"
            + f"- 赛前推荐: {settlement.get('predicted') or '-'}\n"
            + f"- 胜平负命中: {mark_text_fn(settlement.get('is_correct'))}\n"
            + f"- 让球玩法: {settlement.get('handicap_result') or '-'} | 预测 {settlement.get('predicted_handicap') or '-'} | 命中 {mark_text_fn(settlement.get('handicap_is_correct'))}\n"
            + f"- 总进球: {settlement.get('total_goals', '-')} | 预测 {settlement.get('predicted_total_goals') or '-'} | 命中 {mark_text_fn(settlement.get('total_goals_is_correct'))}\n"
            + f"- 比分预测: {settlement.get('predicted_score') or '-'} | 命中 {mark_text_fn(settlement.get('score_is_correct'))}\n"
            + f"- 半全场预测: {settlement.get('predicted_htft') or '-'}\n"
            + f"- ELO变动: 主队 {settlement.get('home_delta', 0):+} / 客队 {settlement.get('away_delta', 0):+}\n"
        )

    strategy_block = (
        "\n\n玩法策略\n"
        + f"- 单关可出手: {_format_play_items(single_plays)}\n"
        + f"- 串关可用: {_format_play_items(parlay_plays)}\n"
        + f"- 仅展示: {_format_play_items(display_only_plays)}"
    )
    high_strategy_block = ""
    if high_strategy.get("enabled"):
        active_items = high_strategy.get("active_matches", [])
        active_count = len(active_items) if isinstance(active_items, list) else int(high_strategy.get("active_count", 0) or 0)
        high_strategy_block = (
            "\n\n高准确率策略\n"
            + f"- 当前命中: {'是' if active_count > 0 else '否'} | 命中策略数 {active_count}\n"
            + f"- 玩法: {high_strategy.get('play_type', '-')} | 选择: {high_strategy.get('pick', '-')}\n"
            + f"- 置信度: {float(high_strategy.get('confidence', 0) or 0):.1%} / 门槛 {float(high_strategy.get('min_confidence', 0) or 0):.1%}\n"
            + f"- 历史命中: {float(high_strategy.get('backtest_accuracy', 0) or 0):.1%} ({int(high_strategy.get('backtest_hits', 0) or 0)}/{int(high_strategy.get('backtest_samples', 0) or 0)})\n"
            + f"- 策略摘要: {high_strategy.get('summary', '-')}\n"
            + f"- 原因: {high_strategy.get('reason', '-')}"
        )
    confidence_block = _build_confidence_calibration_block(prediction)
    runtime_threshold_block = _build_runtime_threshold_block(prediction)
    release = release_row if isinstance(release_row, Mapping) else {}
    release_block = ""
    if release:
        release_block = (
            "\n\nC1 放行门控\n"
            + f"- 正式建议: {'放行' if release.get('release_allowed') else '保留'}\n"
            + f"- 放行动作: {release.get('release_action', '-')}\n"
            + f"- 候选玩法: {release.get('top_play') or '-'}\n"
            + f"- 候选选择: {release.get('top_selection') or '-'}\n"
            + f"- 候选置信度: {float(release.get('top_confidence', 0) or 0):.1%}\n"
            + f"- 阵容源: {release.get('provider_name', '-')}\n"
        )

    return (
        diagnostics_text
        + "\n\n"
        + "比赛分析\n"
        + f"- 对阵: {getattr(match, 'home_team', '-')} vs {getattr(match, 'away_team', '-')}\n"
        + f"- 联赛: {getattr(match, 'league', '-')}\n"
        + f"- 开赛: {getattr(match, 'match_date', '-')} {getattr(match, 'match_time', '-')}\n"
        + f"- 数据源: {getattr(match, 'source', '-')}\n\n"
        + "结果摘要\n"
        + f"- V24推荐: {prediction['recommendation']}\n"
        + f"- 正式建议: {gated_recommendation}\n"
        + f"- 风险等级: {prediction['risk_level']}\n"
        + f"- 综合置信度: {prediction['confidence']:.1%}\n"
        + f"- 预计总进球: {prediction['expected_goals']:.2f}\n"
        + f"- 平局评分: {draw_score:.1%} ({draw_grade})\n\n"
        + "玩法预测维度\n"
        + f"- 让球预测: {handicap_pick} ({handicap_conf:.1%})\n"
        + f"- 总进球预测: {total_goals_pick} ({total_goals_conf:.1%})\n"
        + f"- 半全场预测: {htft_pick} ({htft_conf:.1%})\n"
        + f"- 比分预测: {score_pick} ({score_conf:.1%})\n\n"
        + "实力量化（ELO）\n"
        + f"- 主队评分: {strength.get('home_rating', 0):.1f} ({strength.get('home_score', 0):.1f}/100)\n"
        + f"- 客队评分: {strength.get('away_rating', 0):.1f} ({strength.get('away_score', 0):.1f}/100)\n"
        + f"- 评分差: {strength.get('rating_diff', 0):.1f}\n\n"
        + "多维指标\n"
        + f"- 冷门指数: {indices.get('upset_index', 0):.1%}\n"
        + f"- 稳定指数: {indices.get('stability_index', 0):.1%}\n"
        + f"- 信心指数: {indices.get('confidence_index', 0):.1%}\n\n"
        + "融合概率\n"
        + f"- 主胜: {probs['home']:.1%}\n"
        + f"- 平局: {probs['draw']:.1%}\n"
        + f"- 客胜: {probs['away']:.1%}\n\n"
        + poisson_block_text
        + strategy_block
        + high_strategy_block
        + confidence_block
        + runtime_threshold_block
        + release_block
        + "\n\n模型拆解\n"
        + f"- 市场主/平/客: {market_probs.get('home', 0):.1%} / {market_probs.get('draw', 0):.1%} / {market_probs.get('away', 0):.1%}\n"
        + f"- ELO主/平/客: {elo_probs.get('home', 0):.1%} / {elo_probs.get('draw', 0):.1%} / {elo_probs.get('away', 0):.1%}\n"
        + f"- Poisson主/平/客: {poisson_probs.get('home', 0):.1%} / {poisson_probs.get('draw', 0):.1%} / {poisson_probs.get('away', 0):.1%}\n"
        + f"- XGBoost主/平/客: {xgb_probs.get('home', 0):.1%} / {xgb_probs.get('draw', 0):.1%} / {xgb_probs.get('away', 0):.1%}\n"
        + f"- XGBoost状态: {'Fallback' if xgb_fallback else 'Model'} (ready={xgb_ready})\n"
        + f"- 当前模型: {prediction['model']}"
        + settlement_block
    )
