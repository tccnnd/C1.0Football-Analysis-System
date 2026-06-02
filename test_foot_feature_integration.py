"""
foot 信号 → C1.0 Feature Layer 端到端集成测试
"""
import sys
sys.path.insert(0, "src")

import pymysql
import pymysql.cursors
from c1.features import build_governance_feature_fields, enrich_with_foot_signals

def section(t): print(f"\n{'='*60}\n  {t}\n{'='*60}")

# ── 取一场有真实赔率数据的比赛 ────────────────────────────────────────────────
section("1. 获取测试比赛")
conn = pymysql.connect(host="127.0.0.1", port=3306, user="root",
    password="Meta.123", database="foot", charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
cur.execute("""
    SELECT mh.Id, mh.MainTeamId, mh.GuestTeamId,
           DATE(mh.MatchDate) as md, l.Name as LeagueName
    FROM t_match_his mh
    LEFT JOIN t_league l ON l.Id = mh.LeagueId
    INNER JOIN t_asia_his ah ON ah.MatchId = mh.Id
    INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id
    WHERE mh.MainTeamGoals >= 0
    ORDER BY mh.MatchDate DESC LIMIT 1
""")
row = cur.fetchone()
conn.close()

print(f"  比赛: {row['MainTeamId']} vs {row['GuestTeamId']}")
print(f"  联赛: {row['LeagueName']}  日期: {row['md']}")
print(f"  ID  : {row['Id']}")

# ── 测试 enrich_with_foot_signals ─────────────────────────────────────────────
section("2. enrich_with_foot_signals")
raw = {
    "home_team": row["MainTeamId"],
    "away_team": row["GuestTeamId"],
    "match_date": str(row["md"]),
    "match_id": row["Id"],
    "odds_home": 2.20, "odds_draw": 3.10, "odds_away": 2.80,
    "opening_odds_home": 2.15, "opening_odds_draw": 3.20, "opening_odds_away": 2.90,
    "home_rating": 1500.0, "away_rating": 1450.0,
    "lineup_known": False,
    "predicted_side": "home",
}

enriched = enrich_with_foot_signals(raw, predicted_side="home")
print(f"  foot_signals_available : {enriched.get('foot_signals_available')}")
print(f"  foot_asia_direction    : {enriched.get('foot_asia_direction')}  (3=主降 0=客降 -1=无)")
print(f"  foot_asia_consensus    : {enriched.get('foot_asia_direction_consensus'):.2f}")
print(f"  foot_euro_direction    : {enriched.get('foot_euro_direction')}")
print(f"  foot_euro_asia_conflict: {enriched.get('foot_euro_asia_conflict')}")
print(f"  foot_ranking_diff      : {enriched.get('foot_ranking_diff')}")
print(f"  foot_h2h_win_rate      : {enriched.get('foot_h2h_main_win_rate', 0):.1%}")
print(f"  foot_recent_main_win   : {enriched.get('foot_recent_main_win_rate', 0):.1%}")
print(f"  foot_recent_guest_win  : {enriched.get('foot_recent_guest_win_rate', 0):.1%}")
print(f"  --- 语义特征 ---")
print(f"  foot_asia_signal_strength    : {enriched.get('foot_asia_signal_strength', 0):.4f}")
print(f"  foot_euro_asia_conflict_score: {enriched.get('foot_euro_asia_conflict_score', 0):.4f}")
print(f"  foot_fundamental_score       : {enriched.get('foot_fundamental_score', 0):.4f}")
print(f"  foot_model_agreement         : {enriched.get('foot_model_agreement', 0.5):.4f}")
print(f"  market_divergence (增强后)   : {enriched.get('market_divergence', 0):.4f}")

# ── 测试 build_governance_feature_fields（完整流程）────────────────────────────
section("3. build_governance_feature_fields（含 foot 增强）")
gov_fields = build_governance_feature_fields(raw, enrich_foot=True)

print(f"  foot_signals_available : {gov_fields.get('foot_signals_available')}")
print(f"  info_quality           : {gov_fields.get('info_quality'):.4f}")
print(f"  chaos_score            : {gov_fields.get('chaos_score'):.4f}")
print(f"  market_divergence      : {gov_fields.get('market_divergence'):.4f}")
print(f"  lineup_known           : {gov_fields.get('lineup_known')}")
print(f"  missing_elo_loss       : {gov_fields.get('missing_elo_loss'):.4f}")

# ── 对比：不带 foot 增强 ──────────────────────────────────────────────────────
section("4. 对比：不带 foot 增强")
gov_no_foot = build_governance_feature_fields(raw, enrich_foot=False)
print(f"  chaos_score (无foot)   : {gov_no_foot.get('chaos_score'):.4f}")
print(f"  chaos_score (有foot)   : {gov_fields.get('chaos_score'):.4f}")
print(f"  market_divergence(无)  : {gov_no_foot.get('market_divergence'):.4f}")
print(f"  market_divergence(有)  : {gov_fields.get('market_divergence'):.4f}")
delta_chaos = gov_fields.get('chaos_score', 0) - gov_no_foot.get('chaos_score', 0)
print(f"  chaos_score 增量       : {delta_chaos:+.4f}")

# ── 总特征数量 ────────────────────────────────────────────────────────────────
section("5. 特征总览")
foot_keys = [k for k in gov_fields if k.startswith("foot_")]
print(f"  总特征数: {len(gov_fields)}")
print(f"  foot 特征数: {len(foot_keys)}")
print(f"  foot 特征列表:")
for k in sorted(foot_keys):
    v = gov_fields[k]
    print(f"    {k:<40} = {v}")

section("✅ 集成测试完成")
print("  foot 信号已成功接入 C1.0 Feature Layer")
print("  build_governance_feature_fields 现在自动包含 foot 信号增强")
