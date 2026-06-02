"""
xG 趋势特征引擎 - Step 2

从 Understat 历史数据计算球队近期 xG 趋势特征，
用于增强 XGBoost 预测。

核心特征（赛前可知，基于近N场历史）：
  home_xg_for_avg5      - 主队近5场平均 xG 进攻
  home_xg_against_avg5  - 主队近5场平均 xG 失守
  away_xg_for_avg5      - 客队近5场平均 xG 进攻
  away_xg_against_avg5  - 客队近5场平均 xG 失守
  home_xg_overperform5  - 主队近5场 xG 超额表现（实际进球 - xG）
  away_xg_overperform5  - 客队近5场 xG 超额表现
  xg_diff               - 主客队 xG 进攻差
  xg_defense_diff       - 主客队 xG 防守差
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


XG_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "xg"

# Understat 联赛代码 → 我们系统的联赛名称映射
LEAGUE_NAME_MAP: dict[str, list[str]] = {
    "EPL":        ["英超", "Premier League", "EPL"],
    "La_Liga":    ["西甲", "La Liga", "LaLiga"],
    "Serie_A":    ["意甲", "Serie A", "SerieA"],
    "Bundesliga": ["德甲", "Bundesliga"],
    "Ligue_1":    ["法甲", "Ligue 1", "Ligue1"],
}

# 球队名称标准化（Understat英文名 → 我们系统中文名）
TEAM_NAME_ALIASES: dict[str, str] = {
    # 英超
    "Manchester City": "曼城", "Manchester United": "曼联",
    "Liverpool": "利物浦", "Chelsea": "切尔西",
    "Arsenal": "阿森纳", "Tottenham": "热刺",
    "Newcastle United": "纽卡斯尔", "Aston Villa": "阿斯顿维拉",
    "West Ham": "西汉姆", "Brighton": "布莱顿",
    "Brentford": "布伦特福德", "Fulham": "富勒姆",
    "Crystal Palace": "水晶宫", "Wolves": "狼队",
    "Everton": "埃弗顿", "Nottingham Forest": "诺丁汉森林",
    "Bournemouth": "伯恩茅斯", "Burnley": "伯恩利",
    "Sheffield United": "谢菲尔德联", "Luton": "卢顿",
    "Leicester": "莱斯特城", "Leeds": "利兹联",
    "Southampton": "南安普顿", "Watford": "沃特福德",
    # 西甲
    "Real Madrid": "皇马", "Barcelona": "巴萨",
    "Atletico Madrid": "马竞", "Sevilla": "塞维利亚",
    "Real Sociedad": "皇家社会", "Villarreal": "比利亚雷亚尔",
    "Athletic Club": "毕尔巴鄂", "Valencia": "瓦伦西亚",
    "Betis": "贝蒂斯", "Osasuna": "奥萨苏纳",
    "Girona": "赫罗纳", "Las Palmas": "拉斯帕尔马斯",
    "Getafe": "赫塔费", "Alaves": "阿拉维斯",
    "Celta Vigo": "塞尔塔", "Rayo Vallecano": "拉约瓦列卡诺",
    "Mallorca": "马洛卡", "Cadiz": "加的斯",
    "Almeria": "阿尔梅里亚", "Granada": "格拉纳达",
    # 意甲
    "Inter": "国际米兰", "Juventus": "尤文图斯",
    "AC Milan": "AC米兰", "Napoli": "那不勒斯",
    "Roma": "罗马", "Lazio": "拉齐奥",
    "Atalanta": "亚特兰大", "Fiorentina": "佛罗伦萨",
    "Bologna": "博洛尼亚", "Torino": "都灵",
    "Monza": "蒙扎", "Genoa": "热那亚",
    "Lecce": "莱切", "Cagliari": "卡利亚里",
    "Frosinone": "弗罗西诺内", "Udinese": "乌迪内斯",
    "Sassuolo": "萨索洛", "Empoli": "恩波利",
    "Hellas Verona": "维罗纳", "Salernitana": "萨勒尼塔纳",
    # 德甲
    "Bayern Munich": "拜仁", "Borussia Dortmund": "多特蒙德",
    "RB Leipzig": "莱比锡", "Bayer Leverkusen": "勒沃库森",
    "Eintracht Frankfurt": "法兰克福", "Wolfsburg": "沃尔夫斯堡",
    "Freiburg": "弗莱堡", "Borussia M.Gladbach": "门兴",
    "Union Berlin": "柏林联合", "Hoffenheim": "霍芬海姆",
    "Mainz": "美因茨", "Augsburg": "奥格斯堡",
    "Werder Bremen": "不来梅", "Stuttgart": "斯图加特",
    "Cologne": "科隆", "Bochum": "波鸿",
    "Heidenheim": "海登海姆", "Darmstadt": "达姆施塔特",
    # 法甲
    "Paris Saint-Germain": "巴黎圣日耳曼", "Marseille": "马赛",
    "Monaco": "摩纳哥", "Lyon": "里昂",
    "Lille": "里尔", "Nice": "尼斯",
    "Lens": "朗斯", "Rennes": "雷恩",
    "Strasbourg": "斯特拉斯堡", "Montpellier": "蒙彼利埃",
    "Nantes": "南特", "Toulouse": "图卢兹",
    "Brest": "布雷斯特", "Reims": "兰斯",
    "Le Havre": "勒阿弗尔", "Metz": "梅斯",
    "Lorient": "洛里昂", "Clermont": "克莱蒙",
}


@dataclass
class TeamXGRecord:
    """单场比赛的 xG 记录"""
    date: str
    xg_for: float       # 本队 xG
    xg_against: float   # 对手 xG
    goals_for: int      # 实际进球
    goals_against: int  # 实际失球
    is_home: bool


@dataclass
class TeamXGProfile:
    """球队 xG 历史档案"""
    team_name: str
    records: list[TeamXGRecord] = field(default_factory=list)

    def sorted_records(self) -> list[TeamXGRecord]:
        return sorted(self.records, key=lambda r: r.date)

    def recent_n(self, n: int, before_date: str | None = None) -> list[TeamXGRecord]:
        """获取指定日期之前的最近N场记录"""
        records = self.sorted_records()
        if before_date:
            records = [r for r in records if r.date < before_date]
        return records[-n:] if len(records) >= n else records

    def xg_features(self, n: int = 5, before_date: str | None = None) -> dict[str, float]:
        """计算近N场的 xG 特征"""
        recent = self.recent_n(n, before_date)
        if not recent:
            return self._empty_features()

        xg_for_vals = [r.xg_for for r in recent]
        xg_against_vals = [r.xg_against for r in recent]
        goals_for_vals = [r.goals_for for r in recent]
        goals_against_vals = [r.goals_against for r in recent]

        xg_for_avg = sum(xg_for_vals) / len(xg_for_vals)
        xg_against_avg = sum(xg_against_vals) / len(xg_against_vals)
        goals_for_avg = sum(goals_for_vals) / len(goals_for_vals)
        goals_against_avg = sum(goals_against_vals) / len(goals_against_vals)

        # xG 超额表现：正值=运气好（可能回归），负值=运气差（可能反弹）
        xg_overperform = goals_for_avg - xg_for_avg
        xg_underperform_defense = goals_against_avg - xg_against_avg

        # 近期趋势：最近3场 vs 近5场的差值（正值=上升趋势）
        recent3 = self.recent_n(3, before_date)
        if len(recent3) >= 2:
            xg_for_trend = (sum(r.xg_for for r in recent3) / len(recent3)) - xg_for_avg
        else:
            xg_for_trend = 0.0

        return {
            "xg_for_avg": round(xg_for_avg, 4),
            "xg_against_avg": round(xg_against_avg, 4),
            "xg_overperform": round(xg_overperform, 4),
            "xg_defense_overperform": round(xg_underperform_defense, 4),
            "xg_for_trend": round(xg_for_trend, 4),
            "xg_sample_count": len(recent),
        }

    def _empty_features(self) -> dict[str, float]:
        return {
            "xg_for_avg": 1.3,       # 全局平均值作为默认
            "xg_against_avg": 1.3,
            "xg_overperform": 0.0,
            "xg_defense_overperform": 0.0,
            "xg_for_trend": 0.0,
            "xg_sample_count": 0,
        }


class XGDatabase:
    """
    xG 历史数据库
    加载所有 Understat 数据，按球队建立索引，支持快速查询近期 xG 特征
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir or XG_DATA_DIR
        self._profiles: dict[str, TeamXGProfile] = {}
        self._loaded = False

    def _normalize_team_name(self, name: str) -> str:
        """标准化球队名称（英文→中文，或保持原样）"""
        return TEAM_NAME_ALIASES.get(name, name)

    def load(self) -> None:
        """加载所有 xG 数据文件"""
        if self._loaded:
            return

        if not self._dir.exists():
            self._loaded = True
            return

        for jsonl_file in sorted(self._dir.glob("xg_*.jsonl")):
            try:
                self._load_file(jsonl_file)
            except Exception:
                continue

        self._loaded = True

    def _load_file(self, path: Path) -> None:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                    self._index_match(m)
                except Exception:
                    continue

    def _index_match(self, m: dict) -> None:
        home_name = self._normalize_team_name(str(m.get("home_team", "")))
        away_name = self._normalize_team_name(str(m.get("away_team", "")))
        date = str(m.get("datetime", ""))[:10]  # 只取日期部分

        home_xg = float(m.get("home_xg", 0) or 0)
        away_xg = float(m.get("away_xg", 0) or 0)
        home_goals = int(m.get("home_goals", 0) or 0)
        away_goals = int(m.get("away_goals", 0) or 0)

        if not home_name or not away_name or not date:
            return

        # 主队记录
        if home_name not in self._profiles:
            self._profiles[home_name] = TeamXGProfile(team_name=home_name)
        self._profiles[home_name].records.append(TeamXGRecord(
            date=date,
            xg_for=home_xg,
            xg_against=away_xg,
            goals_for=home_goals,
            goals_against=away_goals,
            is_home=True,
        ))

        # 客队记录
        if away_name not in self._profiles:
            self._profiles[away_name] = TeamXGProfile(team_name=away_name)
        self._profiles[away_name].records.append(TeamXGRecord(
            date=date,
            xg_for=away_xg,
            xg_against=home_xg,
            goals_for=away_goals,
            goals_against=home_goals,
            is_home=False,
        ))

    def get_team_features(
        self,
        team_name: str,
        before_date: str | None = None,
        n: int = 5,
    ) -> dict[str, float]:
        """获取球队的 xG 特征，找不到时返回默认值"""
        if not self._loaded:
            self.load()

        # 尝试直接匹配
        profile = self._profiles.get(team_name)

        # 尝试别名匹配
        if profile is None:
            normalized = self._normalize_team_name(team_name)
            profile = self._profiles.get(normalized)

        # 模糊匹配（部分名称）
        if profile is None:
            for key in self._profiles:
                if team_name in key or key in team_name:
                    profile = self._profiles[key]
                    break

        if profile is None:
            return TeamXGProfile(team_name=team_name)._empty_features()

        return profile.xg_features(n=n, before_date=before_date)

    def build_match_xg_features(
        self,
        home_team: str,
        away_team: str,
        match_date: str | None = None,
        n: int = 5,
    ) -> dict[str, float]:
        """
        为一场比赛构建完整的 xG 特征集
        返回带前缀的特征字典，可直接合并到 XGBoost 特征
        """
        home_feats = self.get_team_features(home_team, before_date=match_date, n=n)
        away_feats = self.get_team_features(away_team, before_date=match_date, n=n)

        return {
            # 主队 xG 特征
            "home_xg_for_avg5":         home_feats["xg_for_avg"],
            "home_xg_against_avg5":     home_feats["xg_against_avg"],
            "home_xg_overperform5":     home_feats["xg_overperform"],
            "home_xg_defense_overp5":   home_feats["xg_defense_overperform"],
            "home_xg_trend5":           home_feats["xg_for_trend"],
            # 客队 xG 特征
            "away_xg_for_avg5":         away_feats["xg_for_avg"],
            "away_xg_against_avg5":     away_feats["xg_against_avg"],
            "away_xg_overperform5":     away_feats["xg_overperform"],
            "away_xg_defense_overp5":   away_feats["xg_defense_overperform"],
            "away_xg_trend5":           away_feats["xg_for_trend"],
            # 差值特征（最重要）
            "xg_attack_diff":           round(home_feats["xg_for_avg"] - away_feats["xg_for_avg"], 4),
            "xg_defense_diff":          round(home_feats["xg_against_avg"] - away_feats["xg_against_avg"], 4),
            "xg_overperform_diff":      round(home_feats["xg_overperform"] - away_feats["xg_overperform"], 4),
            # 数据质量
            "xg_home_sample_count":     float(home_feats["xg_sample_count"]),
            "xg_away_sample_count":     float(away_feats["xg_sample_count"]),
        }

    @property
    def team_count(self) -> int:
        return len(self._profiles)

    @property
    def total_records(self) -> int:
        return sum(len(p.records) for p in self._profiles.values())


# 全局单例（懒加载）
_db: XGDatabase | None = None


def get_xg_database() -> XGDatabase:
    global _db
    if _db is None:
        _db = XGDatabase()
        _db.load()
    return _db


def get_match_xg_features(
    home_team: str,
    away_team: str,
    match_date: str | None = None,
) -> dict[str, float]:
    """便捷函数：获取一场比赛的 xG 特征"""
    return get_xg_database().build_match_xg_features(
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
    )
