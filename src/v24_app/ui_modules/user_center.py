from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Mapping


USER_CENTER_LAYOUT: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "分析与报告",
        (
            ("分析选中", "analyze_selected"),
            ("分析全部", "analyze_all"),
            ("覆盖率监控", "show_coverage_monitor"),
            ("查看运营日报", "show_ops_daily_report"),
            ("查看7天趋势", "show_ops_weekly_trend"),
            ("导出当前视图", "export_current_report"),
            ("导出全部", "export_all_report"),
        ),
    ),
    (
        "结算与复盘",
        (
            ("录入赛果", "settle_selected_result"),
            ("近期结算", "show_recent_settlements"),
            ("让球专项看板", "show_handicap_monitor"),
            ("导出让球14天日报", "export_handicap_shadow_report"),
            ("导出准确率分解", "export_accuracy_decomposition_report"),
        ),
    ),
    (
        "模型管理",
        (
            ("模型总览", "show_model_training_overview"),
            ("XGB状态", "show_xgb_status"),
            ("训练XGB", "train_xgb_now"),
            ("玩法状态", "show_play_model_status"),
            ("训练玩法", "train_play_models"),
        ),
    ),
    (
        "策略校准",
        (
            ("权重状态", "show_ensemble_weight_status"),
            ("校准权重", "calibrate_ensemble_weights"),
            ("阈值状态", "show_play_threshold_status"),
            ("校准玩法", "calibrate_play_thresholds"),
            ("弱分桶校准", "calibrate_thresholds_by_decomposition"),
            ("分层门槛", "calibrate_layered_filter_thresholds"),
            ("覆盖率保护", "run_threshold_coverage_guardrail"),
            ("贝叶斯状态", "show_bayes_calibration_status"),
            ("校准贝叶斯", "calibrate_bayes_calibration"),
            ("接管策略", "show_play_model_policy_status"),
            ("校准接管", "calibrate_play_model_policy"),
        ),
    ),
    (
        "回测",
        (
            ("权重回测", "run_ensemble_backtest"),
            ("玩法回测", "run_play_model_backtest"),
        ),
    ),
    (
        "C1 对照",
        (
            ("导出阵容模板", "export_c1_availability_template"),
            ("导入阵容快照", "import_c1_availability_snapshots"),
            ("同步阵容源", "sync_c1_availability_sources"),
            ("阵容源状态", "show_c1_availability_provider_status"),
            ("运行C1对照", "run_c1_shadow_comparison"),
            ("运行放行评估", "run_c1_release_review"),
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


def open_user_center_window(
    *,
    root: tk.Tk,
    existing_window: tk.Toplevel | None,
    match_count: int,
    analyzed_count: int,
    on_close: Callable[[], None],
    actions: Mapping[str, Callable[[], None]],
) -> tk.Toplevel:
    if existing_window is not None and existing_window.winfo_exists():
        existing_window.lift()
        existing_window.focus_force()
        return existing_window

    window = tk.Toplevel(root)
    window.title("用户中心")
    window.geometry("860x500")
    window.minsize(820, 460)
    window.transient(root)
    window.protocol("WM_DELETE_WINDOW", on_close)

    container = ttk.Frame(window, padding=14)
    container.pack(fill=tk.BOTH, expand=True)

    ttk.Label(container, text="用户中心", font=("Microsoft YaHei UI", 14, "bold")).pack(anchor=tk.W)
    ttk.Label(
        container,
        text=f"当前赛事 {match_count} 场 | 已分析 {analyzed_count} 场",
        style="Sub.TLabel",
    ).pack(anchor=tk.W, pady=(4, 12))

    for section_title, buttons in build_user_center_sections(actions):
        box = ttk.LabelFrame(container, text=section_title, padding=10)
        box.pack(fill=tk.X, pady=(0, 10))
        for index, (button_text, callback) in enumerate(buttons):
            ttk.Button(box, text=button_text, command=callback).pack(side=tk.LEFT, padx=(0, 8) if index < len(buttons) - 1 else 0)

    ttk.Button(container, text="关闭", command=on_close).pack(anchor=tk.E, pady=(8, 0))
    return window
