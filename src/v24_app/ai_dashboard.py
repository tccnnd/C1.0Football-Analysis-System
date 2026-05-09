from __future__ import annotations

import math
import json
import re
import threading
import tkinter as tk
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from .core import (
    AppMatch,
    auto_settle_finished_matches,
    fetch_matches_v24,
    get_high_accuracy_strategy_status,
    get_recent_settlements,
    mark_strategy_allowlist_snapshots,
    persist_prediction_snapshot,
    predict_match,
)
from .ui_modules import (
    build_high_accuracy_strategy_dashboard,
    build_strategy_allowlist_settlement_summary,
    build_strategy_allowlist_tuning_recommendation,
    build_strategy_allowlist_filename,
    build_strategy_allowlist_report_lines,
    select_strategy_allowlist_rows,
)


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


def _admission_payload(prediction: dict) -> dict:
    payload = prediction.get("strategy_admission", {})
    return payload if isinstance(payload, dict) else {}


def _admission_text(prediction: dict) -> str:
    admission = _admission_payload(prediction)
    return str(admission.get("label") or "-")


def _admission_color(prediction: dict) -> str:
    decision = str(_admission_payload(prediction).get("decision") or "")
    if decision == "allow":
        return GREEN
    if decision == "block":
        return RED
    return YELLOW


def _competition_mode_label(prediction: dict) -> str:
    if prediction.get("competition_mode") == "world_cup":
        return "\u4e16\u754c\u676f\u6a21\u5f0f"
    return "\u5e38\u89c4\u6a21\u5f0f"


def _rating_pool_label(prediction: dict) -> str:
    if prediction.get("rating_pool") == "national_team":
        return "\u56fd\u5bb6\u961f ELO"
    return "\u4ff1\u4e50\u90e8 ELO"


def _world_cup_notice(prediction: dict) -> str:
    payload = prediction.get("world_cup_mode")
    if not isinstance(payload, dict) or not payload.get("enabled"):
        return ""
    phase_map = {"group": "\u5c0f\u7ec4\u8d5b", "knockout": "\u6dd8\u6c70\u8d5b", "unknown": "\u5f85\u5224\u5b9a"}
    phase = phase_map.get(str(payload.get("phase") or "unknown"), "\u5f85\u5224\u5b9a")
    group_context = payload.get("group_context", {}) if isinstance(payload.get("group_context"), dict) else {}
    pressure_text = _world_cup_group_context_text(group_context)
    cap = _pct1(payload.get("confidence_cap"))
    adjusted = "\u5df2\u964d\u6743" if payload.get("confidence_adjusted") else "\u672a\u89e6\u53d1\u964d\u6743"
    return (
        "\n\n\u4e16\u754c\u676f\u6a21\u5f0f\n"
        f"- \u8d5b\u5236\u9636\u6bb5\uff1a{phase}\n"
        f"- \u7f6e\u4fe1\u4e0a\u9650\uff1a{cap}\uff08{adjusted}\uff09\n"
        "- \u8bc4\u5206\u6c60\uff1a\u56fd\u5bb6\u961f ELO\uff0c\u4e0d\u4e0e\u4ff1\u4e50\u90e8\u8bc4\u5206\u6df7\u7528\u3002\n"
        f"{pressure_text}"
        "- \u56fd\u5bb6\u961f\u6837\u672c\u7a00\u758f\uff0c\u9635\u5bb9\u3001\u8d5b\u7a0b\u5bc6\u5ea6\u548c\u79ef\u5206\u5f62\u52bf\u9700\u8981\u4f18\u5148\u590d\u6838\u3002\n"
        "- \u5c0f\u7ec4\u8d5b\u8981\u5173\u6ce8\u51c0\u80dc\u7403\u548c\u8f6e\u6362\uff0c\u6dd8\u6c70\u8d5b\u8981\u5173\u6ce8\u52a0\u65f6/\u70b9\u7403\u548c\u4fdd\u5b88\u7b56\u7565\u3002"
    )


def _world_cup_group_context_text(context: dict) -> str:
    if not context:
        return "- \u5c0f\u7ec4\u4e0a\u4e0b\u6587\uff1a\u6682\u65e0\u79ef\u5206\u6570\u636e\uff0c\u9700\u8d5b\u524d\u8865\u5145\u3002\n"
    group = str(context.get("group") or "-")
    group_round = int(context.get("round") or 0)
    tags = context.get("pressure_tags", [])
    tag_labels = {
        "final_group_round": "\u5c0f\u7ec4\u672b\u8f6e",
        "points_tight": "\u79ef\u5206\u63a5\u8fd1",
        "asymmetric_motivation": "\u6218\u610f\u4e0d\u5bf9\u79f0",
        "goal_difference_pressure": "\u51c0\u80dc\u7403\u538b\u529b",
    }
    readable_tags = [tag_labels.get(str(tag), str(tag)) for tag in tags if tag]
    tag_text = "\u3001".join(readable_tags) if readable_tags else "\u5f85\u89c2\u5bdf"
    return (
        f"- \u5c0f\u7ec4\u4e0a\u4e0b\u6587\uff1a{group} \u7b2c{group_round or '-'}\u8f6e | "
        f"\u79ef\u5206 {context.get('home_points', '-')}:{context.get('away_points', '-')} | "
        f"\u51c0\u80dc\u7403 {context.get('home_goal_diff', '-')}:{context.get('away_goal_diff', '-')} | "
        f"\u538b\u529b\u6807\u7b7e {tag_text}\n"
    )


def _analysis_report(row: DashboardRow) -> str:
    match = row.match
    pred = row.prediction
    indices = pred.get("indices", {}) if isinstance(pred.get("indices"), dict) else {}
    probs = pred.get("probabilities", {}) if isinstance(pred.get("probabilities"), dict) else {}
    market_probs = pred.get("market_probabilities", {}) if isinstance(pred.get("market_probabilities"), dict) else {}
    risk = _risk_key(pred.get("risk_level"))
    admission = _admission_payload(pred)
    admission_reasons = admission.get("reasons", []) if isinstance(admission.get("reasons"), list) else []
    admission_reason_text = ", ".join(str(item) for item in admission_reasons[:4]) if admission_reasons else "-"

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
        f"- \u7b56\u7565\u51c6\u5165\uff1a{_admission_text(pred)} | {admission_reason_text}\n"
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
        f"{_world_cup_notice(pred)}"
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
        f"| 策略准入 | {_md_cell(_admission_text(pred))} |\n"
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


def _load_prediction_snapshot_records() -> dict[str, dict]:
    path = PROJECT_ROOT / "data" / "state" / "prediction_snapshots.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    items = payload.get("items", {})
    return items if isinstance(items, dict) else {}


def _parse_match_datetime(match: dict) -> datetime | None:
    date_text = str(match.get("match_date") or "").strip()
    time_text = str(match.get("match_time") or "").strip()
    if not date_text:
        return None
    candidates = []
    if time_text:
        candidates.extend(
            [
                f"{date_text} {time_text}",
                f"{date_text} {time_text[:5]}",
            ]
        )
    candidates.append(date_text)
    for candidate in candidates:
        for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return None


def _snapshot_status(match: dict, now: datetime | None = None) -> str:
    kickoff = _parse_match_datetime(match)
    if kickoff is None:
        return "\u5f85\u590d\u76d8"
    current = now or datetime.now()
    hours_from_kickoff = (current - kickoff).total_seconds() / 3600
    if hours_from_kickoff < 0:
        return "\u5f85\u5f00\u8d5b"
    if hours_from_kickoff <= 3:
        return "\u8fdb\u884c\u4e2d"
    return "\u5f85\u56de\u6536"


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
        self.current_nav_index = 0
        self.show_all_matches = False
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
            "settlements": tk.StringVar(value="0"),
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
        self.show_home_overview()

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
            if index == 0:
                command = self.show_home_overview
            elif index == 1:
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

    def show_home_overview(self) -> None:
        self.current_nav_index = 0
        self._refresh_nav_highlight()
        content = self._page_shell(
            "\u9996\u9875\u6982\u89c8",
            "\u8d5b\u4e8b\u5206\u6790\u603b\u89c8\u3001\u98ce\u9669\u6458\u8981\u548c\u7cfb\u7edf\u72b6\u6001",
        )

        actions = tk.Frame(content, bg=BG)
        actions.pack(fill=tk.X, pady=(0, 18))
        tk.Button(
            actions,
            text="\u8fdb\u5165\u8d5b\u4e8b\u5206\u6790",
            command=lambda: self._select_nav(1, self._build_main),
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.LEFT)
        tk.Button(
            actions,
            text="\u5237\u65b0\u6570\u636e",
            command=self.refresh,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground=TEXT,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.LEFT, padx=(10, 0))

        cards = tk.Frame(content, bg=BG)
        cards.pack(fill=tk.X, pady=(0, 18))
        self._metric_card(cards, "\u4eca\u65e5\u8d5b\u4e8b", self.summary_vars["matches"], "\u573a", TEXT)
        self._metric_card(cards, "\u98ce\u9669\u9884\u8b66", self.summary_vars["alerts"], "\u6b21", RED)
        self._metric_card(cards, "\u5386\u53f2\u80dc\u7387", self.summary_vars["hit_rate"], "", "#7aa2ff")
        self._metric_card(cards, "\u5386\u53f2\u6837\u672c", self.summary_vars["settlements"], "\u573a", TEXT)

        body = tk.Frame(content, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u7cfb\u7edf\u72b6\u6001", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for label, value in [
            ("\u6570\u636e\u6e90", self.data_source),
            ("\u6700\u8fd1\u52a0\u8f7d", self.last_loaded_at),
            ("\u6700\u8fd1\u8017\u65f6", f"{self.last_refresh_seconds:.2f}s" if self.last_refresh_seconds is not None else "-"),
            ("\u5e73\u5747\u7f6e\u4fe1\u5ea6", self._average_confidence()),
            ("\u81ea\u52a8\u5237\u65b0", "\u5df2\u5f00\u542f" if self.auto_refresh_enabled.get() else "\u5df2\u5173\u95ed"),
        ]:
            self._kv_row(left, label, value)

        tk.Label(right, text="\u5feb\u6377\u5165\u53e3", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        shortcuts = [
            ("\u8d5b\u4e8b\u5206\u6790", "\u67e5\u770b\u91cd\u70b9\u8d5b\u4e8b\u3001\u98ce\u9669\u548c\u7f6e\u4fe1\u5ea6\u5206\u5e03", lambda: self._select_nav(1, self._build_main)),
            ("\u590d\u76d8\u4e2d\u5fc3", "\u56de\u6536\u8d5b\u679c\u5e76\u67e5\u770b\u547d\u4e2d\u7387\u4e0e\u9ad8\u7f6e\u4fe1\u5931\u8bef", self.open_review_center),
            ("\u8d5b\u524d\u5feb\u7167", "\u67e5\u770b\u5df2\u4fdd\u5b58\u7684\u8d5b\u524d\u9884\u6d4b\uff0c\u7b49\u5b8c\u573a\u540e\u8fdb\u884c\u590d\u76d8", self.open_snapshot_center),
            ("\u76d1\u63a7\u4e2d\u5fc3", "\u67e5\u770b Agent \u72b6\u6001\u3001\u8fd0\u884c\u65e5\u5fd7\u548c\u8017\u65f6", self.open_monitor_center),
            ("\u6570\u636e\u4e2d\u5fc3", "\u67e5\u770b\u6570\u636e\u6587\u4ef6\u3001\u6a21\u578b\u548c\u7f13\u5b58\u72b6\u6001", self.open_data_center),
        ]
        for title, body_text, command in shortcuts:
            self._shortcut_row(right, title, body_text, command)

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
        tk.Label(header, text="\u91cd\u70b9\u8d5b\u4e8b", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.LEFT)
        self.match_toggle_var = tk.StringVar(value="\u67e5\u770b\u5168\u90e8 \u203a")
        toggle = tk.Label(header, textvariable=self.match_toggle_var, bg=PANEL, fg="#7692ff", font=("Microsoft YaHei UI", 10, "bold"), cursor="hand2")
        toggle.pack(side=tk.RIGHT)
        toggle.bind("<Button-1>", lambda _event: self._toggle_match_list())

        list_wrap = tk.Frame(matches_card, bg=PANEL, height=260)
        list_wrap.pack(fill=tk.X, padx=18, pady=(0, 10))
        list_wrap.pack_propagate(False)
        self.match_canvas = tk.Canvas(list_wrap, bg=PANEL, bd=0, highlightthickness=0)
        self.match_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.match_scrollbar = tk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.match_canvas.yview)
        self.match_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.match_canvas.configure(yscrollcommand=self.match_scrollbar.set)
        self.match_list = tk.Frame(self.match_canvas, bg=PANEL)
        self.match_canvas_window = self.match_canvas.create_window((0, 0), window=self.match_list, anchor=tk.NW)
        self.match_list.bind("<Configure>", lambda _event: self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all")))
        self.match_canvas.bind("<Configure>", lambda event: self.match_canvas.itemconfigure(self.match_canvas_window, width=event.width))
        self._bind_match_scroll(self.match_canvas)

        charts = tk.Frame(content, bg=BG)
        charts.pack(fill=tk.BOTH, expand=True)
        self.risk_chart = self._chart_card(charts, "风险分布")
        self.conf_chart = self._chart_card(charts, "置信度分布")

        self._refresh_matches()
        self._draw_risk_chart()
        self._draw_confidence_chart()

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

    def _shortcut_row(self, parent: tk.Widget, title: str, body: str, command) -> None:
        frame = tk.Frame(parent, bg=PANEL_2, highlightbackground="#172638", highlightthickness=1)
        frame.pack(fill=tk.X, padx=18, pady=7)
        frame.configure(cursor="hand2")
        tk.Label(frame, text=title, bg=PANEL_2, fg=TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor=tk.W, padx=14, pady=(10, 3))
        tk.Label(
            frame,
            text=body,
            bg=PANEL_2,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            justify=tk.LEFT,
            wraplength=360,
        ).pack(anchor=tk.W, padx=14, pady=(0, 10))
        frame.bind("<Button-1>", lambda _event: command())
        for child in frame.winfo_children():
            child.configure(cursor="hand2")
            child.bind("<Button-1>", lambda _event: command())

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
            rows = []
            for match in fetched.matches:
                prediction = predict_match(match)
                persist_prediction_snapshot(match, prediction)
                rows.append(DashboardRow(match, prediction))
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
        self.summary_vars["settlements"].set(str(self._historical_settlement_count()))

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

    def _historical_settlement_count(self) -> int:
        try:
            return len(get_recent_settlements(limit=0))
        except Exception:
            return 0

    def _toggle_match_list(self) -> None:
        self.show_all_matches = not self.show_all_matches
        self._refresh_matches()

    def _bind_match_scroll(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_match_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_match_scroll(child)

    def _on_match_mousewheel(self, event) -> None:
        if self._widget_alive("match_canvas"):
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            if delta:
                self.match_canvas.yview_scroll(delta, "units")
            return "break"

    def _refresh_matches(self) -> None:
        for child in self.match_list.winfo_children():
            child.destroy()

        ranked = sorted(
            self.rows,
            key=lambda row: (
                {"high": 0, "medium": 1, "low": 2}[_risk_key(row.prediction.get("risk_level"))],
                -float(row.prediction.get("confidence", 0) or 0),
            ),
        )
        ranked = ranked if self.show_all_matches else ranked[:3]
        if hasattr(self, "match_toggle_var"):
            text = "\u6536\u8d77 \u2039" if self.show_all_matches else "\u67e5\u770b\u5168\u90e8 \u203a"
            self.match_toggle_var.set(text)

        if not ranked:
            tk.Label(self.match_list, text="暂无通过校验的赛事数据", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 11)).pack(anchor=tk.W, pady=20)
            if self._widget_alive("match_canvas"):
                self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all"))
                self.match_canvas.yview_moveto(0)
            return

        for row in ranked:
            self._match_row(row)
        if self._widget_alive("match_canvas"):
            self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all"))
            self.match_canvas.yview_moveto(0)

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
            ("策略准入", _admission_text(pred), _admission_color(pred), 96),
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
            ("策略准入", _admission_text(pred), _admission_color(pred)),
            ("\u63a8\u8350\u7b56\u7565", _strategy_text(pred), TEXT),
            ("\u7f6e\u4fe1\u5ea6", _pct1(pred.get("confidence")), "#7aa2ff"),
            ("\u8d5b\u4e8b\u6a21\u5f0f", _competition_mode_label(pred), YELLOW if pred.get("competition_mode") == "world_cup" else TEXT),
            ("\u8bc4\u5206\u6c60", _rating_pool_label(pred), YELLOW if pred.get("rating_pool") == "national_team" else TEXT),
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
        trend = self._settlement_trend_summary(settlements)
        allowlist_summary = build_strategy_allowlist_settlement_summary(settlements)
        allowlist_tuning = build_strategy_allowlist_tuning_recommendation(settlements)

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
        tk.Button(
            header,
            text="\u8d5b\u524d\u5feb\u7167",
            command=self.open_snapshot_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        tk.Button(
            header,
            text="\u51c6\u786e\u7387\u8bca\u65ad",
            command=self.open_accuracy_diagnostics,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u5df2\u7ed3\u7b97", str(summary["total"]), TEXT),
            ("1X2 \u547d\u4e2d", summary["one_x_two"], GREEN),
            ("\u8ba9\u7403\u547d\u4e2d", summary["handicap"], "#7aa2ff"),
            ("\u5927\u5c0f\u7403\u547d\u4e2d", summary["ou"], YELLOW),
        ]:
            self._detail_metric(top, label, value, color)

        trend_frame = tk.Frame(shell, bg=BG)
        trend_frame.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u4e3b\u8981\u504f\u5dee", trend["top_bias"], YELLOW if trend["top_bias"] != "-" else TEXT),
            ("\u6700\u4e0d\u7a33\u5b9a\u73a9\u6cd5", trend["weakest_play"], RED if trend["weakest_play"] != "-" else TEXT),
            ("\u9ad8\u7f6e\u4fe1\u5931\u8bef", str(trend["high_conf_misses"]), RED if trend["high_conf_misses"] else GREEN),
            ("\u8c03\u6743\u91cd\u70b9", trend["priority"], "#7aa2ff"),
        ]:
            self._detail_metric(trend_frame, label, str(value), color)

        allowlist_frame = tk.Frame(shell, bg=BG)
        allowlist_frame.pack(fill=tk.X, pady=(0, 16))
        allowlist_hit_rate = str(allowlist_summary.get("hit_rate_text") or "-")
        allowlist_known = int(allowlist_summary.get("known_count", 0) or 0)
        allowlist_hit_color = TEXT if not allowlist_known else GREEN if float(allowlist_summary.get("hit_rate", 0) or 0) >= 0.6 else YELLOW
        for label, value, color in [
            ("\u653e\u884c\u5df2\u7ed3\u7b97", str(allowlist_summary.get("settled_count", 0)), TEXT),
            ("\u653e\u884c 1X2", allowlist_hit_rate, allowlist_hit_color),
            ("\u653e\u884c\u9ad8\u51c6", str(allowlist_summary.get("high_strategy_summary") or "-"), "#7aa2ff"),
            ("\u653e\u884c\u504f\u5dee", str(allowlist_summary.get("top_failure") or "-"), RED if allowlist_summary.get("top_failure") != "-" else TEXT),
            ("\u8c03\u53c2\u5efa\u8bae", str(allowlist_tuning.get("label") or "-"), self._tone_color(str(allowlist_tuning.get("tone") or "neutral"))),
        ]:
            self._detail_metric(allowlist_frame, label, str(value), color)

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

        tk.Label(right, text="\u95ed\u73af\u590d\u76d8", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        detail = tk.Text(
            right,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=18,
        )
        detail.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))

        def show_settlement_detail(index: int) -> None:
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            if not settlements:
                detail.insert(tk.END, "\u6682\u65e0\u5df2\u56de\u6536\u8d5b\u679c\u3002\u7b49\u6bd4\u8d5b\u5b8c\u573a\u540e\uff0c\u70b9\u51fb\u201c\u56de\u6536\u8d5b\u679c\u201d\u751f\u6210\u590d\u76d8\u95ed\u73af\u3002")
            else:
                detail.insert(tk.END, self._settlement_review_text(settlements[index]))
            detail.configure(state=tk.DISABLED)

        if settlements:
            listbox.selection_set(0)
            show_settlement_detail(0)
        else:
            show_settlement_detail(0)

        def on_settlement_select(_event=None) -> None:
            selection = listbox.curselection()
            if selection and settlements:
                show_settlement_detail(int(selection[0]))

        listbox.bind("<<ListboxSelect>>", on_settlement_select)

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
        restored = int(result.get("restored_snapshots", 0) or 0)
        source = str(result.get("source", "-"))
        message = f"\u8d5b\u679c\u56de\u6536\u5b8c\u6210: \u5b8c\u573a {fetched} | \u4fee\u590d\u5feb\u7167 {restored} | \u65b0\u7ed3\u7b97 {new_settled} | \u6570\u636e\u6e90 {source} | \u8017\u65f6 {elapsed:.2f}s"
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

    def open_accuracy_diagnostics(self) -> None:
        settlements = list(reversed(get_recent_settlements(limit=200)))
        diagnostics = self._accuracy_diagnostics(settlements)
        shell = self._page_shell(
            "\u51c6\u786e\u7387\u8bca\u65ad",
            "\u6309\u7f6e\u4fe1\u5ea6\u3001\u9884\u6d4b\u65b9\u5411\u3001\u73a9\u6cd5\u548c\u8054\u8d5b\u62c6\u89e3\u5386\u53f2\u547d\u4e2d\u7387",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 16))
        tk.Button(
            header,
            text="\u8fd4\u56de\u590d\u76d8\u4e2d\u5fc3",
            command=self.open_review_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT)

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u6837\u672c\u6570", str(diagnostics["sample_count"]), TEXT),
            ("\u603b\u4f53 1X2", diagnostics["overall"], "#7aa2ff"),
            ("\u9ad8\u7f6e\u4fe1 1X2", diagnostics["high_conf"], RED if diagnostics["high_conf_is_weak"] else GREEN),
            ("\u4f18\u5316\u91cd\u70b9", diagnostics["priority"], YELLOW),
        ]:
            self._detail_metric(top, label, str(value), color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u5206\u5c42\u547d\u4e2d\u7387", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        for title, rows in [
            ("\u7f6e\u4fe1\u5ea6", diagnostics["confidence"]),
            ("\u9884\u6d4b\u65b9\u5411", diagnostics["direction"]),
            ("\u8d5b\u679c\u7c7b\u578b", diagnostics["result"]),
        ]:
            self._strategy_row(left, title, "\n".join(rows) if rows else "\u6682\u65e0\u6837\u672c")

        tk.Label(right, text="\u73a9\u6cd5\u4e0e\u8054\u8d5b", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        self._strategy_row(right, "\u73a9\u6cd5\u547d\u4e2d", "\n".join(diagnostics["plays"]) if diagnostics["plays"] else "\u6682\u65e0\u6837\u672c")
        self._strategy_row(right, "\u8054\u8d5b Top 6", "\n".join(diagnostics["leagues"]) if diagnostics["leagues"] else "\u6682\u65e0\u6837\u672c")
        self._strategy_row(right, "\u8bca\u65ad\u7ed3\u8bba", diagnostics["conclusion"])

    def _accuracy_diagnostics(self, settlements: list[dict]) -> dict[str, object]:
        recent = [item for item in settlements[:200] if isinstance(item, dict)]
        confidence_groups = {
            "\u9ad8\u7f6e\u4fe1 >=60%": lambda item: float(item.get("prediction_confidence", 0) or 0) >= 0.6,
            "\u4e2d\u7f6e\u4fe1 45%-60%": lambda item: 0.45 <= float(item.get("prediction_confidence", 0) or 0) < 0.6,
            "\u4f4e\u7f6e\u4fe1 <45%": lambda item: float(item.get("prediction_confidence", 0) or 0) < 0.45,
        }
        direction_groups = {
            "\u4e3b\u80dc": lambda item: item.get("predicted") == "\u4e3b\u80dc",
            "\u5e73\u5c40": lambda item: item.get("predicted") == "\u5e73\u5c40",
            "\u5ba2\u80dc": lambda item: item.get("predicted") == "\u5ba2\u80dc",
        }
        result_groups = {
            "\u5b9e\u9645\u4e3b\u80dc": lambda item: item.get("result") == "\u4e3b\u80dc",
            "\u5b9e\u9645\u5e73\u5c40": lambda item: item.get("result") == "\u5e73\u5c40",
            "\u5b9e\u9645\u5ba2\u80dc": lambda item: item.get("result") == "\u5ba2\u80dc",
        }
        plays = [
            ("1X2", "is_correct"),
            ("\u8ba9\u7403", "handicap_is_correct"),
            ("\u5927\u5c0f\u7403", "ou_is_correct"),
            ("\u6bd4\u5206", "score_is_correct"),
        ]
        confidence_rows = self._diagnostic_group_rows(recent, confidence_groups, "is_correct")
        direction_rows = self._diagnostic_group_rows(recent, direction_groups, "is_correct")
        result_rows = self._diagnostic_group_rows(recent, result_groups, "is_correct")
        play_rows = [self._diagnostic_row(label, recent, key) for label, key in plays]
        league_rows = self._league_diagnostic_rows(recent)
        high_conf_items = [item for item in recent if confidence_groups["\u9ad8\u7f6e\u4fe1 >=60%"](item)]
        high_conf_rate = self._hit_rate_value(high_conf_items, "is_correct")
        weakest_play = self._weakest_diagnostic(play_rows)
        priority = self._accuracy_priority(high_conf_rate, weakest_play)
        return {
            "sample_count": len(recent),
            "overall": self._hit_rate_text(recent, "is_correct"),
            "high_conf": self._hit_rate_text(high_conf_items, "is_correct"),
            "high_conf_is_weak": high_conf_rate is not None and high_conf_rate < 0.5,
            "priority": priority,
            "confidence": confidence_rows,
            "direction": direction_rows,
            "result": result_rows,
            "plays": play_rows,
            "leagues": league_rows,
            "conclusion": self._accuracy_conclusion(high_conf_rate, weakest_play, confidence_rows, direction_rows),
        }

    def _diagnostic_group_rows(self, items: list[dict], groups: dict[str, object], key: str) -> list[str]:
        rows: list[str] = []
        for label, predicate in groups.items():
            group_items = [item for item in items if predicate(item)]
            rows.append(self._diagnostic_row(label, group_items, key))
        return rows

    def _diagnostic_row(self, label: str, items: list[dict], key: str) -> str:
        values = [bool(item.get(key)) for item in items if item.get(key) is not None]
        if not values:
            return f"{label}: - / 0\u573a"
        rate = sum(1 for value in values if value) / len(values)
        return f"{label}: {rate:.1%} / {len(values)}\u573a"

    def _hit_rate_value(self, items: list[dict], key: str) -> float | None:
        values = [bool(item.get(key)) for item in items if item.get(key) is not None]
        if not values:
            return None
        return sum(1 for value in values if value) / len(values)

    def _league_diagnostic_rows(self, items: list[dict]) -> list[str]:
        buckets: dict[str, list[dict]] = {}
        for item in items:
            league = str(item.get("league") or "-")
            buckets.setdefault(league, []).append(item)
        rows = []
        for league, league_items in sorted(buckets.items(), key=lambda pair: len(pair[1]), reverse=True)[:6]:
            rows.append(self._diagnostic_row(league, league_items, "is_correct"))
        return rows

    def _weakest_diagnostic(self, rows: list[str]) -> str:
        weakest = "-"
        weakest_rate = 2.0
        for row in rows:
            try:
                label, rest = row.split(":", 1)
                rate_text = rest.strip().split("/", 1)[0].strip().rstrip("%")
                rate = float(rate_text) / 100
            except Exception:
                continue
            if rate < weakest_rate:
                weakest_rate = rate
                weakest = label
        return weakest

    def _accuracy_priority(self, high_conf_rate: float | None, weakest_play: str) -> str:
        if high_conf_rate is not None and high_conf_rate < 0.5:
            return "\u91cd\u6821\u51c6\u7f6e\u4fe1\u5ea6"
        if weakest_play == "\u6bd4\u5206":
            return "\u964d\u4f4e\u6bd4\u5206\u6743\u91cd"
        if weakest_play == "\u5927\u5c0f\u7403":
            return "\u4fee\u6b63\u8fdb\u7403\u671f\u671b"
        if weakest_play == "\u8ba9\u7403":
            return "\u590d\u6838\u76d8\u53e3\u6743\u91cd"
        return "\u5206\u8054\u8d5b\u8c03\u6743"

    def _accuracy_conclusion(
        self,
        high_conf_rate: float | None,
        weakest_play: str,
        confidence_rows: list[str],
        direction_rows: list[str],
    ) -> str:
        parts = []
        if high_conf_rate is not None and high_conf_rate < 0.5:
            parts.append("\u9ad8\u7f6e\u4fe1\u6837\u672c\u547d\u4e2d\u7387\u4e0d\u8db3\uff0c\u8bf4\u660e\u5f53\u524d\u7f6e\u4fe1\u5ea6\u8fd8\u6ca1\u6709\u5f62\u6210\u6709\u6548\u7684\u8fc7\u6ee4\u80fd\u529b\u3002")
        if weakest_play != "-":
            parts.append(f"\u6700\u5f31\u73a9\u6cd5\u662f {weakest_play}\uff0c\u5e94\u5148\u964d\u6743\u6216\u6539\u4e3a\u8f85\u52a9\u53c2\u8003\u3002")
        parts.append("\u4e0b\u4e00\u6b65\u5efa\u8bae\u4e0d\u662f\u6269\u5927\u9884\u6d4b\u8f93\u51fa\uff0c\u800c\u662f\u5148\u6309\u5206\u5c42\u7ed3\u679c\u8bbe\u7f6e\u8fc7\u6ee4\u95e8\u69db\u3002")
        return "\n".join(parts)

    def _settlement_trend_summary(self, settlements: list[dict]) -> dict[str, object]:
        recent = settlements[:80]
        if not recent:
            return {
                "top_bias": "-",
                "weakest_play": "-",
                "high_conf_misses": 0,
                "priority": "\u7b49\u5f85\u6837\u672c",
            }

        bias_counter: Counter[str] = Counter()
        for item in recent:
            for tag in self._settlement_bias_tags(item):
                if tag != "\u65e0\u660e\u663e\u504f\u5dee":
                    bias_counter[tag] += 1
        top_bias = "-"
        if bias_counter:
            tag, count = bias_counter.most_common(1)[0]
            top_bias = f"{tag} {count}\u6b21"

        play_keys = [
            ("1X2", "is_correct"),
            ("\u8ba9\u7403", "handicap_is_correct"),
            ("\u5927\u5c0f\u7403", "ou_is_correct"),
            ("\u6bd4\u5206", "score_is_correct"),
        ]
        weakest_play = "-"
        weakest_rate = 1.1
        for label, key in play_keys:
            values = [bool(item.get(key)) for item in recent if isinstance(item, dict) and item.get(key) is not None]
            if not values:
                continue
            rate = sum(1 for value in values if value) / len(values)
            if rate < weakest_rate:
                weakest_rate = rate
                weakest_play = f"{label} {rate:.1%}"

        high_conf_misses = sum(
            1
            for item in recent
            if item.get("is_correct") is False and float(item.get("prediction_confidence", 0) or 0) >= 0.6
        )
        priority = self._trend_priority_text(top_bias, weakest_play, high_conf_misses)
        return {
            "top_bias": top_bias,
            "weakest_play": weakest_play,
            "high_conf_misses": high_conf_misses,
            "priority": priority,
        }

    def _trend_priority_text(self, top_bias: str, weakest_play: str, high_conf_misses: int) -> str:
        if high_conf_misses:
            return "\u964d\u4f4e\u9ad8\u7f6e\u4fe1\u5355\u5411\u6743\u91cd"
        if "\u5927\u5c0f\u7403" in weakest_play or "\u8fdb\u7403" in top_bias:
            return "\u4f18\u5316\u603b\u8fdb\u7403\u671f\u671b"
        if "\u8ba9\u7403" in weakest_play or "\u8ba9\u7403" in top_bias:
            return "\u590d\u6838\u8ba9\u7403\u76d8\u4e00\u81f4\u6027"
        if "\u5e73\u5c40" in top_bias:
            return "\u589e\u52a0\u5e73\u5c40\u4fdd\u62a4"
        if "\u6bd4\u5206" in weakest_play or "\u6bd4\u5206" in top_bias:
            return "\u964d\u4f4e\u7cbe\u786e\u6bd4\u5206\u6743\u91cd"
        return "\u7ef4\u6301\u5f53\u524d\u6743\u91cd"

    def _hit_rate_text(self, settlements: list[dict], key: str) -> str:
        values = [bool(item.get(key)) for item in settlements if isinstance(item, dict) and item.get(key) is not None]
        if not values:
            return "-"
        return f"{sum(1 for value in values if value) / len(values):.1%}"

    def _settlement_line(self, item: dict) -> str:
        hit = "\u547d\u4e2d" if item.get("is_correct") else "\u5931\u8bef"
        prefix = "\u653e\u884c | " if str(item.get("strategy_allowlist_decision") or "") == "allow" else ""
        return (
            f"{prefix}{item.get('match_date', '-')} {item.get('league', '-')} | "
            f"{item.get('home_team', '-')} {item.get('home_goals', '-')}-{item.get('away_goals', '-')} {item.get('away_team', '-')} | "
            f"\u9884\u6d4b {item.get('predicted', '-')} | {hit} | {_pct1(item.get('prediction_confidence'))}"
        )

    def _hit_label(self, value: object) -> str:
        if value is True:
            return "\u547d\u4e2d"
        if value is False:
            return "\u5931\u8bef"
        return "\u65e0\u9884\u6d4b"

    def _settlement_bias_tags(self, item: dict) -> list[str]:
        tags: list[str] = []
        confidence = float(item.get("prediction_confidence", 0) or 0)
        if item.get("is_correct") is False and confidence >= 0.6:
            tags.append("\u9ad8\u7f6e\u4fe1\u65b9\u5411\u9519\u8bef")
        if item.get("is_correct") is False and item.get("result") == "\u5e73\u5c40":
            tags.append("\u5e73\u5c40\u98ce\u9669\u4f4e\u4f30")
        if item.get("ou_is_correct") is False:
            tags.append("\u8fdb\u7403\u8282\u594f\u504f\u5dee")
        if item.get("handicap_is_correct") is False:
            tags.append("\u8ba9\u7403\u76d8\u504f\u5dee")
        if item.get("score_is_correct") is False and float(item.get("score_confidence", 0) or 0) >= 0.1:
            tags.append("\u6bd4\u5206\u8def\u5f84\u504f\u5dee")
        if not tags:
            tags.append("\u65e0\u660e\u663e\u504f\u5dee")
        return tags

    def _settlement_review_suggestions(self, tags: list[str]) -> list[str]:
        suggestions: list[str] = []
        if "\u9ad8\u7f6e\u4fe1\u65b9\u5411\u9519\u8bef" in tags:
            suggestions.append("\u964d\u4f4e\u7c7b\u4f3c\u573a\u6b21\u7684\u5355\u4e00\u65b9\u5411\u6743\u91cd\uff0c\u4f18\u5148\u68c0\u67e5\u4e34\u573a\u4f24\u505c\u548c\u76d8\u53e3\u80cc\u79bb\u3002")
        if "\u5e73\u5c40\u98ce\u9669\u4f4e\u4f30" in tags:
            suggestions.append("\u589e\u52a0\u5747\u52bf\u6bd4\u8d5b\u7684\u5e73\u5c40\u4fdd\u62a4\u89c4\u5219\uff0c\u5f53\u80dc\u5e73\u8d1f\u6982\u7387\u5dee\u8ddd\u5c0f\u65f6\u81ea\u52a8\u964d\u6743\u3002")
        if "\u8fdb\u7403\u8282\u594f\u504f\u5dee" in tags:
            suggestions.append("\u590d\u6838\u5927\u5c0f\u7403\u6a21\u5757\u7684\u603b\u8fdb\u7403\u671f\u671b\uff0c\u628a\u8054\u8d5b\u8282\u594f\u548c\u8fd1\u671f\u653b\u9632\u72b6\u6001\u52a0\u5165\u6743\u91cd\u3002")
        if "\u8ba9\u7403\u76d8\u504f\u5dee" in tags:
            suggestions.append("\u68c0\u67e5\u8ba9\u7403\u7ebf\u548c\u6a21\u578b\u80dc\u5dee\u7684\u4e00\u81f4\u6027\uff0c\u76d8\u53e3\u4e0e\u6a21\u578b\u76f8\u53cd\u65f6\u6807\u8bb0\u4e3a\u89c2\u671b\u3002")
        if "\u6bd4\u5206\u8def\u5f84\u504f\u5dee" in tags:
            suggestions.append("\u6bd4\u5206\u53ea\u4f5c\u4e3a\u8f85\u52a9\u8def\u5f84\uff0c\u9ad8\u5206\u6563\u573a\u6b21\u4e0d\u5e94\u8f93\u51fa\u8fc7\u5f3a\u7684\u7cbe\u786e\u6bd4\u5206\u7ed3\u8bba\u3002")
        if not suggestions:
            suggestions.append("\u4fdd\u7559\u5f53\u524d\u7b56\u7565\u6743\u91cd\uff0c\u6301\u7eed\u7d2f\u79ef\u6837\u672c\u540e\u518d\u8c03\u6574\u3002")
        return suggestions

    def _settlement_review_text(self, item: dict) -> str:
        tags = self._settlement_bias_tags(item)
        suggestions = self._settlement_review_suggestions(tags)
        actual_score = f"{item.get('home_goals', '-')}-{item.get('away_goals', '-')}"
        allowlist_lines: list[str] = []
        if str(item.get("strategy_allowlist_decision") or "") == "allow":
            allowlist_lines = [
                "",
                "\u7b56\u7565\u653e\u884c\u95ed\u73af",
                f"- \u653e\u884c\u6e05\u5355: {item.get('strategy_allowlist_file') or '-'}",
                f"- \u5bfc\u51fa\u65f6\u95f4: {item.get('strategy_allowlist_exported_at') or '-'}",
                f"- \u653e\u884c\u7ed3\u679c: {self._hit_label(item.get('is_correct'))}",
                f"- \u9ad8\u51c6\u7b56\u7565: {item.get('high_accuracy_strategy_summary') or '-'}",
                f"- \u5f71\u5b50\u89c2\u5bdf: {item.get('high_accuracy_strategy_shadow_summary') or '-'}",
            ]
        lines = [
            "\u8d5b\u524d\u5feb\u7167",
            f"- \u8d5b\u4e8b: {item.get('home_team', '-')} vs {item.get('away_team', '-')}",
            f"- \u8054\u8d5b: {item.get('league', '-')}",
            f"- \u5f00\u8d5b: {item.get('match_date', '-')} {item.get('match_time', '-')}",
            f"- \u9884\u6d4b\u65b9\u5411: {item.get('predicted', '-')}",
            f"- \u7f6e\u4fe1\u5ea6: {_pct1(item.get('prediction_confidence'))}",
            *allowlist_lines,
            "",
            "\u5b9e\u9645\u8d5b\u679c",
            f"- \u6bd4\u5206: {actual_score}",
            f"- \u7ed3\u679c: {item.get('result', '-')}",
            f"- \u603b\u8fdb\u7403: {item.get('total_goals', '-')}",
            "",
            "\u73a9\u6cd5\u547d\u4e2d",
            f"- 1X2: {self._hit_label(item.get('is_correct'))}",
            f"- \u8ba9\u7403: {self._hit_label(item.get('handicap_is_correct'))} | \u9884\u6d4b {item.get('predicted_handicap', '-')} | \u5b9e\u9645 {item.get('handicap_result', '-')}",
            f"- \u5927\u5c0f\u7403: {self._hit_label(item.get('ou_is_correct'))} | \u9884\u6d4b {item.get('predicted_ou', '-')} | \u5b9e\u9645 {item.get('ou_result', '-')}",
            f"- \u6bd4\u5206: {self._hit_label(item.get('score_is_correct'))} | \u9884\u6d4b {item.get('predicted_score', '-')} | \u5b9e\u9645 {actual_score}",
            "",
            "\u504f\u5dee\u6807\u7b7e",
            *[f"- {tag}" for tag in tags],
            "",
            "\u6539\u8fdb\u5efa\u8bae",
            *[f"- {suggestion}" for suggestion in suggestions],
        ]
        return "\n".join(lines)

    def _high_confidence_misses(self, settlements: list[dict]) -> list[dict]:
        misses = [
            item
            for item in settlements
            if isinstance(item, dict)
            and item.get("is_correct") is False
            and float(item.get("prediction_confidence", 0) or 0) >= 0.6
        ]
        return sorted(misses, key=lambda item: float(item.get("prediction_confidence", 0) or 0), reverse=True)

    def _pending_snapshot_rows(self) -> list[dict]:
        snapshots = _load_prediction_snapshot_records()
        settled_ids = {str(item.get("match_id", "")) for item in get_recent_settlements(limit=0) if item.get("match_id")}
        rows: list[dict] = []
        for match_id, record in snapshots.items():
            if str(match_id) in settled_ids or not isinstance(record, dict):
                continue
            match = record.get("match", {})
            prediction = record.get("prediction", {})
            if not isinstance(match, dict) or not isinstance(prediction, dict):
                continue
            rows.append(
                {
                    "match_id": str(match_id),
                    "saved_at": str(record.get("saved_at") or "-"),
                    "match": match,
                    "prediction": prediction,
                    "market_snapshot": record.get("market_snapshot", {}),
                    "strategy_allowlist": self._snapshot_allowlist_payload(record, prediction),
                    "status": _snapshot_status(match),
                }
            )
        return sorted(rows, key=lambda item: str(item.get("saved_at") or ""), reverse=True)

    def _snapshot_allowlist_payload(self, record: dict, prediction: dict) -> dict:
        payload = record.get("strategy_allowlist") if isinstance(record, dict) else {}
        if isinstance(payload, dict) and payload:
            return payload
        payload = prediction.get("strategy_allowlist") if isinstance(prediction, dict) else {}
        return payload if isinstance(payload, dict) else {}

    def _snapshot_line(self, item: dict) -> str:
        match = item.get("match", {}) if isinstance(item.get("match"), dict) else {}
        prediction = item.get("prediction", {}) if isinstance(item.get("prediction"), dict) else {}
        allowlist = item.get("strategy_allowlist", {}) if isinstance(item.get("strategy_allowlist"), dict) else {}
        prefix = "\u653e\u884c\u5f85\u56de\u6536 | " if allowlist else ""
        return (
            f"{prefix}{item.get('status', '-')} | {match.get('match_date', '-')} {match.get('match_time', '-')} | "
            f"{match.get('league', '-')} | {match.get('home_team', '-')} vs {match.get('away_team', '-')} | "
            f"{prediction.get('recommendation', '-')} | {_pct1(prediction.get('confidence'))}"
        )

    def _snapshot_detail_text(self, item: dict) -> str:
        match = item.get("match", {}) if isinstance(item.get("match"), dict) else {}
        prediction = item.get("prediction", {}) if isinstance(item.get("prediction"), dict) else {}
        market = item.get("market_snapshot", {}) if isinstance(item.get("market_snapshot"), dict) else {}
        probs = prediction.get("probabilities", {}) if isinstance(prediction.get("probabilities"), dict) else {}
        indices = prediction.get("indices", {}) if isinstance(prediction.get("indices"), dict) else {}
        allowlist = item.get("strategy_allowlist", {}) if isinstance(item.get("strategy_allowlist"), dict) else {}
        allowlist_text = ""
        if allowlist:
            allowlist_text = (
                "\n\n\u7b56\u7565\u653e\u884c\u56de\u6536\n"
                f"- \u72b6\u6001: \u653e\u884c\u5f85\u56de\u6536\n"
                f"- \u6e05\u5355: {allowlist.get('file', '-')}\n"
                f"- \u5bfc\u51fa\u65f6\u95f4: {allowlist.get('exported_at', '-')}\n"
                f"- \u5019\u9009: {allowlist.get('top_play', '-')} {allowlist.get('top_pick', '-')} / {_pct1(allowlist.get('top_confidence'))}"
            )
        return (
            f"\u5feb\u7167\u65f6\u95f4: {item.get('saved_at', '-')}\n"
            f"\u72b6\u6001: {item.get('status', '-')}\n"
            f"\u8d5b\u4e8b: {match.get('home_team', '-')} vs {match.get('away_team', '-')}\n"
            f"\u8054\u8d5b: {match.get('league', '-')}\n"
            f"\u5f00\u8d5b: {match.get('match_date', '-')} {match.get('match_time', '-')}\n"
            f"\u6765\u6e90: {match.get('source', '-')} / {match.get('source_id', '-')}\n\n"
            f"\u63a8\u8350: {_strategy_text(prediction)}\n"
            f"\u98ce\u9669: {_risk_label(prediction.get('risk_level'))}\n"
            f"\u7f6e\u4fe1\u5ea6: {_pct1(prediction.get('confidence'))}\n"
            f"\u9884\u8ba1\u603b\u8fdb\u7403: {_num(prediction.get('expected_goals'))}\n\n"
            f"\u6982\u7387: {_prob_text(probs, 'home')} / {_prob_text(probs, 'draw')} / {_prob_text(probs, 'away')}\n"
            f"\u51b7\u95e8\u6307\u6570: {_pct1(indices.get('upset_index', 0))}\n"
            f"\u7a33\u5b9a\u6307\u6570: {_pct1(indices.get('stability_index', 0))}\n"
            f"\u4fe1\u5fc3\u6307\u6570: {_pct1(indices.get('confidence_index', 0))}\n\n"
            f"\u5927\u5c0f\u7403: {prediction.get('ou_recommendation', '-')} / {_pct1(prediction.get('ou_confidence'))}\n"
            f"\u8ba9\u7403: {prediction.get('handicap_recommendation', '-')} / {_pct1(prediction.get('handicap_confidence'))}\n"
            f"\u6bd4\u5206: {prediction.get('score_recommendation', '-')} / {_pct1(prediction.get('score_confidence'))}\n\n"
            f"\u5feb\u7167\u76d8\u53e3: \u4e3b {market.get('odds_home', match.get('odds_home', '-'))} | "
            f"\u5e73 {market.get('odds_draw', match.get('odds_draw', '-'))} | "
            f"\u5ba2 {market.get('odds_away', match.get('odds_away', '-'))}"
            f"{allowlist_text}"
        )

    def open_snapshot_center(self) -> None:
        rows = self._pending_snapshot_rows()
        total = len(rows)
        pending_review = sum(1 for item in rows if item.get("status") == "\u5f85\u56de\u6536")
        allowlist_pending = sum(1 for item in rows if isinstance(item.get("strategy_allowlist"), dict) and item.get("strategy_allowlist"))
        high_risk = sum(
            1
            for item in rows
            if _risk_key((item.get("prediction") or {}).get("risk_level") if isinstance(item.get("prediction"), dict) else "") == "high"
        )
        confidences = [
            float((item.get("prediction") or {}).get("confidence", 0) or 0)
            for item in rows
            if isinstance(item.get("prediction"), dict)
        ]
        avg_conf = f"{(sum(confidences) / len(confidences)):.1%}" if confidences else "-"

        shell = self._page_shell(
            "\u8d5b\u524d\u5feb\u7167",
            "\u4fdd\u7559\u8d5b\u524d\u9884\u6d4b\u3001\u76d8\u53e3\u548c\u98ce\u9669\u72b6\u6001\uff0c\u7b49\u5b8c\u573a\u540e\u56de\u6536\u590d\u76d8",
        )
        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 16))
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
        tk.Button(
            header,
            text="\u8fd4\u56de\u590d\u76d8\u4e2d\u5fc3",
            command=self.open_review_center,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        top = tk.Frame(shell, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for label, value, color in [
            ("\u5feb\u7167\u603b\u6570", str(total), TEXT),
            ("\u5f85\u56de\u6536", str(pending_review), YELLOW if pending_review else GREEN),
            ("\u653e\u884c\u5f85\u56de\u6536", str(allowlist_pending), YELLOW if allowlist_pending else GREEN),
            ("\u9ad8\u98ce\u9669", str(high_risk), RED if high_risk else GREEN),
            ("\u5e73\u5747\u7f6e\u4fe1", avg_conf, "#7aa2ff"),
        ]:
            self._detail_metric(top, label, value, color)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = self._card(body, PANEL)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = self._card(body, PANEL)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u5f85\u590d\u76d8\u5217\u8868", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
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

        tk.Label(right, text="\u5feb\u7167\u8be6\u60c5", bg=PANEL, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 10))
        detail = tk.Text(
            right,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=18,
        )
        detail.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))

        def show_detail(index: int) -> None:
            detail.configure(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            if not rows:
                detail.insert(tk.END, "\u6682\u65e0\u8d5b\u524d\u5feb\u7167\u3002\u5237\u65b0\u8d5b\u4e8b\u540e\uff0c\u7cfb\u7edf\u4f1a\u81ea\u52a8\u4fdd\u5b58\u5f85\u590d\u76d8\u7684\u8d5b\u524d\u9884\u6d4b\u3002")
            else:
                detail.insert(tk.END, self._snapshot_detail_text(rows[index]))
            detail.configure(state=tk.DISABLED)

        for item in rows:
            listbox.insert(tk.END, self._snapshot_line(item))
        if rows:
            listbox.selection_set(0)
            show_detail(0)
        else:
            listbox.insert(tk.END, "\u6682\u65e0\u5f85\u590d\u76d8\u5feb\u7167")
            show_detail(0)

        def on_select(_event=None) -> None:
            selection = listbox.curselection()
            if selection and rows:
                show_detail(int(selection[0]))

        listbox.bind("<<ListboxSelect>>", on_select)

    def export_strategy_allowlist(self) -> Path | None:
        if not self.rows:
            messagebox.showinfo("\u5bfc\u51fa\u653e\u884c\u6e05\u5355", "\u5f53\u524d\u8fd8\u6ca1\u6709\u5df2\u52a0\u8f7d\u7684\u8d5b\u4e8b\u5206\u6790\u7ed3\u679c\u3002")
            return None

        allowed = select_strategy_allowlist_rows(self.rows)
        if not allowed:
            self.status_var.set("\u5f53\u524d\u6ca1\u6709\u6b63\u5f0f\u653e\u884c\u573a\u6b21")
            messagebox.showinfo("\u5bfc\u51fa\u653e\u884c\u6e05\u5355", "\u5f53\u524d\u6ca1\u6709\u7b56\u7565\u51c6\u5165\u4e3a\u6b63\u5f0f\u653e\u884c\u7684\u573a\u6b21\u3002")
            return None

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        path = REPORT_DIR / build_strategy_allowlist_filename(now)
        path.write_text("\n".join(build_strategy_allowlist_report_lines(allowed, generated_at=now)), encoding="utf-8")
        link_summary = mark_strategy_allowlist_snapshots(
            [(row.match, row.prediction) for row in allowed],
            allowlist_file=path.name,
            exported_at=now,
        )
        marked = int(link_summary.get("marked", 0) or 0)
        self.status_var.set(f"\u653e\u884c\u6e05\u5355\u5df2\u5bfc\u51fa: {path.name} | \u5f85\u56de\u6536 {marked} \u573a")
        messagebox.showinfo("\u5bfc\u51fa\u653e\u884c\u6e05\u5355", f"\u5df2\u751f\u6210\u653e\u884c\u6e05\u5355:\n{path}\n\n\u5df2\u63a5\u5165\u590d\u76d8\u56de\u6536: {marked} \u573a")
        return path

    def open_strategy_library(self) -> None:
        status = get_high_accuracy_strategy_status()
        settlements = list(reversed(get_recent_settlements(limit=200)))
        dashboard = build_high_accuracy_strategy_dashboard(status, settlements)
        shell = self._page_shell(
            "\u7b56\u7565\u770b\u677f",
            "\u5c55\u793a\u9ad8\u51c6\u7b56\u7565\u6c60\u3001\u56de\u6d4b\u5206\u5c42\u3001\u7a33\u5b9a\u6027\u548c\u771f\u5b9e\u7ed3\u7b97\u53cd\u9988",
        )

        header = tk.Frame(shell, bg=BG)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            header,
            text=f"\u72b6\u6001: {'ON' if dashboard.get('enabled') else 'OFF'} | \u66f4\u65b0: {dashboard.get('updated_at', '-')}",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 10),
        ).pack(side=tk.LEFT)
        tk.Button(
            header,
            text="\u5bfc\u51fa\u653e\u884c\u6e05\u5355",
            command=self.export_strategy_allowlist,
            bg=BLUE,
            fg="white",
            activebackground="#3d5ee7",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(
            header,
            text="\u5237\u65b0\u770b\u677f",
            command=self.open_strategy_library,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#172638",
            activeforeground="white",
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=18,
            pady=7,
        ).pack(side=tk.RIGHT)

        scroll_wrap = tk.Frame(shell, bg=BG)
        scroll_wrap.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(scroll_wrap, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_wrap, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        content = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=content, anchor=tk.NW)
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))

        top = tk.Frame(content, bg=BG)
        top.pack(fill=tk.X, pady=(0, 16))
        for metric in dashboard.get("metrics", []):
            if not isinstance(metric, dict):
                continue
            color = self._tone_color(str(metric.get("tone") or "neutral"))
            self._detail_metric(top, str(metric.get("label") or "-"), str(metric.get("value") or "-"), color)

        body = tk.Frame(content, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        left = tk.Frame(body, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 14))
        right = tk.Frame(body, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="\u5f53\u524d\u7b56\u7565\u6c60", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(2, 8))
        pool_rows = dashboard.get("pool_rows", [])
        if pool_rows:
            for row in pool_rows:
                if isinstance(row, dict):
                    self._strategy_row(left, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(left, "\u6682\u65e0\u53ef\u7528\u7b56\u7565", "\u8bf7\u5148\u6267\u884c\u9ad8\u51c6\u7b56\u7565\u56de\u6d4b\uff0c\u8ba9\u7cfb\u7edf\u4ece\u5386\u53f2\u6837\u672c\u4e2d\u751f\u6210\u7b56\u7565\u6c60\u3002")

        tk.Label(left, text="\u56de\u6d4b\u4e0e\u6837\u672c", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        for label, value in dashboard.get("validation_rows", []):
            self._strategy_row(left, str(label), str(value))

        tk.Label(right, text="\u771f\u5b9e\u7ed3\u7b97\u53cd\u9988", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(2, 8))
        settlement_rows = dashboard.get("settlement_rows", [])
        if settlement_rows:
            for row in settlement_rows:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))
        else:
            self._strategy_row(right, "\u5c1a\u65e0\u547d\u4e2d\u53cd\u9988", "\u8fd1\u671f\u7ed3\u7b97\u4e2d\u8fd8\u6ca1\u6709\u8bb0\u5f55\u5230\u9ad8\u51c6\u7b56\u7565\u547d\u4e2d\u9879\u3002\u540e\u7eed\u8d5b\u679c\u56de\u6536\u540e\u4f1a\u5728\u8fd9\u91cc\u663e\u793a\u3002")

        allowlist_summary = dashboard.get("allowlist_settlement_summary", {}) if isinstance(dashboard.get("allowlist_settlement_summary"), dict) else {}
        tk.Label(right, text="\u653e\u884c\u590d\u76d8\u7edf\u8ba1", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        self._strategy_row(
            right,
            f"\u653e\u884c\u547d\u4e2d: {allowlist_summary.get('hit_rate_text', '-')} | \u6837\u672c {allowlist_summary.get('known_count', 0)}",
            (
                f"\u9ad8\u51c6\u547d\u4e2d: {allowlist_summary.get('high_strategy_summary', '-')} | "
                f"\u8ba9\u7403 {allowlist_summary.get('handicap_hit_rate_text', '-')} | "
                f"\u5927\u5c0f {allowlist_summary.get('ou_hit_rate_text', '-')} | "
                f"\u4e3b\u8981\u504f\u5dee: {allowlist_summary.get('top_failure', '-')}"
            ),
        )
        allowlist_tuning = dashboard.get("allowlist_tuning", {}) if isinstance(dashboard.get("allowlist_tuning"), dict) else {}
        tuning_rows = allowlist_tuning.get("rows", []) if isinstance(allowlist_tuning.get("rows"), list) else []
        if tuning_rows:
            tuning_body = "\n".join(f"{label}: {value}" for label, value in tuning_rows if isinstance(label, str))
            self._strategy_row(right, f"\u653e\u884c\u95e8\u69db\u5efa\u8bae: {allowlist_tuning.get('label', '-')}", tuning_body)
        allowlist_settlement_rows = dashboard.get("allowlist_settlement_rows", [])
        if allowlist_settlement_rows:
            for row in allowlist_settlement_rows:
                if isinstance(row, dict):
                    self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        tk.Label(right, text="\u4f7f\u7528\u5efa\u8bae", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        for row in dashboard.get("guidance_rows", []):
            if isinstance(row, dict):
                self._strategy_row(right, str(row.get("title") or "-"), str(row.get("body") or "-"))

        tk.Label(right, text="当前准入清单", bg=BG, fg=TEXT, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W, padx=18, pady=(16, 8))
        admission_rows = self._strategy_admission_rows()
        if admission_rows:
            for title, body_text in admission_rows:
                self._strategy_row(right, title, body_text)
        else:
            self._strategy_row(right, "暂无准入结果", "加载并分析赛事后，这里会显示正式放行、观察和阻断清单。")

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

    def _strategy_admission_rows(self, limit: int = 12) -> list[tuple[str, str]]:
        order = {"allow": 0, "observe": 1, "block": 2}
        ranked = sorted(
            self.rows,
            key=lambda row: (
                order.get(str(_admission_payload(row.prediction).get("decision") or "observe"), 1),
                -float(row.prediction.get("confidence", 0) or 0),
            ),
        )
        items: list[tuple[str, str]] = []
        for row in ranked[: max(0, int(limit))]:
            admission = _admission_payload(row.prediction)
            reasons = admission.get("reasons", []) if isinstance(admission.get("reasons"), list) else []
            reason_text = ", ".join(str(item) for item in reasons[:4]) if reasons else "-"
            title = f"{_admission_text(row.prediction)} | {row.match.league} | {row.match.home_team} vs {row.match.away_team}"
            body = (
                f"推荐: {_strategy_text(row.prediction)} | 风险 {_risk_label(row.prediction.get('risk_level'))} | 置信 {_pct1(row.prediction.get('confidence'))}\n"
                f"高准正式/观察: {int(admission.get('active_count', 0) or 0)} / {int(admission.get('shadow_count', 0) or 0)} | "
                f"候选 {admission.get('top_play', '-')} {admission.get('top_pick', '-')}\n"
                f"原因: {reason_text}"
            )
            items.append((title, body))
        return items

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

    def _tone_color(self, tone: str) -> str:
        return {"good": GREEN, "warning": YELLOW, "bad": RED, "info": "#7aa2ff", "neutral": TEXT}.get(str(tone or "neutral"), TEXT)

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
