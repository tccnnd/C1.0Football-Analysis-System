import json
from pathlib import Path
from collections import defaultdict

data = json.loads(Path("reports/shadow_history/shadow_history_20260529_162822.json").read_text(encoding="utf-8"))
rows = data["rows"]

by_action = defaultdict(lambda: {"v24": 0, "c1": 0, "n": 0})
for r in rows:
    a = r["governance_action"]
    by_action[a]["n"] += 1
    if r.get("v24_correct"): by_action[a]["v24"] += 1
    if r.get("c1_correct"):  by_action[a]["c1"]  += 1

print("=== 1000 场大规模验证结果 ===\n")
print("Governance 分组准确率:")
print(f"  {'Action':<12} {'V24':>6} {'C1.0':>6} {'N':>6}")
print(f"  {'-'*32}")
for a in ["APPROVE", "DOWNGRADE", "BLOCK"]:
    d = by_action[a]
    if d["n"] == 0: continue
    print(f"  {a:<12} {d['v24']/d['n']:>5.1%} {d['c1']/d['n']:>5.1%} {d['n']:>6}")

# Governance 分离度
approve_v24 = by_action["APPROVE"]["v24"] / max(by_action["APPROVE"]["n"], 1)
downgrade_v24 = by_action["DOWNGRADE"]["v24"] / max(by_action["DOWNGRADE"]["n"], 1)
approve_c1 = by_action["APPROVE"]["c1"] / max(by_action["APPROVE"]["n"], 1)
downgrade_c1 = by_action["DOWNGRADE"]["c1"] / max(by_action["DOWNGRADE"]["n"], 1)
print(f"\n  Governance 分离度:")
print(f"    V24:  APPROVE({approve_v24:.1%}) - DOWNGRADE({downgrade_v24:.1%}) = {approve_v24-downgrade_v24:+.1%}")
print(f"    C1.0: APPROVE({approve_c1:.1%}) - DOWNGRADE({downgrade_c1:.1%}) = {approve_c1-downgrade_c1:+.1%}")

# foot 信号
print("\nfoot 信号分组:")
groups = {
    "亚赔对抗模型": [r for r in rows if "FOOT_ASIA_SIGNAL_AGAINST_MODEL" in r.get("reason_codes", [])],
    "无亚赔对抗": [r for r in rows if "FOOT_ASIA_SIGNAL_AGAINST_MODEL" not in r.get("reason_codes", [])],
    "欧亚冲突": [r for r in rows if "FOOT_EURO_ASIA_CONFLICT" in r.get("reason_codes", [])],
}
print(f"  {'Group':<14} {'V24':>6} {'C1.0':>6} {'N':>5}")
print(f"  {'-'*34}")
for name, group in groups.items():
    known = [r for r in group if r.get("actual") != "unknown"]
    if not known: continue
    v = sum(1 for r in known if r.get("v24_correct")) / len(known)
    c = sum(1 for r in known if r.get("c1_correct")) / len(known)
    print(f"  {name:<14} {v:>5.1%} {c:>5.1%} {len(known):>5}")

# 联赛分布
print("\n联赛分布:")
leagues = defaultdict(int)
for r in rows:
    leagues[r.get("league", "?")] += 1
for league, cnt in sorted(leagues.items(), key=lambda x: -x[1])[:7]:
    print(f"  {league:<20} {cnt}")
