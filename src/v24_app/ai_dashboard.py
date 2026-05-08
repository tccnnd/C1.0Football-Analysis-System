from __future__ import annotations

import math
import json
import re
import threading
import tkinter as tk
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from .core import AppMatch, auto_settle_finished_matches, fetch_matches_v24, get_recent_settlements, predict_match


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
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports"
SETTINGS_PATH = PROJECT_ROOT / "data" / "state" / "ai_dashboard_settings.json"


@dataclass
class DashboardRow:
    match: AppMatch
    prediction: dict


def _pct(value: object) -> str:
    try:
        return f"{float(value):.0%}"
    except Exception:
        return "-"


def _pct1(value: object) -> str:
    try:
        return f"{float(value):.1%}"
    except Exception:
        return "-"


def _num(value: object, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _prob_text(probabilities: dict, key: str) -> str:
    labels = {"home": "\u4e3b\u80dc", "draw": "\u5e73\u5c40", "away": "\u5ba2\u80dc"}
    return f"{labels[key]} {_pct1(probabilities.get(key, 0))}"


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


def _analysis_report(row: DashboardRow) -> str:
    match = row.match
    pred = row.prediction
    indices = pred.get("indices", {}) if isinstance(pred.get("indices"), dict) else {}
    probs = pred.get("probabilities", {}) if isinstance(pred.get("probabilities"), dict) else {}
    market_probs = pred.get("market_probabilities", {}) if isinstance(pred.get("market_probabilities"), dict) else {}
    risk = _risk_key(pred.get("risk_level"))

    risk_reason = {
        "high": "\u51b7\u95e8\u6307\u6570\u504f\u9ad8\uff0c\u5e02\u573a\u4e0e\u6a21\u578b\u53ef\u80fd\u5b58\u5728\u660e\u663e\u5206\u6b67\u3002",
        "medium": "\u5b58\u5728\u4e00\u5b9a\u6ce2\u52a8\uff0c\u5efa\u8bae\u964d\u4f4e\u6743\u91cd\u5e76\u7ed3\u5408\u8d5b\u524d\u4fe1\u606f\u590d\u6838\u3002",
        "low": "\u7efc\u5408\u6307\u6807\u76f8\u5bf9\u7a33\u5b9a\uff0c\u76ee\u524d\u6ca1\u6709\u89e6\u53d1\u660e\u663e\u98ce\u9669\u4fe1\u53f7\u3002",
    }[risk]
    market_line = ""
    if market_probs:
        market_line = (
            "\n"
            f"- \u5e02\u573a\u9690\u542b\u6982\u7387\uff1a"
            f"{_prob_text(market_probs, 'home')} / {_prob_text(market_probs, 'draw')} / {_prob_text(market_probs, 'away')}"
        )

    return (
        f"\u5bf9\u9635\uff1a{match.home_team} vs {match.away_team}\n"
        f"\u8054\u8d5b\uff1a{match.league}\n"
        f"\u5f00\u8d5b\uff1a{match.match_date} {match.match_time}\n\n"
        "\u6838\u5fc3\u7ed3\u8bba\n"
        f"- \u63a8\u8350\u7b56\u7565\uff1a{_strategy_text(pred)}\n"
        f"- \u98ce\u9669\u7b49\u7ea7\uff1a{_risk_label(pred.get('risk_level'))}\n"
        f"- \u7efc\u5408\u7f6e\u4fe1\u5ea6\uff1a{_pct1(pred.get('confidence'))}\n"
        f"- \u9884\u8ba1\u603b\u8fdb\u7403\uff1a{_num(pred.get('expected_goals'))}\n\n"
        "\u6982\u7387\u5206\u5e03\n"
        f"- {_prob_text(probs, 'home')} / {_prob_text(probs, 'draw')} / {_prob_text(probs, 'away')}"
        f"{market_line}\n\n"
        "\u73a9\u6cd5\u7ef4\u5ea6\n"
        f"- \u5927\u5c0f\u7403\uff1a{pred.get('ou_recommendation', '-')} ({_pct1(pred.get('ou_confidence'))})\n"
        f"- \u8ba9\u7403\uff1a{pred.get('handicap_recommendation', '-')} ({_pct1(pred.get('handicap_confidence'))})\n"
        f"- \u6bd4\u5206\uff1a{pred.get('score_recommendation', '-')} ({_pct1(pred.get('score_confidence'))})\n"
        f"- \u534a\u5168\u573a\uff1a{pred.get('htft_recommendation', '-')} ({_pct1(pred.get('htft_confidence'))})\n\n"
        "\u98ce\u9669\u89e3\u8bfb\n"
        f"- {risk_reason}\n"
        f"- \u51b7\u95e8\u6307\u6570\uff1a{_pct1(indices.get('upset_index', 0))}\n"
        f"- \u7a33\u5b9a\u6307\u6570\uff1a{_pct1(indices.get('stability_index', 0))}\n"
        f"- \u4fe1\u5fc3\u6307\u6570\uff1a{_pct1(indices.get('confidence_index', 0))}\n\n"
        "\u590d\u6838\u5efa\u8bae\n"
        "- \u8d5b\u524d\u91cd\u70b9\u590d\u6838\u4f24\u505c\u3001\u9996\u53d1\u3001\u76d8\u53e3\u53d8\u5316\u548c\u5e02\u573a\u70ed\u5ea6\u3002\n"
        "- \u82e5\u4e34\u573a\u76d8\u53e3\u4e0e\u6a21\u578b\u65b9\u5411\u6301\u7eed\u80cc\u79bb\uff0c\u5e94\u4e0b\u8c03\u7b56\u7565\u6743\u91cd\u3002"
    )


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text, flags=re.UNICODE).strip("_")
    return cleaned[:80] or "match"


def _md_cell(value: object) -> str:
    return str(value if value is not None else "-").replace("|", "/").replace("\n", " ")


def _prob_table(title: str, probabilities: dict) -> str:
    if not isinstance(probabilities, dict) or not probabilities:
        return f"### {title}\n\n暂无数据\n"
    return (
        f"### {title}\n\n"
        "| 主胜 | 平局 | 客胜 |\n"
        "|---:|---:|---:|\n"
        f"| {_pct1(probabilities.get('home', 0))} | {_pct1(probabilities.get('draw', 0))} | {_pct1(probabilities.get('away', 0))} |\n"
    )


def _index_table(indices: dict) -> str:
    return (
        "| 指标 | 数值 |\n"
        "|---|---:|\n"
        f"| 冷门指数 | {_pct1(indices.get('upset_index', 0))} |\n"
        f"| 稳定指数 | {_pct1(indices.get('stability_index', 0))} |\n"
        f"| 信心指数 | {_pct1(indices.get('confidence_index', 0))} |\n"
    )


def _markdown_report(row: DashboardRow, generated_at: datetime | None = None) -> str:
    now = generated_at or datetime.now()
    match = row.match
    pred = row.prediction
    probs = pred.get("probabilities", {}) if isinstance(pred.get("probabilities"), dict) else {}
    market_probs = pred.get("market_probabilities", {}) if isinstance(pred.get("market_probabilities"), dict) else {}
    elo_probs = pred.get("elo_probabilities", {}) if isinstance(pred.get("elo_probabilities"), dict) else {}
    poisson_probs = pred.get("poisson_probabilities", {}) if isinstance(pred.get("poisson_probabilities"), dict) else {}
    xgb_probs = pred.get("xgb_probabilities", {}) if isinstance(pred.get("xgb_probabilities"), dict) else {}
    handicap_probs = pred.get("handicap_probabilities", {}) if isinstance(pred.get("handicap_probabilities"), dict) else {}
    ou_probs = pred.get("ou_probabilities", {}) if isinstance(pred.get("ou_probabilities"), dict) else {}
    indices = pred.get("indices", {}) if isinstance(pred.get("indices"), dict) else {}
    return (
        f"# {match.home_team} vs {match.away_team} \u8d5b\u4e8b\u5206\u6790\u62a5\u544a\n\n"
        "## 1. 基本信息\n\n"
        "| 字段 | 内容 |\n"
        "|---|---|\n"
        f"| 生成时间 | {now.strftime('%Y-%m-%d %H:%M:%S')} |\n"
        f"| 联赛 | {_md_cell(match.league)} |\n"
        f"| 开赛时间 | {_md_cell(match.match_date)} {_md_cell(match.match_time)} |\n"
        f"| 数据源 | {_md_cell(match.source)} |\n"
        f"| 数据 ID | {_md_cell(match.source_id or '-')} |\n\n"
        "## 2. 核心结论\n\n"
        "| 项目 | 结果 |\n"
        "|---|---|\n"
        f"| 推荐策略 | {_md_cell(_strategy_text(pred))} |\n"
        f"| 风险等级 | {_md_cell(_risk_label(pred.get('risk_level')))} |\n"
        f"| 综合置信度 | {_pct1(pred.get('confidence'))} |\n"
        f"| 预计总进球 | {_num(pred.get('expected_goals'))} |\n"
        f"| 当前模型 | {_md_cell(pred.get('model', '-'))} |\n\n"
        "## 3. 概率分布\n\n"
        f"{_prob_table('融合概率', probs)}\n"
        f"{_prob_table('市场隐含概率', market_probs)}\n"
        f"{_prob_table('ELO 概率', elo_probs)}\n"
        f"{_prob_table('Poisson 概率', poisson_probs)}\n"
        f"{_prob_table('XGBoost 概率', xgb_probs)}\n"
        "## 4. 玩法维度\n\n"
        "| 玩法 | 推荐 | 置信度 | 补充 |\n"
        "|---|---|---:|---|\n"
        f"| 1X2 | {_md_cell(pred.get('recommendation', '-'))} | {_pct1(pred.get('confidence'))} | 主胜/平局/客胜 |\n"
        f"| 大小球 | {_md_cell(pred.get('ou_recommendation', '-'))} | {_pct1(pred.get('ou_confidence'))} | Over {_pct1(ou_probs.get('over'))} / Under {_pct1(ou_probs.get('under'))} |\n"
        f"| 让球 | {_md_cell(pred.get('handicap_recommendation', '-'))} | {_pct1(pred.get('handicap_confidence'))} | H {_pct1(handicap_probs.get('home'))} / D {_pct1(handicap_probs.get('draw'))} / A {_pct1(handicap_probs.get('away'))} |\n"
        f"| 比分 | {_md_cell(pred.get('score_recommendation', '-'))} | {_pct1(pred.get('score_confidence'))} | 精确比分候选 |\n"
        f"| 半全场 | {_md_cell(pred.get('htft_recommendation', '-'))} | {_pct1(pred.get('htft_confidence'))} | 节奏推演 |\n\n"
        "## 5. 风控指标\n\n"
        f"{_index_table(indices)}\n"
        "## 6. 盘口与市场数据\n\n"
        "| 指标 | 数值 |\n"
        "|---|---:|\n"
        f"| 即时主胜赔率 | {_num(match.odds_home, 3)} |\n"
        f"| 即时平局赔率 | {_num(match.odds_draw, 3)} |\n"
        f"| 即时客胜赔率 | {_num(match.odds_away, 3)} |\n"
        f"| 初盘主胜赔率 | {_num(match.opening_odds_home, 3)} |\n"
        f"| 初盘平局赔率 | {_num(match.opening_odds_draw, 3)} |\n"
        f"| 初盘客胜赔率 | {_num(match.opening_odds_away, 3)} |\n"
        f"| 让球线 | {_num(match.handicap_line, 2)} |\n"
        f"| 返还率 | {_pct1(match.return_rate)} |\n"
        f"| Kelly 主胜 | {_num(match.kelly_home, 3)} |\n"
        f"| Kelly 平局 | {_num(match.kelly_draw, 3)} |\n"
        f"| Kelly 客胜 | {_num(match.kelly_away, 3)} |\n\n"
        "## 7. AI 分析摘要\n\n"
        f"{_analysis_report(row)}\n\n"
        "## 8. 复核清单\n\n"
        "- [ ] 复核首发阵容与关键伤停\n"
        "- [ ] 复核临场盘口是否继续偏离模型方向\n"
        "- [ ] 复核市场热度与赔率变化是否一致\n"
        "- [ ] 高风险场次降低策略权重或仅观察\n"
        "- [ ] 赛后回收赛果并进入复盘中心\n"
    )


def _bytes_text(size: int) -> str:
    value = float(max(size, 0))
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _dir_stats(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    count = 0
    size = 0
    try:
        files = path.rglob("*")
        for item in files:
            try:
                if item.is_file():
                    count += 1
                    size += item.stat().st_size
            except OSError:
                continue
    except OSError:
        return count, size
    return count, size


def _mtime_text(path: Path) -> str:
    try:
        if not path.exists():
            return "-"
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return "-"


def _load_dashboard_settings() -> dict:
    try:
        if not SETTINGS_PATH.exists():
            return {}
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_dashboard_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


class SmartMatchDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("智能赛事分析系统")
        self.root.geometry("1120x820")
        self.root.minsize(980, 720)
        self.root.configure(bg=BG)

        self.rows: list[DashboardRow] = []
        self.data_source = "-"
        self.last_loaded_at = "-"
        self.last_refresh_seconds: float | None = None
        self.event_log: list[tuple[str, str, str]] = []
        self.current_nav_index = 1
        self.nav_items: list[tuple[tk.Frame, list[tk.Label]]] = []
        settings = _load_dashboard_settings()
        self.auto_refresh_enabled = tk.BooleanVar(value=bool(settings.get("auto_refresh_enabled", False)))
        self.auto_refresh_interval_min = tk.IntVar(value=max(3, min(int(settings.get("auto_refresh_interval_min", 10) or 10), 120)))
        self._auto_refresh_after_id: str | None = None
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
        self._schedule_auto_refresh()

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

    def _clear_main(self) -> None:
        for child in self.main.winfo_children():
            child.destroy()

    def _page_shell(self, title: str, subtitle: str = "") -> tk.Frame:
        self._clear_main()
        shell = tk.Frame(self.main, bg=BG)
        shell.pack(fill=tk.BOTH, expand=True, padx=22, pady=20)
        tk.Label(shell, text=title, bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        if subtitle:
            tk.Label(shell, text=subtitle, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(6, 16))
        return shell

    def _widget_alive(self, name: str) -> bool:
        widget = getattr(self, name, None)
        try:
            return bool(widget is not None and widget.winfo_exists())
        except tk.TclError:
            return False

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
        for index, (icon, text, active) in enumerate(nav):
            command = None
            if index in (0, 1):
                command = self._build_main
            elif index == 2:
                command = self.open_monitor_center
            elif index == 3:
                command = self.open_history_reports
            elif index == 4:
                command = self.open_strategy_library
            elif index == 5:
                command = self.open_data_center
            elif index == 6:
                command = self.open_system_settings
            self._nav_item(index, icon, text, active, command=command)

    def _nav_item(self, index: int, icon: str, text: str, active: bool, command=None) -> None:
        bg = "#4051c8" if active else SIDEBAR
        item = tk.Frame(self.sidebar, bg=bg, height=48)
        item.pack(fill=tk.X, padx=16, pady=4)
        item.pack_propagate(False)
        icon_label = tk.Label(item, text=icon, bg=bg, fg=TEXT, font=("Microsoft YaHei UI", 13))
        icon_label.pack(side=tk.LEFT, padx=(16, 12))
        text_label = tk.Label(item, text=text, bg=bg, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold" if active else "normal"))
        text_label.pack(side=tk.LEFT)
        self.nav_items.append((item, [icon_label, text_label]))
        if command is not None:
            wrapped = lambda: self._select_nav(index, command)
            item.configure(cursor="hand2")
            item.bind("<Button-1>", lambda _event: wrapped())
            for child in item.winfo_children():
                child.configure(cursor="hand2")
                child.bind("<Button-1>", lambda _event: wrapped())

    def _select_nav(self, index: int, command) -> None:
        self.current_nav_index = index
        self._refresh_nav_highlight()
        command()

    def _refresh_nav_highlight(self) -> None:
        for index, (item, labels) in enumerate(self.nav_items):
            active = index == self.current_nav_index
            bg = "#4051c8" if active else SIDEBAR
            item.configure(bg=bg)
            for label in labels:
                label.configure(bg=bg, font=("Microsoft YaHei UI", 11 if label is labels[1] else 13, "bold" if active and label is labels[1] else "normal"))

    def _build_main(self) -> None:
        self.current_nav_index = 1
        self._refresh_nav_highlight()
        self._clear_main()
        content = tk.Frame(self.main, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=24)

        title = tk.Frame(content, bg=BG)
        title.pack(fill=tk.X)
        tk.Label(title, text="今日概览", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 17, "bold")).pack(side=tk.LEFT)
        tk.Label(title, textvariable=self.date_var, bg=BG, fg=MUTED, font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            title,
            text="\u590d\u76d8\u4e2d\u5fc3",
            command=self.open_review_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=6,
        ).pack(side=tk.RIGHT, padx=(8, 0))
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

        self.match_list = tk.Frame(matches_card, bg=PANEL, height=208)
        self.match_list.pack(fill=tk.X, padx=18, pady=(0, 10))
        self.match_list.pack_propagate(False)

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
        self._log_event("INFO", "\u5f00\u59cb\u5237\u65b0\u8d5b\u4e8b\u6570\u636e")
        self.status_var.set("正在聚合赛事数据并执行 AI 分析...")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _schedule_auto_refresh(self) -> None:
        if self._auto_refresh_after_id is not None:
            try:
                self.root.after_cancel(self._auto_refresh_after_id)
            except Exception:
                pass
            self._auto_refresh_after_id = None
        if not self.auto_refresh_enabled.get():
            return
        interval = max(3, min(int(self.auto_refresh_interval_min.get()), 120))
        self.auto_refresh_interval_min.set(interval)
        self._auto_refresh_after_id = self.root.after(interval * 60 * 1000, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        self._auto_refresh_after_id = None
        if not self.auto_refresh_enabled.get():
            return
        self._log_event("INFO", "\u81ea\u52a8\u5237\u65b0\u89e6\u53d1")
        self.refresh()
        self._schedule_auto_refresh()

    def _on_auto_refresh_changed(self) -> None:
        interval = max(3, min(int(self.auto_refresh_interval_min.get()), 120))
        self.auto_refresh_interval_min.set(interval)
        _save_dashboard_settings(
            {
                "auto_refresh_enabled": bool(self.auto_refresh_enabled.get()),
                "auto_refresh_interval_min": interval,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        self._schedule_auto_refresh()
        if self.auto_refresh_enabled.get():
            self.status_var.set(f"\u81ea\u52a8\u5237\u65b0\u5df2\u5f00\u542f\uff0c\u95f4\u9694 {self.auto_refresh_interval_min.get()} \u5206\u949f")
            self._log_event("INFO", f"\u81ea\u52a8\u5237\u65b0\u5f00\u542f: {self.auto_refresh_interval_min.get()} min")
        else:
            self.status_var.set("\u81ea\u52a8\u5237\u65b0\u5df2\u5173\u95ed")
            self._log_event("INFO", "\u81ea\u52a8\u5237\u65b0\u5173\u95ed")

    def _load_worker(self) -> None:
        started = time.perf_counter()
        try:
            fetched = fetch_matches_v24(strict_today=True)
            rows = [DashboardRow(match, predict_match(match)) for match in fetched.matches]
            elapsed = time.perf_counter() - started
            self.root.after(0, lambda: self._apply_rows(rows, fetched.diagnostics.source, elapsed))
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self.last_refresh_seconds = elapsed
            self.root.after(0, lambda: self._show_error(exc))

    def _show_error(self, exc: Exception) -> None:
        self._log_event("ERROR", f"\u52a0\u8f7d\u5931\u8d25: {exc}")
        self.status_var.set(f"加载失败: {exc}")
        messagebox.showerror("加载失败", str(exc))

    def _apply_rows(self, rows: list[DashboardRow], source: str, elapsed: float | None = None) -> None:
        self.rows = rows
        self.data_source = source or "-"
        self.last_loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_refresh_seconds = elapsed
        self.date_var.set(datetime.now().strftime("(%Y-%m-%d)"))
        self._refresh_metrics()
        if self._widget_alive("match_list"):
            self._refresh_matches()
        if self._widget_alive("risk_chart"):
            self._draw_risk_chart()
        if self._widget_alive("conf_chart"):
            self._draw_confidence_chart()
        if elapsed is not None:
            self._log_event("OK", f"\u5206\u6790\u5b8c\u6210: {len(rows)} \u573a | \u6570\u636e\u6e90 {source or '-'} | \u8017\u65f6 {elapsed:.2f}s")
        else:
            self._log_event("OK", f"\u5206\u6790\u5b8c\u6210: {len(rows)} \u573a | \u6570\u636e\u6e90 {source or '-'}")
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
        )[:3]

        if not ranked:
            tk.Label(self.match_list, text="暂无通过校验的赛事数据", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 11)).pack(anchor=tk.W, pady=20)
            return

        for row in ranked:
            self._match_row(row)

    def _match_row(self, row: DashboardRow) -> None:
        match = row.match
        pred = row.prediction
        frame = tk.Frame(self.match_list, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, pady=3)
        frame.configure(cursor="hand2")

        left = tk.Frame(frame, bg=PANEL_2)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=18, pady=8)
        tk.Label(left, text=match.league, bg=PANEL_2, fg="#6d8dff", font=("Microsoft YaHei UI", 9, "bold")).pack(anchor=tk.W)
        tk.Label(left, text=f"{match.home_team} vs {match.away_team}", bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W, pady=(4, 2))
        tk.Label(left, text=f"开赛时间：{match.match_date} {match.match_time}", bg=PANEL_2, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)

        for title, value, color, width in [
            ("风险等级", _risk_label(pred.get("risk_level")), _risk_color(pred.get("risk_level")), 112),
            ("置信度", _pct(pred.get("confidence")), TEXT, 88),
            ("推荐策略", _strategy_text(pred), TEXT, 168),
        ]:
            block = tk.Frame(frame, bg=PANEL_2, width=width)
            block.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6), pady=8)
            block.pack_propagate(False)
            tk.Label(block, text=title, bg=PANEL_2, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
            tk.Label(block, text=value, bg=PANEL_2, fg=color, font=("Microsoft YaHei UI", 12, "bold"), wraplength=width - 8, justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 0))

        self._bind_detail_open(frame, row)

    def _bind_detail_open(self, widget: tk.Widget, row: DashboardRow) -> None:
        widget.bind("<Button-1>", lambda _event: self.open_match_detail(row))
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_detail_open(child, row)

    def open_match_detail(self, row: DashboardRow) -> None:
        title = f"{row.match.home_team} vs {row.match.away_team}"
        shell = self._page_shell(title, f"{row.match.league}  |  {row.match.match_date} {row.match.match_time}")

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        tk.Button(
            top,
            text="\u8fd4\u56de\u6982\u89c8",
            command=self._build_main,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=6,
        ).pack(side=tk.LEFT)
        tk.Button(
            top,
            text="\u4fdd\u5b58\u62a5\u544a",
            command=lambda: self.save_match_report(row),
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=16,
            pady=6,
        ).pack(side=tk.RIGHT)

        summary = tk.Frame(shell, bg=BG)
        summary.pack(fill=tk.X, pady=(0, 16))
        pred = row.prediction
        for label, value, color in [
            ("\u98ce\u9669\u7b49\u7ea7", _risk_label(pred.get("risk_level")), _risk_color(pred.get("risk_level"))),
            ("\u63a8\u8350\u7b56\u7565", _strategy_text(pred), TEXT),
            ("\u7f6e\u4fe1\u5ea6", _pct1(pred.get("confidence")), "#7aa2ff"),
            ("\u9884\u8ba1\u8fdb\u7403", _num(pred.get("expected_goals")), TEXT),
        ]:
            self._detail_metric(summary, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        tk.Label(left, text="\u6982\u7387\u4e0e\u98ce\u9669", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        self._draw_probability_panel(left, row)

        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="AI \u5206\u6790\u62a5\u544a", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        text = tk.Text(
            right,
            wrap=tk.WORD,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            padx=16,
            pady=8,
        )
        text.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 14))
        text.insert("1.0", _analysis_report(row))
        text.configure(state=tk.DISABLED)

    def save_match_report(self, row: DashboardRow) -> Path:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        name = f"ai_match_report_{now.strftime('%Y%m%d_%H%M%S')}_{_slug(row.match.home_team)}_vs_{_slug(row.match.away_team)}.md"
        path = REPORT_DIR / name
        path.write_text(_markdown_report(row, generated_at=now), encoding="utf-8")
        self.status_var.set(f"\u62a5\u544a\u5df2\u4fdd\u5b58: {path.name}")
        messagebox.showinfo("\u4fdd\u5b58\u62a5\u544a", f"\u5df2\u751f\u6210\u62a5\u544a:\n{path}")
        return path

    def open_history_reports(self) -> None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(REPORT_DIR.glob("ai_match_report_*.md"), key=lambda path: path.stat().st_mtime, reverse=True)

        shell = self._page_shell("\u5386\u53f2\u62a5\u544a", f"\u62a5\u544a\u76ee\u5f55: {REPORT_DIR}")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(
            left,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            width=38,
            font=("Microsoft YaHei UI", 10),
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview = tk.Text(
            right,
            wrap=tk.WORD,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            padx=16,
            pady=12,
        )
        preview.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        def show_file(index: int) -> None:
            if index < 0 or index >= len(files):
                return
            path = files[index]
            try:
                content = path.read_text(encoding="utf-8")
            except Exception as exc:
                content = f"\u8bfb\u53d6\u5931\u8d25: {exc}"
            preview.configure(state=tk.NORMAL)
            preview.delete("1.0", tk.END)
            preview.insert("1.0", content)
            preview.configure(state=tk.DISABLED)

        for path in files:
            stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            listbox.insert(tk.END, f"{stamp}  {path.name}")

        if files:
            listbox.selection_set(0)
            show_file(0)
        else:
            preview.insert("1.0", "\u6682\u65e0\u5355\u573a\u5206\u6790\u62a5\u544a\u3002")
            preview.configure(state=tk.DISABLED)

        listbox.bind("<<ListboxSelect>>", lambda _event: show_file(listbox.curselection()[0] if listbox.curselection() else -1))

    def open_data_center(self) -> None:
        shell = self._page_shell(
            "\u6570\u636e\u4e2d\u5fc3",
            "\u5f53\u524d\u6570\u636e\u6e90\u3001\u7f13\u5b58\u3001\u6a21\u578b\u72b6\u6001\u548c\u62a5\u544a\u4ea7\u7269",
        )

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        risk_counts = self._risk_counts()
        report_count = len(list(REPORT_DIR.glob("ai_match_report_*.md"))) if REPORT_DIR.exists() else 0
        metrics = [
            ("\u6570\u636e\u6e90", self.data_source, "#7aa2ff"),
            ("\u4eca\u65e5\u8d5b\u4e8b", str(len(self.rows)), TEXT),
            ("\u9ad8\u98ce\u9669", str(risk_counts.get("high", 0)), RED),
            ("\u5386\u53f2\u62a5\u544a", str(report_count), TEXT),
        ]
        for label, value, color in metrics:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u8fd0\u884c\u72b6\u6001", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        status_rows = [
            ("\u9879\u76ee\u76ee\u5f55", str(PROJECT_ROOT)),
            ("\u6700\u8fd1\u52a0\u8f7d", self.last_loaded_at),
            ("\u5f53\u524d\u6a21\u578b", self._dominant_model_name()),
            ("\u5e73\u5747\u7f6e\u4fe1\u5ea6", self._average_confidence()),
            ("\u62a5\u544a\u76ee\u5f55", str(REPORT_DIR)),
        ]
        for label, value in status_rows:
            self._kv_row(left, label, value)

        tk.Label(right, text="\u6570\u636e\u6587\u4ef6", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        data_rows = self._data_inventory_rows()
        for label, value in data_rows:
            self._kv_row(right, label, value)

        tk.Button(
            shell,
            text="\u5237\u65b0\u6570\u636e",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(anchor=tk.E, pady=(14, 0))

    def _dominant_model_name(self) -> str:
        for row in self.rows:
            model = str(row.prediction.get("model") or "").strip()
            if model:
                return model
        return "-"

    def _average_confidence(self) -> str:
        values = [float(row.prediction.get("confidence", 0) or 0) for row in self.rows]
        if not values:
            return "-"
        return f"{sum(values) / len(values):.1%}"

    def _data_inventory_rows(self) -> list[tuple[str, str]]:
        paths = [
            ("cache", PROJECT_ROOT / "data" / "cache"),
            ("state", PROJECT_ROOT / "data" / "state"),
            ("models", PROJECT_ROOT / "data" / "models"),
            ("c1_state", PROJECT_ROOT / "data" / "c1_state"),
            ("reports", REPORT_DIR),
        ]
        rows: list[tuple[str, str]] = []
        for label, path in paths:
            count, size = _dir_stats(path)
            rows.append((label, f"{count} files / {_bytes_text(size)} / updated {_mtime_text(path)}"))

        key_files = [
            ("500_config", PROJECT_ROOT / "config" / "500_config.json"),
            ("settlements", PROJECT_ROOT / "data" / "state" / "settlements.json"),
            ("prediction_snapshots", PROJECT_ROOT / "data" / "state" / "prediction_snapshots.json"),
            ("xgb_model", PROJECT_ROOT / "data" / "models" / "xgb_v0_match_outcome.json"),
        ]
        for label, path in key_files:
            rows.append((label, f"{'OK' if path.exists() else 'missing'} / updated {_mtime_text(path)}"))
        return rows

    def _kv_row(self, parent: tk.Widget, label: str, value: str) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X, padx=18, pady=7)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=18, anchor=tk.W, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        tk.Label(row, text=value, bg=PANEL, fg=TEXT, anchor=tk.W, justify=tk.LEFT, wraplength=320, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _log_event(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.event_log.insert(0, (stamp, level, message))
        self.event_log = self.event_log[:200]

    def open_monitor_center(self) -> None:
        shell = self._page_shell(
            "\u76d1\u63a7\u4e2d\u5fc3",
            "\u8fd0\u884c\u65e5\u5fd7\u3001\u5206\u6790\u8017\u65f6\u3001\u6570\u636e\u6e90\u548c\u98ce\u9669\u72b6\u6001",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X)
        tk.Button(
            header,
            text="\u5237\u65b0\u8d5b\u4e8b",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT)

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        risk_counts = self._risk_counts()
        metrics = [
            ("\u6700\u8fd1\u8017\u65f6", f"{self.last_refresh_seconds:.2f}s" if self.last_refresh_seconds is not None else "-"),
            ("\u6570\u636e\u6e90", self.data_source, "#7aa2ff"),
            ("\u8d5b\u4e8b\u6570", str(len(self.rows)), TEXT),
            ("\u9884\u8b66", str(risk_counts.get("high", 0)), RED),
        ]
        for label, value, color in metrics:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="Agent \u72b6\u6001", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        agent_rows = [
            ("DataHunter", "\u5df2\u63a5\u5165" if self.rows else "\u7b49\u5f85\u6570\u636e"),
            ("MarketEntropy", f"\u9ad8\u98ce\u9669 {risk_counts.get('high', 0)} / \u4e2d\u98ce\u9669 {risk_counts.get('medium', 0)}"),
            ("Simulation", f"\u5df2\u63a8\u6f14 {len(self.rows)} \u573a"),
            ("RiskGuardian", "\u6b63\u5e38" if risk_counts.get("high", 0) == 0 else "\u89e6\u53d1\u9884\u8b66"),
            ("StrategyComposer", f"\u62a5\u544a {len(list(REPORT_DIR.glob('ai_match_report_*.md'))) if REPORT_DIR.exists() else 0} \u4efd"),
        ]
        for label, value in agent_rows:
            self._kv_row(left, label, value)

        tk.Label(right, text="\u8fd0\u884c\u65e5\u5fd7", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        logbox = tk.Listbox(
            right,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            font=("Consolas", 10),
            activestyle="none",
        )
        logbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        if not self.event_log:
            logbox.insert(tk.END, "no events")
        else:
            for stamp, level, message in self.event_log:
                logbox.insert(tk.END, f"{stamp} [{level}] {message}")

    def open_review_center(self) -> None:
        settlements = list(reversed(get_recent_settlements(limit=200)))
        summary = self._settlement_summary(settlements)

        shell = self._page_shell(
            "\u590d\u76d8\u4e2d\u5fc3",
            "\u56de\u6536\u5b8c\u573a\u8d5b\u679c\uff0c\u68c0\u67e5\u547d\u4e2d\u7387\u3001\u73a9\u6cd5\u504f\u5dee\u548c\u9ad8\u7f6e\u4fe1\u5931\u8bef",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X)
        tk.Button(
            header,
            text="\u56de\u6536\u8d5b\u679c",
            command=self.run_result_recovery,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT)

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u5df2\u7ed3\u7b97", str(summary["total"]), TEXT),
            ("1X2 \u547d\u4e2d", summary["one_x_two"], GREEN),
            ("\u8ba9\u7403\u547d\u4e2d", summary["handicap"], "#7aa2ff"),
            ("\u5927\u5c0f\u7403\u547d\u4e2d", summary["ou"], YELLOW),
        ]:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u6700\u8fd1\u590d\u76d8", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        listbox = tk.Listbox(
            left,
            bg=PANEL,
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        for item in settlements[:80]:
            listbox.insert(tk.END, self._settlement_line(item))
        if not settlements:
            listbox.insert(tk.END, "\u6682\u65e0\u590d\u76d8\u7ed3\u7b97\u8bb0\u5f55")

        tk.Label(right, text="\u504f\u5dee\u91cd\u70b9", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        misses = self._high_confidence_misses(settlements)
        if misses:
            for item in misses[:10]:
                self._strategy_row(
                    right,
                    f"{item.get('home_team', '-')} vs {item.get('away_team', '-')}",
                    f"\u7f6e\u4fe1\u5ea6 {_pct1(item.get('prediction_confidence'))} | \u9884\u6d4b {item.get('predicted', '-')} | \u5b9e\u9645 {item.get('result', '-')} | {item.get('home_goals', '-')}-{item.get('away_goals', '-')}",
                )
        else:
            self._strategy_row(right, "\u9ad8\u7f6e\u4fe1\u5931\u8bef", "\u6682\u672a\u53d1\u73b0\u7f6e\u4fe1\u5ea6 >=60% \u4e14 1X2 \u5931\u8bef\u7684\u8bb0\u5f55")

    def run_result_recovery(self) -> None:
        self.status_var.set("\u6b63\u5728\u56de\u6536\u8d5b\u679c...")
        self._log_event("INFO", "\u5f00\u59cb\u56de\u6536\u8d5b\u679c")
        prediction_cache = {row.match.match_id: row.prediction for row in self.rows}

        def worker() -> None:
            started = time.perf_counter()
            try:
                result = auto_settle_finished_matches(prediction_cache=prediction_cache, lookback_days=2)
            except Exception as exc:
                self.root.after(0, lambda: self._finish_result_recovery_error(exc))
                return
            elapsed = time.perf_counter() - started
            self.root.after(0, lambda: self._finish_result_recovery(result, elapsed))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_result_recovery(self, result: dict, elapsed: float) -> None:
        new_settled = int(result.get("new_settled", 0) or 0)
        fetched = int(result.get("fetched_finished", 0) or 0)
        source = str(result.get("source", "-"))
        message = f"\u8d5b\u679c\u56de\u6536\u5b8c\u6210: \u5b8c\u573a {fetched} | \u65b0\u7ed3\u7b97 {new_settled} | \u6570\u636e\u6e90 {source} | \u8017\u65f6 {elapsed:.2f}s"
        self.status_var.set(message)
        self._log_event("OK", message)
        self.summary_vars["hit_rate"].set(self._historical_hit_rate())
        detail = "\n".join(str(item) for item in result.get("messages", []) if item) or message
        messagebox.showinfo("\u8d5b\u679c\u56de\u6536", detail)

    def _finish_result_recovery_error(self, exc: Exception) -> None:
        self.status_var.set(f"\u8d5b\u679c\u56de\u6536\u5931\u8d25: {exc}")
        self._log_event("ERROR", f"\u8d5b\u679c\u56de\u6536\u5931\u8d25: {exc}")
        messagebox.showerror("\u8d5b\u679c\u56de\u6536\u5931\u8d25", str(exc))

    def _settlement_summary(self, settlements: list[dict]) -> dict[str, str | int]:
        return {
            "total": len(settlements),
            "one_x_two": self._hit_rate_text(settlements, "is_correct"),
            "handicap": self._hit_rate_text(settlements, "handicap_is_correct"),
            "ou": self._hit_rate_text(settlements, "ou_is_correct"),
        }

    def _hit_rate_text(self, settlements: list[dict], key: str) -> str:
        values = [bool(item.get(key)) for item in settlements if isinstance(item, dict) and item.get(key) is not None]
        if not values:
            return "-"
        return f"{sum(1 for value in values if value) / len(values):.1%}"

    def _settlement_line(self, item: dict) -> str:
        hit = "\u547d\u4e2d" if item.get("is_correct") else "\u5931\u8bef"
        return (
            f"{item.get('match_date', '-')} {item.get('league', '-')} | "
            f"{item.get('home_team', '-')} {item.get('home_goals', '-')}-{item.get('away_goals', '-')} {item.get('away_team', '-')} | "
            f"\u9884\u6d4b {item.get('predicted', '-')} | {hit} | {_pct1(item.get('prediction_confidence'))}"
        )

    def _high_confidence_misses(self, settlements: list[dict]) -> list[dict]:
        misses = [
            item
            for item in settlements
            if isinstance(item, dict)
            and item.get("is_correct") is False
            and float(item.get("prediction_confidence", 0) or 0) >= 0.6
        ]
        return sorted(misses, key=lambda item: float(item.get("prediction_confidence", 0) or 0), reverse=True)

    def open_strategy_library(self) -> None:
        shell = self._page_shell(
            "\u7b56\u7565\u5e93",
            "\u63a8\u8350\u7b56\u7565\u3001\u98ce\u9669\u89c4\u5219\u3001\u7f6e\u4fe1\u5ea6\u5206\u5c42\u548c\u73a9\u6cd5\u7ef4\u5ea6",
        )

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        avg_conf = self._average_confidence()
        high_count = self._risk_counts().get("high", 0)
        metrics = [
            ("\u7b56\u7565\u6570", "6", TEXT),
            ("\u73a9\u6cd5\u7ef4\u5ea6", "5", "#7aa2ff"),
            ("\u5e73\u5747\u7f6e\u4fe1", avg_conf, TEXT),
            ("\u98ce\u9669\u89e6\u53d1", str(high_count), RED if high_count else GREEN),
        ]
        for label, value, color in metrics:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u6838\u5fc3\u7b56\u7565", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        strategy_rows = [
            ("\u4e3b\u80dc/\u5e73/\u5ba2\u80dc", "\u57fa\u4e8e\u5e02\u573a\u3001ELO\u3001Poisson\u3001XGB \u878d\u5408\u6982\u7387\u9009\u62e9\u4e3b\u7ed3\u8bba"),
            ("\u5927\u5c0f\u7403", "\u4f7f\u7528\u8fdb\u7403\u671f\u671b\u548c Poisson \u5206\u5e03\u63a8\u5bfc 2.5 \u7403\u65b9\u5411"),
            ("\u8ba9\u7403", "\u6839\u636e\u76d8\u53e3\u7ebf\u3001\u80dc\u5e73\u8d1f\u6982\u7387\u548c\u4e13\u5bb6\u6a21\u578b\u8f93\u51fa\u751f\u6210"),
            ("\u6bd4\u5206", "\u4ece Poisson \u6bd4\u5206\u5206\u5e03\u4e2d\u9009\u53d6\u6982\u7387\u66f4\u9ad8\u7684\u5019\u9009"),
            ("\u534a\u5168\u573a", "\u4f9d\u636e\u534a\u573a/\u5168\u573a\u72b6\u6001\u6982\u7387\u63a8\u5bfc\u8282\u594f\u8d70\u5411"),
            ("\u4fdd\u5b88\u9632\u5b88", "\u9ad8\u98ce\u9669\u6216\u51b7\u95e8\u6307\u6570\u504f\u9ad8\u65f6\u964d\u4f4e\u63a8\u8350\u6743\u91cd"),
        ]
        for label, value in strategy_rows:
            self._strategy_row(left, label, value)

        tk.Label(right, text="\u98ce\u63a7\u89c4\u5219", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        rule_rows = [
            ("\u4f4e\u98ce\u9669", "\u7f6e\u4fe1\u5ea6\u53ef\u7528\uff0c\u51b7\u95e8\u6307\u6570\u4f4e\uff0c\u5e02\u573a\u548c\u6a21\u578b\u65b9\u5411\u57fa\u672c\u4e00\u81f4"),
            ("\u4e2d\u98ce\u9669", "\u6982\u7387\u5dee\u8ddd\u4e0d\u5927\u6216\u7a33\u5b9a\u6307\u6570\u4e0d\u8db3\uff0c\u9700\u8981\u8d5b\u524d\u590d\u6838"),
            ("\u9ad8\u98ce\u9669", "\u51b7\u95e8\u6307\u6570\u504f\u9ad8\u6216\u76d8\u53e3/\u70ed\u5ea6\u5b58\u5728\u5f02\u5e38\uff0c\u4ee5\u9632\u5b88\u6216\u89c2\u671b\u4e3a\u4e3b"),
            ("\u7f6e\u4fe1\u5ea6 <50%", "\u4e0d\u5efa\u8bae\u4f5c\u4e3a\u4e3b\u7b56\u7565\uff0c\u53ea\u7528\u4e8e\u89c2\u5bdf"),
            ("\u7f6e\u4fe1\u5ea6 50%-60%", "\u4f4e\u6743\u91cd\uff0c\u9700\u914d\u5408\u98ce\u9669\u7b49\u7ea7\u5224\u65ad"),
            ("\u7f6e\u4fe1\u5ea6 60%-70%", "\u5e38\u89c4\u53ef\u7528\u533a\u95f4\uff0c\u4ecd\u9700\u68c0\u67e5\u4e34\u573a\u4fe1\u606f"),
            ("\u7f6e\u4fe1\u5ea6 >70%", "\u4f18\u5148\u7ea7\u8f83\u9ad8\uff0c\u4f46\u82e5\u98ce\u9669\u7b49\u7ea7\u9ad8\u4ecd\u9700\u964d\u6743"),
        ]
        for label, value in rule_rows:
            self._strategy_row(right, label, value)

    def _strategy_row(self, parent: tk.Widget, title: str, body: str) -> None:
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, padx=18, pady=6)
        tk.Label(frame, text=title, bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, padx=14, pady=(10, 3))
        tk.Label(
            frame,
            text=body,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify=tk.LEFT,
            wraplength=350,
        ).pack(anchor=tk.W, padx=14, pady=(0, 10))

    def open_system_settings(self) -> None:
        shell = self._page_shell(
            "\u7cfb\u7edf\u8bbe\u7f6e",
            "\u672c\u5730\u8fd0\u884c\u53c2\u6570\u3001\u6570\u636e\u76ee\u5f55\u3001\u62a5\u544a\u76ee\u5f55\u548c\u98ce\u63a7\u9608\u503c\u8bf4\u660e",
        )

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u8fd0\u884c\u53c2\u6570", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 12))
        control = tk.Frame(left, bg=PANEL)
        control.pack(fill=tk.X, padx=18, pady=(0, 12))
        tk.Checkbutton(
            control,
            text="\u542f\u7528\u81ea\u52a8\u5237\u65b0",
            variable=self.auto_refresh_enabled,
            command=self._on_auto_refresh_changed,
            bg=PANEL,
            fg=TEXT,
            selectcolor=PANEL_2,
            activebackground=PANEL,
            activeforeground=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor=tk.W)

        interval = tk.Frame(left, bg=PANEL)
        interval.pack(fill=tk.X, padx=18, pady=(0, 16))
        tk.Label(interval, text="\u5237\u65b0\u95f4\u9694\uff08\u5206\u949f\uff09", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        tk.Spinbox(
            interval,
            from_=3,
            to=120,
            width=6,
            textvariable=self.auto_refresh_interval_min,
            command=self._on_auto_refresh_changed,
            bg=PANEL_2,
            fg=TEXT,
            buttonbackground=PANEL_2,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
        ).pack(side=tk.RIGHT)

        for label, value in [
            ("\u5f53\u524d\u6570\u636e\u6e90", self.data_source),
            ("\u6700\u8fd1\u52a0\u8f7d", self.last_loaded_at),
            ("\u6700\u8fd1\u8017\u65f6", f"{self.last_refresh_seconds:.2f}s" if self.last_refresh_seconds is not None else "-"),
            ("\u9879\u76ee\u76ee\u5f55", str(PROJECT_ROOT)),
            ("\u6570\u636e\u76ee\u5f55", str(PROJECT_ROOT / "data")),
            ("\u62a5\u544a\u76ee\u5f55", str(REPORT_DIR)),
            ("\u8bbe\u7f6e\u6587\u4ef6", str(SETTINGS_PATH)),
        ]:
            self._kv_row(left, label, value)

        tk.Label(right, text="\u98ce\u63a7\u9608\u503c\u8bf4\u660e", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 12))
        settings_rows = [
            ("\u9ad8\u98ce\u9669", "\u51b7\u95e8\u6307\u6570\u9ad8\u6216\u5e02\u573a/\u6a21\u578b\u5206\u6b67\u660e\u663e\u65f6\u89e6\u53d1"),
            ("\u4e2d\u98ce\u9669", "\u6982\u7387\u8fb9\u754c\u4e0d\u6e05\u6216\u7a33\u5b9a\u6027\u4e0d\u8db3\u65f6\u89e6\u53d1"),
            ("\u4f4e\u98ce\u9669", "\u6a21\u578b\u3001\u5e02\u573a\u548c\u7a33\u5b9a\u6307\u6807\u65b9\u5411\u76f8\u5bf9\u4e00\u81f4"),
            ("\u7f6e\u4fe1\u5ea6\u5206\u5c42", "<50% \u89c2\u5bdf\uff0c50%-60% \u4f4e\u6743\u91cd\uff0c60%-70% \u5e38\u89c4\uff0c>70% \u9ad8\u4f18\u5148\u7ea7"),
            ("\u81ea\u52a8\u5237\u65b0", "\u4ec5\u5728\u5f53\u524d APP \u8fd0\u884c\u671f\u95f4\u751f\u6548\uff0c\u4e0d\u5199\u5165\u914d\u7f6e\u6587\u4ef6"),
            ("\u7248\u672c\u7ba1\u7406", "Git \u5df2\u542f\u7528\uff0c\u6bcf\u4e2a\u529f\u80fd\u70b9\u72ec\u7acb\u63d0\u4ea4"),
        ]
        for label, value in settings_rows:
            self._strategy_row(right, label, value)

        tk.Button(
            shell,
            text="\u7acb\u5373\u5237\u65b0",
            command=self.refresh,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(anchor=tk.E, pady=(14, 0))

    def _detail_metric(self, parent: tk.Widget, label: str, value: str, color: str) -> None:
        frame = self._card(parent, PANEL)
        frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        tk.Label(frame, text=label, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=14, pady=(12, 3))
        tk.Label(frame, text=value, bg=PANEL, fg=color, font=("Microsoft YaHei UI", 14, "bold"), wraplength=150, justify=tk.LEFT).pack(anchor=tk.W, padx=14, pady=(0, 12))

    def _draw_probability_panel(self, parent: tk.Widget, row: DashboardRow) -> None:
        pred = row.prediction
        probs = pred.get("probabilities", {}) if isinstance(pred.get("probabilities"), dict) else {}
        indices = pred.get("indices", {}) if isinstance(pred.get("indices"), dict) else {}
        items = [
            ("\u4e3b\u80dc", probs.get("home", 0), "#7aa2ff"),
            ("\u5e73\u5c40", probs.get("draw", 0), YELLOW),
            ("\u5ba2\u80dc", probs.get("away", 0), GREEN),
            ("\u51b7\u95e8", indices.get("upset_index", 0), RED),
            ("\u7a33\u5b9a", indices.get("stability_index", 0), GREEN),
            ("\u4fe1\u5fc3", indices.get("confidence_index", 0), "#7aa2ff"),
        ]
        for label, value, color in items:
            self._bar_row(parent, label, float(value or 0), color)

        plays = tk.Frame(parent, bg=PANEL)
        plays.pack(fill=tk.X, padx=18, pady=(18, 8))
        for label, value in [
            ("\u5927\u5c0f\u7403", f"{pred.get('ou_recommendation', '-')}  {_pct1(pred.get('ou_confidence'))}"),
            ("\u8ba9\u7403", f"{pred.get('handicap_recommendation', '-')}  {_pct1(pred.get('handicap_confidence'))}"),
            ("\u53ef\u80fd\u6bd4\u5206", f"{pred.get('score_recommendation', '-')}  {_pct1(pred.get('score_confidence'))}"),
            ("\u534a\u5168\u573a", f"{pred.get('htft_recommendation', '-')}  {_pct1(pred.get('htft_confidence'))}"),
        ]:
            line = tk.Frame(plays, bg=PANEL)
            line.pack(fill=tk.X, pady=5)
            tk.Label(line, text=label, bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
            tk.Label(line, text=value, bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.RIGHT)

    def _bar_row(self, parent: tk.Widget, label: str, value: float, color: str) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X, padx=18, pady=7)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=8, anchor=tk.W, font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        canvas = tk.Canvas(row, height=12, bg="#172233", bd=0, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 10))
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 180)
        canvas.create_rectangle(0, 0, width, 12, fill="#172233", outline="")
        canvas.create_rectangle(0, 0, max(2, width * max(0.0, min(value, 1.0))), 12, fill=color, outline="")
        tk.Label(row, text=_pct1(value), bg=PANEL, fg=TEXT, width=7, anchor=tk.E, font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.RIGHT)

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
