from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Mapping

from .c1_release import (
    comparison_window_row_values,
    filter_comparison_rows,
    filter_release_rows,
    release_window_row_values,
)
from .c1_availability_flow import build_c1_release_guard_history_rows, build_c1_release_guard_history_text


def show_c1_release_window(
    *,
    root: tk.Tk,
    existing_window: tk.Toplevel | None,
    total_matches: int,
    summary: dict,
    rows: list[dict],
    default_filter: str,
    on_export_allowlist: Callable[[list[dict]], None],
) -> tk.Toplevel:
    if existing_window is not None and existing_window.winfo_exists():
        existing_window.destroy()

    window = tk.Toplevel(root)
    window.title("C1 放行评估")
    window.geometry("1120x560")
    window.minsize(980, 480)
    window.transient(root)

    container = ttk.Frame(window, padding=14)
    container.pack(fill=tk.BOTH, expand=True)

    ttk.Label(container, text="C1 放行评估", font=("Microsoft YaHei UI", 14, "bold")).pack(anchor=tk.W)
    ttk.Label(
        container,
        text=f"场次 {total_matches} | 放行 {summary.get('release_allowed_count', 0)} | Release {summary.get('release_counts', {})} | Provider {summary.get('provider_counts', {})}",
        style="Sub.TLabel",
    ).pack(anchor=tk.W, pady=(4, 10))

    filter_row = ttk.Frame(container)
    filter_row.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(filter_row, text="筛选", style="Sub.TLabel").pack(side=tk.LEFT)
    filter_var = tk.StringVar(value=default_filter)
    filter_box = ttk.Combobox(filter_row, state="readonly", width=12, textvariable=filter_var, values=["全部", "可放行", "保留"])
    filter_box.pack(side=tk.LEFT, padx=(8, 12))
    summary_var = tk.StringVar(value=f"显示 {len(rows)} / {total_matches} 场")
    ttk.Label(filter_row, textvariable=summary_var, style="Sub.TLabel").pack(side=tk.LEFT)

    columns = ("match", "governance", "release", "candidate", "selection", "confidence", "provider", "reason")
    tree = ttk.Treeview(container, columns=columns, show="headings")
    headings = {
        "match": "比赛",
        "governance": "治理",
        "release": "放行动作",
        "candidate": "候选玩法",
        "selection": "候选选择",
        "confidence": "候选置信度",
        "provider": "阵容源",
        "reason": "主因",
    }
    widths = {
        "match": 220,
        "governance": 90,
        "release": 110,
        "candidate": 90,
        "selection": 120,
        "confidence": 95,
        "provider": 110,
        "reason": 180,
    }
    for key in columns:
        tree.heading(key, text=headings[key])
        tree.column(key, width=widths[key], anchor=tk.CENTER if key not in {"match", "reason"} else tk.W)

    tree_frame = ttk.Frame(container)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _render_rows() -> None:
        tree.delete(*tree.get_children())
        current_rows = filter_release_rows(rows, filter_var.get())
        summary_var.set(f"显示 {len(current_rows)} / {total_matches} 场")
        for item in current_rows:
            tree.insert("", tk.END, values=release_window_row_values(item))

    filter_box.bind("<<ComboboxSelected>>", lambda _event: _render_rows())
    _render_rows()

    footer = ttk.Frame(container)
    footer.pack(fill=tk.X, pady=(10, 0))
    ttk.Label(
        footer,
        text=f"Governance: {summary.get('governance_counts', {})} | Release: {summary.get('release_counts', {})}",
        style="Sub.TLabel",
        justify=tk.LEFT,
    ).pack(side=tk.LEFT)
    ttk.Button(footer, text="导出放行清单", command=lambda: on_export_allowlist(rows)).pack(side=tk.RIGHT, padx=(0, 8))
    ttk.Button(footer, text="关闭", command=window.destroy).pack(side=tk.RIGHT)
    return window


def show_c1_comparison_window(
    *,
    root: tk.Tk,
    existing_window: tk.Toplevel | None,
    total_matches: int,
    summary: dict,
    rows: list[dict],
    markdown_report: str,
    json_report: str,
    on_apply_to_main: Callable[[list[dict]], None],
    on_export_pending_template: Callable[[list[dict]], None],
) -> tk.Toplevel:
    if existing_window is not None and existing_window.winfo_exists():
        existing_window.destroy()

    window = tk.Toplevel(root)
    window.title("C1 对照结果")
    window.geometry("1260x620")
    window.minsize(1100, 520)
    window.transient(root)

    container = ttk.Frame(window, padding=14)
    container.pack(fill=tk.BOTH, expand=True)

    ttk.Label(container, text="C1 对照结果", font=("Microsoft YaHei UI", 14, "bold")).pack(anchor=tk.W)
    ttk.Label(
        container,
        text=f"场次 {total_matches} | 治理分布 {summary.get('governance_counts', {})} | 原因码 {summary.get('reason_code_counts', {})}",
        style="Sub.TLabel",
    ).pack(anchor=tk.W, pady=(4, 10))

    filter_row = ttk.Frame(container)
    filter_row.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(filter_row, text="筛选", style="Sub.TLabel").pack(side=tk.LEFT)
    filter_var = tk.StringVar(value="全部")
    filter_options = ["全部", "待处理", "补阵容", "观察", "复核分歧", "可放行", "接近阻断", "阻断"]
    filter_box = ttk.Combobox(filter_row, state="readonly", width=12, textvariable=filter_var, values=filter_options)
    filter_box.pack(side=tk.LEFT, padx=(8, 12))
    filter_summary_var = tk.StringVar(value=f"显示 {len(rows)} / {total_matches} 场")
    ttk.Label(filter_row, textvariable=filter_summary_var, style="Sub.TLabel").pack(side=tk.LEFT)

    columns = ("match", "v24", "c1", "action", "suggested", "reason", "codes", "diverged", "near_block", "gap")
    tree = ttk.Treeview(container, columns=columns, show="headings")
    headings = {
        "match": "比赛",
        "v24": "V24",
        "c1": "C1",
        "action": "治理动作",
        "suggested": "建议动作",
        "reason": "主因",
        "codes": "原因码",
        "diverged": "方向分歧",
        "near_block": "接近阻断",
        "gap": "置信差",
    }
    widths = {
        "match": 220,
        "v24": 150,
        "c1": 130,
        "action": 90,
        "suggested": 90,
        "reason": 170,
        "codes": 240,
        "diverged": 72,
        "near_block": 72,
        "gap": 78,
    }
    for key in columns:
        tree.heading(key, text=headings[key])
        tree.column(key, width=widths[key], anchor=tk.CENTER if key not in {"match", "codes"} else tk.W)

    tree_frame = ttk.Frame(container)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _render_rows() -> None:
        tree.delete(*tree.get_children())
        current_rows = filter_comparison_rows(rows, filter_var.get())
        filter_summary_var.set(f"显示 {len(current_rows)} / {total_matches} 场")
        for item in current_rows:
            tree.insert("", tk.END, values=comparison_window_row_values(item))

    filter_box.bind("<<ComboboxSelected>>", lambda _event: _render_rows())
    _render_rows()

    footer = ttk.Frame(container)
    footer.pack(fill=tk.X, pady=(10, 0))
    meta = (
        f"Markdown: {markdown_report}\n"
        f"JSON: {json_report}\n"
        f"Side Divergence: {summary.get('side_divergence_count', 0)} | "
        f"Blocked: {summary.get('blocked_count', 0)} | Near Block: {summary.get('near_block_count', 0)}"
    )
    ttk.Label(footer, text=meta, style="Sub.TLabel", justify=tk.LEFT).pack(side=tk.LEFT)
    ttk.Button(footer, text="应用到主列表", command=lambda: on_apply_to_main(rows)).pack(side=tk.RIGHT, padx=(0, 8))
    ttk.Button(footer, text="仅导出待处理模板", command=lambda: on_export_pending_template(rows)).pack(side=tk.RIGHT, padx=(0, 8))
    ttk.Button(footer, text="关闭", command=window.destroy).pack(side=tk.RIGHT)
    return window


def show_c1_release_guard_history_window(
    *,
    root: tk.Tk,
    existing_window: tk.Toplevel | None,
    rows: list[Mapping[str, object]],
    header: str,
    on_close: Callable[[], None],
) -> tk.Toplevel:
    if existing_window is not None and existing_window.winfo_exists():
        existing_window.lift()
        existing_window.focus_force()
        return existing_window

    window = tk.Toplevel(root)
    window.title("C1 放行门控审计")
    window.geometry("1180x720")
    window.minsize(980, 560)
    window.transient(root)
    window.protocol("WM_DELETE_WINDOW", on_close)

    container = ttk.Frame(window, padding=14)
    container.pack(fill=tk.BOTH, expand=True)
    ttk.Label(container, text="C1 放行门控审计", font=("Microsoft YaHei UI", 14, "bold")).pack(anchor=tk.W)
    ttk.Label(container, text=header, style="Sub.TLabel").pack(anchor=tk.W, pady=(4, 10))

    table_rows = build_c1_release_guard_history_rows(rows, limit=50)
    columns = ("time", "file", "status", "raw_status", "mode", "policy", "quality", "matches", "reasons", "issue")
    tree = ttk.Treeview(container, columns=columns, show="headings", height=10)
    headings = {
        "time": "时间",
        "file": "报告",
        "status": "状态",
        "raw_status": "原始",
        "mode": "模式",
        "policy": "策略阻/开",
        "quality": "质检F/W",
        "matches": "场次",
        "reasons": "源原因",
        "issue": "首要问题",
    }
    widths = {
        "time": 150,
        "file": 230,
        "status": 70,
        "raw_status": 70,
        "mode": 120,
        "policy": 80,
        "quality": 80,
        "matches": 58,
        "reasons": 64,
        "issue": 260,
    }
    for key in columns:
        tree.heading(key, text=headings[key])
        tree.column(key, width=widths[key], anchor=tk.W if key in {"file", "issue"} else tk.CENTER)

    table_frame = ttk.Frame(container)
    table_frame.pack(fill=tk.BOTH, expand=False)
    y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
    tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    detail_label_var = tk.StringVar(value="报告详情")
    ttk.Label(container, textvariable=detail_label_var, style="Sub.TLabel").pack(anchor=tk.W, pady=(12, 4))
    detail_frame = ttk.Frame(container)
    detail_frame.pack(fill=tk.BOTH, expand=True)
    detail = tk.Text(detail_frame, wrap=tk.NONE, font=("Consolas", 10), background="#fbfdff")
    detail_y = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=detail.yview)
    detail_x = ttk.Scrollbar(detail_frame, orient=tk.HORIZONTAL, command=detail.xview)
    detail.configure(yscrollcommand=detail_y.set, xscrollcommand=detail_x.set)
    detail.grid(row=0, column=0, sticky="nsew")
    detail_y.grid(row=0, column=1, sticky="ns")
    detail_x.grid(row=1, column=0, sticky="ew")
    detail_frame.rowconfigure(0, weight=1)
    detail_frame.columnconfigure(0, weight=1)

    row_by_id: dict[str, Mapping[str, object]] = {}
    for idx, item in enumerate(table_rows):
        iid = str(idx)
        row_by_id[iid] = item
        tree.insert(
            "",
            tk.END,
            iid=iid,
            values=(
                item.get("time", "-"),
                item.get("file", "-"),
                item.get("status", "-"),
                item.get("raw_status", "-"),
                item.get("runtime_mode", "-"),
                item.get("policy", "-"),
                item.get("quality", "-"),
                item.get("matches", "0"),
                item.get("provider_reasons", "0"),
                item.get("issue", "-"),
            ),
        )

    def _set_detail(text: str, label: str) -> None:
        detail.configure(state=tk.NORMAL)
        detail.delete("1.0", tk.END)
        detail.insert("1.0", text)
        detail.configure(state=tk.DISABLED)
        detail_label_var.set(label)

    def _show_selected_detail(_event: object | None = None) -> None:
        selection = tree.selection()
        if not selection:
            _set_detail(build_c1_release_guard_history_text(rows), "报告详情 | 汇总")
            return
        item = row_by_id.get(selection[0], {})
        label = f"报告详情 | {item.get('file', '-')}"
        text = str(item.get("text") or "").strip() or build_c1_release_guard_history_text(rows)
        _set_detail(text, label)

    tree.bind("<<TreeviewSelect>>", _show_selected_detail)
    if table_rows:
        tree.selection_set("0")
        tree.focus("0")
        _show_selected_detail()
    else:
        _show_selected_detail()

    footer = ttk.Frame(container)
    footer.pack(fill=tk.X, pady=(10, 0))
    ttk.Label(footer, text=f"显示 {len(table_rows)} / {len(rows)} 份报告", style="Sub.TLabel").pack(side=tk.LEFT)
    ttk.Button(footer, text="关闭", command=on_close).pack(side=tk.RIGHT)
    return window
