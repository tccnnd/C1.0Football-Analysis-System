"""
从 foot MySQL 历史数据预计算 ELO 评分

用 35 万场历史比赛按时间顺序更新 ELO，
最终输出每支球队的当前评分到 V24 的 ratings 文件。

用法：
    python build_elo_from_foot.py                # 全量计算
    python build_elo_from_foot.py --since 2018   # 从 2018 年开始
    python build_elo_from_foot.py --dry-run      # 只计算不保存
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# ── ELO 计算核心 ─────────────────────────────────────────────────────────────

DEFAULT_RATING = 1500.0
K_FACTOR = 32.0
HOME_ADVANTAGE = 65.0


def expected_score(rating_a: float, rating_b: float) -> float:
    """A 对 B 的期望得分"""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def update_elo(
    home_rating: float,
    away_rating: float,
    home_goals: int,
    away_goals: int,
    k: float = K_FACTOR,
    home_adv: float = HOME_ADVANTAGE,
) -> tuple[float, float]:
    """更新 ELO 评分，返回 (new_home, new_away)"""
    # 实际得分：胜=1 平=0.5 负=0
    if home_goals > away_goals:
        actual_home = 1.0
    elif home_goals < away_goals:
        actual_home = 0.0
    else:
        actual_home = 0.5

    # 加入主场优势
    adj_home = home_rating + home_adv
    exp_home = expected_score(adj_home, away_rating)

    # 进球差加权（大比分胜利获得更多分）
    goal_diff = abs(home_goals - away_goals)
    if goal_diff <= 1:
        multiplier = 1.0
    elif goal_diff == 2:
        multiplier = 1.5
    else:
        multiplier = (11.0 + goal_diff) / 8.0

    delta = k * multiplier * (actual_home - exp_home)
    new_home = home_rating + delta
    new_away = away_rating - delta
    return round(new_home, 2), round(new_away, 2)


# ── 从 MySQL 取历史比赛 ──────────────────────────────────────────────────────

def fetch_all_matches(since_year: int = 2006) -> list[dict]:
    """按时间顺序取所有已完赛比赛"""
    import pymysql, pymysql.cursors
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root",
        password=os.environ.get("FOOT_MYSQL_PASSWORD", "Meta.123"),
        database="foot", charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT mh.MainTeamId, mh.GuestTeamId,
               mh.MainTeamGoals, mh.GuestTeamGoals,
               mh.MatchDate
        FROM t_match_his mh
        WHERE mh.MainTeamGoals >= 0
          AND mh.GuestTeamGoals >= 0
          AND YEAR(mh.MatchDate) >= %s
        ORDER BY mh.MatchDate ASC
    """, (since_year,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="从 foot 历史数据计算 ELO 评分")
    parser.add_argument("--since", type=int, default=2006, help="起始年份（默认 2006）")
    parser.add_argument("--dry-run", action="store_true", help="只计算不保存")
    parser.add_argument("--top", type=int, default=50, help="显示 Top N 球队")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  从 foot 历史数据计算 ELO 评分")
    print(f"  起始年份: {args.since}  K={K_FACTOR}  主场优势={HOME_ADVANTAGE}")
    print(f"{'='*60}\n")

    # 1. 取数据
    print("1. 从 MySQL 取历史比赛...")
    t0 = time.time()
    matches = fetch_all_matches(args.since)
    print(f"   取到 {len(matches):,} 场比赛  耗时 {time.time()-t0:.1f}s")

    if not matches:
        print("   ❌ 无数据")
        sys.exit(1)

    # 2. 按时间顺序计算 ELO
    print("2. 计算 ELO 评分...")
    ratings: dict[str, float] = defaultdict(lambda: DEFAULT_RATING)
    match_count: dict[str, int] = defaultdict(int)
    t0 = time.time()

    for i, m in enumerate(matches):
        home = str(m["MainTeamId"])
        away = str(m["GuestTeamId"])
        hg = int(m["MainTeamGoals"])
        ag = int(m["GuestTeamGoals"])

        new_home, new_away = update_elo(
            ratings[home], ratings[away], hg, ag
        )
        ratings[home] = new_home
        ratings[away] = new_away
        match_count[home] += 1
        match_count[away] += 1

        if (i + 1) % 50000 == 0:
            print(f"   已处理 {i+1:,} 场...")

    elapsed = time.time() - t0
    print(f"   完成: {len(matches):,} 场  {len(ratings):,} 支球队  耗时 {elapsed:.1f}s")

    # 3. 过滤低样本球队（至少 10 场）
    min_matches = 10
    filtered = {team: rating for team, rating in ratings.items()
                if match_count[team] >= min_matches}
    print(f"   过滤后: {len(filtered):,} 支球队（至少 {min_matches} 场）")

    # 4. 统计
    sorted_teams = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    avg_rating = sum(filtered.values()) / len(filtered) if filtered else 0
    max_team, max_rating = sorted_teams[0] if sorted_teams else ("", 0)
    min_team, min_rating = sorted_teams[-1] if sorted_teams else ("", 0)

    print(f"\n3. 统计:")
    print(f"   平均评分: {avg_rating:.1f}")
    print(f"   最高: {max_team} ({max_rating:.1f})")
    print(f"   最低: {min_team} ({min_rating:.1f})")
    print(f"   标准差: {(sum((r-avg_rating)**2 for r in filtered.values())/len(filtered))**0.5:.1f}")

    # 5. Top N
    print(f"\n4. Top {args.top} 球队:")
    print(f"   {'排名':<4} {'球队':<20} {'评分':<8} {'场次':<6}")
    print(f"   {'-'*4} {'-'*20} {'-'*8} {'-'*6}")
    for i, (team, rating) in enumerate(sorted_teams[:args.top], 1):
        print(f"   {i:<4} {team:<20} {rating:<8.1f} {match_count[team]:<6}")

    # 6. 保存
    if args.dry_run:
        print(f"\n5. [DRY RUN] 不保存")
    else:
        print(f"\n5. 保存评分...")
        # 保存到 V24 的 ratings 文件
        state_dir = PROJECT_ROOT / "data" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        ratings_file = state_dir / "ratings.json"

        # 合并现有评分（保留 V24 已有的，foot 计算的作为补充）
        existing = {}
        if ratings_file.exists():
            try:
                existing = json.loads(ratings_file.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        # foot 评分覆盖（更大样本量更准确）
        merged = dict(existing)
        new_count = 0
        updated_count = 0
        for team, rating in filtered.items():
            if team not in merged:
                new_count += 1
            else:
                updated_count += 1
            merged[team] = rating

        ratings_file.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"   保存到: {ratings_file}")
        print(f"   总球队: {len(merged):,}  新增: {new_count}  更新: {updated_count}")

        # 同时保存一份 foot 专用的评分文件（用于对比）
        foot_ratings_file = state_dir / "foot_elo_ratings.json"
        foot_ratings_file.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "foot_mysql_history",
                    "matches_processed": len(matches),
                    "teams_count": len(filtered),
                    "k_factor": K_FACTOR,
                    "home_advantage": HOME_ADVANTAGE,
                    "since_year": args.since,
                    "ratings": dict(sorted_teams),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"   foot 专用评分: {foot_ratings_file}")

    print(f"\n{'='*60}")
    print(f"  完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
