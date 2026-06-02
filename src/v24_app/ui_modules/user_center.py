from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Mapping


# Phase 5 重构：6组 → 3组，减少视觉噪音
# 原"模型管理"+"策略校准"+"回测" → "模型与校准"
# 原"分析与报告"+"结算与复盘"    → "分析与结算"
# 原"C1 对照"                    → "C1 管理"（保持独立）
USER_CENTER_LAYOUT: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "分析与结算",
        (
            ("分析选中",         "analyze_selected"),
            ("分析全部",         "analyze_all"),
            ("录入赛果",         "settle_selected_result"),
            ("近期结算",         "show_recent_settlements"),
            ("覆盖率监控",       "show_coverage_monitor"),
            ("查看运营日报",     "show_ops_daily_report"),
            ("查看7天趋势",      "show_ops_weekly_trend"),
            ("让球专项看板",     "show_handicap_monitor"),
            ("导出让球14天日报", "export_handicap_shadow_report"),
            ("导出准确率分解",   "export_accuracy_decomposition_report"),
            ("导出当前视图",     "export_current_report"),
            ("导出全部",         "export_all_report"),
        ),
    ),
    (
        "模型与校准",
        (
            ("模型总览",     "show_model_training_overview"),
            ("XGB状态",      "show_xgb_status"),
            ("训练XGB",      "train_xgb_now"),
            ("玩法状态",     "show_play_model_status"),
            ("训练玩法",     "train_play_models"),
            ("权重状态",     "show_ensemble_weight_status"),
            ("校准权重",     "calibrate_ensemble_weights"),
            ("阈值状态",     "show_play_threshold_status"),
            ("校准玩法",     "calibrate_play_thresholds"),
            ("弱分桶校准",   "calibrate_thresholds_by_decomposition"),
            ("分层门槛",     "calibrate_layered_filter_thresholds"),
            ("覆盖率保护",   "run_threshold_coverage_guardrail"),
            ("贝叶斯状态",   "show_bayes_calibration_status"),
            ("校准贝叶斯",   "calibrate_bayes_calibration"),
            ("接管策略",     "show_play_model_policy_status"),
            ("校准接管",     "calibrate_play_model_policy"),
            ("权重回测",     "run_ensemble_backtest"),
            ("玩法回测",     "run_play_model_backtest"),
            ("高准策略",     "run_high_accuracy_strategy_backtest"),
            ("接管审计导出", "export_play_model_takeover_gate_audit_report"),
        ),
    ),
    (
        "C1 管理",
        (
            ("导出阵容模板", "export_c1_availability_template"),
            ("导入阵容快照", "import_c1_availability_snapshots"),
            ("同步阵容源",   "sync_c1_availability_sources"),
            ("阵容源状态",   "show_c1_availability_provider_status"),
            ("运行C1对照",   "run_c1_shadow_comparison"),
            ("运行放行评估", "run_c1_release_review"),
            ("放行门控审计", "open_c1_release_guard_history"),
            ("正式建议清单", "open_c1_formal_recommendations"),
            ("打开放行清单", "open_c1_release_allowlist"),
            ("打开C1工作台", "open_c1_workbench"),
        ),
    ),
)


def build_user_center_sections(actions: Mapping[str, Callable[[], None]]) -> list[tuple[str, list[tuple[str, Callable[[], None]]]]]:
    sections: list[tuple[str, list[tuple[str, Callable[[], None]]]]] = []
    for section_title, items in USER_CENTER_LAYOUT:
        buttons: list[tuple[str, Callable[[], None]]] = []
        for button_text, action_key in items:
            action = actions.get(action_key)
            if action is None:
                raise RuntimeError(f"Missing user-center action: {action_key}")
            buttons.append((button_text, action))
        sections.append((section_title, buttons))
    return sections


def _render_section_buttons(
    parent: tk.Widget,
    buttons: list[tuple[str, Callable[[], None]]],
    cols: int = 6,
) -> None:
    """把按钮列表以网格方式渲染到 parent 中。"""
    for idx, (text, cmd) in enumerate(buttons):
        row, col = divmod(idx, cols)
        ttk.Button(parent, text=text, command=cmd).grid(
            row=row, column=col, sticky=tk.W, padx=(0, 6), pady=(0, 4)
        )


def build_user_center_panel(
    container: tk.Widget,
    *,
    actions: Mapping[str, Callable[[], None]],
    center_actions: Mapping[str, Callable[[], None]] | None = None,
    on_close: Callable[[], None],
    match_count: int = 0,
    analyzed_count: int = 0,
) -> None:
    """
    Phase 5 重构：在 container 内渲染用户中心内嵌面板。

    center_actions 可选，键为 "model_center" / "analysis_center" / "c1_center"，
    用于在顶部渲染功能中心快速入口按钮。
    """
    # ── 顶部：功能中心快速入口 ──────────────────────────────────
    if center_actions:
        shortcut_frame = ttk.LabelFrame(container, text="功能中心", padding=8)
        shortcut_frame.pack(fill=tk.X, pady=(0, 8))
        labels = {
            "model_center":    "📊 模型中心",
            "analysis_center": "📈 分析中心",
            "c1_center":       "🔍 C1管理中心",
        }
        for key, label in labels.items():
            cmd = center_actions.get(key)
            if cmd is not None:
                ttk.Button(shortcut_frame, text=label, command=cmd).pack(
                    side=tk.LEFT, padx=(0, 8)
                )

    # ── 统计信息 ────────────────────────────────────────────────
    ttk.Label(
        container,
        text=f"当前赛事 {match_count} 场 | 已分析 {analyzed_count} 场",
        style="Sub.TLabel",
    ).pack(anchor=tk.W, pady=(0, 8))

    # ── 三组功能按钮 ────────────────────────────────────────────
    for section_title, buttons in build_user_center_sections(actions):
        box = ttk.LabelFrame(container, text=section_title, padding=8)
        box.pack(fill=tk.X, pady=(0, 8))
        _render_section_buttons(box, buttons, cols=6)

    # ── 收起按钮 ────────────────────────────────────────────────
    ttk.Button(container, text="收起用户中心", command=on_close).pack(
        anchor=tk.E, pady=(4, 0)
    )


def open_user_center_window(
    *,
    root: tk.Tk,
    existing_window: tk.Toplevel | None,
    match_count: int,
    analyzed_count: int,
    on_close: Callable[[], None],
    actions: Mapping[str, Callable[[], None]],
) -> tk.Toplevel:
    """独立窗口版（传统模式，供外部调用保持兼容）。"""
    if existing_window is not None and existing_window.winfo_exists():
        existing_window.lift()
        existing_window.focus_force()
        return existing_window

    window = tk.Toplevel(root)
    window.title("用户中心")
    window.geometry("900x560")
    window.minsize(860, 480)
    window.transient(root)
    window.protocol("WM_DELETE_WINDOW", on_close)

    container = ttk.Frame(window, padding=14)
    container.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        container,
        text="用户中心",
        font=("Microsoft YaHei UI", 14, "bold"),
    ).pack(anchor=tk.W)

    build_user_center_panel(
        container,
        actions=actions,
        on_close=on_close,
        match_count=match_count,
        analyzed_count=analyzed_count,
    )
    return window
