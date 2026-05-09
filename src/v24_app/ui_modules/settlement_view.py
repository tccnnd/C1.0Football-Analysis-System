from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Mapping


def build_gate_summary_text(gate: Mapping[str, object] | object) -> str:
    resolved = gate if isinstance(gate, Mapping) else {}
    overall = resolved.get("overall", {}) if isinstance(resolved, Mapping) else {}
    singles = resolved.get("singles", {}) if isinstance(resolved, Mapping) else {}
    parlays = resolved.get("parlays", {}) if isinstance(resolved, Mapping) else {}
    return (
        f"Gate-Overall: 命中率 {float(overall.get('hit_rate', 0) or 0):.1%} | "
        f"EV偏差 {float(overall.get('ev_bias', 0) or 0):+.1%} | "
        f"连败 {overall.get('losing_streak', 0)} | 熔断 {'ON' if overall.get('breaker_on') else 'OFF'}\n"
        f"Singles: 命中率 {float(singles.get('hit_rate', 0) or 0):.1%} | EV偏差 {float(singles.get('ev_bias', 0) or 0):+.1%} | 样本 {singles.get('sample_count', 0)}\n"
        f"Parlays: 命中率 {float(parlays.get('hit_rate', 0) or 0):.1%} | EV偏差 {float(parlays.get('ev_bias', 0) or 0):+.1%} | 样本 {parlays.get('sample_count', 0)}"
    )


def build_single_settlement_row(item: Mapping[str, object], mark_text_fn: Callable[[object], str]) -> tuple[object, ...]:
    return (
        item.get("timestamp", "-"),
        item.get("league", "-"),
        f"{item.get('home_team', '-')} vs {item.get('away_team', '-')}",
        f"{item.get('home_goals', '-')}:{item.get('away_goals', '-')}",
        item.get("predicted") or "-",
        mark_text_fn(item.get("is_correct")),
        item.get("high_accuracy_strategy_summary") or "-",
        f"{item.get('predicted_handicap') or '-'} / {mark_text_fn(item.get('handicap_is_correct'))}",
        f"{item.get('predicted_total_goals') or '-'} / {item.get('total_goals', '-')}",
        f"{item.get('predicted_score') or '-'} / {mark_text_fn(item.get('score_is_correct'))}",
    )


def build_parlay_settlement_row(item: Mapping[str, object]) -> tuple[object, ...]:
    legs = item.get("legs", [])
    leg_text = " + ".join(
        f"[{leg.get('play_type')}] {leg.get('home_team')} vs {leg.get('away_team')} {leg.get('pick')}"
        for leg in legs
        if isinstance(leg, Mapping)
    )
    return (
        item.get("settled_at") or item.get("created_at") or "-",
        "Y" if item.get("mixed") else "N",
        leg_text or "-",
        f"{float(item.get('expected_hit', 0) or 0):.1%}",
        "命中" if item.get("is_hit") else "未中",
    )


def show_recent_settlements_window(
    *,
    root: tk.Tk,
    single_items: list[dict],
    parlay_items: list[dict],
    gate: Mapping[str, object],
    mark_text_fn: Callable[[object], str],
) -> tk.Toplevel:
    window = tk.Toplevel(root)
    window.title("近期结算记录")
    window.geometry("1220x720")
    window.minsize(1080, 620)

    container = ttk.Frame(window, padding=12)
    container.pack(fill=tk.BOTH, expand=True)

    ttk.Label(container, text=build_gate_summary_text(gate), justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 10))

    notebook = ttk.Notebook(container)
    notebook.pack(fill=tk.BOTH, expand=True)

    single_frame = ttk.Frame(notebook, padding=8)
    parlay_frame = ttk.Frame(notebook, padding=8)
    notebook.add(single_frame, text="单场结算")
    notebook.add(parlay_frame, text="二串一结算")

    single_columns = ("time", "league", "match", "result", "pred", "hit", "high_strategy", "handicap", "goals", "score")
    single_tree = ttk.Treeview(single_frame, columns=single_columns, show="headings")
    single_headings = {
        "time": "时间",
        "league": "联赛",
        "match": "对阵",
        "result": "赛果",
        "pred": "胜平负",
        "hit": "命中",
        "handicap": "让球",
        "goals": "总进球",
        "score": "比分",
    }
    single_widths = {
        "time": 142,
        "league": 110,
        "match": 220,
        "result": 70,
        "pred": 90,
        "hit": 60,
        "handicap": 170,
        "goals": 140,
        "score": 130,
    }
    for key in single_columns:
        single_tree.heading(key, text=single_headings.get(key, key))
        single_tree.column(key, width=single_widths.get(key, 90), anchor=tk.CENTER)
    single_scroll = ttk.Scrollbar(single_frame, orient=tk.VERTICAL, command=single_tree.yview)
    single_tree.configure(yscrollcommand=single_scroll.set)
    single_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    single_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    for item in reversed(single_items):
        single_tree.insert("", tk.END, values=build_single_settlement_row(item, mark_text_fn))

    parlay_columns = ("time", "mixed", "legs", "expected", "status")
    parlay_tree = ttk.Treeview(parlay_frame, columns=parlay_columns, show="headings")
    parlay_headings = {
        "time": "时间",
        "mixed": "混合",
        "legs": "二串一内容",
        "expected": "组合命中率",
        "status": "状态",
    }
    parlay_widths = {
        "time": 142,
        "mixed": 60,
        "legs": 760,
        "expected": 110,
        "status": 90,
    }
    for key in parlay_columns:
        parlay_tree.heading(key, text=parlay_headings[key])
        parlay_tree.column(key, width=parlay_widths[key], anchor=tk.CENTER if key != "legs" else tk.W)
    parlay_scroll = ttk.Scrollbar(parlay_frame, orient=tk.VERTICAL, command=parlay_tree.yview)
    parlay_tree.configure(yscrollcommand=parlay_scroll.set)
    parlay_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    parlay_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    for item in reversed(parlay_items):
        parlay_tree.insert("", tk.END, values=build_parlay_settlement_row(item))

    return window
