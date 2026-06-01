"""
Understat xG 数据桥接层

从 understat.com 获取预期进球（xG）数据，
转换为 C1.0 Feature Layer 可用的特征。

覆盖联赛：EPL, La_Liga, Bundesliga, Serie_A, Ligue_1, RFPL
赛季范围：2014/15 至今

设计原则：
- 按赛季缓存到本地 JSON，避免频繁请求
- 失败时静默降级（返回空特征）
- 支持按球队查询赛季 xG 统计
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Understat 联赛代码映射
LEAGUE_MAP = {
    "英超": "EPL", "EPL": "EPL", "Premier League": "EPL",
    "西甲": "La_Liga", "La Liga": "La_Liga", "西班牙甲组联赛": "La_Liga",
    "德甲": "Bundesliga", "Bundesliga": "Bundesliga",
    "意甲": "Serie_A", "Serie A": "Serie_A",
    "法甲": "Ligue_1", "Ligue 1": "Ligue_1",
    "俄超": "RFPL", "RFPL": "RFPL",
}

# 缓存目录
_CACHE_DIR: Optional[Path] = None


def _get_cache_dir() -> Path:
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "xg"
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def _cache_path(league: str, season: str) -> Path:
    return _get_cache_dir() / f"xg_{league}_{season}.json"


def _cache_is_fresh(path: Path, max_age_hours: int = 24) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < max_age_hours * 3600


def _load_cached(league: str, season: str) -> list[dict] | None:
    path = _cache_path(league, season)
    if not _cache_is_fresh(path):
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cache(league: str, season: str, data: list[dict]) -> None:
    path = _cache_path(league, season)
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ── 数据获取 ──────────────────────────────────────────────────────────────────

def fetch_league_xg(league: str, season: str) -> list[dict]:
    """
    获取指定联赛赛季的所有比赛 xG 数据。
    优先从缓存读取，缓存过期则从 Understat 获取。
    """
    understat_league = LEAGUE_MAP.get(league, league)
    cached = _load_cached(understat_league, season)
    if cached is not None:
        return cached

    try:
        from understatapi import UnderstatClient
        client = UnderstatClient()
        results = client.league(league=understat_league).get_match_data(season=season)
        matches = [dict(m) for m in results] if results else []
        _save_cache(understat_league, season, matches)
        return matches
    except Exception as exc:
        logger.warning("xg_bridge: 获取 %s %s 失败: %s", league, season, exc)
        return []


def fetch_team_xg_stats(
    team_name: str,
    league: str,
    season: str | None = None,
) -> dict[str, Any]:
    """
    获取球队在指定联赛赛季的 xG 统计。

    返回：
    {
        "matches_played": int,
        "xg_for_total": float,      # 总预期进球
        "xg_against_total": float,  # 总预期失球
        "xg_for_avg": float,        # 场均预期进球
        "xg_against_avg": float,    # 场均预期失球
        "xg_diff_avg": float,       # 场均 xG 差
        "goals_for_total": int,
        "goals_against_total": int,
        "xg_overperformance": float, # 实际进球 - xG（正值=超额表现）
    }
    """
    if season is None:
        now = datetime.now()
        season = str(now.year) if now.month >= 8 else str(now.year - 1)

    matches = fetch_league_xg(league, season)
    if not matches:
        return {}

    team_lower = team_name.lower().strip()
    xg_for = 0.0
    xg_against = 0.0
    goals_for = 0
    goals_against = 0
    count = 0

    for m in matches:
        h = m.get("h", {})
        a = m.get("a", {})
        xg = m.get("xG", {})
        h_title = str(h.get("title", "")).lower().strip()
        a_title = str(a.get("title", "")).lower().strip()

        if team_lower in h_title or h_title in team_lower:
            # 球队是主队
            xg_for += float(xg.get("h", 0) or 0)
            xg_against += float(xg.get("a", 0) or 0)
            goals_for += int(m.get("goals", {}).get("h", 0) or 0)
            goals_against += int(m.get("goals", {}).get("a", 0) or 0)
            count += 1
        elif team_lower in a_title or a_title in team_lower:
            # 球队是客队
            xg_for += float(xg.get("a", 0) or 0)
            xg_against += float(xg.get("h", 0) or 0)
            goals_for += int(m.get("goals", {}).get("a", 0) or 0)
            goals_against += int(m.get("goals", {}).get("h", 0) or 0)
            count += 1

    if count == 0:
        return {}

    return {
        "matches_played": count,
        "xg_for_total": round(xg_for, 3),
        "xg_against_total": round(xg_against, 3),
        "xg_for_avg": round(xg_for / count, 3),
        "xg_against_avg": round(xg_against / count, 3),
        "xg_diff_avg": round((xg_for - xg_against) / count, 3),
        "goals_for_total": goals_for,
        "goals_against_total": goals_against,
        "xg_overperformance": round(goals_for - xg_for, 3),
    }


def get_match_xg(
    home_team: str,
    away_team: str,
    match_date: str,
    league: str,
) -> dict[str, Any]:
    """
    获取单场比赛的 xG 数据（赛后）。

    返回：
    {
        "xg_home": float,
        "xg_away": float,
        "xg_total": float,
        "found": bool,
    }
    """
    try:
        dt = datetime.strptime(match_date, "%Y-%m-%d")
    except Exception:
        return {"found": False}

    season = str(dt.year) if dt.month >= 8 else str(dt.year - 1)
    matches = fetch_league_xg(league, season)
    if not matches:
        return {"found": False}

    home_lower = home_team.lower().strip()
    away_lower = away_team.lower().strip()

    for m in matches:
        h = m.get("h", {})
        a = m.get("a", {})
        h_title = str(h.get("title", "")).lower().strip()
        a_title = str(a.get("title", "")).lower().strip()
        m_date = str(m.get("datetime", ""))[:10]

        if m_date == match_date and (home_lower in h_title or h_title in home_lower) and (away_lower in a_title or a_title in away_lower):
            xg = m.get("xG", {})
            xg_h = float(xg.get("h", 0) or 0)
            xg_a = float(xg.get("a", 0) or 0)
            return {
                "xg_home": round(xg_h, 3),
                "xg_away": round(xg_a, 3),
                "xg_total": round(xg_h + xg_a, 3),
                "found": True,
                "understat_id": m.get("id"),
            }

    return {"found": False}


# ── C1.0 Feature Layer 集成 ───────────────────────────────────────────────────

def build_xg_features(
    home_team: str,
    away_team: str,
    league: str,
    season: str | None = None,
) -> dict[str, float]:
    """
    构建 xG 特征字典，供 C1.0 Feature Layer 使用。

    返回 8 个特征：
    - xg_home_for_avg: 主队场均预期进球
    - xg_home_against_avg: 主队场均预期失球
    - xg_away_for_avg: 客队场均预期进球
    - xg_away_against_avg: 客队场均预期失球
    - xg_home_diff: 主队 xG 差（攻-守）
    - xg_away_diff: 客队 xG 差
    - xg_match_expected_goals: 预期总进球（主队攻 + 客队攻）
    - xg_home_overperformance: 主队超额表现
    """
    result = {
        "xg_home_for_avg": 0.0,
        "xg_home_against_avg": 0.0,
        "xg_away_for_avg": 0.0,
        "xg_away_against_avg": 0.0,
        "xg_home_diff": 0.0,
        "xg_away_diff": 0.0,
        "xg_match_expected_goals": 0.0,
        "xg_home_overperformance": 0.0,
        "xg_available": 0.0,
    }

    try:
        home_stats = fetch_team_xg_stats(home_team, league, season)
        away_stats = fetch_team_xg_stats(away_team, league, season)

        if not home_stats or not away_stats:
            return result

        result["xg_home_for_avg"] = home_stats.get("xg_for_avg", 0.0)
        result["xg_home_against_avg"] = home_stats.get("xg_against_avg", 0.0)
        result["xg_away_for_avg"] = away_stats.get("xg_for_avg", 0.0)
        result["xg_away_against_avg"] = away_stats.get("xg_against_avg", 0.0)
        result["xg_home_diff"] = home_stats.get("xg_diff_avg", 0.0)
        result["xg_away_diff"] = away_stats.get("xg_diff_avg", 0.0)
        result["xg_match_expected_goals"] = round(
            home_stats.get("xg_for_avg", 0.0) + away_stats.get("xg_for_avg", 0.0), 3
        )
        result["xg_home_overperformance"] = home_stats.get("xg_overperformance", 0.0)
        result["xg_available"] = 1.0
    except Exception as exc:
        logger.debug("xg_bridge: build_xg_features 失败: %s", exc)

    return result
