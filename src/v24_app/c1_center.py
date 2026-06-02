"""
C1管理中心窗口 - Phase 4
整合所有C1功能：阵容管理、对照运行、结果查看、审计查询
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ui import FootballPredictionApp


class C1CenterWindow:
    """C1管理中心窗口 - 整合10个C1功能"""

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
        self.window.title("C1管理中心")
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
            text="C1管理中心",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            container,
            text="阵容管理、对照运行、结果查看、审计查询",
            style="Sub.TLabel",
        ).pack(anchor=tk.W, pady=(4, 10))

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True)

        self._build_availability_tab(notebook)
        self._build_comparison_tab(notebook)
        self._build_result_tab(notebook)
        self._build_audit_tab(notebook)

        footer = ttk.Frame(container)
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(footer, text="关闭", command=self.close).pack(side=tk.RIGHT)

    # ── 标签页构建 ──────────────────────────────────────────────

    def _build_availability_tab(self, notebook: ttk.Notebook) -> None:
        """阵容管理"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="阵容管理")

        template_frame = ttk.LabelFrame(tab, text="阵容模板", padding=10)
        template_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(template_frame, text="导出阵容模板",
                   command=self._export_c1_availability_template).pack(side=tk.LEFT)

        snapshot_frame = ttk.LabelFrame(tab, text="阵容快照", padding=10)
        snapshot_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(snapshot_frame, text="导入阵容快照",
                   command=self._import_c1_availability_snapshots).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(snapshot_frame, text="同步阵容源",
                   command=self._sync_c1_availability_sources).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(snapshot_frame, text="阵容源状态",
                   command=self._show_c1_availability_provider_status).pack(side=tk.LEFT)

    def _build_comparison_tab(self, notebook: ttk.Notebook) -> None:
        """对照运行"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="对照运行")

        shadow_frame = ttk.LabelFrame(tab, text="Shadow对照", padding=10)
        shadow_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(shadow_frame, text="运行C1对照",
                   command=self._run_c1_shadow_comparison).pack(side=tk.LEFT)

        release_frame = ttk.LabelFrame(tab, text="放行评估", padding=10)
        release_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(release_frame, text="运行放行评估",
                   command=self._run_c1_release_review).pack(side=tk.LEFT)

    def _build_result_tab(self, notebook: ttk.Notebook) -> None:
        """结果查看"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="结果查看")

        result_frame = ttk.LabelFrame(tab, text="对照结果", padding=10)
        result_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(result_frame, text="正式建议清单",
                   command=self._open_c1_formal_recommendations).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(result_frame, text="打开放行清单",
                   command=self._open_c1_release_allowlist).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(result_frame, text="打开C1工作台",
                   command=self._open_c1_workbench).pack(side=tk.LEFT)

    def _build_audit_tab(self, notebook: ttk.Notebook) -> None:
        """审计查询"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="审计查询")

        audit_frame = ttk.LabelFrame(tab, text="门控审计", padding=10)
        audit_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(audit_frame, text="放行门控审计历史",
                   command=self._open_c1_release_guard_history).pack(side=tk.LEFT)

    # ── 功能委托（转发到主应用） ────────────────────────────────

    def _export_c1_availability_template(self) -> None:
        if hasattr(self.app, 'export_c1_availability_template'):
            self.app.export_c1_availability_template()

    def _import_c1_availability_snapshots(self) -> None:
        if hasattr(self.app, 'import_c1_availability_snapshots'):
            self.app.import_c1_availability_snapshots()

    def _sync_c1_availability_sources(self) -> None:
        if hasattr(self.app, 'sync_c1_availability_sources'):
            self.app.sync_c1_availability_sources()

    def _show_c1_availability_provider_status(self) -> None:
        if hasattr(self.app, 'show_c1_availability_provider_status'):
            self.app.show_c1_availability_provider_status()

    def _run_c1_shadow_comparison(self) -> None:
        if hasattr(self.app, 'run_c1_shadow_comparison'):
            self.app.run_c1_shadow_comparison()

    def _run_c1_release_review(self) -> None:
        if hasattr(self.app, 'run_c1_release_review'):
            self.app.run_c1_release_review()

    def _open_c1_formal_recommendations(self) -> None:
        if hasattr(self.app, 'open_c1_formal_recommendations'):
            self.app.open_c1_formal_recommendations()

    def _open_c1_release_allowlist(self) -> None:
        if hasattr(self.app, 'open_c1_release_allowlist'):
            self.app.open_c1_release_allowlist()

    def _open_c1_workbench(self) -> None:
        if hasattr(self.app, 'open_c1_workbench'):
            self.app.open_c1_workbench()

    def _open_c1_release_guard_history(self) -> None:
        if hasattr(self.app, 'open_c1_release_guard_history'):
            self.app.open_c1_release_guard_history()
