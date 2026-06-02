"""
模型中心窗口 - Phase 2
整合所有模型相关功能：模型状态、训练管理、策略校准、回测验证、实时监控
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ui import FootballPredictionApp


class ModelCenterWindow:
    """模型中心窗口 - 整合模型相关功能"""

    def __init__(self, root: tk.Tk, app: FootballPredictionApp):
        self.root = root
        self.app = app
        self.window: tk.Toplevel | None = None
        self._notebook: ttk.Notebook | None = None
        self._monitoring_after_id: str | None = None
        self._monitoring_text: tk.Text | None = None
        self._monitoring_auto_var: tk.BooleanVar | None = None

    def open(self, focus_tab: str | None = None) -> None:
        """打开模型中心窗口，可选直接切换到指定标签"""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            if focus_tab and self._notebook:
                self._switch_to_tab(focus_tab)
            return

        self.window = tk.Toplevel(self.root)
        self.window.title("模型中心 — 状态 · 训练 · 校准 · 回测 · 监控")
        self.window.geometry("1240x720")
        self.window.minsize(1000, 600)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self._build_layout()

        if focus_tab and self._notebook:
            self._switch_to_tab(focus_tab)

    def _switch_to_tab(self, tab_text: str) -> None:
        """切换到指定名称的标签页"""
        if self._notebook is None:
            return
        for idx in range(self._notebook.index("end")):
            if self._notebook.tab(idx, "text") == tab_text:
                self._notebook.select(idx)
                break
        
    def close(self) -> None:
        """关闭窗口"""
        self._stop_monitoring_auto_refresh()
        if self.window is not None:
            self.window.destroy()
            self.window = None
            
    def _build_layout(self) -> None:
        """构建窗口布局"""
        container = ttk.Frame(self.window, padding=14)
        container.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(
            container,
            text="模型中心",
            font=("Microsoft YaHei UI", 14, "bold")
        ).pack(anchor=tk.W)
        
        ttk.Label(
            container,
            text="模型状态 · 训练管理 · 策略校准 · 回测验证 · 实时监控",
            font=("Microsoft YaHei UI", 9),
            foreground="#64748b",
        ).pack(anchor=tk.W, pady=(2, 10))

        # 创建标签页
        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True)
        self._notebook = notebook
        
        # 标签1: 模型状态
        self._build_model_status_tab(notebook)
        
        # 标签2: 训练管理
        self._build_training_tab(notebook)
        
        # 标签3: 策略校准
        self._build_calibration_tab(notebook)
        
        # 标签4: 回测验证
        self._build_backtest_tab(notebook)

        # 标签5: 实时监控
        self._build_monitoring_tab(notebook)
        
        # 底部按钮
        footer = ttk.Frame(container)
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(footer, text="刷新状态", command=self._refresh_all).pack(side=tk.LEFT)
        ttk.Button(footer, text="关闭", command=self.close).pack(side=tk.RIGHT)
        
    def _build_model_status_tab(self, notebook: ttk.Notebook) -> None:
        """构建模型状态标签页"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="模型状态")
        
        # 状态显示区域
        status_text = tk.Text(
            tab,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            bg="#fbfdff",
            fg="#1f2937"
        )
        scroll = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=status_text.yview)
        status_text.configure(yscrollcommand=scroll.set)
        status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 加载模型状态
        self._load_model_status(status_text)

        
    def _build_training_tab(self, notebook: ttk.Notebook) -> None:
        """构建训练管理标签页"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="训练管理")
        
        # XGB训练区域
        xgb_frame = ttk.LabelFrame(tab, text="XGBoost模型", padding=10)
        xgb_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            xgb_frame,
            text="查看XGB状态",
            command=self._show_xgb_status
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            xgb_frame,
            text="训练XGB",
            command=self._train_xgb
        ).pack(side=tk.LEFT)
        
        # 玩法模型训练区域
        play_frame = ttk.LabelFrame(tab, text="玩法模型", padding=10)
        play_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            play_frame,
            text="查看玩法状态",
            command=self._show_play_model_status
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            play_frame,
            text="训练玩法模型",
            command=self._train_play_models
        ).pack(side=tk.LEFT)

        
    def _build_calibration_tab(self, notebook: ttk.Notebook) -> None:
        """构建策略校准标签页"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="策略校准")
        
        # 权重校准
        weight_frame = ttk.LabelFrame(tab, text="集成权重", padding=10)
        weight_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            weight_frame,
            text="查看权重状态",
            command=self._show_ensemble_weight_status
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            weight_frame,
            text="校准权重",
            command=self._calibrate_ensemble_weights
        ).pack(side=tk.LEFT)
        
        # 阈值校准
        threshold_frame = ttk.LabelFrame(tab, text="玩法阈值", padding=10)
        threshold_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            threshold_frame,
            text="查看阈值状态",
            command=self._show_play_threshold_status
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            threshold_frame,
            text="校准玩法阈值",
            command=self._calibrate_play_thresholds
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            threshold_frame,
            text="弱分桶校准",
            command=self._calibrate_thresholds_by_decomposition
        ).pack(side=tk.LEFT)

        
        # 贝叶斯校准
        bayes_frame = ttk.LabelFrame(tab, text="贝叶斯校准", padding=10)
        bayes_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            bayes_frame,
            text="查看贝叶斯状态",
            command=self._show_bayes_calibration_status
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            bayes_frame,
            text="校准贝叶斯",
            command=self._calibrate_bayes_calibration
        ).pack(side=tk.LEFT)
        
        # 接管策略
        policy_frame = ttk.LabelFrame(tab, text="接管策略", padding=10)
        policy_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            policy_frame,
            text="查看接管策略",
            command=self._show_play_model_policy_status
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(
            policy_frame,
            text="校准接管策略",
            command=self._calibrate_play_model_policy
        ).pack(side=tk.LEFT)
        
    def _build_backtest_tab(self, notebook: ttk.Notebook) -> None:
        """构建回测验证标签页"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="回测验证")
        
        # 权重回测
        weight_bt_frame = ttk.LabelFrame(tab, text="权重回测", padding=10)
        weight_bt_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            weight_bt_frame,
            text="运行权重回测",
            command=self._run_ensemble_backtest
        ).pack(side=tk.LEFT)

        
        # 玩法回测
        play_bt_frame = ttk.LabelFrame(tab, text="玩法回测", padding=10)
        play_bt_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            play_bt_frame,
            text="运行玩法回测",
            command=self._run_play_model_backtest
        ).pack(side=tk.LEFT)
        
        # 高准策略回测
        high_acc_frame = ttk.LabelFrame(tab, text="高准策略", padding=10)
        high_acc_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            high_acc_frame,
            text="运行高准策略回测",
            command=self._run_high_accuracy_strategy_backtest
        ).pack(side=tk.LEFT)
        
        # 审计导出
        audit_frame = ttk.LabelFrame(tab, text="审计报告", padding=10)
        audit_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            audit_frame,
            text="导出接管审计报告",
            command=self._export_play_model_takeover_gate_audit_report
        ).pack(side=tk.LEFT)

    def _build_monitoring_tab(self, notebook: ttk.Notebook) -> None:
        """构建实时监控标签页"""
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="实时监控")

        # 顶部工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(
            toolbar,
            text="立即刷新",
            command=self._refresh_monitoring,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self._monitoring_auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            toolbar,
            text="自动刷新 (10秒)",
            variable=self._monitoring_auto_var,
            command=self._on_monitoring_auto_toggle,
        ).pack(side=tk.LEFT, padx=(0, 16))

        ttk.Button(
            toolbar,
            text="导出指标",
            command=self._export_monitoring_metrics,
        ).pack(side=tk.LEFT)

        self._monitoring_last_update_var = tk.StringVar(value="")
        ttk.Label(
            toolbar,
            textvariable=self._monitoring_last_update_var,
            style="Sub.TLabel",
        ).pack(side=tk.RIGHT)

        # 监控内容区域（Text + 滚动条）
        text_frame = ttk.Frame(tab)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self._monitoring_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#0d1117",
            fg="#c9d1d9",
            insertbackground="#c9d1d9",
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._monitoring_text.yview)
        self._monitoring_text.configure(yscrollcommand=scroll.set)
        self._monitoring_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 配置颜色标签
        self._monitoring_text.tag_configure("header",   foreground="#58a6ff", font=("Consolas", 9, "bold"))
        self._monitoring_text.tag_configure("ok",       foreground="#3fb950")
        self._monitoring_text.tag_configure("warn",     foreground="#d29922")
        self._monitoring_text.tag_configure("critical", foreground="#f85149")
        self._monitoring_text.tag_configure("dim",      foreground="#8b949e")
        self._monitoring_text.tag_configure("value",    foreground="#e3b341")

        # 首次加载
        self._refresh_monitoring()
        self._start_monitoring_auto_refresh()

    # ========== 实时监控方法 ==========

    def _start_monitoring_auto_refresh(self) -> None:
        """启动自动刷新定时器"""
        self._stop_monitoring_auto_refresh()
        if self._monitoring_auto_var and self._monitoring_auto_var.get():
            if self.window and self.window.winfo_exists():
                self._monitoring_after_id = self.window.after(10_000, self._monitoring_auto_tick)

    def _stop_monitoring_auto_refresh(self) -> None:
        """停止自动刷新定时器"""
        if self._monitoring_after_id is not None:
            try:
                if self.window and self.window.winfo_exists():
                    self.window.after_cancel(self._monitoring_after_id)
            except Exception:
                pass
            self._monitoring_after_id = None

    def _monitoring_auto_tick(self) -> None:
        self._monitoring_after_id = None
        if self.window and self.window.winfo_exists():
            self._refresh_monitoring()
            self._start_monitoring_auto_refresh()

    def _on_monitoring_auto_toggle(self) -> None:
        if self._monitoring_auto_var and self._monitoring_auto_var.get():
            self._start_monitoring_auto_refresh()
        else:
            self._stop_monitoring_auto_refresh()

    def _refresh_monitoring(self) -> None:
        """刷新监控面板内容（在后台线程中获取数据，在主线程中更新 UI）"""
        def _worker():
            try:
                from .model_monitoring import get_monitor
                monitor = get_monitor()
                system  = monitor.get_system_metrics()
                models  = monitor.get_all_models_health()
                alerts  = monitor.get_alerts()
                recent  = monitor.get_recent_predictions(limit=8)
                return system, models, alerts, recent, None
            except Exception as exc:
                return None, [], [], [], str(exc)

        def _done(result):
            system, models, alerts, recent, err = result
            if self._monitoring_text is None:
                return
            if self.window is None or not self.window.winfo_exists():
                return
            self._render_monitoring(system, models, alerts, recent, err)
            from datetime import datetime
            self._monitoring_last_update_var.set(
                f"更新: {datetime.now().strftime('%H:%M:%S')}"
            )

        t = threading.Thread(target=lambda: _done(_worker()), daemon=True)
        t.start()

    def _render_monitoring(self, system, models, alerts, recent, err) -> None:
        """将监控数据渲染到 Text 控件"""
        w = self._monitoring_text
        if w is None:
            return

        w.configure(state=tk.NORMAL)
        w.delete("1.0", tk.END)

        if err:
            w.insert(tk.END, f"监控数据加载失败: {err}\n", "critical")
            w.configure(state=tk.DISABLED)
            return

        from datetime import datetime

        def line(text="", tag=None):
            if tag:
                w.insert(tk.END, text + "\n", tag)
            else:
                w.insert(tk.END, text + "\n")

        def kv(key, val, val_tag="value"):
            w.insert(tk.END, f"  {key:<22}")
            w.insert(tk.END, f"{val}\n", val_tag)

        # ── 系统指标 ──────────────────────────────────────────
        line("═" * 72, "header")
        line("  系统指标", "header")
        line("═" * 72, "header")
        if system:
            kv("内存使用",   f"{system.memory_mb:.1f} MB")
            kv("CPU 使用",   f"{system.cpu_percent:.1f}%")
            kv("活跃模型",   str(system.active_models))
            kv("总预测次数", str(system.total_predictions))
            kv("平均延迟",   f"{system.avg_latency_ms:.2f} ms")
        else:
            line("  暂无系统数据", "dim")

        # ── 模型健康 ──────────────────────────────────────────
        line()
        line("═" * 72, "header")
        line("  模型健康状态", "header")
        line("═" * 72, "header")

        if not models:
            line("  暂无模型数据（尚未进行任何预测）", "dim")
        else:
            try:
                from .model_monitoring import get_monitor
                monitor = get_monitor()
            except Exception:
                monitor = None

            for h in models:
                # 状态图标
                if h.error_rate > 0.05:
                    status_tag = "critical"
                    icon = "🔴"
                elif h.avg_latency_ms > 100 or h.error_rate > 0.01:
                    status_tag = "warn"
                    icon = "🟡"
                else:
                    status_tag = "ok"
                    icon = "🟢"

                line()
                w.insert(tk.END, f"  {icon} {h.model_name}\n", status_tag)
                kv("  总预测数",   str(h.total_predictions))
                kv("  平均延迟",   f"{h.avg_latency_ms:.2f} ms",
                   "warn" if h.avg_latency_ms > 50 else "value")
                kv("  错误率",     f"{h.error_rate:.2%}",
                   "critical" if h.error_rate > 0.05 else "warn" if h.error_rate > 0 else "ok")
                kv("  最后预测",   h.last_prediction_time or "—", "dim")

                if monitor:
                    pct = monitor.get_latency_percentiles(h.model_name)
                    kv("  P50/P90/P99",
                       f"{pct['p50']:.1f} / {pct['p90']:.1f} / {pct['p99']:.1f} ms")
                    cs = monitor.get_confidence_stats(h.model_name)
                    kv("  置信度 avg/min",
                       f"{cs['avg']:.1%} / {cs['min']:.1%}",
                       "warn" if cs["avg"] < 0.5 else "value")

        # ── 告警 ──────────────────────────────────────────────
        line()
        line("═" * 72, "header")
        line("  告警", "header")
        line("═" * 72, "header")

        if not alerts:
            line("  ✅ 无告警，系统运行正常", "ok")
        else:
            for a in alerts:
                tag = "critical" if a["level"] == "critical" else "warn"
                icon = "❌" if a["level"] == "critical" else "⚠️"
                line(f"  {icon}  [{a['model']}]  {a['message']}", tag)

        # ── 最近预测 ──────────────────────────────────────────
        line()
        line("═" * 72, "header")
        line("  最近预测记录", "header")
        line("═" * 72, "header")

        if not recent:
            line("  暂无预测记录", "dim")
        else:
            for pred in reversed(recent):
                ts = pred.timestamp[11:19]  # HH:MM:SS
                conf_tag = "warn" if pred.confidence < 0.5 else "ok"
                w.insert(tk.END, f"  [{ts}] ", "dim")
                w.insert(tk.END, f"{pred.model_name:<32}", "value")
                w.insert(tk.END, f"  {pred.latency_ms:6.2f}ms  ")
                w.insert(tk.END, f"conf={pred.confidence:.1%}\n", conf_tag)

        line()
        w.configure(state=tk.DISABLED)

    def _export_monitoring_metrics(self) -> None:
        """导出监控指标到文件"""
        def _worker():
            try:
                from .model_monitoring import get_monitor
                monitor = get_monitor()
                out = monitor.export_metrics()
                return str(out), None
            except Exception as exc:
                return None, str(exc)

        def _done(result):
            path, err = result
            if err:
                messagebox.showerror("导出失败", err, parent=self.window)
            else:
                messagebox.showinfo("导出成功", f"指标已导出到:\n{path}", parent=self.window)

        threading.Thread(target=lambda: _done(_worker()), daemon=True).start()

    # ========== 模型状态方法 ==========

    def _load_model_status(self, text_widget: tk.Text) -> None:
        """加载模型状态"""
        try:
            from .core import (
                get_xgb_training_status,
                get_play_model_training_status,
                get_ensemble_weight_status,
                get_bayes_calibration_status,
                get_play_threshold_status,
                get_play_model_policy_status,
                get_training_data_coverage_status,
                get_training_model_gate_status,
            )
            from .ui_modules import build_model_training_overview_text

            
            coverage_status = get_training_data_coverage_status()
            training_gate_status = get_training_model_gate_status(coverage_status)
            
            status_text = build_model_training_overview_text(
                xgb_status=get_xgb_training_status(),
                play_model_status=get_play_model_training_status(),
                ensemble_status=get_ensemble_weight_status(),
                bayes_status=get_bayes_calibration_status(),
                threshold_status=get_play_threshold_status(),
                policy_status=get_play_model_policy_status(),
                coverage_status=coverage_status,
                training_gate_status=training_gate_status,
            )
            
            text_widget.configure(state=tk.NORMAL)
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", status_text)
            text_widget.configure(state=tk.DISABLED)
        except Exception as e:
            text_widget.configure(state=tk.NORMAL)
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", f"加载模型状态失败: {e}")
            text_widget.configure(state=tk.DISABLED)
    
    def _refresh_all(self) -> None:
        """刷新所有状态 — 重新加载模型状态标签页"""
        if self._notebook is None:
            return
        # 找到模型状态标签页的 Text widget 并刷新
        try:
            tab = self._notebook.nametowidget(self._notebook.tabs()[0])
            for child in tab.winfo_children():
                if hasattr(child, "configure") and child.winfo_class() == "Text":
                    self._load_model_status(child)
                    break
            self._refresh_monitoring()
        except Exception:
            pass

    # ========== XGB相关方法 ==========

    def _show_xgb_status(self) -> None:
        """显示XGB状态"""
        if hasattr(self.app, "show_xgb_status"):
            self.app.show_xgb_status()
        else:
            from .ui_modules import open_text_view_window
            from .core import get_xgb_training_status
            from .ui_modules import build_model_training_overview_text
            status = get_xgb_training_status()
            text = f"XGBoost 训练状态:\n\n"
            for k, v in status.items():
                text += f"  {k}: {v}\n"
            open_text_view_window(self.root, "XGBoost 状态", text)

    def _train_xgb(self) -> None:
        """训练XGB"""
        if hasattr(self.app, "train_xgb_now"):
            self.app.train_xgb_now()
        else:
            messagebox.showinfo("训练XGB", "请从主界面执行训练操作")

    # ========== 玩法模型相关方法 ==========

    def _show_play_model_status(self) -> None:
        """显示玩法模型状态"""
        try:
            from .core import get_play_model_training_status
            from .ui_modules import build_play_model_training_status_text
            text = build_play_model_training_status_text(get_play_model_training_status())
            from .ui_modules import open_text_view_window
            open_text_view_window(self.root, "玩法模型状态", text)
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self.window)

    def _train_play_models(self) -> None:
        """训练玩法模型"""
        if hasattr(self.app, "_app_train_play_models"):
            self.app._app_train_play_models()
        elif hasattr(self.app, "train_play_models_now"):
            self.app.train_play_models_now()
        else:
            messagebox.showinfo("训练玩法模型", "请从主界面执行训练操作")

    # ========== 权重校准相关方法 ==========

    def _show_ensemble_weight_status(self) -> None:
        """显示集成权重状态"""
        try:
            from .core import get_ensemble_weight_status
            from .ui_modules import build_ensemble_weight_status_text, open_text_view_window
            text = build_ensemble_weight_status_text(get_ensemble_weight_status())
            open_text_view_window(self.root, "Ensemble 权重状态", text)
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self.window)

    def _calibrate_ensemble_weights(self) -> None:
        """校准集成权重"""
        if hasattr(self.app, "_app_calibrate_ensemble_weights"):
            self.app._app_calibrate_ensemble_weights()
        else:
            messagebox.showinfo("校准权重", "请从主界面执行校准操作")

    # ========== 阈值校准相关方法 ==========

    def _show_play_threshold_status(self) -> None:
        """显示玩法阈值状态"""
        try:
            from .core import get_play_threshold_status
            from .ui_modules import build_play_threshold_status_text, open_text_view_window
            text = build_play_threshold_status_text(get_play_threshold_status())
            open_text_view_window(self.root, "玩法阈值状态", text)
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self.window)

    def _calibrate_play_thresholds(self) -> None:
        """校准玩法阈值"""
        if hasattr(self.app, "_app_calibrate_play_thresholds"):
            self.app._app_calibrate_play_thresholds()
        else:
            messagebox.showinfo("校准阈值", "请从主界面执行校准操作")

    def _calibrate_thresholds_by_decomposition(self) -> None:
        """弱分桶校准"""
        if hasattr(self.app, "_app_calibrate_thresholds_by_decomposition"):
            self.app._app_calibrate_thresholds_by_decomposition()
        else:
            messagebox.showinfo("弱分桶校准", "请从主界面执行校准操作")

    # ========== 贝叶斯校准相关方法 ==========

    def _show_bayes_calibration_status(self) -> None:
        """显示贝叶斯校准状态"""
        try:
            from .core import get_bayes_calibration_status
            from .ui_modules import build_bayes_calibration_status_text, open_text_view_window
            text = build_bayes_calibration_status_text(get_bayes_calibration_status())
            open_text_view_window(self.root, "贝叶斯校准状态", text)
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self.window)

    def _calibrate_bayes_calibration(self) -> None:
        """校准贝叶斯"""
        if hasattr(self.app, "_app_calibrate_bayes_calibration"):
            self.app._app_calibrate_bayes_calibration()
        else:
            messagebox.showinfo("校准贝叶斯", "请从主界面执行校准操作")

    # ========== 接管策略相关方法 ==========

    def _show_play_model_policy_status(self) -> None:
        """显示接管策略状态"""
        try:
            from .core import get_play_model_policy_status
            from .ui_modules import build_play_model_policy_status_text, open_text_view_window
            text = build_play_model_policy_status_text(get_play_model_policy_status())
            open_text_view_window(self.root, "玩法接管策略", text)
        except Exception as e:
            messagebox.showerror("错误", str(e), parent=self.window)

    def _calibrate_play_model_policy(self) -> None:
        """校准接管策略"""
        if hasattr(self.app, "_app_calibrate_play_model_policy"):
            self.app._app_calibrate_play_model_policy()
        else:
            messagebox.showinfo("校准策略", "请从主界面执行校准操作")

    # ========== 回测相关方法 ==========

    def _run_ensemble_backtest(self) -> None:
        """运行权重回测"""
        if hasattr(self.app, "_app_run_ensemble_backtest"):
            self.app._app_run_ensemble_backtest()
        else:
            messagebox.showinfo("权重回测", "请从主界面执行回测操作")

    def _run_play_model_backtest(self) -> None:
        """运行玩法回测"""
        if hasattr(self.app, "_app_run_play_model_backtest"):
            self.app._app_run_play_model_backtest()
        else:
            messagebox.showinfo("玩法回测", "请从主界面执行回测操作")

    def _run_high_accuracy_strategy_backtest(self) -> None:
        """运行高准策略回测"""
        if hasattr(self.app, "_app_run_high_accuracy_strategy_backtest"):
            self.app._app_run_high_accuracy_strategy_backtest()
        else:
            messagebox.showinfo("高准策略回测", "请从主界面执行回测操作")

    def _export_play_model_takeover_gate_audit_report(self) -> None:
        """导出接管审计报告"""
        if hasattr(self.app, "_app_export_play_model_takeover_gate_audit_report"):
            self.app._app_export_play_model_takeover_gate_audit_report()
        else:
            messagebox.showinfo("审计报告", "请从主界面执行导出操作")
