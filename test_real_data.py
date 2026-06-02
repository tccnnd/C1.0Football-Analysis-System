"""用真实历史数据测试桥接层信号提取"""
import sys
sys.path.insert(0, "src")

import pymysql
import pymysql.cursors
from c1.data.foot_bridge import get_foot_bridge

bridge = get_foot_bridge()

# 取最近5场有亚赔数据的比赛
conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root",
    password="Meta.123", database="foot",
    charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()
cur.execute("""
    SELECT DISTINCT mh.Id, mh.MainTeamId, mh.GuestTeamId,
           DATE(mh.MatchDate) as md
    FROM t_match_his mh
    INNER JOIN t_asia_his ah ON ah.MatchId = mh.Id
    INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id
    ORDER BY mh.MatchDate DESC
    LIMIT 5
""")
rows = cur.fetchall()
conn.close()

print("找到有赔率数据的比赛:")
for r in rows:
    print(f"  {r['md']}  {r['MainTeamId']} vs {r['GuestTeamId']}  (id={r['Id']})")

print()
# 测试每场比赛的信号提取
for r in rows[:3]:
    print(f"{'='*60}")
    print(f"  {r['MainTeamId']} vs {r['GuestTeamId']}  ({r['md']})")
    print(f"{'='*60}")
    signals = bridge.get_signals_for_match(
        main_team_id=r["MainTeamId"],
        guest_team_id=r["GuestTeamId"],
        match_date=str(r["md"]),
        match_id=r["Id"],
    )
    print(f"  has_data          : {signals.has_data}")
    print(f"  error             : {signals.error!r}")
    print(f"  league            : {signals.league_name}")
    print(f"  asia_direction    : {signals.asia_direction}  (3=主降 0=客降 -1=无)")
    print(f"  asia_consensus    : {signals.asia_direction_consensus:.2f}")
    print(f"  asia_let_ball     : 初盘={signals.asia_let_ball_opening}  即时={signals.asia_let_ball_instant}  变化={signals.asia_let_ball_move:+.3f}")
    print(f"  euro_direction    : {signals.euro_direction}")
    print(f"  euro_asia_conflict: {signals.euro_asia_conflict}")
    print(f"  ranking_diff      : {signals.ranking_diff}")
    print(f"  h2h_win_rate      : {signals.h2h_main_win_rate:.2%}")
    print(f"  recent_main_win   : {signals.recent_main_win_rate:.2%}")
    print(f"  recent_guest_win  : {signals.recent_guest_win_rate:.2%}")
    print(f"  c1_my_let_ball    : {signals.c1_my_let_ball}")
    print(f"  model_signals     : {signals.model_signals}")
    print(f"  model_consensus   : {signals.model_consensus}")
    print()
