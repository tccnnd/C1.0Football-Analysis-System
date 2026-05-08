from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


def show_c1_formal_recommendations_window(
    *,
    root: tk.Tk,
    existing_window: tk.Toplevel | None,
    rows: list[dict],
    on_export_allowlist: Callable[[], None],
) -> tk.Toplevel:
    if existing_window is not None and existing_window.winfo_exists():
        existing_window.destroy()

    window = tk.Toplevel(root)
    window.title("C1 正式建议清单")
    window.geometry("980x520")
    window.minsize(860, 460)
    window.transient(root)

    container = ttk.Frame(window, padding=14)
    container.pack(fill=tk.BOTH, expand=True)

    ttk.Label(container, text="C1 正式建议清单", font=("Microsoft YaHei UI", 14, "bold")).pack(anchor=tk.W)
    ttk.Label(
        container,
        text=f"当前可放行 {len(rows)} 场 | 已按候选置信度排序",
        style="Sub.TLabel",
    ).pack(anchor=tk.W, pady=(4, 10))

    columns = ("match", "official", "play", "selection", "confidence", "provider", "reason")
    tree = ttk.Treeview(container, columns=columns, show="headings")
    headings = {
        "match": "比赛",
        "official": "正式建议",
        "play": "玩法",
        "selection": "候选选择",
        "confidence": "置信度",
        "provider": "阵容源",
        "reason": "治理主因",
    }
    widths = {
        "match": 230,
        "official": 140,
        "play": 90,
        "selection": 140,
        "confidence": 95,
        "provider": 110,
        "reason": 170,
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

    for item in rows:
        line = item.get("line")
        selection_text = str(item.get("selection") or "-")
        if line not in (None, ""):
            selection_text = f"{selection_text} {line}"
        tree.insert(
            "",
            tk.END,
            values=(
                item.get("match_label", "-"),
                item.get("official_pick", "-"),
                item.get("play", "-"),
                selection_text,
                f"{float(item.get('confidence', 0) or 0):.2%}",
                item.get("provider_name", "-"),
                item.get("primary_reason_code", "-"),
            ),
        )

    footer = ttk.Frame(container)
    footer.pack(fill=tk.X, pady=(10, 0))
    ttk.Label(footer, text="该清单只包含 C1 release_allowed=true 的比赛。", style="Sub.TLabel").pack(side=tk.LEFT)
    ttk.Button(footer, text="导出放行清单", command=on_export_allowlist).pack(side=tk.RIGHT, padx=(0, 8))
    ttk.Button(footer, text="关闭", command=window.destroy).pack(side=tk.RIGHT)
    return window
