from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
import sys
from tkinter import filedialog, messagebox, ttk

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.runtime import (
    get_default_ui_filter,
    get_runtime_mode,
    is_release_gate_active,
    run_controlled_release_for_legacy_matches,
    run_shadow_comparison_for_legacy_matches,
)
from .ui_bindings import apply_class_bindings, validate_class_bindings
from .ui_modules import (
    build_analysis_status_text,
    build_auto_settle_popup_message,
    build_auto_settle_status_text,
    build_c1_rows_from_marks,
    build_c1_mark_apply_plan,
    build_export_report_lines,
    build_formal_release_rows,
    build_release_allowlist_lines,
    collect_release_allowed_match_ids,
    compute_pending_match_ids,
    find_release_row,
    format_release_candidate_text,
    build_c1_apply_dialog_text,
    build_c1_apply_status_text,
    build_c1_availability_provider_status_lines,
    build_c1_release_guard_report_filename,
    build_c1_release_guard_history_text,
    build_c1_release_guard_report_lines,
    build_c1_release_review_availability_guard,
    build_c1_release_review_guard_status_text,
    build_c1_snapshot_import_message_text,
    build_c1_snapshot_import_status_text,
    build_c1_sync_message_text,
    build_c1_sync_status_text,
    build_c1_template_export_message_text,
    build_c1_template_export_status_text,
    build_release_review_status_text,
    build_shadow_comparison_status_text,
    build_bayes_calibration_status_text,
    build_bayes_calibration_apply_status_text,
    build_bayes_calibration_apply_message,
    build_calibrate_ensemble_apply_message,
    build_calibrate_ensemble_apply_status_text,
    build_ensemble_backtest_apply_status_text,
    build_ensemble_backtest_success_message,
    build_ensemble_weight_status_text,
    build_high_accuracy_strategy_backtest_message,
    build_high_accuracy_strategy_backtest_status_text,
    build_model_training_overview_text,
    build_export_message_text,
    build_export_status_text,
    build_play_model_backtest_apply_status_text,
    build_play_model_backtest_success_message,
    build_play_model_policy_apply_status_text,
    build_play_model_policy_apply_success_message,
    build_play_model_policy_status_text,
    build_play_model_training_status_text,
    build_play_threshold_apply_status_text,
    build_play_threshold_apply_success_message,
    build_play_threshold_status_text,
    build_threshold_bucket_tuning_apply_status_text,
    build_threshold_bucket_tuning_apply_message,
    summarize_prediction_coverage,
    build_coverage_monitor_text,
    build_coverage_status_suffix,
    build_coverage_guardrail_apply_status_text,
    build_coverage_guardrail_apply_message,
    read_latest_ops_daily_report,
    parse_ops_daily_summary_text,
    build_ops_trend_rows,
    build_ops_trend_text,
    build_threshold_change_table_text,
    export_ops_trend_csv,
    export_threshold_trend_csv,
    load_ops_heartbeat,
    build_ops_heartbeat_summary_text,
    open_text_view_window,
    build_c1_mode_status_text,
    build_main_list_sort_key,
    build_parlay_detail_lines,
    build_report_filename,
    build_train_play_models_apply_message,
    build_train_play_models_apply_status_text,
    build_training_health_action_rows,
    build_training_health_repair_result_text,
    build_training_model_gate_rows,
    training_health_action_button_text,
    build_train_xgb_apply_message,
    build_train_xgb_apply_status_text,
    build_xgb_status_text,
    build_diagnostics_text,
    build_match_details_text,
    build_pending_match_details_text,
    build_poisson_block,
    build_settlement_status_text,
    collect_visible_match_ids,
    configure_c1_tree_tags,
    ensure_report_dir,
    resolve_selected_prediction_for_details,
    resolve_current_filter,
    resolve_final_bindings,
    resolve_release_gate_pick,
    select_matches_for_export,
    show_c1_comparison_window,
    show_c1_release_window,
    show_c1_formal_recommendations_window,
    show_recent_settlements_window,
    sync_tree_c1_action_column,
    should_run_pre_export_analysis,
    build_user_center_sections,
    is_settlement_score_in_range,
    parse_settlement_score_inputs,
    refresh_parlay_recommendations,
    restore_c1_marks_for_matches,
    adapt_release_review_result,
    adapt_shadow_comparison_result,
    should_show_match_for_filter,
    compute_c1_action_counts,
    should_refresh_after_auto_settle,
    export_c1_availability_template,
    get_c1_availability_provider_statuses,
    get_c1_release_review_availability_guard,
    import_c1_availability_snapshots,
    load_c1_release_guard_report_history,
    should_auto_rerun_shadow_after_import,
    should_auto_rerun_shadow_after_sync,
    summarize_c1_rows,
    sync_c1_availability_sources,
    build_handicap_dashboard_text,
    build_handicap_shadow_report_filename,
    build_handicap_shadow_report_lines,
    build_accuracy_decomposition_artifacts,
    build_accuracy_decomposition_report_lines,
    build_accuracy_decomposition_report_filename,
    build_accuracy_decomposition_csv_text,
    build_accuracy_decomposition_csv_filename,
)

from .core import (
    AppMatch,
    FetchDiagnostics,
    auto_settle_finished_matches,
    calibrate_ensemble_weights_now,
    calibrate_play_thresholds_now,
    calibrate_play_thresholds_by_settlement_now,
    calibrate_play_thresholds_coverage_guardrail_now,
    calibrate_layered_filter_thresholds_now,
    calibrate_bayes_calibration_now,
    fetch_matches_v24,
    generate_mix_parlay_recommendations,
    get_ensemble_weight_status,
    get_active_parlay_recommendations,
    get_gate_metrics,
    get_play_threshold_status,
    get_play_model_training_status,
    get_play_model_policy_status,
    get_bayes_calibration_status,
    get_training_data_coverage_status,
    get_training_model_gate_status,
    get_recent_parlay_settlements,
    get_prediction_snapshot_migration_report,
    get_xgb_training_status,
    get_recent_settlements,
    run_high_accuracy_strategy_backtest,
    load_c1_comparison_marks_cache,
    load_prediction_snapshot_cache,
    migrate_prediction_snapshots,
    persist_prediction_snapshot,
    predict_match,
    run_ensemble_backtest,
    run_play_model_backtest,
    repair_training_data_health,
    save_c1_comparison_marks_cache,
    settle_match_result,
    calibrate_play_model_policy_now,
    train_play_models_now,
    train_xgb_v0_now,
)


class FootballPredictionApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("V24 足球预测 APP")
        self.root.geometry("1460x840")
        self.root.minsize(1240, 740)

        self.matches: list[AppMatch] = []
        self.predictions: dict[str, dict] = {}
        self.diagnostics = FetchDiagnostics()
        self.snapshot_migration_report: dict = {}
        self.c1_comparison_marks: dict[str, dict] = load_c1_comparison_marks_cache()
        self.c1_release_rows: list[dict] = []
        self.c1_release_summary: dict = {}
        self.c1_runtime_mode = get_runtime_mode()

        self.status_var = tk.StringVar(value="准备就绪")
        self.summary_var = tk.StringVar(value="等待加载赛事")
        self.c1_stats_var = tk.StringVar(value="显示 0/0")
        self.c1_filter_status_var = tk.StringVar(value="当前筛选: 全部")
        self.c1_mode_status_var = tk.StringVar(value=f"C1模式: {self.c1_runtime_mode}")
        self.c1_release_guard_var = tk.StringVar(value="放行门控: 未检查")
        self.formal_toolbar_var = tk.StringVar(value="只看正式建议(0)")
        self.pending_toolbar_var = tk.StringVar(value="只看待处理(0)")
        self.near_block_toolbar_var = tk.StringVar(value="只看接近阻断(0)")
        self.block_toolbar_var = tk.StringVar(value="只看阻断(0)")
        self.restore_all_toolbar_var = tk.StringVar(value="恢复全部")
        self.c1_stat_button_vars = {
            "正式建议": tk.StringVar(value="正式建议 0"),
            "待处理": tk.StringVar(value="待处理 0"),
            "补阵容": tk.StringVar(value="补阵容 0"),
            "观察": tk.StringVar(value="观察 0"),
            "可放行": tk.StringVar(value="可放行 0"),
            "接近阻断": tk.StringVar(value="接近阻断 0"),
            "阻断": tk.StringVar(value="阻断 0"),
        }
        self.c1_filter_var = tk.StringVar(value="全部")
        self.auto_settle_enabled = tk.BooleanVar(value=True)
        self.auto_settle_interval_min = tk.IntVar(value=8)
        self._auto_settle_after_id: str | None = None
        self._auto_settle_running = False
        self.user_center_window: tk.Toplevel | None = None
        self.ops_daily_window: tk.Toplevel | None = None
        self.ops_trend_window: tk.Toplevel | None = None
        self.c1_release_guard_history_window: tk.Toplevel | None = None
        self._busy_tasks: set[str] = set()

        self._configure_style()
        self._build_layout()
        self._refresh_c1_release_guard_status()
        self.refresh_matches()
        self._schedule_auto_settle()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.configure(bg="#eef3f8")
        style.configure("App.TFrame", background="#eef3f8")
        style.configure("Card.TFrame", background="#fbfdff")
        style.configure(
            "Title.TLabel",
            font=("Microsoft YaHei UI", 18, "bold"),
            background="#eef3f8",
            foreground="#0f172a",
        )
        style.configure(
            "Sub.TLabel",
            font=("Microsoft YaHei UI", 10),
            background="#eef3f8",
            foreground="#475569",
        )
        style.configure("Treeview", rowheight=30, font=("Microsoft YaHei UI", 10))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(header, text="V24 足球预测 APP | 第四阶段", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text="Ensemble(市场+ELO+Poisson+XGBv0) + 多维指标 + 赛果结算闭环",
            style="Sub.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        toolbar = ttk.Frame(outer, style="App.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(toolbar, text="刷新赛事", command=self.refresh_matches).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="分析选中", command=self.analyze_selected).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="分析全部", command=self.analyze_all).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="自动回收赛果", command=self.auto_settle_results).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="模型状态", command=self.show_model_training_overview).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="用户中心", command=self.open_user_center).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            toolbar,
            textvariable=self.formal_toolbar_var,
            command=lambda: self._set_c1_filter("正式建议"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            toolbar,
            textvariable=self.pending_toolbar_var,
            command=lambda: self._set_c1_filter("待处理"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            toolbar,
            textvariable=self.near_block_toolbar_var,
            command=lambda: self._set_c1_filter("接近阻断"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            toolbar,
            textvariable=self.block_toolbar_var,
            command=lambda: self._set_c1_filter("阻断"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            toolbar,
            textvariable=self.restore_all_toolbar_var,
            command=lambda: self._set_c1_filter("全部"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(toolbar, textvariable=self.c1_filter_status_var, style="Sub.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(toolbar, textvariable=self.c1_mode_status_var, style="Sub.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            toolbar,
            textvariable=self.c1_release_guard_var,
            command=self.show_c1_availability_provider_status,
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(toolbar, text="C1筛选", style="Sub.TLabel").pack(side=tk.RIGHT, padx=(8, 4))
        c1_filter = ttk.Combobox(
            toolbar,
            state="readonly",
            width=10,
            textvariable=self.c1_filter_var,
            values=["全部", "正式建议", "待处理", "补阵容", "观察", "复核分歧", "可放行", "接近阻断", "阻断"],
        )
        c1_filter.pack(side=tk.RIGHT, padx=(0, 12))
        c1_filter.bind("<<ComboboxSelected>>", lambda _event: self._apply_main_list_filter())
        ttk.Checkbutton(
            toolbar,
            text="自动轮询回收",
            variable=self.auto_settle_enabled,
            command=self._on_toggle_auto_settle,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Spinbox(
            toolbar,
            from_=2,
            to=60,
            width=4,
            textvariable=self.auto_settle_interval_min,
            command=self._on_toggle_auto_settle,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Label(toolbar, text="分钟", style="Sub.TLabel").pack(side=tk.RIGHT, padx=(4, 8))
        c1_stats = ttk.Frame(toolbar, style="App.TFrame")
        c1_stats.pack(side=tk.RIGHT, padx=(0, 12))
        ttk.Label(c1_stats, text="C1统计", style="Sub.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            c1_stats,
            textvariable=self.c1_stat_button_vars["正式建议"],
            command=lambda: self._set_c1_filter("正式建议"),
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            c1_stats,
            textvariable=self.c1_stat_button_vars["待处理"],
            command=lambda: self._set_c1_filter("待处理"),
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 4))
        for action in ["补阵容", "观察", "可放行", "接近阻断", "阻断"]:
            ttk.Button(
                c1_stats,
                textvariable=self.c1_stat_button_vars[action],
                command=lambda value=action: self._set_c1_filter(value),
                width=10,
            ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(c1_stats, text="全部", command=lambda: self._set_c1_filter("全部"), width=6).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(c1_stats, textvariable=self.c1_stats_var, style="Sub.TLabel").pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(toolbar, textvariable=self.summary_var, style="Sub.TLabel").pack(side=tk.RIGHT)

        content = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(content, style="Card.TFrame", padding=12)
        right = ttk.Frame(content, style="Card.TFrame", padding=12)
        content.add(left, weight=3)
        content.add(right, weight=2)

        columns = (
            "date",
            "time",
            "league",
            "home",
            "away",
            "pick",
            "high_strategy",
            "c1_action",
            "confidence",
            "upset",
            "stability",
            "signal",
        )
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        headings = {
            "date": "日期",
            "time": "时间",
            "league": "联赛",
            "home": "主队",
            "away": "客队",
            "pick": "推荐",
            "high_strategy": "高准策略",
            "c1_action": "C1动作",
            "confidence": "置信度",
            "upset": "冷门指数",
            "stability": "稳定指数",
            "signal": "信心指数",
        }
        widths = {
            "date": 96,
            "time": 72,
            "league": 86,
            "home": 126,
            "away": 126,
            "pick": 70,
            "high_strategy": 104,
            "c1_action": 92,
            "confidence": 84,
            "upset": 92,
            "stability": 92,
            "signal": 92,
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", lambda _event: self.analyze_selected())

        tk.Label(
            right,
            text="诊断与分析详情",
            font=("Microsoft YaHei UI", 13, "bold"),
            bg="#fbfdff",
            fg="#111827",
        ).pack(anchor=tk.W)

        self.inline_actions_container = ttk.Frame(right, style="Card.TFrame")

        self.details = tk.Text(
            right,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            bg="#fbfdff",
            fg="#1f2937",
            relief=tk.FLAT,
            padx=4,
            pady=8,
        )
        detail_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.details.yview)
        self.details.configure(yscrollcommand=detail_scroll.set)
        self.details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(10, 0))
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(10, 0))

        footer = ttk.Frame(outer, style="App.TFrame")
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Sub.TLabel").pack(anchor=tk.W)

    def refresh_matches(self) -> None:
        self._run_background(
            task_key="refresh",
            start_status="正在按 V24 严格模式获取赛事...",
            worker=self._refresh_matches_worker,
            on_success=self._apply_refresh_matches,
            error_title="刷新赛事失败",
        )

    def _refresh_matches_worker(self) -> dict:
        result = fetch_matches_v24(strict_today=True)
        migration_report = migrate_prediction_snapshots()
        snapshot_sync = self._ensure_prediction_snapshots_for_matches(result.matches)
        return {
            "fetch_result": result,
            "migration_report": migration_report,
            "snapshot_sync": snapshot_sync,
        }

    def _ensure_prediction_snapshots_for_matches(self, matches: list[AppMatch]) -> dict:
        if not matches:
            return {"created": 0, "updated": 0}
        existing = load_prediction_snapshot_cache()
        created = 0
        updated = 0
        for match in matches:
            cached_prediction = existing.get(match.match_id)
            if isinstance(cached_prediction, dict):
                persist_prediction_snapshot(match, cached_prediction)
                updated += 1
                continue
            prediction = predict_match(match)
            persist_prediction_snapshot(match, prediction)
            created += 1
        return {"created": created, "updated": updated}

    def _apply_refresh_matches(self, payload: dict) -> None:
        result = payload.get("fetch_result")
        if result is None:
            return
        self.matches = result.matches
        self.diagnostics = result.diagnostics
        self.predictions = {}
        self.c1_release_rows = []
        self.c1_release_summary = {}
        self._refresh_c1_release_guard_status()
        self.snapshot_migration_report = payload.get("migration_report", {}) or {}
        snapshot_sync = payload.get("snapshot_sync", {}) or {}

        self.tree.delete(*self.tree.get_children())
        for match in self.matches:
            self.tree.insert(
                "",
                tk.END,
                iid=match.match_id,
                values=(
                    match.match_date,
                    match.match_time,
                    match.league,
                    match.home_team,
                    match.away_team,
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                ),
            )
        restored_marks = self._restore_c1_marks_for_visible_matches()
        self._apply_main_list_filter()

        created = int(snapshot_sync.get("created", 0))
        updated = int(snapshot_sync.get("updated", 0))
        if self.matches:
            self.summary_var.set(f"当前 {len(self.matches)} 场 | 数据源 {self.diagnostics.source}")
            if created > 0 or updated > 0:
                extra = f" | 恢复 C1标记 {restored_marks} 场" if restored_marks > 0 else ""
                self.status_var.set(f"快照同步完成: 新增 {created} 场 | 补齐 source_id {updated} 场{extra}")
            else:
                extra = f" | 恢复 C1标记 {restored_marks} 场" if restored_marks > 0 else ""
                self.status_var.set(f"已通过 V24 校验加载 {len(self.matches)} 场赛事{extra}")
            first = self.matches[0]
            self.tree.selection_set(first.match_id)
            self.tree.focus(first.match_id)
            self.on_tree_select()
        else:
            self.summary_var.set("当前 0 场 | 未找到有效赛事源")
            self.status_var.set("没有通过 V24 校验的赛事数据")
            self._show_diagnostics_only()

    def _run_background(
        self,
        task_key: str,
        start_status: str,
        worker,
        on_success,
        error_title: str,
    ) -> None:
        if task_key in self._busy_tasks:
            return

        self._busy_tasks.add(task_key)
        if start_status:
            self.status_var.set(start_status)

        def runner() -> None:
            try:
                payload = worker()
            except Exception as exc:
                self.root.after(0, lambda: self._finish_background_error(task_key, error_title, exc))
                return
            self.root.after(0, lambda: self._finish_background_success(task_key, on_success, payload))

        threading.Thread(target=runner, daemon=True).start()

    def _finish_background_success(self, task_key: str, on_success, payload) -> None:
        self._busy_tasks.discard(task_key)
        on_success(payload)

    def _finish_background_error(self, task_key: str, error_title: str, exc: Exception) -> None:
        self._busy_tasks.discard(task_key)
        if task_key == "auto_settle":
            self._auto_settle_running = False
            self._schedule_auto_settle()
        self.status_var.set(f"{error_title}: {exc}")
        messagebox.showerror(error_title, str(exc))

    def selected_match(self) -> AppMatch | None:
        selection = self.tree.selection()
        if not selection:
            return None

        selected_id = selection[0]
        for match in self.matches:
            if match.match_id == selected_id:
                return match
        return None

    def open_user_center(self) -> None:
        _app_open_user_center_final(self)

    def _close_user_center(self) -> None:
        if self.user_center_window is not None and self.user_center_window.winfo_exists():
            self.user_center_window.destroy()
        self.user_center_window = None
        self._clear_inline_actions()

    def analyze_selected(self) -> None:
        match = self.selected_match()
        if match is None:
            messagebox.showinfo("提示", "当前没有可分析的有效赛事。")
            return

        prediction = predict_match(match)
        self.predictions[match.match_id] = prediction
        persist_prediction_snapshot(match, prediction)
        self._update_tree_row(match, prediction)
        self._show_match_details(match, prediction)
        self.status_var.set(f"已完成分析: {match.home_team} vs {match.away_team}")

    def analyze_all(self) -> None:
        if not self.matches:
            messagebox.showinfo("提示", "当前没有通过校验的赛事可供分析。")
            return

        for match in self.matches:
            prediction = predict_match(match)
            self.predictions[match.match_id] = prediction
            persist_prediction_snapshot(match, prediction)
            self._update_tree_row(match, prediction)

        selected = self.selected_match() or self.matches[0]
        self._show_match_details(selected, self.predictions[selected.match_id])
        self.status_var.set(f"批量分析完成，共 {len(self.matches)} 场")

    def settle_selected_result(self) -> None:
        _app_settle_selected_result(self)

    def show_recent_settlements(self) -> None:
        _app_show_recent_settlements_table(self)

    def show_handicap_monitor(self) -> None:
        _app_show_handicap_monitor(self)

    def show_coverage_monitor(self) -> None:
        _app_show_coverage_monitor(self)

    def show_ops_daily_report(self) -> None:
        _app_show_ops_daily_report(self)

    def show_ops_weekly_trend(self) -> None:
        _app_show_ops_weekly_trend(self)

    def run_threshold_coverage_guardrail(self) -> None:
        _app_run_threshold_coverage_guardrail(self)

    def export_handicap_shadow_report(self) -> None:
        _app_export_handicap_shadow_report(self)

    def export_accuracy_decomposition_report(self) -> None:
        _app_export_accuracy_decomposition_report(self)

    def auto_settle_results(self) -> None:
        self._run_auto_settle(show_popup=True)

    def _run_auto_settle(self, show_popup: bool) -> None:
        self._run_background(
            task_key="auto_settle",
            start_status="正在自动回收赛果...",
            worker=lambda: auto_settle_finished_matches(
                prediction_cache=self.predictions if self.predictions else None,
                lookback_days=2,
            ),
            on_success=lambda result: self._apply_auto_settle_result(result, show_popup),
            error_title="自动回收赛果失败",
        )

    def _apply_auto_settle_result(self, result: dict, show_popup: bool) -> None:
        if not show_popup:
            self._auto_settle_running = False
            self._schedule_auto_settle()
        self.status_var.set(build_auto_settle_status_text(result))

        if show_popup:
            messagebox.showinfo("自动回收赛果", build_auto_settle_popup_message(result))

        if should_refresh_after_auto_settle(
            new_settled=int(result.get("new_settled", 0) or 0),
            has_matches=bool(self.matches),
        ):
            self.refresh_matches()

    def _on_toggle_auto_settle(self) -> None:
        self._schedule_auto_settle()
        if self.auto_settle_enabled.get():
            self.status_var.set(f"自动轮询已开启，每 {self.auto_settle_interval_min.get()} 分钟回收赛果")
        else:
            self.status_var.set("自动轮询已关闭")

    def _schedule_auto_settle(self) -> None:
        if self._auto_settle_after_id is not None:
            try:
                self.root.after_cancel(self._auto_settle_after_id)
            except Exception:
                pass
            self._auto_settle_after_id = None

        if not self.auto_settle_enabled.get():
            return

        interval_min = max(2, min(int(self.auto_settle_interval_min.get()), 60))
        self.auto_settle_interval_min.set(interval_min)
        self._auto_settle_after_id = self.root.after(interval_min * 60 * 1000, self._auto_settle_tick)

    def _auto_settle_tick(self) -> None:
        self._auto_settle_after_id = None
        if not self.auto_settle_enabled.get():
            return
        if self._auto_settle_running or "auto_settle" in self._busy_tasks:
            self._schedule_auto_settle()
            return

        self._auto_settle_running = True
        self._run_auto_settle(show_popup=False)

    def _on_close(self) -> None:
        self._close_user_center()
        _app_close_ops_daily_window(self)
        _app_close_ops_trend_window(self)
        if self._auto_settle_after_id is not None:
            try:
                self.root.after_cancel(self._auto_settle_after_id)
            except Exception:
                pass
            self._auto_settle_after_id = None
        self.root.destroy()

    def _xgb_status_text(self) -> str:
        return build_xgb_status_text(get_xgb_training_status())

    def show_xgb_status(self) -> None:
        messagebox.showinfo("XGBoost 状态", self._xgb_status_text())

    def show_model_training_overview(self) -> None:
        self._close_user_center()
        coverage_status = get_training_data_coverage_status()
        training_gate_status = get_training_model_gate_status(coverage_status)
        self._write_details(
            build_model_training_overview_text(
                xgb_status=get_xgb_training_status(),
                play_model_status=get_play_model_training_status(),
                ensemble_status=get_ensemble_weight_status(),
                bayes_status=get_bayes_calibration_status(),
                threshold_status=get_play_threshold_status(),
                policy_status=get_play_model_policy_status(),
                coverage_status=coverage_status,
                training_gate_status=training_gate_status,
            )
        )
        self._show_training_health_repair_actions(coverage_status, training_gate_status)
        self.status_var.set("已显示模型训练状态总览")

    def _show_training_health_repair_actions(self, coverage_status: dict, training_gate_status: dict | None = None) -> None:
        action_rows = build_training_health_action_rows(coverage_status)
        gate_rows = build_training_model_gate_rows(training_gate_status or {})
        if not action_rows:
            return
        container = self.inline_actions_container
        container.pack(fill=tk.X, pady=(8, 2), before=self.details)
        section = ttk.LabelFrame(container, text="训练健康修复入口", padding=8)
        section.pack(fill=tk.X, pady=(0, 8))
        seen_actions: set[str] = set()
        button_index = 0
        for row in action_rows:
            action_key = str(row.get("action_key") or "refresh_training_health")
            if action_key in seen_actions:
                continue
            seen_actions.add(action_key)
            button = ttk.Button(
                section,
                text=training_health_action_button_text(action_key),
                command=lambda key=action_key: self._run_training_health_repair_action(key),
            )
            button.grid(row=button_index // 4, column=button_index % 4, sticky=tk.W, padx=(0, 8), pady=(0, 6))
            button_index += 1
        for row in gate_rows:
            action_key = str(row.get("action_key") or "")
            if action_key not in {"train_xgb", "train_play_models", "run_play_model_backtest"} or action_key in seen_actions:
                continue
            seen_actions.add(action_key)
            button = ttk.Button(
                section,
                text=training_health_action_button_text(action_key),
                command=lambda key=action_key: self._run_training_health_repair_action(key),
            )
            button.grid(row=button_index // 4, column=button_index % 4, sticky=tk.W, padx=(0, 8), pady=(0, 6))
            button_index += 1
        ttk.Button(
            section,
            text=training_health_action_button_text("refresh_training_health"),
            command=self.show_model_training_overview,
        ).grid(row=button_index // 4, column=button_index % 4, sticky=tk.W, padx=(0, 8), pady=(0, 6))

    def _run_training_health_repair_action(self, action_key: str) -> None:
        if action_key == "refresh_training_health":
            self.show_model_training_overview()
            return
        if action_key == "run_play_model_backtest":
            self.run_play_model_backtest()
            return
        if action_key == "train_xgb":
            self.train_xgb_now()
            return
        if action_key == "train_play_models":
            self.train_play_models()
            return
        if action_key == "import_historical_samples":
            self._import_training_health_samples()
            return
        self._run_background(
            task_key=f"training_health_repair:{action_key}",
            start_status=f"正在执行训练健康修复: {training_health_action_button_text(action_key)}...",
            worker=lambda: repair_training_data_health(action_key),
            on_success=self._apply_training_health_repair_result,
            error_title="训练健康修复失败",
        )

    def _import_training_health_samples(self) -> None:
        path_text = filedialog.askopenfilename(
            title="选择历史赛果文件",
            filetypes=[
                ("History files", "*.csv *.json *.jsonl"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json *.jsonl"),
                ("All files", "*.*"),
            ],
        )
        if not path_text:
            return
        input_path = Path(path_text)
        self._run_background(
            task_key="training_health_repair:import_historical_samples",
            start_status="正在导入历史赛果样本...",
            worker=lambda: repair_training_data_health("import_historical_samples", input_path=input_path),
            on_success=self._apply_training_health_repair_result,
            error_title="训练健康修复失败",
        )

    def _apply_training_health_repair_result(self, result: dict) -> None:
        result_text = build_training_health_repair_result_text(result)
        self.show_model_training_overview()
        self.status_var.set(result_text.splitlines()[0])
        messagebox.showinfo("训练健康修复", result_text)

    def train_xgb_now(self) -> None:
        self._run_background(
            task_key="train_xgb",
            start_status="正在训练 XGB...",
            worker=train_xgb_v0_now,
            on_success=self._apply_train_xgb_result,
            error_title="训练XGB失败",
        )

    def _apply_train_xgb_result(self, result: dict) -> None:
        self.status_var.set(build_train_xgb_apply_status_text(result))
        messagebox.showinfo(
            "训练XGB",
            build_train_xgb_apply_message(result, self._xgb_status_text()),
        )

    def export_current_report(self) -> None:
        _app_export_visible_report(self)

    def on_tree_select(self, _event=None) -> None:
        match = self.selected_match()
        if match is None:
            self._show_diagnostics_only()
            return

        prediction = self.predictions.get(match.match_id)
        if prediction:
            self._show_match_details(match, prediction)
            return

        self._write_details(build_pending_match_details_text(diagnostics_text=self._diagnostics_text(), match=match))

    def _update_tree_row(self, match: AppMatch, prediction: dict) -> None:
        indices = prediction.get("indices", {})
        high_strategy = prediction.get("high_accuracy_strategy", {}) if isinstance(prediction.get("high_accuracy_strategy"), dict) else {}
        high_strategy_text = "-"
        if high_strategy.get("enabled"):
            high_strategy_text = high_strategy.get("summary") or ("命中" if high_strategy.get("active") else "未命中")
        self.tree.item(
            match.match_id,
            values=(
                match.match_date,
                match.match_time,
                match.league,
                match.home_team,
                match.away_team,
                self._release_gate_pick_text(match.match_id, prediction),
                high_strategy_text,
                self._current_c1_action_text(match.match_id),
                f"{prediction['confidence']:.1%}",
                f"{indices.get('upset_index', 0):.1%}",
                f"{indices.get('stability_index', 0):.1%}",
                f"{indices.get('confidence_index', 0):.1%}",
            ),
        )
        self._apply_main_list_filter()

    def _current_c1_action_text(self, match_id: str) -> str:
        if not hasattr(self, "c1_comparison_marks"):
            return "-"
        mark = getattr(self, "c1_comparison_marks", {}).get(match_id, {}) or {}
        return str(mark.get("suggested_action", "-")) if isinstance(mark, dict) else "-"

    def _c1_action_priority(self, action: str) -> int:
        priority = {
            "阻断": 0,
            "接近阻断": 1,
            "补阵容": 2,
            "复核分歧": 3,
            "观察": 4,
            "可放行": 5,
            "-": 6,
        }
        return priority.get(str(action or "-"), 7)

    def _release_confidence_priority(self, match_id: str) -> float:
        row = self._current_release_row(match_id)
        if not row:
            return -1.0
        return float(row.get("top_confidence", 0) or 0)

    def _set_c1_filter(self, value: str) -> None:
        if hasattr(self, "c1_filter_var"):
            self.c1_filter_var.set(value)
        self._apply_main_list_filter()

    def _apply_main_list_filter(self) -> None:
        selected = self.c1_filter_var.get() if hasattr(self, "c1_filter_var") else "全部"
        self.c1_filter_status_var.set(f"当前筛选: {selected}")
        visible_matches: list[AppMatch] = []
        release_allowed_ids = self._release_allowed_match_ids()
        for match in self.matches:
            if not self.tree.exists(match.match_id):
                continue
            action = self._current_c1_action_text(match.match_id)
            release_allowed = match.match_id in release_allowed_ids
            visible = should_show_match_for_filter(
                selected_filter=selected,
                action=action,
                release_allowed=release_allowed,
            )
            if visible:
                visible_matches.append(match)
                self.tree.reattach(match.match_id, "", tk.END)
            else:
                self.tree.detach(match.match_id)
        visible_matches.sort(
            key=lambda item: build_main_list_sort_key(
                selected_filter=selected,
                action=self._current_c1_action_text(item.match_id),
                release_confidence=self._release_confidence_priority(item.match_id),
                match=item,
                action_priority_fn=self._c1_action_priority,
            )
        )
        for index, match in enumerate(visible_matches):
            self.tree.move(match.match_id, "", index)
        self._refresh_c1_action_stats(visible_count=len(visible_matches))

    def _refresh_c1_action_stats(self, *, visible_count: int | None = None) -> None:
        release_allowed_ids = self._release_allowed_match_ids()
        active_release_allowed_ids = self._active_release_allowed_match_ids()
        counts, pending_count, formal_count, total = compute_c1_action_counts(
            matches=self.matches,
            action_text_by_match_id=self._current_c1_action_text,
            release_allowed_ids=release_allowed_ids,
        )
        formal_var = self.c1_stat_button_vars.get("正式建议")
        if formal_var is not None:
            formal_var.set(f"正式建议 {formal_count}")
        self.formal_toolbar_var.set(f"只看正式建议({formal_count})")
        pending_var = self.c1_stat_button_vars.get("待处理")
        if pending_var is not None:
            pending_var.set(f"待处理 {pending_count}")
        self.pending_toolbar_var.set(f"只看待处理({pending_count})")
        self.near_block_toolbar_var.set(f"只看接近阻断({counts['接近阻断']})")
        self.block_toolbar_var.set(f"只看阻断({counts['阻断']})")
        self.restore_all_toolbar_var.set("恢复全部")
        for action, count in counts.items():
            button_var = self.c1_stat_button_vars.get(action)
            if button_var is not None:
                button_var.set(f"{action} {count}")
        if visible_count is None:
            visible_count = total
        self.c1_stats_var.set(f"显示 {visible_count}/{total}")
        self.c1_mode_status_var.set(
            build_c1_mode_status_text(
                runtime_mode=self.c1_runtime_mode,
                active_allowed_count=len(active_release_allowed_ids),
                release_allowed_count=len(release_allowed_ids),
            )
        )

    def _refresh_c1_release_guard_status(self, guard: dict | None = None) -> dict:
        current_guard = guard if isinstance(guard, dict) else get_c1_release_review_availability_guard(PROJECT_ROOT)
        if hasattr(self, "c1_release_guard_var"):
            self.c1_release_guard_var.set(build_c1_release_review_guard_status_text(current_guard))
        return current_guard

    def _write_c1_release_guard_block_report(self, guard: dict, *, matches_count: int) -> Path:
        report_dir = PROJECT_ROOT / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        report_path = report_dir / build_c1_release_guard_report_filename(now)
        report_path.write_text(
            "\n".join(build_c1_release_guard_report_lines(guard, matches_count=matches_count, generated_at=now)),
            encoding="utf-8",
        )
        return report_path

    def _restore_c1_marks_for_visible_matches(self) -> int:
        if not hasattr(self, "c1_comparison_marks"):
            self.c1_comparison_marks = {}
        return restore_c1_marks_for_matches(
            tree=self.tree,
            matches=self.matches,
            c1_comparison_marks=self.c1_comparison_marks,
            action_text_by_match_id=self._current_c1_action_text,
        )

    def _diagnostics_text(self) -> str:
        migration = self.snapshot_migration_report or get_prediction_snapshot_migration_report()
        return build_diagnostics_text(
            diagnostics=self.diagnostics,
            snapshot_migration_report=migration,
            xgb_status=get_xgb_training_status(),
        )

    def _show_diagnostics_only(self) -> None:
        self._write_details(
            self._diagnostics_text()
            + "\n\n"
            + "当前没有展示任何赛事，因为系统已切换到 V24 严格模式。\n"
            + "只有通过赛事源校验和页面字段校验的数据，才会进入列表。"
        )

    def _format_poisson_block(self, poisson: dict) -> str:
        return _app_format_poisson_block(self, poisson)

    def _show_match_details(self, match: AppMatch, prediction: dict, settlement: dict | None = None) -> None:
        _app_show_match_details_with_parlays(self, match, prediction, settlement)

    def _clear_inline_actions(self) -> None:
        container = getattr(self, "inline_actions_container", None)
        if container is None:
            return
        for child in container.winfo_children():
            child.destroy()
        container.pack_forget()

    def _write_details(self, content: str, *, clear_actions: bool = True) -> None:
        if clear_actions:
            self._clear_inline_actions()
        self.details.config(state=tk.NORMAL)
        self.details.delete("1.0", tk.END)
        self.details.insert("1.0", content)
        self.details.config(state=tk.DISABLED)


def _app_mark_text(self: FootballPredictionApp, value: object) -> str:
    if value is True:
        return "Y"
    if value is False:
        return "N"
    return "-"


def _app_prediction_summary_fields(self: FootballPredictionApp, prediction: dict) -> tuple[str, float, str, float, str, float]:
    poisson = prediction.get("poisson", {})

    total_goals_pick = str(prediction.get("total_goals_recommendation") or "-")
    total_goals_conf = float(prediction.get("total_goals_confidence", 0) or 0)
    if total_goals_pick == "-":
        top_total_goals = poisson.get("top_total_goals", [])
        if top_total_goals:
            top_goal = top_total_goals[0]
            total_goals_pick = f"{top_goal.get('goals', '-')}球"
            total_goals_conf = float(top_goal.get("probability", 0) or 0)

    score_pick = str(prediction.get("score_recommendation") or "-")
    score_conf = float(prediction.get("score_confidence", 0) or 0)
    if score_pick == "-":
        top_scores = poisson.get("top_scores", [])
        if top_scores:
            top_score = top_scores[0]
            score_pick = str(top_score.get("score", "-"))
            score_conf = float(top_score.get("probability", 0) or 0)

    htft_pick = str(prediction.get("htft_recommendation") or "-")
    htft_conf = float(prediction.get("htft_confidence", 0) or 0)
    if htft_pick == "-":
        htft_top = poisson.get("htft_top", [])
        if htft_top:
            top_htft = htft_top[0]
            htft_pick = str(top_htft.get("label", "-"))
            htft_conf = float(top_htft.get("probability", 0) or 0)

    return total_goals_pick, total_goals_conf, htft_pick, htft_conf, score_pick, score_conf


def _app_format_poisson_block(self: FootballPredictionApp, poisson: dict) -> str:
    return build_poisson_block(poisson)


def _app_show_match_details(
    self: FootballPredictionApp,
    match: AppMatch,
    prediction: dict,
    settlement: dict | None = None,
) -> None:
    poisson = prediction.get("poisson", {})
    total_goals_pick, total_goals_conf, htft_pick, htft_conf, score_pick, score_conf = self._prediction_summary_fields(
        prediction
    )
    gated_recommendation = self._release_gate_pick_text(match.match_id, prediction)
    release_row = self._current_release_row(match.match_id)
    details = build_match_details_text(
        diagnostics_text=self._diagnostics_text(),
        match=match,
        prediction=prediction,
        total_goals_pick=total_goals_pick,
        total_goals_conf=total_goals_conf,
        htft_pick=htft_pick,
        htft_conf=htft_conf,
        score_pick=score_pick,
        score_conf=score_conf,
        gated_recommendation=gated_recommendation,
        release_row=release_row,
        settlement=settlement,
        mark_text_fn=self._mark_text,
        poisson_block_text=self._format_poisson_block(poisson),
    )
    self._write_details(details)


def _app_settle_selected_result(self: FootballPredictionApp) -> None:
    match = self.selected_match()
    if match is None:
        messagebox.showinfo("提示", "请先选择一场比赛再录入赛果。")
        return

    dialog = tk.Toplevel(self.root)
    dialog.title("录入赛果结算")
    dialog.geometry("360x220")
    dialog.transient(self.root)
    dialog.grab_set()

    ttk.Label(dialog, text=f"{match.home_team} vs {match.away_team}", font=("Microsoft YaHei UI", 11, "bold")).pack(
        pady=(14, 8)
    )
    ttk.Label(dialog, text=f"{match.match_date} {match.match_time} | {match.league}").pack(pady=(0, 12))

    score_row = ttk.Frame(dialog)
    score_row.pack(pady=(0, 12))
    ttk.Label(score_row, text="主队进球").pack(side=tk.LEFT)
    home_entry = ttk.Entry(score_row, width=5)
    home_entry.insert(0, "0")
    home_entry.pack(side=tk.LEFT, padx=(8, 16))
    ttk.Label(score_row, text="客队进球").pack(side=tk.LEFT)
    away_entry = ttk.Entry(score_row, width=5)
    away_entry.insert(0, "0")
    away_entry.pack(side=tk.LEFT, padx=(8, 0))

    def on_submit() -> None:
        try:
            home_goals, away_goals = parse_settlement_score_inputs(home_entry.get(), away_entry.get())
        except ValueError:
            messagebox.showerror("输入错误", "请填写整数比分。", parent=dialog)
            return

        if not is_settlement_score_in_range(home_goals, away_goals):
            messagebox.showerror("输入错误", "比分范围需在 0-20 之间。", parent=dialog)
            return

        prediction = self.predictions.get(match.match_id) or predict_match(match)
        self.predictions[match.match_id] = prediction
        persist_prediction_snapshot(match, prediction)

        settlement = settle_match_result(
            match=match,
            home_goals=home_goals,
            away_goals=away_goals,
            prediction=prediction,
        )

        refreshed_prediction = predict_match(match)
        self.predictions[match.match_id] = refreshed_prediction
        self._update_tree_row(match, refreshed_prediction)
        self._show_match_details(match, refreshed_prediction, settlement=settlement)

        self.status_var.set(
            build_settlement_status_text(
                match=match,
                home_goals=home_goals,
                away_goals=away_goals,
                settlement=settlement,
                mark_text_fn=self._mark_text,
            )
        )
        dialog.destroy()

    action_row = ttk.Frame(dialog)
    action_row.pack(pady=(6, 0))
    ttk.Button(action_row, text="确认结算", command=on_submit).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(action_row, text="取消", command=dialog.destroy).pack(side=tk.LEFT)


_ORIGINAL_ANALYZE_SELECTED = FootballPredictionApp.analyze_selected
_ORIGINAL_ANALYZE_ALL = FootballPredictionApp.analyze_all


def _refresh_parlay_recommendations_ui(self: FootballPredictionApp) -> list[dict]:
    self.parlay_recommendations = refresh_parlay_recommendations(
        matches=self.matches,
        predictions=self.predictions,
        active_release_allowed_ids=self._active_release_allowed_match_ids(),
        generator_fn=generate_mix_parlay_recommendations,
        limit=5,
    )
    return self.parlay_recommendations


def _app_build_analysis_status_text(self: FootballPredictionApp, base_status: str, parlay_count: int) -> str:
    return build_analysis_status_text(
        base_status=base_status,
        gate_active=is_release_gate_active(self.c1_runtime_mode),
        allowed_count=len(self._release_allowed_match_ids()),
        active_allowed_count=len(self._active_release_allowed_match_ids()),
        parlay_count=parlay_count,
    )


def _app_show_match_details_with_parlays(
    self: FootballPredictionApp,
    match: AppMatch,
    prediction: dict,
    settlement: dict | None = None,
) -> None:
    _app_show_match_details(self, match, prediction, settlement)
    parlays = getattr(self, "parlay_recommendations", [])
    if not parlays:
        return
    lines = build_parlay_detail_lines(parlays, limit=5)
    if not lines:
        return
    current = self.details.get("1.0", tk.END).rstrip()
    self._write_details(current + "\n\n" + "\n".join(lines))


def _app_analyze_selected_with_parlays(self: FootballPredictionApp) -> None:
    _ORIGINAL_ANALYZE_SELECTED(self)
    gated_matches = [match for match in self.matches if match.match_id in self.predictions]
    self._refresh_release_gate_after_analysis(gated_matches)
    parlays = _refresh_parlay_recommendations_ui(self)
    match = self.selected_match()
    if match is not None and match.match_id in self.predictions:
        self._show_match_details(match, self.predictions[match.match_id])
    summary = _app_coverage_summary(self)
    status = _app_build_analysis_status_text(self, self.status_var.get(), len(parlays))
    self.status_var.set(f"{status} | {build_coverage_status_suffix(summary)}")


def _app_analyze_all_with_parlays(self: FootballPredictionApp) -> None:
    _ORIGINAL_ANALYZE_ALL(self)
    gated_matches = [match for match in self.matches if match.match_id in self.predictions]
    self._refresh_release_gate_after_analysis(gated_matches)
    parlays = _refresh_parlay_recommendations_ui(self)
    match = self.selected_match() or (self.matches[0] if self.matches else None)
    if match is not None and match.match_id in self.predictions:
        self._show_match_details(match, self.predictions[match.match_id])
    summary = _app_coverage_summary(self)
    status = _app_build_analysis_status_text(self, self.status_var.get(), len(parlays))
    self.status_var.set(f"{status} | {build_coverage_status_suffix(summary)}")


def _app_show_recent_settlements_table(self: FootballPredictionApp) -> None:
    single_items = get_recent_settlements(limit=20)
    parlay_items = get_recent_parlay_settlements(limit=20)
    gate = get_gate_metrics(window=20)
    if not single_items and not parlay_items:
        messagebox.showinfo("近期结算", "暂无结算记录。")
        return
    show_recent_settlements_window(
        root=self.root,
        single_items=single_items,
        parlay_items=parlay_items,
        gate=gate,
        mark_text_fn=self._mark_text,
    )


def _app_show_handicap_monitor(self: FootballPredictionApp) -> None:
    settlements = get_recent_settlements(limit=200)
    if not settlements:
        messagebox.showinfo("让球专项看板", "暂无结算记录。")
        return
    text = build_handicap_dashboard_text(settlements, window=30, breaker_threshold=3)
    messagebox.showinfo("让球专项看板", text)


def _app_coverage_summary(self: FootballPredictionApp) -> dict:
    formal_rows = self._build_formal_release_rows() if hasattr(self, "_build_formal_release_rows") else []
    formal_count = len(formal_rows) if isinstance(formal_rows, list) else 0
    return summarize_prediction_coverage(
        predictions=self.predictions,
        formal_count=formal_count,
    )


def _app_show_coverage_monitor(self: FootballPredictionApp) -> None:
    if not self.predictions:
        messagebox.showinfo("覆盖率监控", "当前没有分析结果，请先执行分析。")
        return
    summary = _app_coverage_summary(self)
    messagebox.showinfo("覆盖率监控", build_coverage_monitor_text(summary))


def _app_close_ops_daily_window(self: FootballPredictionApp) -> None:
    if self.ops_daily_window is not None and self.ops_daily_window.winfo_exists():
        self.ops_daily_window.destroy()
    self.ops_daily_window = None


def _app_close_ops_trend_window(self: FootballPredictionApp) -> None:
    if self.ops_trend_window is not None and self.ops_trend_window.winfo_exists():
        self.ops_trend_window.destroy()
    self.ops_trend_window = None


def _app_close_c1_release_guard_history_window(self: FootballPredictionApp) -> None:
    if self.c1_release_guard_history_window is not None and self.c1_release_guard_history_window.winfo_exists():
        self.c1_release_guard_history_window.destroy()
    self.c1_release_guard_history_window = None


def _app_show_ops_daily_report(self: FootballPredictionApp) -> None:
    report_dir = ensure_report_dir(PROJECT_ROOT)
    payload = read_latest_ops_daily_report(report_dir)
    if not bool(payload.get("ok")):
        messagebox.showinfo("运营日报", "未找到运营日报，请先运行调度器日报。")
        return
    heartbeat = load_ops_heartbeat(report_dir)
    header = f"{payload.get('path', '-')}\n{build_ops_heartbeat_summary_text(heartbeat)}"

    def _export_daily_csv() -> None:
        _app_export_ops_daily_csv(self, report_dir=report_dir, payload=payload)

    self.ops_daily_window = open_text_view_window(
        root=self.root,
        existing_window=self.ops_daily_window,
        title="运营日报",
        header=header,
        content=str(payload.get("text", "")),
        on_close=lambda: _app_close_ops_daily_window(self),
        actions=[("导出CSV", _export_daily_csv)],
        width=1020,
        height=700,
    )


def _app_show_ops_weekly_trend(self: FootballPredictionApp) -> None:
    report_dir = ensure_report_dir(PROJECT_ROOT)
    days = 7
    rows = build_ops_trend_rows(report_dir, days=days)
    if not rows:
        messagebox.showinfo("7天趋势", "未找到可用运营日报，请先运行调度器日报。")
        return
    trend_text = build_ops_trend_text(report_dir, days=days)
    threshold_table = build_threshold_change_table_text(rows)
    heartbeat = load_ops_heartbeat(report_dir)
    threshold_days = sum(
        1
        for row in rows
        if any(
            isinstance(row.get(key), (float, int))
            for key in ("threshold_1x2", "threshold_handicap", "threshold_total_goals", "threshold_score", "threshold_htft")
        )
    )
    header = (
        build_ops_heartbeat_summary_text(heartbeat)
        + f"\nThreshold snapshots: {threshold_days}/{len(rows)} days"
    )

    def _export_weekly_csv() -> None:
        _app_export_ops_trend_csv(self, report_dir=report_dir, rows=rows, days=days)

    def _export_threshold_csv() -> None:
        _app_export_threshold_trend_csv(self, report_dir=report_dir, rows=rows, days=days)

    self.ops_trend_window = open_text_view_window(
        root=self.root,
        existing_window=self.ops_trend_window,
        title="运营7天趋势",
        header=header,
        content=trend_text if threshold_table else (trend_text + "\n\nThreshold Change Table\n- no data"),
        on_close=lambda: _app_close_ops_trend_window(self),
        actions=[("导出CSV", _export_weekly_csv), ("导出阈值7天", _export_threshold_csv)],
        width=980,
        height=640,
    )


def _app_export_ops_daily_csv(self: FootballPredictionApp, *, report_dir: Path, payload: dict) -> None:
    text = str(payload.get("text", ""))
    source_path = str(payload.get("path", "ops_daily_summary_unknown.md"))
    filename = Path(source_path).name
    row = parse_ops_daily_summary_text(text, filename)
    csv_path = export_ops_trend_csv(report_dir, rows=[row], days=1)
    if csv_path is None:
        messagebox.showinfo("运营日报", "当前日报数据为空，无法导出 CSV。")
        return
    self.status_var.set(f"运营日报CSV已导出: {csv_path.name}")
    messagebox.showinfo("运营日报CSV", f"已导出到:\n{csv_path}")


def _app_export_ops_trend_csv(
    self: FootballPredictionApp,
    *,
    report_dir: Path,
    rows: list[dict],
    days: int,
) -> None:
    csv_path = export_ops_trend_csv(report_dir, rows=rows, days=days)
    if csv_path is None:
        messagebox.showinfo("运营趋势CSV", "当前趋势数据为空，无法导出 CSV。")
        return
    alert_days = sum(1 for row in rows if bool(row.get("is_alert")))
    self.status_var.set(f"运营趋势CSV已导出: {csv_path.name}")
    messagebox.showinfo("运营趋势CSV", f"已导出到:\n{csv_path}\n异常日: {alert_days}")


def _app_export_threshold_trend_csv(
    self: FootballPredictionApp,
    *,
    report_dir: Path,
    rows: list[dict],
    days: int,
) -> None:
    csv_path = export_threshold_trend_csv(report_dir, rows=rows, days=days)
    if csv_path is None:
        messagebox.showinfo("阈值趋势CSV", "当前阈值趋势数据为空，无法导出 CSV。")
        return
    self.status_var.set(f"阈值趋势CSV已导出: {csv_path.name}")
    messagebox.showinfo("阈值趋势CSV", f"已导出到:\n{csv_path}")


def _app_export_handicap_shadow_report(self: FootballPredictionApp) -> None:
    settlements = get_recent_settlements(limit=500)
    if not settlements:
        messagebox.showinfo("导出让球日报", "暂无结算记录。")
        return
    report_dir = ensure_report_dir(PROJECT_ROOT)
    report_name = build_handicap_shadow_report_filename()
    report_path = report_dir / report_name
    lines = build_handicap_shadow_report_lines(
        settlements,
        days=14,
        gate_window=30,
        breaker_threshold=3,
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    self.status_var.set(f"让球14天日报已导出: {report_name}")
    messagebox.showinfo("导出让球日报", f"已导出到:\n{report_path}")


def _app_export_accuracy_decomposition_report(self: FootballPredictionApp) -> None:
    settlements = get_recent_settlements(limit=500)
    parlay_items = get_recent_parlay_settlements(limit=500)
    if not settlements and not parlay_items:
        messagebox.showinfo("导出准确率分解", "暂无可用结算记录。")
        return

    artifacts = build_accuracy_decomposition_artifacts(
        project_root=PROJECT_ROOT,
        settlements=settlements,
        parlay_settlements=parlay_items,
    )
    rows = artifacts.get("rows", [])
    summary = artifacts.get("summary", {})

    report_dir = ensure_report_dir(PROJECT_ROOT)
    md_name = build_accuracy_decomposition_report_filename()
    csv_name = build_accuracy_decomposition_csv_filename()
    md_path = report_dir / md_name
    csv_path = report_dir / csv_name

    lines = build_accuracy_decomposition_report_lines(rows, summary)
    md_path.write_text("\n".join(lines), encoding="utf-8")
    csv_path.write_text(build_accuracy_decomposition_csv_text(rows), encoding="utf-8")

    self.status_var.set(f"准确率分解已导出: {md_name}")
    messagebox.showinfo("导出准确率分解", f"Markdown:\n{md_path}\n\nCSV:\n{csv_path}")


def _app_ensemble_weight_status_text(self) -> str:
    return build_ensemble_weight_status_text(get_ensemble_weight_status())


def _app_show_ensemble_weight_status(self) -> None:
    messagebox.showinfo("Ensemble 权重", self._ensemble_weight_status_text())


def _app_apply_calibrate_ensemble_result(self, result: dict) -> None:
    self.status_var.set(build_calibrate_ensemble_apply_status_text(result))
    messagebox.showinfo(
        "校准权重",
        build_calibrate_ensemble_apply_message(result, self._ensemble_weight_status_text()),
    )


def _app_calibrate_ensemble_weights(self) -> None:
    self._run_background(
        task_key="calibrate_ensemble",
        start_status="正在校准 ensemble 权重...",
        worker=calibrate_ensemble_weights_now,
        on_success=self._apply_calibrate_ensemble_result,
        error_title="校准权重失败",
    )


def _app_run_ensemble_backtest(self) -> None:
    self._run_background(
        task_key="ensemble_backtest",
        start_status="正在回测 ensemble 权重...",
        worker=run_ensemble_backtest,
        on_success=self._apply_ensemble_backtest_result,
        error_title="权重回测失败",
    )


def _app_apply_ensemble_backtest_result_v2(self, result: dict) -> None:
    ok = bool(result.get("ok"))
    reason = result.get("reason", "-")
    self.status_var.set(build_ensemble_backtest_apply_status_text(result))
    if not ok:
        messagebox.showinfo("权重回测", f"回测未完成\n原因: {reason}")
        return
    messagebox.showinfo("权重回测", build_ensemble_backtest_success_message(result))


def _app_run_play_model_backtest(self) -> None:
    self._run_background(
        task_key="play_model_backtest",
        start_status="正在回测玩法影子模型...",
        worker=run_play_model_backtest,
        on_success=self._apply_play_model_backtest_result,
        error_title="玩法回测失败",
    )


def _app_apply_high_accuracy_strategy_backtest_result(self, result: dict) -> None:
    ok = bool(result.get("ok"))
    reason = result.get("reason", "-")
    self.status_var.set(build_high_accuracy_strategy_backtest_status_text(result))
    if not ok:
        messagebox.showinfo("高准确率策略", f"回测未完成\n原因: {reason}")
        return
    messagebox.showinfo("高准确率策略", build_high_accuracy_strategy_backtest_message(result))


def _app_run_high_accuracy_strategy_backtest(self) -> None:
    self._run_background(
        task_key="high_accuracy_strategy_backtest",
        start_status="正在用历史数据搜索高准确率策略...",
        worker=run_high_accuracy_strategy_backtest,
        on_success=self._apply_high_accuracy_strategy_backtest_result,
        error_title="高准确率策略失败",
    )


def _app_play_threshold_status_text(self) -> str:
    return build_play_threshold_status_text(get_play_threshold_status())


def _app_show_play_threshold_status(self) -> None:
    messagebox.showinfo("玩法阈值", self._play_threshold_status_text())


def _app_apply_play_threshold_result(self, result: dict) -> None:
    calibrated = bool(result.get("calibrated"))
    reason = result.get("reason", "-")
    self.status_var.set(build_play_threshold_apply_status_text(result))
    if not calibrated:
        messagebox.showinfo("校准玩法阈值", f"校准未完成\n原因: {reason}")
        return
    messagebox.showinfo(
        "校准玩法阈值",
        build_play_threshold_apply_success_message(result, self._play_threshold_status_text()),
    )


def _app_calibrate_play_thresholds(self) -> None:
    self._run_background(
        task_key="calibrate_play_thresholds",
        start_status="正在校准玩法阈值...",
        worker=calibrate_play_thresholds_now,
        on_success=self._apply_play_threshold_result,
        error_title="校准玩法阈值失败",
    )


def _app_apply_threshold_bucket_tuning_result(self, result: dict) -> None:
    calibrated = bool(result.get("calibrated"))
    reason = result.get("reason", "-")
    self.status_var.set(build_threshold_bucket_tuning_apply_status_text(result))
    coverage_text = build_coverage_monitor_text(_app_coverage_summary(self))
    if not calibrated and reason not in {"no_significant_bucket_gap"}:
        messagebox.showinfo("弱分桶校准", f"校准未完成\n原因: {reason}")
        return
    messagebox.showinfo(
        "弱分桶校准",
        build_threshold_bucket_tuning_apply_message(result, self._play_threshold_status_text()) + "\n\n" + coverage_text,
    )


def _app_calibrate_thresholds_by_decomposition(self) -> None:
    self._run_background(
        task_key="threshold_bucket_tuning",
        start_status="正在执行弱分桶阈值校准...",
        worker=calibrate_play_thresholds_by_settlement_now,
        on_success=self._apply_threshold_bucket_tuning_result,
        error_title="弱分桶校准失败",
    )


def _app_apply_layered_filter_threshold_result(self, result: dict) -> None:
    calibrated = bool(result.get("calibrated"))
    reason = result.get("reason", "-")
    league_rules = int(result.get("league_rule_count", 0) or 0)
    global_rules = int(result.get("global_rule_count", 0) or 0)
    self.status_var.set(f"分层门槛{'完成' if calibrated else '失败'} | global={global_rules} | league={league_rules}")
    if not calibrated:
        messagebox.showinfo("分层门槛", f"执行未完成\n原因: {reason}")
        return
    messagebox.showinfo(
        "分层门槛",
        f"已按近期复盘分层设置过滤门槛\n"
        f"- 结算样本: {int(result.get('sample_count', 0) or 0)}\n"
        f"- 分层记录: {int(result.get('record_count', 0) or 0)}\n"
        f"- 全局玩法规则: {global_rules}\n"
        f"- 联赛玩法规则: {league_rules}\n\n"
        + self._play_threshold_status_text(),
    )


def _app_calibrate_layered_filter_thresholds(self) -> None:
    self._run_background(
        task_key="layered_filter_thresholds",
        start_status="正在按分层结果设置过滤门槛...",
        worker=calibrate_layered_filter_thresholds_now,
        on_success=self._apply_layered_filter_threshold_result,
        error_title="分层门槛失败",
    )


def _app_apply_threshold_coverage_guardrail_result(self, result: dict) -> None:
    calibrated = bool(result.get("calibrated"))
    reason = result.get("reason", "-")
    self.status_var.set(build_coverage_guardrail_apply_status_text(result))
    if not calibrated and reason not in {"no_guardrail_change_needed"}:
        messagebox.showinfo("覆盖率保护", f"执行未完成\n原因: {reason}")
        return
    messagebox.showinfo(
        "覆盖率保护",
        build_coverage_guardrail_apply_message(result, self._play_threshold_status_text()),
    )


def _app_run_threshold_coverage_guardrail(self) -> None:
    self._run_background(
        task_key="threshold_coverage_guardrail",
        start_status="正在执行覆盖率保护...",
        worker=calibrate_play_thresholds_coverage_guardrail_now,
        on_success=self._apply_threshold_coverage_guardrail_result,
        error_title="覆盖率保护失败",
    )


def _app_bayes_calibration_status_text(self) -> str:
    return build_bayes_calibration_status_text(get_bayes_calibration_status())


def _app_show_bayes_calibration_status(self) -> None:
    messagebox.showinfo("贝叶斯校准", self._bayes_calibration_status_text())


def _app_apply_bayes_calibration_result(self, result: dict) -> None:
    calibrated = bool(result.get("calibrated"))
    reason = result.get("reason", "-")
    self.status_var.set(build_bayes_calibration_apply_status_text(result))
    if not calibrated and reason != "no_significant_improvement":
        messagebox.showinfo("贝叶斯校准", f"校准未完成\n原因: {reason}")
        return
    messagebox.showinfo(
        "贝叶斯校准",
        build_bayes_calibration_apply_message(result, self._bayes_calibration_status_text()),
    )


def _app_calibrate_bayes_calibration(self) -> None:
    self._run_background(
        task_key="calibrate_bayes_calibration",
        start_status="正在搜索贝叶斯最优参数...",
        worker=calibrate_bayes_calibration_now,
        on_success=self._apply_bayes_calibration_result,
        error_title="贝叶斯校准失败",
    )




def _app_train_play_models(self) -> None:
    self._run_background(
        task_key="train_play_models",
        start_status="正在训练玩法专用模型...",
        worker=train_play_models_now,
        on_success=self._apply_train_play_models_result,
        error_title="训练玩法模型失败",
    )


def _app_apply_calibrate_play_model_policy_result(self, result: dict) -> None:
    calibrated = bool(result.get("calibrated"))
    reason = result.get("reason", "-")
    self.status_var.set(build_play_model_policy_apply_status_text(result))
    if not calibrated:
        messagebox.showinfo("玩法接管策略", f"校准未完成\n原因: {reason}")
        return
    messagebox.showinfo(
        "玩法接管策略",
        build_play_model_policy_apply_success_message(result, self._play_model_policy_status_text()),
    )


def _app_calibrate_play_model_policy(self) -> None:
    self._run_background(
        task_key="calibrate_play_model_policy",
        start_status="正在校准玩法接管策略...",
        worker=calibrate_play_model_policy_now,
        on_success=self._apply_calibrate_play_model_policy_result,
        error_title="校准玩法接管策略失败",
    )


def _app_apply_train_play_models_result_v2(self, result: dict) -> None:
    self.status_var.set(build_train_play_models_apply_status_text(result))
    messagebox.showinfo(
        "玩法模型",
        build_train_play_models_apply_message(result, self._play_model_status_text()),
    )


def _app_show_play_model_status_v2(self) -> None:
    messagebox.showinfo("玩法模型", self._play_model_status_text())


def _app_show_play_model_policy_status_v2(self) -> None:
    messagebox.showinfo("玩法接管策略", self._play_model_policy_status_text())


def _app_apply_play_model_backtest_result_v3(self, result: dict) -> None:
    ok = bool(result.get("ok"))
    reason = result.get("reason", "-")
    self.status_var.set(build_play_model_backtest_apply_status_text(result))
    if not ok:
        messagebox.showinfo("玩法回测", f"回测未完成\n原因: {reason}")
        return
    messagebox.showinfo("玩法回测", build_play_model_backtest_success_message(result))


def _app_play_model_status_text_v3(self) -> str:
    return build_play_model_training_status_text(get_play_model_training_status())


def _app_play_model_policy_status_text_v4(self) -> str:
    return build_play_model_policy_status_text(get_play_model_policy_status())


def _app_export_c1_availability_template(self) -> None:
    matches = list(self.matches)
    if not matches:
        messagebox.showinfo("C1 阵容模板", "当前没有可导出的赛事。")
        return
    default_path = PROJECT_ROOT / "reports" / "c1_availability_template_manual.csv"
    target = filedialog.asksaveasfilename(
        title="导出 C1 阵容模板",
        defaultextension=".csv",
        initialfile=default_path.name,
        initialdir=str(default_path.parent),
        filetypes=[("CSV 文件", "*.csv")],
    )
    if not target:
        return
    self._run_background(
        task_key="c1_export_availability_template",
        start_status="正在导出 C1 阵容模板...",
        worker=lambda: _app_export_c1_availability_template_worker(matches, Path(target)),
        on_success=self._apply_export_c1_availability_template_result,
        error_title="导出 C1 阵容模板失败",
    )


def _app_export_c1_availability_template_worker(matches: list[AppMatch], target: Path) -> dict:
    return export_c1_availability_template(matches, target)


def _app_apply_export_c1_availability_template_result(self, result: dict) -> None:
    count = int(result.get("rows", 0))
    path = str(result.get("path", ""))
    self.status_var.set(build_c1_template_export_status_text(count))
    messagebox.showinfo("C1 阵容模板", build_c1_template_export_message_text(count, path))


def _app_import_c1_availability_snapshots(self) -> None:
    source = filedialog.askopenfilename(
        title="导入 C1 阵容快照",
        filetypes=[("支持的文件", "*.csv *.json *.jsonl"), ("CSV 文件", "*.csv"), ("JSON 文件", "*.json"), ("JSONL 文件", "*.jsonl")],
    )
    if not source:
        return
    self._run_background(
        task_key="c1_import_availability",
        start_status="正在导入 C1 阵容快照...",
        worker=lambda: _app_import_c1_availability_snapshots_worker(Path(source)),
        on_success=self._apply_import_c1_availability_snapshots_result,
        error_title="导入 C1 阵容快照失败",
    )


def _app_import_c1_availability_snapshots_worker(source: Path) -> dict:
    return import_c1_availability_snapshots(PROJECT_ROOT, source, replace=False)


def _app_sync_c1_availability_sources(self) -> None:
    self._run_background(
        task_key="c1_sync_availability_sources",
        start_status="正在同步 C1 阵容源...",
        worker=_app_sync_c1_availability_sources_worker,
        on_success=self._apply_sync_c1_availability_sources_result,
        error_title="同步 C1 阵容源失败",
    )


def _app_sync_c1_availability_sources_worker() -> dict:
    return sync_c1_availability_sources(PROJECT_ROOT, replace=False)


def _app_apply_sync_c1_availability_sources_result(self, result: dict) -> None:
    total_rows = int(result.get("total_rows", 0))
    total_keys = int(result.get("total_keys", 0))
    failed_providers = int(result.get("failed_providers", 0) or 0)
    self._refresh_c1_release_guard_status(build_c1_release_review_availability_guard(result))
    self.status_var.set(build_c1_sync_status_text(total_rows, total_keys, failed_providers=failed_providers))
    messagebox.showinfo("C1 阵容源同步", build_c1_sync_message_text(result))
    if should_auto_rerun_shadow_after_sync(has_matches=bool(getattr(self, "matches", []))) and total_rows > 0:
        self._run_background(
            task_key="c1_shadow_comparison",
            start_status="阵容源已同步，正在自动重跑 C1 对照...",
            worker=lambda: _app_run_c1_shadow_comparison_worker(list(self.matches)),
            on_success=self._apply_c1_shadow_comparison_result,
            error_title="同步后自动重跑 C1 对照失败",
        )


def _app_show_c1_availability_provider_status(self) -> None:
    self._refresh_c1_release_guard_status()
    statuses = get_c1_availability_provider_statuses(PROJECT_ROOT)
    lines = build_c1_availability_provider_status_lines(statuses)
    messagebox.showinfo("阵容源状态", "\n".join(lines))


def _app_open_c1_release_guard_history(self) -> None:
    report_dir = PROJECT_ROOT / "reports"
    rows = load_c1_release_guard_report_history(report_dir, limit=10)
    if not rows:
        messagebox.showinfo("放行门控审计", "当前没有 C1 放行门控阻止审计报告。")
        return
    latest = rows[0]
    header = f"最近 {len(rows)} 份阻止报告 | 最新: {latest.get('name', '-')}"
    self.c1_release_guard_history_window = open_text_view_window(
        root=self.root,
        existing_window=self.c1_release_guard_history_window,
        title="C1 放行门控审计",
        header=header,
        content=build_c1_release_guard_history_text(rows),
        on_close=lambda: _app_close_c1_release_guard_history_window(self),
        width=1040,
        height=720,
    )
    self.status_var.set(f"已打开 C1 放行门控审计 | {latest.get('name', '-')}")


def _app_apply_import_c1_availability_snapshots_result(self, result: dict) -> None:
    imported_rows = int(result.get("imported_rows", 0))
    written_keys = int(result.get("written_keys", 0))
    self._refresh_c1_release_guard_status()
    self.status_var.set(build_c1_snapshot_import_status_text(imported_rows, written_keys))
    messagebox.showinfo("C1 阵容快照", build_c1_snapshot_import_message_text(result))
    if should_auto_rerun_shadow_after_import(
        has_matches=bool(getattr(self, "matches", [])),
        imported_rows=imported_rows,
    ):
        self._run_background(
            task_key="c1_shadow_comparison",
            start_status="阵容快照已更新，正在自动重跑 C1 对照...",
            worker=lambda: _app_run_c1_shadow_comparison_worker(list(self.matches)),
            on_success=self._apply_c1_shadow_comparison_result,
            error_title="自动重跑 C1 对照失败",
        )


def _app_run_c1_shadow_comparison(self) -> None:
    matches = list(self.matches)
    if not matches:
        messagebox.showinfo("C1 对照", "当前没有可用于对照的赛事。")
        return
    self._run_background(
        task_key="c1_shadow_comparison",
        start_status="正在运行 C1 shadow comparison...",
        worker=lambda: _app_run_c1_shadow_comparison_worker(matches),
        on_success=self._apply_c1_shadow_comparison_result,
        error_title="运行 C1 对照失败",
    )


def _app_run_c1_shadow_comparison_worker(matches: list[AppMatch]) -> dict:
    result = run_shadow_comparison_for_legacy_matches(
        project_root=PROJECT_ROOT,
        matches=matches,
    )
    return adapt_shadow_comparison_result(result)


def _app_apply_c1_shadow_comparison_result(self, result: dict) -> None:
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    counts = summary.get("governance_counts", {}) if isinstance(summary, dict) else {}
    rows = result.get("rows", []) if isinstance(result, dict) else []
    self.status_var.set(build_shadow_comparison_status_text(int(result.get("total_matches", 0)), counts))
    self._show_c1_comparison_window(
        total_matches=int(result.get("total_matches", 0)),
        summary=summary,
        rows=rows,
        markdown_report=str(result.get("markdown_report", "-")),
        json_report=str(result.get("json_report", "-")),
    )


def _app_build_c1_rows_from_marks(self) -> list[dict]:
    marks = getattr(self, "c1_comparison_marks", {}) if hasattr(self, "c1_comparison_marks") else {}
    return build_c1_rows_from_marks(
        matches=self.matches,
        marks=marks,
        predictions=self.predictions,
        action_priority_fn=self._c1_action_priority,
    )


def _app_summarize_c1_rows(rows: list[dict]) -> dict:
    return summarize_c1_rows(rows)


def _app_open_c1_workbench(self) -> None:
    rows = _app_build_c1_rows_from_marks(self)
    if not rows:
        messagebox.showinfo("C1 工作台", "当前没有已应用到主列表的 C1 标记。")
        return
    summary = _app_summarize_c1_rows(rows)
    self._show_c1_comparison_window(
        total_matches=len(rows),
        summary=summary,
        rows=rows,
        markdown_report="-",
        json_report="-",
    )


def _app_run_c1_release_review(self) -> None:
    matches = list(self.matches)
    if not matches:
        messagebox.showinfo("C1 放行评估", "当前没有可用于放行评估的赛事。")
        return
    guard = get_c1_release_review_availability_guard(PROJECT_ROOT)
    self._refresh_c1_release_guard_status(guard)
    if not bool(guard.get("allowed", True)):
        self.c1_release_rows = []
        self.c1_release_summary = {"availability_guard": guard}
        self._apply_runtime_mode_default_filter()
        report_path = self._write_c1_release_guard_block_report(guard, matches_count=len(matches))
        self.status_var.set(f"{guard.get('status_text') or 'C1 放行评估已阻止'} | {report_path.name}")
        messagebox.showwarning(
            "C1 放行评估",
            f"{guard.get('message') or 'C1 阵容源质量门控未通过。'}\n\n审计报告: {report_path}",
        )
        return
    self._run_background(
        task_key="c1_release_review",
        start_status="正在运行 C1 受控放行评估...",
        worker=lambda: _app_run_c1_release_review_worker(matches),
        on_success=self._apply_c1_release_review_result,
        error_title="运行 C1 放行评估失败",
    )


def _app_run_c1_release_review_worker(matches: list[AppMatch]) -> dict:
    guard = get_c1_release_review_availability_guard(PROJECT_ROOT)
    if not bool(guard.get("allowed", True)):
        return {
            "total_matches": 0,
            "requested_matches": len(matches),
            "rows": [],
            "summary": {
                "release_allowed_count": 0,
                "availability_guard": guard,
                "blocked_by_availability_guard": True,
            },
            "blocked_by_availability_guard": True,
            "block_message": str(guard.get("message") or ""),
        }
    result = run_controlled_release_for_legacy_matches(
        project_root=PROJECT_ROOT,
        matches=matches,
    )
    return adapt_release_review_result(result)


def _app_current_release_row(self, match_id: str) -> dict:
    rows = getattr(self, "c1_release_rows", [])
    return find_release_row(rows, match_id)


def _app_release_allowed_match_ids(self) -> set[str]:
    rows = getattr(self, "c1_release_rows", [])
    return collect_release_allowed_match_ids(rows)


def _app_active_release_allowed_match_ids(self) -> set[str]:
    if not is_release_gate_active(self.c1_runtime_mode):
        return set()
    return self._release_allowed_match_ids()


def _app_release_gate_pick_text(self, match_id: str, prediction: dict) -> str:
    return resolve_release_gate_pick(
        gate_active=is_release_gate_active(self.c1_runtime_mode),
        prediction=prediction,
        row=self._current_release_row(match_id),
    )


def _app_format_release_candidate_text(self, row: dict, prediction: dict | None = None) -> str:
    return format_release_candidate_text(row, prediction)


def _app_build_formal_release_rows(self) -> list[dict]:
    rows = list(getattr(self, "c1_release_rows", []))
    return build_formal_release_rows(rows=rows, predictions=self.predictions)


def _app_refresh_release_gate_after_analysis(self, matches: list[AppMatch]) -> None:
    if not matches:
        self.c1_release_rows = []
        self.c1_release_summary = {}
        return
    result = _app_run_c1_release_review_worker(matches)
    self.c1_release_summary = dict(result.get("summary", {}))
    self.c1_release_rows = list(result.get("rows", []))
    if bool(result.get("blocked_by_availability_guard")):
        guard = self.c1_release_summary.get("availability_guard", {})
        self._refresh_c1_release_guard_status(guard if isinstance(guard, dict) else None)
        if isinstance(guard, dict):
            report_path = self._write_c1_release_guard_block_report(guard, matches_count=len(matches))
        else:
            report_path = None
        if hasattr(self, "status_var"):
            suffix = f" | {report_path.name}" if report_path is not None else ""
            self.status_var.set(f"{guard.get('status_text') or 'C1 放行评估已阻止'}{suffix}")
        self._apply_runtime_mode_default_filter()
        return
    for match in matches:
        if match.match_id in self.predictions and self.tree.exists(match.match_id):
            self._update_tree_row(match, self.predictions[match.match_id])
    self._apply_runtime_mode_default_filter()


def _app_apply_runtime_mode_default_filter(self) -> None:
    formal_rows = self._build_formal_release_rows()
    target_filter = get_default_ui_filter(self.c1_runtime_mode, has_formal_rows=bool(formal_rows))
    if hasattr(self, "c1_filter_var"):
        self.c1_filter_var.set(target_filter)
    self._apply_main_list_filter()


def _app_open_c1_formal_recommendations(self) -> None:
    rows = self._build_formal_release_rows()
    if not rows:
        messagebox.showinfo("正式建议清单", "当前没有可放行的正式建议。")
        return
    self.c1_formal_window = show_c1_formal_recommendations_window(
        root=self.root,
        existing_window=getattr(self, "c1_formal_window", None),
        rows=rows,
        on_export_allowlist=lambda: self._export_c1_release_allowlist(getattr(self, "c1_release_rows", [])),
    )


def _app_apply_c1_release_review_result(self, result: dict) -> None:
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    self.c1_release_summary = dict(summary) if isinstance(summary, dict) else {}
    self.c1_release_rows = list(result.get("rows", [])) if isinstance(result, dict) else []
    guard = self.c1_release_summary.get("availability_guard", {})
    self._refresh_c1_release_guard_status(guard if isinstance(guard, dict) and guard else None)
    self._apply_runtime_mode_default_filter()
    if isinstance(result, dict) and bool(result.get("blocked_by_availability_guard")):
        guard = self.c1_release_summary.get("availability_guard", {})
        report_path = (
            self._write_c1_release_guard_block_report(
                guard,
                matches_count=int(result.get("requested_matches", result.get("total_matches", 0)) or 0),
            )
            if isinstance(guard, dict)
            else None
        )
        suffix = f" | {report_path.name}" if report_path is not None else ""
        self.status_var.set(f"{guard.get('status_text') or 'C1 放行评估已阻止'}{suffix}")
        message = str(result.get("block_message") or "C1 阵容源质量门控未通过。")
        if report_path is not None:
            message += f"\n\n审计报告: {report_path}"
        messagebox.showwarning("C1 放行评估", message)
        return
    self.status_var.set(
        build_release_review_status_text(
            int(result.get("total_matches", 0)),
            int(summary.get("release_allowed_count", 0)),
        )
    )
    self._show_c1_release_window(
        total_matches=int(result.get("total_matches", 0)),
        summary=summary,
        rows=self.c1_release_rows,
    )


def _app_export_c1_release_allowlist(self, rows: list[dict] | None = None) -> None:
    candidate_rows = list(rows) if isinstance(rows, list) else list(getattr(self, "c1_release_rows", []))
    allow_rows = [item for item in candidate_rows if item.get("release_allowed")]
    if not allow_rows:
        messagebox.showinfo("放行清单", "当前没有可导出的放行建议。")
        return

    report_dir = PROJECT_ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"c1_release_allowlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    summary = getattr(self, "c1_release_summary", {}) if hasattr(self, "c1_release_summary") else {}
    lines = build_release_allowlist_lines(allow_rows=allow_rows, summary=summary)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    self.status_var.set(f"放行清单已导出 | {report_path.name}")
    messagebox.showinfo("放行清单", f"已导出 {len(allow_rows)} 场\n{report_path}")


def _app_open_c1_release_allowlist(self) -> None:
    rows = list(getattr(self, "c1_release_rows", []))
    if not rows:
        messagebox.showinfo("放行清单", "当前没有可用的放行评估结果。")
        return
    summary = dict(getattr(self, "c1_release_summary", {}))
    self._show_c1_release_window(
        total_matches=len(rows),
        summary=summary,
        rows=rows,
        default_filter="可放行",
    )


def _app_show_c1_release_window(self, *, total_matches: int, summary: dict, rows: list[dict], default_filter: str = "全部") -> None:
    self.c1_release_window = show_c1_release_window(
        root=self.root,
        existing_window=getattr(self, "c1_release_window", None),
        total_matches=total_matches,
        summary=summary,
        rows=rows,
        default_filter=default_filter,
        on_export_allowlist=self._export_c1_release_allowlist,
    )


def _app_show_c1_comparison_window(self, *, total_matches: int, summary: dict, rows: list[dict], markdown_report: str, json_report: str) -> None:
    self.c1_comparison_window = show_c1_comparison_window(
        root=self.root,
        existing_window=getattr(self, "c1_comparison_window", None),
        total_matches=total_matches,
        summary=summary,
        rows=rows,
        markdown_report=markdown_report,
        json_report=json_report,
        on_apply_to_main=self._apply_c1_comparison_to_main_list,
        on_export_pending_template=self._export_c1_pending_template,
    )


def _app_export_c1_pending_template(self, rows: list[dict]) -> None:
    pending_ids = compute_pending_match_ids(rows)
    if not pending_ids:
        messagebox.showinfo("待处理模板", "当前没有需要导出的待处理比赛。")
        return

    matches = [match for match in self.matches if match.match_id in pending_ids]
    if not matches:
        messagebox.showinfo("待处理模板", "当前待处理比赛未命中主列表，无法导出模板。")
        return

    default_path = PROJECT_ROOT / "reports" / "c1_availability_template_pending.csv"
    target = filedialog.asksaveasfilename(
        title="导出待处理阵容模板",
        defaultextension=".csv",
        initialfile=default_path.name,
        initialdir=str(default_path.parent),
        filetypes=[("CSV 文件", "*.csv")],
    )
    if not target:
        return

    self._run_background(
        task_key="c1_export_pending_template",
        start_status="正在导出待处理阵容模板...",
        worker=lambda: _app_export_c1_availability_template_worker(matches, Path(target)),
        on_success=self._apply_export_c1_pending_template_result,
        error_title="导出待处理阵容模板失败",
    )


def _app_apply_export_c1_pending_template_result(self, result: dict) -> None:
    count = int(result.get("rows", 0))
    path = str(result.get("path", ""))
    self.status_var.set(f"待处理阵容模板已导出 | {count} 行")
    messagebox.showinfo("待处理模板", f"模板已导出\n行数: {count}\n路径: {path}")


def _app_apply_c1_comparison_to_main_list(self, rows: list[dict]) -> None:
    if not hasattr(self, "c1_comparison_marks"):
        self.c1_comparison_marks = {}

    configure_c1_tree_tags(self.tree)

    marks_by_match_id, tags_by_match_id, buckets, applied = build_c1_mark_apply_plan(
        rows=rows,
        exists_fn=self.tree.exists,
    )
    for match_id, tag in tags_by_match_id.items():
        self.tree.item(match_id, tags=(tag,))
    self.c1_comparison_marks.update(marks_by_match_id)

    save_c1_comparison_marks_cache(self.c1_comparison_marks)

    self.status_var.set(build_c1_apply_status_text(applied=applied, buckets=buckets))
    sync_tree_c1_action_column(
        tree=self.tree,
        matches=self.matches,
        action_text_by_match_id=self._current_c1_action_text,
    )
    self._apply_main_list_filter()
    detail_payload = resolve_selected_prediction_for_details(
        selected_match=self.selected_match(),
        predictions=self.predictions,
    )
    if detail_payload is not None:
        selected, prediction = detail_payload
        self._show_match_details(selected, prediction)
    messagebox.showinfo("应用到主列表", build_c1_apply_dialog_text(applied=applied, buckets=buckets))


def _app_build_export_report_lines(self, matches: list[AppMatch], *, current_filter: str, scope_label: str) -> list[str]:
    marks = getattr(self, "c1_comparison_marks", {}) if hasattr(self, "c1_comparison_marks") else {}
    return build_export_report_lines(
        matches=matches,
        all_match_count=len(self.matches),
        predictions=self.predictions,
        c1_marks=marks if isinstance(marks, dict) else {},
        release_gate_pick_fn=self._release_gate_pick_text,
        predict_match_fn=predict_match,
        current_filter=current_filter,
        scope_label=scope_label,
    )


def _app_export_report_for_matches(self, matches: list[AppMatch], *, scope_slug: str, scope_label: str) -> None:
    if not matches:
        messagebox.showinfo("提示", "当前范围内没有可导出的赛事。")
        return

    report_dir = ensure_report_dir(PROJECT_ROOT)
    report_path = report_dir / build_report_filename(scope_slug)
    current_filter = resolve_current_filter(self.c1_filter_var if hasattr(self, "c1_filter_var") else None)
    lines = _app_build_export_report_lines(self, matches, current_filter=current_filter, scope_label=scope_label)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    self.status_var.set(build_export_status_text(report_path.name))
    messagebox.showinfo(
        "导出完成",
        build_export_message_text(scope_label=scope_label, match_count=len(matches), report_path=report_path),
    )


def _app_export_visible_report(self) -> None:
    if not self.matches:
        messagebox.showinfo("提示", "当前没有有效赛事，无法导出报告。")
        return

    if should_run_pre_export_analysis(self.predictions):
        self.analyze_all()

    visible_ids = collect_visible_match_ids(self.tree if hasattr(self, "tree") else None)
    matches = select_matches_for_export(self.matches, visible_ids)
    scope_label = "当前筛选视图"
    _app_export_report_for_matches(self, matches, scope_slug="visible", scope_label=scope_label)


def _app_export_all_report(self) -> None:
    if not self.matches:
        messagebox.showinfo("提示", "当前没有有效赛事，无法导出报告。")
        return

    if should_run_pre_export_analysis(self.predictions):
        self.analyze_all()

    _app_export_report_for_matches(self, list(self.matches), scope_slug="full", scope_label="全部赛事")


def _app_open_user_center_final(self) -> None:
    actions = {
        "analyze_selected": self.analyze_selected,
        "analyze_all": self.analyze_all,
        "show_coverage_monitor": self.show_coverage_monitor,
        "show_ops_daily_report": self.show_ops_daily_report,
        "show_ops_weekly_trend": self.show_ops_weekly_trend,
        "export_current_report": self.export_current_report,
        "export_all_report": self.export_all_report,
        "settle_selected_result": self.settle_selected_result,
        "show_recent_settlements": self.show_recent_settlements,
        "show_handicap_monitor": self.show_handicap_monitor,
        "export_handicap_shadow_report": self.export_handicap_shadow_report,
        "export_accuracy_decomposition_report": self.export_accuracy_decomposition_report,
        "show_xgb_status": self.show_xgb_status,
        "show_model_training_overview": self.show_model_training_overview,
        "train_xgb_now": self.train_xgb_now,
        "show_play_model_status": self.show_play_model_status,
        "train_play_models": self.train_play_models,
        "show_ensemble_weight_status": self.show_ensemble_weight_status,
        "calibrate_ensemble_weights": self.calibrate_ensemble_weights,
        "show_play_threshold_status": self.show_play_threshold_status,
        "calibrate_play_thresholds": self.calibrate_play_thresholds,
        "calibrate_thresholds_by_decomposition": self.calibrate_thresholds_by_decomposition,
        "calibrate_layered_filter_thresholds": self.calibrate_layered_filter_thresholds,
        "run_threshold_coverage_guardrail": self.run_threshold_coverage_guardrail,
        "show_bayes_calibration_status": self.show_bayes_calibration_status,
        "calibrate_bayes_calibration": self.calibrate_bayes_calibration,
        "show_play_model_policy_status": self.show_play_model_policy_status,
        "calibrate_play_model_policy": self.calibrate_play_model_policy,
        "run_ensemble_backtest": self.run_ensemble_backtest,
        "run_play_model_backtest": self.run_play_model_backtest,
        "run_high_accuracy_strategy_backtest": self.run_high_accuracy_strategy_backtest,
        "export_c1_availability_template": self.export_c1_availability_template,
        "import_c1_availability_snapshots": self.import_c1_availability_snapshots,
        "sync_c1_availability_sources": self.sync_c1_availability_sources,
        "show_c1_availability_provider_status": self.show_c1_availability_provider_status,
        "open_c1_release_guard_history": self.open_c1_release_guard_history,
        "run_c1_shadow_comparison": self.run_c1_shadow_comparison,
        "run_c1_release_review": self.run_c1_release_review,
        "open_c1_formal_recommendations": self.open_c1_formal_recommendations,
        "open_c1_release_allowlist": self.open_c1_release_allowlist,
        "open_c1_workbench": self.open_c1_workbench,
    }
    self._close_user_center()
    container = self.inline_actions_container
    container.pack(fill=tk.X, pady=(8, 2), before=self.details)

    for section_title, buttons in build_user_center_sections(actions):
        section = ttk.LabelFrame(container, text=section_title, padding=8)
        section.pack(fill=tk.X, pady=(0, 8))
        for index, (button_text, callback) in enumerate(buttons):
            button = ttk.Button(section, text=button_text, command=callback)
            button.grid(row=index // 6, column=index % 6, sticky=tk.W, padx=(0, 8), pady=(0, 6))

    ttk.Button(container, text="收起用户中心", command=self._close_user_center).pack(anchor=tk.E, pady=(0, 6))
    self._write_details(
        "用户中心\n\n"
        + f"- 当前赛事: {len(self.matches)} 场\n"
        + f"- 已分析: {len(self.predictions)} 场\n"
        + "- 功能入口已切换为主界面内嵌面板，不再打开独立窗口。\n"
        + "- 点击上方按钮即可执行分析、结算、训练、校准、回测和 C1 对照任务。",
        clear_actions=False,
    )
    self.status_var.set("已打开用户中心")


_FINAL_BINDINGS: dict[str, object] = resolve_final_bindings(globals())
apply_class_bindings(FootballPredictionApp, _FINAL_BINDINGS)
validate_class_bindings(FootballPredictionApp, _FINAL_BINDINGS)


def main() -> None:
    root = tk.Tk()
    FootballPredictionApp(root)
    root.mainloop()
