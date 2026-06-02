"""xG → C1.0 Feature Layer 端到端集成测试"""
import sys
sys.path.insert(0, "src")

from c1.features import build_governance_feature_fields

raw = {
    "home_team": "Manchester City",
    "away_team": "Liverpool",
    "league": "EPL",
    "match_date": "2024-03-10",
    "odds_home": 1.85, "odds_draw": 3.60, "odds_away": 4.20,
    "opening_odds_home": 1.80, "opening_odds_draw": 3.70, "opening_odds_away": 4.50,
    "home_rating": 2005.0, "away_rating": 1982.0,
    "lineup_known": True,
    "predicted_side": "home",
    "market_side": "home",
}

fields = build_governance_feature_fields(raw, enrich_foot=False)

print("=== xG 特征集成测试 ===\n")
xg_keys = [k for k in fields if k.startswith("xg_")]
print(f"xG 特征数: {len(xg_keys)}")
for k in sorted(xg_keys):
    print(f"  {k:<30} = {fields[k]}")

print(f"\n  xg_available: {fields.get('xg_available')}")
if fields.get("xg_available"):
    print("\n✅ xG 数据已成功注入 C1.0 Feature Layer")
    print(f"  预期总进球: {fields.get('xg_match_expected_goals'):.2f}")
    print(f"  主队 xG 差: {fields.get('xg_home_diff'):+.3f}")
    print(f"  客队 xG 差: {fields.get('xg_away_diff'):+.3f}")
else:
    print("\n⚠️  xG 数据未获取到（可能联赛不在 Understat 覆盖范围）")
