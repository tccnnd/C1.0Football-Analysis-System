"""分析让球二路策略命中率"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

DATA = Path(__file__).parents[1] / "data" / "history" / "jc_matches_2022_2026.jsonl"

def market_probs(oh, od, oa):
    h, d, a = 1/max(oh,1.01), 1/max(od,1.01), 1/max(oa,1.01)
    t = h+d+a
    return h/t, d/t, a/t

def confidence_new(top, second):
    return min(1.0, 0.85*top + 0.15*max(top-second, 0.0))

def wilson_lower(hits, n, z=1.645):
    if n == 0: return 0.0
    p = hits/n
    denom = 1 + z*z/n
    centre = p + z*z/(2*n)
    spread = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return max(0.0, (centre-spread)/denom)

with open(DATA, encoding="utf-8") as f:
    matches = [json.loads(l) for l in f if l.strip()]

# 让球二路策略：排除让平，只选让胜/让负
by_thresh = defaultdict(lambda: [0, 0])
thresholds = [round(t/100, 2) for t in range(50, 80, 2)]

for m in matches:
    oh = float(m.get("odds_home") or 0)
    od = float(m.get("odds_draw") or 0)
    oa = float(m.get("odds_away") or 0)
    if oh < 1.01 or od < 1.01 or oa < 1.01:
        continue
    ph, pd, pa = market_probs(oh, od, oa)
    probs = {"home": ph, "draw": pd, "away": pa}
    ordered = sorted(probs.items(), key=lambda x: -x[1])
    top_side = ordered[0][0]
    top_prob = ordered[0][1]
    second_prob = ordered[1][1]
    conf = confidence_new(top_prob, second_prob)
    if top_side == "draw":
        continue
    actual_hc = m.get("handicap_result", "")
    if not actual_hc:
        continue
    predicted_hc = "让胜" if top_side == "home" else "让负"
    hit = predicted_hc == actual_hc
    for thresh in thresholds:
        if conf >= thresh:
            by_thresh[thresh][0] += hit
            by_thresh[thresh][1] += 1

print("让球二路策略（排除让平，只选让胜/让负）")
print(f"{'门槛':>6} {'样本':>6} {'命中':>6} {'命中率':>8} {'Wilson':>8}")
print("-" * 44)
for thresh in sorted(by_thresh.keys()):
    h, t = by_thresh[thresh]
    if t >= 50:
        w = wilson_lower(h, t)
        print(f"{thresh:>6.2f} {t:>6} {h:>6} {h/t:>8.1%} {w:>8.3f}")

# 分析：让球赔率分布
print("\n让球赔率分布（handicap_bonus）")
bonuses = [float(m.get("handicap_bonus") or 0) for m in matches if m.get("handicap_bonus")]
bonuses = [b for b in bonuses if 1.5 <= b <= 3.0]
buckets = defaultdict(int)
for b in bonuses:
    buckets[round(b*10)/10] += 1
for k in sorted(buckets.keys()):
    if buckets[k] >= 50:
        print(f"  赔率~{k:.1f}: {buckets[k]}场")
