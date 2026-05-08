from __future__ import annotations

import math
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import messagebox

from .core import AppMatch, fetch_matches_v24, get_recent_settlements, predict_match


BG = "#070d16"
PANEL = "#0c1420"
PANEL_2 = "#111b29"
SIDEBAR = "#0c111c"
BORDER = "#1c2a3a"
TEXT = "#e8eef8"
MUTED = "#94a3b8"
BLUE = "#4f6ef7"
GREEN = "#54d37c"
YELLOW = "#ffd84d"
RED = "#ef5b57"


@dataclass
class DashboardRow:
    match: AppMatch
    prediction: dict


def _pct(value: object) -> str:
    try:
        return f"{float(value):.0%}"
    except Exception:
        return "-"


def _risk_key(label: object) -> str:
    text = str(label or "").upper()
    if "HIGH" in text or "高" in text:
        return "high"
    if "MEDIUM" in text or "中" in text:
        return "medium"
    return "low"


def _risk_label(label: object) -> str:
    key = _risk_key(label)
    return {"low": "低风险", "medium": "中风险", "high": "高风险"}[key]


def _risk_color(label: object) -> str:
    return {"low": GREEN, "medium": YELLOW, "high": RED}[_risk_key(label)]


def _strategy_text(prediction: dict) -> str:
    pick = str(prediction.get("recommendation") or "-")
    ou = str(prediction.get("ou_recommendation") or "").strip()
    score = str(prediction.get("score_recommendation") or "").strip()
    risk = _risk_key(prediction.get("risk_level"))
    if risk == "high":
        return f"谨慎 / {ou or score or pick}"
    if risk == "medium":
        return f"{pick} / {ou or score or '观察'}"
    return pick


class SmartMatchDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("智能赛事分析系统")
        self.root.geometry("1120x820")
        self.root.minsize(980, 720)
        self.root.configure(bg=BG)

        self.rows: list[DashboardRow] = []
        self.status_var = tk.StringVar(value="正在加载赛事数据...")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.summary_vars = {
            "matches": tk.StringVar(value="0"),
            "reports": tk.StringVar(value="0"),
            "alerts": tk.StringVar(value="0"),
            "hit_rate": tk.StringVar(value="-"),
        }

        self._build_layout()
        self.refresh()

    def _build_layout(self) -> None:
        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(self.shell, bg=SIDEBAR, width=235)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.main = tk.Frame(self.shell, bg=BG)
        self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self) -> None:
        header = tk.Frame(self.sidebar, bg=SIDEBAR)
        header.pack(fill=tk.X, padx=24, pady=(22, 28))
        tk.Label(header, text="▰", bg=SIDEBAR, fg=TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="智能赛事分析系统",
            bg=SIDEBAR,
            fg=TEXT,
            font=("Microsoft YaHei UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=(10, 0))

        nav = [
            ("⌂", "首页概览", False),
            ("◇", "赛事分析", True),
            ("◎", "监控中心", False),
            ("▣", "历史报告", False),
            ("♧", "策略库", False),
            ("▤", "数据中心", False),
            ("⚙", "系统设置", False),
        ]
        for icon, text, active in nav:
            self._nav_item(icon, text, active)

        bottom = tk.Frame(self.sidebar, bg=SIDEBAR)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=24)
        tk.Label(bottom, text="●  个人开发者", bg=SIDEBAR, fg=TEXT, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(0, 12))
        tk.Label(bottom, text="⇱  退出登录", bg=SIDEBAR, fg=TEXT, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W)

    def _nav_item(self, icon: str, text: str, active: bool) -> None:
        bg = "#4051c8" if active else SIDEBAR
        item = tk.Frame(self.sidebar, bg=bg, height=48)
        item.pack(fill=tk.X, padx=16, pady=4)
        item.pack_propagate(False)
        tk.Label(item, text=icon, bg=bg, fg=TEXT, font=("Microsoft YaHei UI", 13)).pack(side=tk.LEFT, padx=(16, 12))
        tk.Label(item, text=text, bg=bg, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold" if active else "normal")).pack(side=tk.LEFT)

    def _build_main(self) -> None:
        content = tk.Frame(self.main, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=24)

        title = tk.Frame(content, bg=BG)
        title.pack(fill=tk.X)
        tk.Label(title, text="今日概览", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 17, "bold")).pack(side=tk.LEFT)
        tk.Label(title, textvariable=self.date_var, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            title,
            text="刷新",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=6,
        ).pack(side=tk.RIGHT)

        cards = tk.Frame(content, bg=BG)
        cards.pack(fill=tk.X, pady=(22, 18))
        self._metric_card(cards, "分析赛事", self.summary_vars["matches"], "场", TEXT)
        self._metric_card(cards, "生成报告", self.summary_vars["reports"], "份", TEXT)
        self._metric_card(cards, "异常预警", self.summary_vars["alerts"], "次", RED)
        self._metric_card(cards, "胜率（历史）", self.summary_vars["hit_rate"], "", "#7aa2ff")

        matches_card = self._card(content)
        matches_card.pack(fill=tk.X, pady=(0, 16))
        header = tk.Frame(matches_card, bg=PANEL)
        header.pack(fill=tk.X, padx=18, pady=(16, 8))
        tk.Label(header, text="重点赛事", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text="查看全部 ›", bg=PANEL, fg="#7692ff", font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.RIGHT)

        self.match_list = tk.Frame(matches_card, bg=PANEL)
        self.match_list.pack(fill=tk.X, padx=18, pady=(0, 14))

        charts = tk.Frame(content, bg=BG)
        charts.pack(fill=tk.BOTH, expand=True)
        self.risk_chart = self._chart_card(charts, "风险分布")
        self.conf_chart = self._chart_card(charts, "置信度分布")

        footer = tk.Label(content, textvariable=self.status_var, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 9))
        footer.pack(anchor=tk.W, pady=(10, 0))

    def _card(self, parent: tk.Widget, bg: str = PANEL) -> tk.Frame:
        frame = tk.Frame(parent, bg=bg, highlightbackground="#101d2c", highlightthickness=1)
        return frame

    def _metric_card(self, parent: tk.Widget, label: str, value: tk.StringVar, suffix: str, color: str) -> None:
        frame = self._card(parent, PANEL)
        frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 14))
        tk.Label(frame, text=label, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(pady=(18, 6))
        line = tk.Frame(frame, bg=PANEL)
        line.pack(pady=(0, 18))
        tk.Label(line, textvariable=value, bg=PANEL, fg=color, font=("Microsoft YaHei UI", 24, "bold")).pack(side=tk.LEFT)
        tk.Label(line, text=suffix, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(side=tk.LEFT, padx=(5, 0), pady=(8, 0))

    def _chart_card(self, parent: tk.Widget, title: str) -> tk.Canvas:
        frame = self._card(parent, PANEL)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        tk.Label(frame, text=title, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 14, "bold")).pack(anchor=tk.W, padx=20, pady=(16, 4))
        canvas = tk.Canvas(frame, bg=PANEL, bd=0, highlightthickness=0, height=190)
        canvas.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))
        return canvas

    def refresh(self) -> None:
        self.status_var.set("正在聚合赛事数据并执行 AI 分析...")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        try:
            fetched = fetch_matches_v24(strict_today=True)
            rows = [DashboardRow(match, predict_match(match)) for match in fetched.matches]
            self.root.after(0, lambda: self._apply_rows(rows, fetched.diagnostics.source))
        except Exception as exc:
            self.root.after(0, lambda: self._show_error(exc))

    def _show_error(self, exc: Exception) -> None:
        self.status_var.set(f"加载失败: {exc}")
        messagebox.showerror("加载失败", str(exc))

    def _apply_rows(self, rows: list[DashboardRow], source: str) -> None:
        self.rows = rows
        self.date_var.set(datetime.now().strftime("(%Y-%m-%d)"))
        self._refresh_metrics()
        self._refresh_matches()
        self._draw_risk_chart()
        self._draw_confidence_chart()
        self.status_var.set(f"已完成 {len(rows)} 场赛事分析 | 数据源 {source or '-'}")

    def _refresh_metrics(self) -> None:
        total = len(self.rows)
        alerts = sum(1 for row in self.rows if _risk_key(row.prediction.get("risk_level")) == "high")
        self.summary_vars["matches"].set(str(total))
        self.summary_vars["reports"].set(str(total))
        self.summary_vars["alerts"].set(str(alerts))
        self.summary_vars["hit_rate"].set(self._historical_hit_rate())

    def _historical_hit_rate(self) -> str:
        try:
            settlements = get_recent_settlements(limit=200)
        except Exception:
            return "-"
        hits = 0
        total = 0
        for item in settlements:
            if not isinstance(item, dict):
                continue
            if "is_correct" in item:
                total += 1
                hits += 1 if item.get("is_correct") else 0
        if total == 0:
            return "-"
        return f"{hits / total:.1%}"

    def _refresh_matches(self) -> None:
        for child in self.match_list.winfo_children():
            child.destroy()

        ranked = sorted(
            self.rows,
            key=lambda row: (
                {"high": 0, "medium": 1, "low": 2}[_risk_key(row.prediction.get("risk_level"))],
                -float(row.prediction.get("confidence", 0) or 0),
            ),
        )[:6]

        if not ranked:
            tk.Label(self.match_list, text="暂无通过校验的赛事数据", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 11)).pack(anchor=tk.W, pady=20)
            return

        for row in ranked:
            self._match_row(row)

    def _match_row(self, row: DashboardRow) -> None:
        match = row.match
        pred = row.prediction
        frame = tk.Frame(self.match_list, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, pady=5)

        left = tk.Frame(frame, bg=PANEL_2)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=18, pady=12)
        tk.Label(left, text=match.league, bg=PANEL_2, fg="#6d8dff", font=("Microsoft YaHei UI", 9, "bold")).pack(anchor=tk.W)
        tk.Label(left, text=f"{match.home_team} vs {match.away_team}", bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W, pady=(4, 2))
        tk.Label(left, text=f"开赛时间：{match.match_date} {match.match_time}", bg=PANEL_2, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)

        for title, value, color, width in [
            ("风险等级", _risk_label(pred.get("risk_level")), _risk_color(pred.get("risk_level")), 112),
            ("置信度", _pct(pred.get("confidence")), TEXT, 88),
            ("推荐策略", _strategy_text(pred), TEXT, 168),
        ]:
            block = tk.Frame(frame, bg=PANEL_2, width=width)
            block.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6), pady=12)
            block.pack_propagate(False)
            tk.Label(block, text=title, bg=PANEL_2, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
            tk.Label(block, text=value, bg=PANEL_2, fg=color, font=("Microsoft YaHei UI", 12, "bold"), wraplength=width - 8, justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 0))

    def _risk_counts(self) -> dict[str, int]:
        counts = {"low": 0, "medium": 0, "high": 0}
        for row in self.rows:
            counts[_risk_key(row.prediction.get("risk_level"))] += 1
        return counts

    def _draw_risk_chart(self) -> None:
        c = self.risk_chart
        c.delete("all")
        counts = self._risk_counts()
        total = max(sum(counts.values()), 1)
        cx, cy, radius = 96, 90, 58
        start = 90
        colors = {"low": GREEN, "medium": YELLOW, "high": RED}
        labels = {"low": "低风险", "medium": "中风险", "high": "高风险"}
        for key in ["low", "medium", "high"]:
            extent = 360 * counts[key] / total
            if extent > 0:
                c.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=start, extent=-extent, fill=colors[key], outline=PANEL)
            start -= extent
        c.create_oval(cx - 31, cy - 31, cx + 31, cy + 31, fill=PANEL, outline=PANEL)

        y = 42
        for key in ["low", "medium", "high"]:
            c.create_rectangle(205, y + 2, 214, y + 11, fill=colors[key], outline=colors[key])
            pct = counts[key] / total
            c.create_text(225, y + 7, text=f"{labels[key]}   {counts[key]} ({pct:.1%})", fill=TEXT, anchor=tk.W, font=("Microsoft YaHei UI", 10))
            y += 34

    def _draw_confidence_chart(self) -> None:
        c = self.conf_chart
        c.delete("all")
        bins = [0, 0, 0, 0]
        for row in self.rows:
            conf = float(row.prediction.get("confidence", 0) or 0)
            if conf < 0.5:
                bins[0] += 1
            elif conf < 0.6:
                bins[1] += 1
            elif conf < 0.7:
                bins[2] += 1
            else:
                bins[3] += 1

        labels = ["<50%", "50%-60%", "60%-70%", ">70%"]
        left, bottom, top = 42, 150, 30
        max_value = max(max(bins), 1)
        c.create_line(left, top, left, bottom, fill="#263448")
        c.create_line(left, bottom, 360, bottom, fill="#263448")
        for i in range(5):
            y = bottom - i * (bottom - top) / 4
            c.create_line(left, y, 360, y, fill="#152233")
            c.create_text(left - 18, y, text=str(math.ceil(max_value * i / 4)), fill=MUTED, font=("Microsoft YaHei UI", 8))
        for idx, value in enumerate(bins):
            x = 76 + idx * 72
            height = 0 if max_value == 0 else value / max_value * 105
            c.create_rectangle(x, bottom - height, x + 34, bottom, fill=BLUE, outline="#7590ff")
            c.create_text(x + 17, bottom + 18, text=labels[idx], fill=MUTED, font=("Microsoft YaHei UI", 9))


def main() -> None:
    root = tk.Tk()
    SmartMatchDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
