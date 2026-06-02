"""测试 Dixon-Coles 修正引擎"""
import sys, time
sys.path.insert(0, "src")

from c1.inference.engines.dixon_coles import DixonColesEngine, dixon_coles_correction

print("=== Dixon-Coles 修正引擎测试 ===\n")

engine = DixonColesEngine()
print(f"Available: {engine.available}")
print(f"Fitted: {engine.fitted}")
print(f"Rho: {engine.rho}")

# 对比独立 Poisson vs Dixon-Coles 修正
print("\n1. 独立 Poisson vs Dixon-Coles 修正:")
from math import exp, factorial

def poisson_1x2(home_lam, away_lam, max_g=8):
    h, d, a = 0.0, 0.0, 0.0
    for i in range(max_g+1):
        for j in range(max_g+1):
            p = (home_lam**i * exp(-home_lam) / factorial(i)) * (away_lam**j * exp(-away_lam) / factorial(j))
            if i > j: h += p
            elif i == j: d += p
            else: a += p
    t = h + d + a
    return {"home": h/t, "draw": d/t, "away": a/t}

tests = [
    (1.8, 1.0, "强主 vs 弱客"),
    (1.3, 1.3, "均势"),
    (0.8, 1.6, "弱主 vs 强客"),
    (2.5, 0.8, "超强主"),
]

print(f"  {'场景':<12} {'Poisson H/D/A':<24} {'Dixon-Coles H/D/A':<24} {'Draw 差异'}")
print(f"  {'-'*72}")
for h_lam, a_lam, desc in tests:
    p = poisson_1x2(h_lam, a_lam)
    dc = dixon_coles_correction(h_lam, a_lam)
    draw_diff = dc["draw"] - p["draw"]
    print(f"  {desc:<12} {p['home']:.1%}/{p['draw']:.1%}/{p['away']:.1%}    {dc['home']:.1%}/{dc['draw']:.1%}/{dc['away']:.1%}    {draw_diff:+.2%}")

# 从 ELO 评分预测
print("\n2. 从 ELO 评分预测:")
tests2 = [
    (2005, 1982, "曼城 vs 利物浦"),
    (1600, 1400, "强队 vs 弱队"),
    (1500, 1500, "均势"),
]
for h_elo, a_elo, desc in tests2:
    probs = engine.predict_from_ratings(h_elo, a_elo)
    print(f"  {desc:<16} H={probs['home']:.1%} D={probs['draw']:.1%} A={probs['away']:.1%}")

# 性能测试
print("\n3. 性能测试:")
t0 = time.perf_counter()
for _ in range(10000):
    dixon_coles_correction(1.5, 1.2)
elapsed = (time.perf_counter() - t0) * 1000
print(f"  10000 次预测: {elapsed:.1f}ms ({elapsed/10:.3f}ms/次)")

print("\n✅ Dixon-Coles 修正引擎测试完成")
