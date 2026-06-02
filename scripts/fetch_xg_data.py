"""
Step 1: 批量抓取 Understat xG 历史数据
覆盖：英超/西甲/意甲/德甲/法甲，2019-2024 赛季
输出：data/xg/xg_matches_{league}_{season}.jsonl

字段说明（来自 Understat）：
  id          - 比赛ID
  datetime    - 比赛时间
  h/a         - 主客队 {id, title, short_title}
  goals.h/a   - 实际进球
  xG.h/a      - 预期进球（核心特征）
  forecast    - 赛前预测概率 {w/d/l}
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from understatapi import UnderstatClient

# 配置
LEAGUES = {
    "EPL":        "英超",
    "La_Liga":    "西甲",
    "Serie_A":    "意甲",
    "Bundesliga": "德甲",
    "Ligue_1":    "法甲",
}
SEASONS = ["2019", "2020", "2021", "2022", "2023"]  # 2019=2019/20赛季

OUTPUT_DIR = ROOT / "data" / "xg"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "fetch_summary.json"


def fetch_league_season(client, league: str, season: str) -> list[dict]:
    """抓取单个联赛单个赛季的所有比赛 xG 数据"""
    matches = client.league(league=league).get_match_data(season=season)
    # 只保留已完成的比赛
    results = [m for m in matches if m.get("isResult")]
    return results


def normalize_match(m: dict, league: str, season: str) -> dict:
    """标准化字段，方便后续使用"""
    return {
        "understat_id": str(m.get("id", "")),
        "league": league,
        "season": season,
        "datetime": str(m.get("datetime", "")),
        "home_team": m.get("h", {}).get("title", ""),
        "away_team": m.get("a", {}).get("title", ""),
        "home_goals": int(m.get("goals", {}).get("h", 0) or 0),
        "away_goals": int(m.get("goals", {}).get("a", 0) or 0),
        "home_xg": float(m.get("xG", {}).get("h", 0) or 0),
        "away_xg": float(m.get("xG", {}).get("a", 0) or 0),
        # 赛前预测概率（Understat 自己的模型）
        "forecast_home_win": float(m.get("forecast", {}).get("w", 0) or 0),
        "forecast_draw":     float(m.get("forecast", {}).get("d", 0) or 0),
        "forecast_away_win": float(m.get("forecast", {}).get("l", 0) or 0),
    }


def main():
    summary = {}
    total_matches = 0

    with UnderstatClient() as client:
        for league_code, league_name in LEAGUES.items():
            summary[league_code] = {}
            for season in SEASONS:
                out_file = OUTPUT_DIR / f"xg_{league_code}_{season}.jsonl"

                # 跳过已存在的文件
                if out_file.exists():
                    existing = sum(1 for _ in out_file.open(encoding="utf-8"))
                    print(f"  跳过 {league_name} {season}: 已有 {existing} 场")
                    summary[league_code][season] = existing
                    total_matches += existing
                    continue

                print(f"  抓取 {league_name} {season}...", end=" ", flush=True)
                try:
                    matches = fetch_league_season(client, league_code, season)
                    normalized = [normalize_match(m, league_code, season) for m in matches]

                    with open(out_file, "w", encoding="utf-8") as f:
                        for item in normalized:
                            f.write(json.dumps(item, ensure_ascii=False) + "\n")

                    print(f"{len(normalized)} 场")
                    summary[league_code][season] = len(normalized)
                    total_matches += len(normalized)

                    # 礼貌性延迟，避免被封
                    time.sleep(1.5)

                except Exception as e:
                    print(f"失败: {e}")
                    summary[league_code][season] = f"error: {e}"

    SUMMARY_FILE.write_text(
        json.dumps({"total": total_matches, "leagues": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n完成！共 {total_matches} 场比赛 xG 数据")
    print(f"输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    print("开始抓取 Understat xG 数据...")
    print(f"联赛: {', '.join(LEAGUES.values())}")
    print(f"赛季: {', '.join(SEASONS)}\n")
    main()
