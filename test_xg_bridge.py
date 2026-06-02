"""测试 xG 桥接层"""
import sys
sys.path.insert(0, "src")

from c1.data.xg_bridge import fetch_team_xg_stats, build_xg_features, get_match_xg

print("=== xG 桥接层测试 ===\n")

# 1. 球队 xG 统计
print("1. 球队 xG 统计（曼城 EPL 2023）:")
stats = fetch_team_xg_stats("Manchester City", "EPL", "2023")
if stats:
    for k, v in stats.items():
        print(f"   {k}: {v}")
else:
    print("   未找到数据")

print()

# 2. 球队 xG 统计（利物浦）
print("2. 球队 xG 统计（利物浦 EPL 2023）:")
stats2 = fetch_team_xg_stats("Liverpool", "EPL", "2023")
if stats2:
    for k, v in stats2.items():
        print(f"   {k}: {v}")

print()

# 3. 构建比赛 xG 特征
print("3. 比赛 xG 特征（曼城 vs 利物浦）:")
features = build_xg_features("Manchester City", "Liverpool", "EPL", "2023")
for k, v in features.items():
    print(f"   {k}: {v}")

print()

# 4. 单场比赛 xG
print("4. 单场比赛 xG（2023-08-11 Burnley vs Man City）:")
match_xg = get_match_xg("Burnley", "Manchester City", "2023-08-11", "EPL")
for k, v in match_xg.items():
    print(f"   {k}: {v}")

print("\n✅ xG 桥接层测试完成")
