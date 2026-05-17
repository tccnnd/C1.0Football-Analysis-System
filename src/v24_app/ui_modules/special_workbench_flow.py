from __future__ import annotations

from typing import Callable, Mapping


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
