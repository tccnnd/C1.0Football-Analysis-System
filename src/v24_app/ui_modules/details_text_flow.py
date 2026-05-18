from __future__ import annotations

from typing import Any, Callable, Mapping

from .strategy_dashboard_flow import (
    format_high_accuracy_strategy_release_explanation,
    format_strategy_admission_pick,
    format_strategy_admission_reasons,
    format_strategy_admission_replay_guard,
    format_strategy_admission_thresholds,
)


def _format_backfill_report_lines(title: str, report: Mapping[str, object] | object) -> list[str]:
    resolved = report if isinstance(report, Mapping) else {}
    if not resolved:
        return []
    lines = ["", title]
    for key in ("checked", "updated", "restored", "already_ready", "missing_prediction", "invalid_match", "skipped_limit", "backfilled"):
        if key in resolved:
            lines.append(f"- {key}: {resolved.get(key, 0)}")
    fact_ref_kinds = resolved.get("fact_ref_kinds")
    if isinstance(fact_ref_kinds, Mapping) and fact_ref_kinds:
        counts = ", ".join(f"{key}={int(value or 0)}" for key, value in sorted(fact_ref_kinds.items()))
        lines.append(f"- fact_ref_kinds: {counts}")
    return lines


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
        trace_backfill = migration.get("trace_fact_ref_backfill")
        if isinstance(trace_backfill, Mapping) and trace_backfill:
            lines.extend(_format_backfill_report_lines("Trace Fact 回填", trace_backfill))
        history_trace_backfill = migration.get("analysis_history_trace_fact_ref_backfill")
        if isinstance(history_trace_backfill, Mapping) and history_trace_backfill:
            lines.extend(_format_backfill_report_lines("Analysis History Trace 回填", history_trace_backfill))

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


def _pct_text(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except (TypeError, ValueError):
        return "-"


def _format_jc_strategy_evidence(item: Mapping[str, object] | object) -> list[str]:
    resolved = item if isinstance(item, Mapping) else {}
    layer = resolved.get("layer", {}) if isinstance(resolved.get("layer"), Mapping) else {}
    if str(layer.get("data_layer") or "") != "jc_stratified_market":
        return []
    bucket = resolved.get("jc_bucket", {}) if isinstance(resolved.get("jc_bucket"), Mapping) else {}
    context = resolved.get("jc_context", {}) if isinstance(resolved.get("jc_context"), Mapping) else {}
    stability = bucket.get("stability", {}) if isinstance(bucket.get("stability"), Mapping) else {}
    return [
        f"- JC stable bucket: {bucket.get('dimension') or resolved.get('dimension') or '-'} / {bucket.get('bucket') or resolved.get('scope_value') or '-'}",
        (
            f"- JC backtest: {_pct_text(bucket.get('accuracy', resolved.get('backtest_accuracy')))} "
            f"({int(bucket.get('hit_count', resolved.get('backtest_hits', 0)) or 0)}/"
            f"{int(bucket.get('sample_count', resolved.get('backtest_samples', 0)) or 0)}) | "
            f"Wilson {_pct_text(bucket.get('wilson_lower', resolved.get('wilson_lower')))}"
        ),
        (
            f"- JC runtime match: confidence_bucket={context.get('confidence_bucket') or '-'} | "
            f"odds_bucket={context.get('odds_bucket') or '-'} | "
            f"pick_odds={float(context.get('pick_odds', 0) or 0):.2f}"
        ),
        (
            f"- JC stability: {'stable' if bool(stability.get('stable')) else 'watch'} | "
            f"score {_pct_text(stability.get('stability_score'))} | "
            f"recent30 {_pct_text(stability.get('recent_30_accuracy'))}"
        ),
    ]


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


def _float_value(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_metric_map(values: object, *, percent: bool = False) -> str:
    if not isinstance(values, Mapping):
        return "-"
    parts: list[str] = []
    for key in ("home", "draw", "away"):
        value = values.get(key)
        if value is None:
            continue
        numeric = _float_value(value)
        if percent:
            parts.append(f"{key}={numeric:+.1%}")
        else:
            parts.append(f"{key}={numeric:.3f}")
    return " / ".join(parts) if parts else "-"


def _build_market_entropy_block(prediction: Mapping[str, object]) -> str:
    entropy = prediction.get("market_entropy")
    if not isinstance(entropy, Mapping):
        return ""
    risk = prediction.get("market_entropy_risk")
    risk_overlay = risk if isinstance(risk, Mapping) else {}
    sequence = entropy.get("sequence") if isinstance(entropy.get("sequence"), Mapping) else {}
    signals = entropy.get("signals")
    signal_text = ", ".join(str(item) for item in signals) if isinstance(signals, list) and signals else "-"
    overlay_text = "applied" if bool(risk_overlay.get("applied")) else "none"
    if risk_overlay.get("reason"):
        overlay_text += f" ({risk_overlay.get('reason')})"
    return (
        "\n\nMarketEntropy"
        + f"\n- level={entropy.get('level', '-')} | score={_float_value(entropy.get('score')):.1%} | risk_overlay={overlay_text}"
        + f"\n- odds_slope: {_format_metric_map(entropy.get('odds_slope'), percent=True)}"
        + f"\n- sequence: samples={int(_float_value(sequence.get('sample_count')))} | interval={_float_value(sequence.get('latest_interval_minutes')):.1f}m | velocity={_format_metric_map(sequence.get('latest_velocity'), percent=True)}"
        + f"\n- history_step={_float_value(sequence.get('max_step_change')):+.1%} | step_side={sequence.get('step_side', '-')}"
        + f"\n- strongest_steam={entropy.get('strongest_steam_side', '-')} | market_favorite={entropy.get('market_favorite', '-')}"
        + f"\n- Kelly: {_format_metric_map(entropy.get('kelly'))} | span={_float_value(entropy.get('kelly_span')):.3f} | low={entropy.get('kelly_low_side', '-')}"
        + f"\n- pick={entropy.get('pick_side', '-')} | pick_slope={_float_value(entropy.get('pick_slope')):+.1%} | pick_kelly_gap={_float_value(entropy.get('pick_kelly_gap')):.3f}"
        + f"\n- signals: {signal_text}"
    )


def _build_handicap_margin_block(prediction: Mapping[str, object]) -> str:
    signal = prediction.get("handicap_margin_consistency")
    if not isinstance(signal, Mapping):
        return ""
    signals = signal.get("signals")
    signal_text = ", ".join(str(item) for item in signals) if isinstance(signals, list) and signals else "-"
    return (
        "\n\nHandicap Margin Consistency"
        + f"\n- level={signal.get('level', '-')} | score={_float_value(signal.get('score')):.1%}"
        + f"\n- handicap_line={_float_value(signal.get('handicap_line')):+.2f} | model_margin={_float_value(signal.get('model_margin_goals')):+.2f}"
        + f"\n- market_side={signal.get('market_side', '-')} | model_side={signal.get('model_side', '-')}"
        + f"\n- line_depth={_float_value(signal.get('line_depth')):.2f} | margin_depth={_float_value(signal.get('margin_depth')):.2f} | depth_gap={_float_value(signal.get('depth_gap')):+.2f}"
        + f"\n- handicap_pick={signal.get('handicap_pick_side', '-')} | model_pick={signal.get('model_pick_side', '-')}"
        + f"\n- signals: {signal_text}"
    )


def _build_draw_release_guard_block(prediction: Mapping[str, object]) -> str:
    guard = prediction.get("draw_release_guard")
    if not isinstance(guard, Mapping):
        return ""
    evidence = guard.get("evidence") if isinstance(guard.get("evidence"), Mapping) else {}
    status = "blocked" if bool(guard.get("blocked")) else "allowed" if bool(guard.get("base_takeover")) else "watch" if bool(guard.get("weak_score")) else "idle"
    evidence_text = (
        f"source={evidence.get('source', '-')} | precision={_pct_text(evidence.get('precision'))} | "
        f"draw_rate={_pct_text(evidence.get('draw_rate'))} | lift={_pct_text(evidence.get('lift'))}"
        if evidence
        else "no blocked-odds evidence"
    )
    return (
        "\n\nDraw Release Guard"
        + f"\n- release={status} | reason={guard.get('reason', '-')}"
        + f"\n- blocked_odds={guard.get('odds_bucket', '-')} | draw_odds={_float_value(guard.get('odds_draw')):.3f} | score_floor={_pct_text(guard.get('min_score'))}"
        + f"\n- raw_takeover={bool(guard.get('base_takeover'))} | watch_score={bool(guard.get('weak_score'))} | blocked={bool(guard.get('blocked'))}"
        + f"\n- evidence: {evidence_text}"
    )


def _build_supervisor_block(prediction: Mapping[str, object]) -> str:
    supervisor = prediction.get("supervisor")
    if not isinstance(supervisor, Mapping):
        return ""
    decision = supervisor.get("decision") if isinstance(supervisor.get("decision"), Mapping) else {}
    agents = supervisor.get("agents") if isinstance(supervisor.get("agents"), list) else []
    actions = supervisor.get("next_actions") if isinstance(supervisor.get("next_actions"), list) else []
    lines = [
        "",
        "Supervisor / Orchestrator",
        (
            f"- status={supervisor.get('status', '-')} | "
            f"release_allowed={bool(decision.get('release_allowed'))} | "
            f"human_review={bool(decision.get('requires_human_review'))}"
        ),
        f"- next_actions: {', '.join(str(item) for item in actions) if actions else '-'}",
    ]
    for item in agents:
        if not isinstance(item, Mapping):
            continue
        outputs = item.get("outputs") if isinstance(item.get("outputs"), Mapping) else {}
        actions = item.get("actions") if isinstance(item.get("actions"), list) else []
        summary_parts: list[str] = []
        if outputs.get("signals"):
            summary_parts.append(f"signals={len(outputs.get('signals') or [])}")
        if outputs.get("recommendation"):
            summary_parts.append(f"pick={outputs.get('recommendation')}")
        if outputs.get("admission_decision"):
            summary_parts.append(f"decision={outputs.get('admission_decision')}")
        if item.get("rationale"):
            summary_parts.append(f"why={item.get('rationale')}")
        if actions:
            summary_parts.append(f"actions={','.join(str(action) for action in actions[:3])}")
        summary = " | ".join(summary_parts) if summary_parts else str(item.get("trigger") or "-")
        lines.append(f"- {item.get('name', '-')}: {item.get('status', '-')} | {summary}")
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
    admission = prediction.get("strategy_admission", {}) if isinstance(prediction.get("strategy_admission"), Mapping) else {}

    settlement_block = ""
    if settlement is not None:
        high_summary = settlement.get("high_accuracy_strategy_summary") or "-"
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
        release_explanation = format_high_accuracy_strategy_release_explanation(high_strategy, admission, limit=3)
        high_strategy_block = (
            "\n\n高准确率策略\n"
            + f"- 当前命中: {'是' if active_count > 0 else '否'} | 命中策略数 {active_count}\n"
            + f"- 玩法: {high_strategy.get('play_type', '-')} | 选择: {high_strategy.get('pick', '-')}\n"
            + f"- 置信度: {float(high_strategy.get('confidence', 0) or 0):.1%} / 门槛 {float(high_strategy.get('min_confidence', 0) or 0):.1%}\n"
            + f"- 历史命中: {float(high_strategy.get('backtest_accuracy', 0) or 0):.1%} ({int(high_strategy.get('backtest_hits', 0) or 0)}/{int(high_strategy.get('backtest_samples', 0) or 0)})\n"
            + f"- 策略摘要: {high_strategy.get('summary', '-')}\n"
            + f"- 原因: {high_strategy.get('reason', '-')}\n"
            + "- 放行解释:\n"
            + release_explanation
        )
    if high_strategy.get("enabled"):
        evidence_source = active_items[0] if isinstance(active_items, list) and active_items else high_strategy
        jc_evidence = _format_jc_strategy_evidence(evidence_source)
        if jc_evidence:
            high_strategy_block += "\n" + "\n".join(jc_evidence)
    admission_block = ""
    if admission:
        reason_text = format_strategy_admission_reasons(admission, limit=5)
        threshold_text = format_strategy_admission_thresholds(admission)
        pick_text = format_strategy_admission_pick(admission)
        replay_guard_text = format_strategy_admission_replay_guard(admission)
        admission_block = (
            "\n\n策略准入白名单\n"
            + f"- 准入结论: {admission.get('label', '-')}\n"
            + f"- 放行状态: {'可放行' if admission.get('release_allowed') else '不可放行'}\n"
            + f"- 高准正式/观察: {int(admission.get('active_count', 0) or 0)} / {int(admission.get('shadow_count', 0) or 0)}\n"
            + f"- 候选玩法: {pick_text}\n"
            + f"- 原因: {reason_text}\n"
            + f"- 准入门槛: {threshold_text}"
            + (f"\n- Agent Replay: {replay_guard_text}" if replay_guard_text != "-" else "")
        )
    confidence_block = _build_confidence_calibration_block(prediction)
    runtime_threshold_block = _build_runtime_threshold_block(prediction)
    draw_release_guard_block = _build_draw_release_guard_block(prediction)
    market_entropy_block = _build_market_entropy_block(prediction)
    handicap_margin_block = _build_handicap_margin_block(prediction)
    supervisor_block = _build_supervisor_block(prediction)
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
        + draw_release_guard_block
        + ("\n" if draw_release_guard_block else "")
        + market_entropy_block
        + ("\n" if market_entropy_block else "")
        + handicap_margin_block
        + ("\n" if handicap_margin_block else "")
        + supervisor_block
        + ("\n" if supervisor_block else "")
        + poisson_block_text
        + strategy_block
        + high_strategy_block
        + admission_block
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
