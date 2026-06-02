"""
分析中心窗口 - Phase 3
整合所有分析报告功能：结算管理、专项监控、运营报告、导出管理
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ui import FootballPredictionApp


class AnalysisCenterWindow:
    """分析中心窗口 - 整合12个分析报告功能"""

    def __init__(self, root: tk.Tk, app: FootballPredictionApp):
        self.root = root
        self.app = app
        self.window: tk.Toplevel | None = None

    def open(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.root)
        self.window.title("分析中心")
        self.window.geometry("1200x700")
        self.window.minsize(1000, 600)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._build_layout()

    def close(self) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None

    def _build_layout(self) -> None:
        container = ttk.Frame(self.window, padding=14)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text="分析中心",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            container,
            text="结算管理、专项监控、运营报告、导出管理",
            style="Sub.TLabel",
        ).pack(anchor=tk.W, pady=(4, 10))

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True)

        self._build_settlement_tab(notebook)
        self._build_monitor_tab(notebook)
        self._build_report_tab(notebook)
        self._build_export_tab(notebook)

        footer = ttk.Frame(container)
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(footer, text="关闭", command=self.close).pack(side=tk.RIGHT)

    # ── 标签页构建 ──────────────────────────────────────────────

    def _build_settlement_tab(self, notebook: ttk.Notebook) -> None:
        """结算管理"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="结算管理")

        settle_frame = ttk.LabelFrame(tab, text="赛果录入", padding=10)
        settle_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(settle_frame, text="录入赛果",
                   command=self._settle_selected_result).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(settle_frame, text="自动回收赛果",
                   command=self._auto_settle_results).pack(side=tk.LEFT)

        recent_frame = ttk.LabelFrame(tab, text="近期结算", padding=10)
        recent_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(recent_frame, text="查看近期结算",
                   command=self._show_recent_settlements).pack(side=tk.LEFT)

    def _build_monitor_tab(self, notebook: ttk.Notebook) -> None:
        """专项监控"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="专项监控")

        handicap_frame = ttk.LabelFrame(tab, text="让球监控", padding=10)
        handicap_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(handicap_frame, text="让球专项看板",
                   command=self._show_handicap_monitor).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(handicap_frame, text="导出让球14天日报",
                   command=self._export_handicap_shadow_report).pack(side=tk.LEFT)

        coverage_frame = ttk.LabelFrame(tab, text="覆盖率监控", padding=10)
        coverage_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(coverage_frame, text="覆盖率监控",
                   command=self._show_coverage_monitor).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(coverage_frame, text="覆盖率保护",
                   command=self._run_threshold_coverage_guardrail).pack(side=tk.LEFT)

        accuracy_frame = ttk.LabelFrame(tab, text="准确率分析", padding=10)
        accuracy_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(accuracy_frame, text="导出准确率分解",
                   command=self._export_accuracy_decomposition_report).pack(side=tk.LEFT)

    def _build_report_tab(self, notebook: ttk.Notebook) -> None:
        """运营报告"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="运营报告")

        daily_frame = ttk.LabelFrame(tab, text="日报", padding=10)
        daily_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(daily_frame, text="查看运营日报",
                   command=self._show_ops_daily_report).pack(side=tk.LEFT)

        trend_frame = ttk.LabelFrame(tab, text="趋势分析", padding=10)
        trend_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(trend_frame, text="查看7天趋势",
                   command=self._show_ops_weekly_trend).pack(side=tk.LEFT)

    def _build_export_tab(self, notebook: ttk.Notebook) -> None:
        """导出管理"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="导出管理")

        export_frame = ttk.LabelFrame(tab, text="报告导出", padding=10)
        export_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(export_frame, text="导出当前视图",
                   command=self._export_current_report).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(export_frame, text="导出全部",
                   command=self._export_all_report).pack(side=tk.LEFT)

    # ── 功能委托（转发到主应用） ────────────────────────────────

    def _settle_selected_result(self) -> None:
        if hasattr(self.app, 'settle_selected_result'):
            self.app.settle_selected_result()

    def _auto_settle_results(self) -> None:
        if hasattr(self.app, 'auto_settle_results'):
            self.app.auto_settle_results()

    def _show_recent_settlements(self) -> None:
        if hasattr(self.app, 'show_recent_settlements'):
            self.app.show_recent_settlements()

    def _show_handicap_monitor(self) -> None:
        if hasattr(self.app, 'show_handicap_monitor'):
            self.app.show_handicap_monitor()

    def _export_handicap_shadow_report(self) -> None:
        if hasattr(self.app, 'export_handicap_shadow_report'):
            self.app.export_handicap_shadow_report()

    def _show_coverage_monitor(self) -> None:
        if hasattr(self.app, 'show_coverage_monitor'):
            self.app.show_coverage_monitor()

    def _run_threshold_coverage_guardrail(self) -> None:
        if hasattr(self.app, 'run_threshold_coverage_guardrail'):
            self.app.run_threshold_coverage_guardrail()

    def _export_accuracy_decomposition_report(self) -> None:
        if hasattr(self.app, 'export_accuracy_decomposition_report'):
            self.app.export_accuracy_decomposition_report()

    def _show_ops_daily_report(self) -> None:
        if hasattr(self.app, 'show_ops_daily_report'):
            self.app.show_ops_daily_report()

    def _show_ops_weekly_trend(self) -> None:
        if hasattr(self.app, 'show_ops_weekly_trend'):
            self.app.show_ops_weekly_trend()

    def _export_current_report(self) -> None:
        if hasattr(self.app, 'export_current_report'):
            self.app.export_current_report()
        else:
            messagebox.showinfo("导出当前视图", "功能开发中...")

    def _export_all_report(self) -> None:
        if hasattr(self.app, 'export_all_report'):
            self.app.export_all_report()
        else:
            messagebox.showinfo("导出全部", "功能开发中...")
