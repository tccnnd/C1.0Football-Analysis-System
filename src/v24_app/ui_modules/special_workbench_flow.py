from __future__ import annotations

from typing import Callable, Mapping


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: object, default: str = "-") -> str:
    text = str(value if value is not None else "").strip()
    return text or default

from .model_status_flow import (
    build_training_health_action_rows,
    build_training_health_card_rows,
    build_training_model_gate_rows,
)

SPECIAL_WORKBENCH_LAYOUT: tuple[tuple[str, tuple[dict[str, str], ...]], ...] = (
    (
        "复盘闭环",
        (
            {
                "title": "复盘中心",
                "body": "回收赛果、查看近期命中率、偏差归因和高置信失误。",
                "action_key": "open_review_center",
                "tone": "neutral",
            },
            {
                "title": "AI视频复盘专项",
                "body": "集中查看视频记忆健康、视频来源覆盖、补标注建议和降级边界。",
                "action_key": "open_ai_video_review_center_window",
                "tone": "info",
            },
            {
                "title": "复盘证据缺口专项",
                "body": "处理缺回放、缺本地视频、缺事件代理样本的复盘证据闭环。",
                "action_key": "open_video_review_evidence_gap_center_window",
                "tone": "warning",
            },
            {
                "title": "事件代理专项",
                "body": "查看 StatsBomb/Event Proxy 样本质量、修复动作和质量报告。",
                "action_key": "open_statsbomb_review_training_center_window",
                "tone": "info",
            },
            {
                "title": "事件代理复盘闭环",
                "body": "跟踪 StatsBomb 覆盖率、复盘样本生成和闭环完成度。",
                "action_key": "open_statsbomb_review_training_closure_window",
                "tone": "info",
            },
        ),
    ),
    (
        "策略与接管",
        (
            {
                "title": "策略看板",
                "body": "查看高准策略池、回测分层、稳定性和真实结算反馈。",
                "action_key": "open_strategy_library",
                "tone": "neutral",
            },
            {
                "title": "放行回收闭环",
                "body": "检查正式放行后的待回收、缺快照、超期和质量趋势。",
                "action_key": "open_strategy_release_recovery_loop_window",
                "tone": "warning",
            },
            {
                "title": "接管审计历史",
                "body": "查看玩法接管 gate 的历史转场、导出报告和审计文件。",
                "action_key": "open_play_model_takeover_gate_audit_history",
                "tone": "warning",
            },
            {
                "title": "玩法接管策略",
                "body": "查看总进球/比分模型接管门槛、有效策略和阻断原因。",
                "action_key": "open_play_model_policy_detail_window",
                "tone": "neutral",
            },
            {
                "title": "调参审计历史",
                "body": "查看调参审计转场、导出文件和最新外部报告。",
                "action_key": "open_strategy_policy_audit_history",
                "tone": "info",
            },
            {
                "title": "平局专项诊断",
                "body": "查看平局召回、误报、分层表现和当前平局守门策略。",
                "action_key": "open_draw_specialist_backtest_window",
                "tone": "info",
            },
            {
                "title": "准确率诊断",
                "body": "查看近期命中率、偏差类型和高置信错误归因。",
                "action_key": "open_accuracy_diagnostics",
                "tone": "warning",
            },
        ),
    ),
    (
        "数据与运行",
        (
            {
                "title": "赛前快照",
                "body": "查看已保存的赛前预测，等待完场后进入复盘。",
                "action_key": "open_snapshot_center",
                "tone": "neutral",
            },
            {
                "title": "数据中心",
                "body": "查看数据文件、模型文件、缓存池和训练数据健康状态。",
                "action_key": "open_data_center",
                "tone": "neutral",
            },
            {
                "title": "监控中心",
                "body": "查看 Agent 状态、后台任务、执行日志和耗时。",
                "action_key": "open_monitor_center",
                "tone": "neutral",
            },
            {
                "title": "回收运行记录",
                "body": "查看赛果回收任务历史、成功率、失败原因和耗时。",
                "action_key": "open_recovery_run_center",
                "tone": "info",
            },
        ),
    ),
)


def build_special_workbench_sections(
    actions: Mapping[str, Callable[[], None]],
) -> list[tuple[str, list[dict[str, object]]]]:
    sections: list[tuple[str, list[dict[str, object]]]] = []
    missing: list[str] = []
    for section_title, entries in SPECIAL_WORKBENCH_LAYOUT:
        rows: list[dict[str, object]] = []
        for entry in entries:
            action_key = entry["action_key"]
            action = actions.get(action_key)
            if action is None:
                missing.append(action_key)
                continue
            rows.append({**entry, "command": action})
        sections.append((section_title, rows))
    if missing:
        raise RuntimeError(f"Missing special workbench action(s): {', '.join(missing[:8])}")
    return sections


def build_review_center_special_summary_rows(
    *,
    video_review_center_summary: Mapping[str, object] | object,
    evidence_gap_batch_status: Mapping[str, object] | object,
    video_source_coverage: Mapping[str, object] | object,
    statsbomb_review_center_summary: Mapping[str, object] | object,
    statsbomb_review_closure_summary: Mapping[str, object] | object,
) -> list[dict[str, str]]:
    video_summary = video_review_center_summary if isinstance(video_review_center_summary, Mapping) else {}
    gap_status = evidence_gap_batch_status if isinstance(evidence_gap_batch_status, Mapping) else {}
    source_coverage = video_source_coverage if isinstance(video_source_coverage, Mapping) else {}
    proxy_summary = statsbomb_review_center_summary if isinstance(statsbomb_review_center_summary, Mapping) else {}
    closure_summary = statsbomb_review_closure_summary if isinstance(statsbomb_review_closure_summary, Mapping) else {}
    missing_evidence_count = int(source_coverage.get("no_review_evidence_count", 0) or 0)
    gap_completion = float(gap_status.get("completion_rate", 0) or 0)
    return [
        {
            "title": "专项中心",
            "body": "视频复盘、证据缺口、事件代理和闭环样本质量已集中到专项窗口处理。",
            "action_key": "open_special_workbench",
            "tone": "neutral",
        },
        {
            "title": str(video_summary.get("title") or "AI视频复盘"),
            "body": str(video_summary.get("body") or "-"),
            "action_key": "open_ai_video_review_center_window",
            "tone": str(video_summary.get("tone") or "neutral"),
        },
        {
            "title": f"证据缺口 | {gap_status.get('status', '-')}",
            "body": (
                f"{gap_status.get('summary_text', '-')}\n"
                f"完成率 {gap_completion:.0%} | 当前缺证据 {missing_evidence_count} 场"
            ),
            "action_key": "open_video_review_evidence_gap_center_window",
            "tone": "warning" if missing_evidence_count > 0 else "good",
        },
        {
            "title": str(proxy_summary.get("title") or "事件代理专项"),
            "body": str(proxy_summary.get("body") or "-"),
            "action_key": "open_statsbomb_review_training_center_window",
            "tone": str(proxy_summary.get("tone") or "neutral"),
        },
        {
            "title": str(closure_summary.get("title") or "事件代理复盘闭环"),
            "body": str(closure_summary.get("body") or "-"),
            "action_key": "open_statsbomb_review_training_closure_window",
            "tone": str(closure_summary.get("tone") or "neutral"),
        },
    ]


def build_strategy_special_summary_rows(
    *,
    play_model_policy_status: Mapping[str, object] | object,
    release_recovery_loop: Mapping[str, object] | object,
    draw_release_guard_tuning: Mapping[str, object] | object,
    accuracy_diagnostics: Mapping[str, object] | object,
    statsbomb_review_training_quality: Mapping[str, object] | object | None = None,
    statsbomb_review_training_signal: Mapping[str, object] | object | None = None,
    limit: int = 7,
) -> list[dict[str, object]]:
    play_status = _as_mapping(play_model_policy_status)
    release = _as_mapping(release_recovery_loop)
    draw_tuning = _as_mapping(draw_release_guard_tuning)
    accuracy = _as_mapping(accuracy_diagnostics)
    statsbomb_quality = _as_mapping(statsbomb_review_training_quality)
    statsbomb_signal = _as_mapping(statsbomb_review_training_signal)
    statsbomb_weight_gate = _as_mapping(statsbomb_signal.get("weight_gate"))
    policy = _as_mapping(play_status.get("policy"))
    effective_policy = _as_mapping(play_status.get("effective_policy"))
    takeover_gate = _as_mapping(play_status.get("takeover_gate"))
    takeover_audit = _as_mapping(play_status.get("takeover_gate_audit"))
    takeover_report = _as_mapping(play_status.get("takeover_gate_audit_report"))
    rows = [
        {
            "title": "放行回收闭环",
            "body": (
                f"{_text(release.get('summary_text'), _text(release.get('health_text'), '暂无闭环摘要'))}\n"
                f"待回收 {_safe_int(release.get('ready_for_recovery_count'))} | 告警 {_safe_int(release.get('alert_count'))}"
            ),
            "action_key": "open_strategy_release_recovery_loop_window",
            "tone": "warning" if _safe_int(release.get("ready_for_recovery_count")) else "neutral",
        },
        {
            "title": "接管审计历史",
            "body": (
                f"历史 {_safe_int(takeover_audit.get('history_count'), _safe_int(takeover_report.get('history_count')))} | "
                f"最近转变 {_text(takeover_audit.get('latest_transition'), _text(takeover_report.get('latest_transition')))}\n"
                f"最近原因 {_text(takeover_audit.get('latest_reason'), _text(takeover_report.get('latest_reason')))}"
            ),
            "action_key": "open_play_model_takeover_gate_audit_history",
            "tone": "warning" if _text(takeover_gate.get("status"), "") in {"block", "watch"} else "neutral",
        },
        {
            "title": "玩法接管策略",
            "body": (
                f"gate {_text(takeover_gate.get('status'), '-')} | blocked={bool(play_status.get('policy_blocked_by_gate'))}\n"
                f"scoreline {_text(_as_mapping(policy.get('scoreline')).get('takeover_enabled'), '-')} -> {_text(_as_mapping(effective_policy.get('scoreline')).get('takeover_enabled'), '-')}\n"
                f"total_goals {_text(_as_mapping(policy.get('total_goals')).get('takeover_enabled'), '-')} -> {_text(_as_mapping(effective_policy.get('total_goals')).get('takeover_enabled'), '-')}"
            ),
            "action_key": "open_play_model_policy_detail_window",
            "tone": "warning" if bool(play_status.get("policy_blocked_by_gate")) else "neutral",
        },
        {
            "title": "StatsBomb接管执行层",
            "body": (
                f"quality {_text(statsbomb_quality.get('status'), '-')} | "
                f"signal {_text(statsbomb_signal.get('status'), '-')} | "
                f"samples {_safe_int(statsbomb_quality.get('sample_count'))} | "
                f"issues {_safe_int(statsbomb_quality.get('issue_count'))}\n"
                f"gate {_text(statsbomb_weight_gate.get('mode'), '-')} | "
                f"enabled={bool(statsbomb_weight_gate.get('enabled'))} | "
                f"reason {_text(statsbomb_weight_gate.get('reason'), _text(statsbomb_signal.get('summary_text'), '-'))}\n"
                f"next {_text(statsbomb_weight_gate.get('recommendation'), _text(statsbomb_signal.get('summary_text'), '-'))}"
            ),
            "action_key": "open_statsbomb_review_training_center_window",
            "tone": (
                "good"
                if _text(statsbomb_quality.get("status"), "") == "healthy" and _text(statsbomb_weight_gate.get("mode"), "") == "active"
                else "danger"
                if _text(statsbomb_quality.get("status"), "") == "blocked" or _text(statsbomb_weight_gate.get("mode"), "") == "disabled"
                else "warning"
                if _text(statsbomb_quality.get("status"), "") == "attention" or _text(statsbomb_weight_gate.get("mode"), "") == "report_only"
                else "neutral"
            ),
        },
        {
            "title": "平局专项诊断",
            "body": (
                f"{_text(draw_tuning.get('summary_text'), _text(draw_tuning.get('label'), '暂无平局诊断'))}\n"
                f"{_text(draw_tuning.get('reason_text'), _text(draw_tuning.get('description'), '-'))}"
            ),
            "action_key": "open_draw_specialist_backtest_window",
            "tone": _text(draw_tuning.get("tone"), "neutral"),
        },
        {
            "title": "准确率诊断",
            "body": (
                f"样本 {_safe_int(accuracy.get('sample_count'))} | 总体 {_text(accuracy.get('overall'), '-')}\n"
                f"优先 {_text(accuracy.get('priority'), '-')}"
            ),
            "action_key": "open_accuracy_diagnostics",
            "tone": "warning" if _safe_int(accuracy.get("sample_count")) and _text(accuracy.get("priority"), "") != "-" else "neutral",
        },
        {
            "title": "调参审计历史",
            "body": "查看策略调参审计历史、导出文件和最近回放记录。",
            "action_key": "open_strategy_policy_audit_history",
            "tone": "info",
        },
    ]
    return rows[: max(0, int(limit))]


def build_data_training_special_section_rows(
    actions: Mapping[str, Callable[[], None]],
    *,
    coverage_status: Mapping[str, object] | object,
    training_gate_status: Mapping[str, object] | object,
    data_health_status: Mapping[str, object] | object,
) -> list[dict[str, object]]:
    coverage = coverage_status if isinstance(coverage_status, Mapping) else {}
    data_health = data_health_status if isinstance(data_health_status, Mapping) else {}
    training_cards = build_training_health_card_rows(coverage, limit=4)
    training_actions = build_training_health_action_rows(coverage, limit=3)
    gate_rows = build_training_model_gate_rows(training_gate_status, limit=3)

    inventory_rows = data_health.get("inventory_rows", []) if isinstance(data_health.get("inventory_rows"), list) else []
    inventory_text = " | ".join(
        f"{str(item[0])}: {str(item[1])}"
        for item in inventory_rows[:3]
        if isinstance(item, (list, tuple)) and len(item) >= 2
    ) or "-"
    data_source = str(data_health.get("data_source") or "-")
    source_health = str(data_health.get("source_health") or "-")
    cache_status = str(data_health.get("cache_status") or "-")

    missing: list[str] = []
    rows: list[dict[str, object]] = []

    def _attach(action_key: str, title: str, body: str) -> None:
        command = actions.get(action_key)
        if command is None:
            missing.append(action_key)
            return
        rows.append(
            {
                "title": title,
                "body": body,
                "action_key": action_key,
                "command": command,
            }
        )

    health_body = " | ".join(
        f"{str(row.get('label') or '-')}: {str(row.get('value') or '-')}"
        for row in training_cards[:3]
    ) or "-"
    health_detail = str(training_cards[0].get("detail") or "-") if training_cards else "-"
    _attach(
        "show_model_training_overview",
        "训练健康卡片",
        f"{health_body}\n{health_detail}",
    )

    if training_actions:
        first_action = training_actions[0]
        suggestion_body = f"{str(first_action.get('value') or '-')} | {str(first_action.get('detail') or '-')}"
    else:
        suggestion_body = "进入训练总览查看补数建议"
    suggestion_body = f"{suggestion_body}\n补数与特征重建闭环: 生成复盘样本 -> 重建XGB样本 -> 刷新训练健康"
    _attach(
        "show_model_training_overview",
        "优先补数建议",
        suggestion_body,
    )

    gate_head_row = gate_rows[0] if gate_rows else {}
    gate_head_body = f"{str(gate_head_row.get('value') or '-')} | {str(gate_head_row.get('detail') or '-')}"
    xgb_gate_row = gate_rows[1] if len(gate_rows) > 1 else (gate_rows[0] if gate_rows else {})
    _attach(
        "show_model_training_overview",
        "XGB 训练 gate",
        f"{gate_head_body} | {str(xgb_gate_row.get('value') or '-')} | {str(xgb_gate_row.get('detail') or '-')}",
    )

    play_gate_row = gate_rows[2] if len(gate_rows) > 2 else {}
    _attach(
        "show_model_training_overview",
        "玩法模型训练 gate",
        f"{gate_head_body} | {str(play_gate_row.get('value') or '-')} | {str(play_gate_row.get('detail') or '-')}",
    )

    _attach(
        "open_data_center",
        "数据文件 / 模型文件 / 缓存健康摘要",
        f"数据源 {data_source} | 源健康 {source_health} | 缓存 {cache_status}\n{inventory_text}",
    )

    if missing:
        raise RuntimeError(f"Missing data training section action(s): {', '.join(missing[:8])}")
    return rows


def build_special_workbench_overview_rows() -> list[dict[str, str]]:
    section_names = " / ".join(str(section_title) for section_title, _entries in SPECIAL_WORKBENCH_LAYOUT)
    overview_rows = [
        {
            "label": "专项总数",
            "value": str(sum(len(entries) for _section_title, entries in SPECIAL_WORKBENCH_LAYOUT)),
            "tone": "good",
            "detail": section_names,
        }
    ]
    tones = ("info", "warning", "neutral")
    for index, (section_title, entries) in enumerate(SPECIAL_WORKBENCH_LAYOUT):
        sample_titles = [str(entry.get("title") or "-") for entry in entries[:2] if isinstance(entry, dict)]
        detail = " / ".join(sample_titles) if sample_titles else "-"
        overview_rows.append(
            {
                "label": str(section_title),
                "value": str(len(entries)),
                "tone": tones[index % len(tones)],
                "detail": detail,
            }
        )
    return overview_rows
