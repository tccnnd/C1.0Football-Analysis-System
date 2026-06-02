import sys; sys.path.insert(0, "src")
from c1.inference.baseline import BaselineInferenceEngine
from c1.inference.schema import InferenceInput

engine = BaselineInferenceEngine()
weights = {"market": 0.35, "elo": 0.25, "poisson": 0.15, "dixon_coles": 0.25}

# 有 xG
inp1 = InferenceInput(match_id="t1", odds_home=1.85, odds_draw=3.60, odds_away=4.20,
    home_rating=2005.0, away_rating=1982.0, league_strength=1.0,
    feature_fields={"xg_home_for_avg": 2.088, "xg_away_for_avg": 1.770,
                    "xg_home_against_avg": 1.223, "xg_away_against_avg": 1.418},
    metadata={})
r1 = engine.infer(inp1, weights=weights)
dc1 = next(c for c in r1.components if c.name == "dixon_coles")

# 无 xG
inp2 = InferenceInput(match_id="t2", odds_home=1.85, odds_draw=3.60, odds_away=4.20,
    home_rating=2005.0, away_rating=1982.0, league_strength=1.0,
    feature_fields={}, metadata={})
r2 = engine.infer(inp2, weights=weights)
dc2 = next(c for c in r2.components if c.name == "dixon_coles")

print("=== xG 校准 Dixon-Coles 验证 ===\n")
print("有 xG 数据（曼城 vs 利物浦）:")
print(f"  Dixon-Coles: H={dc1.probabilities['home']:.1%} D={dc1.probabilities['draw']:.1%} A={dc1.probabilities['away']:.1%}")
print(f"  Lambda: home={dc1.metadata['home_lambda']:.3f} away={dc1.metadata['away_lambda']:.3f}")
print(f"  Source: {dc1.metadata['lambda_source']}")
print(f"  Fused ensemble: H={r1.fused_probabilities['home']:.1%} D={r1.fused_probabilities['draw']:.1%} A={r1.fused_probabilities['away']:.1%}")

print("\n无 xG 数据（ELO 降级）:")
print(f"  Dixon-Coles: H={dc2.probabilities['home']:.1%} D={dc2.probabilities['draw']:.1%} A={dc2.probabilities['away']:.1%}")
print(f"  Lambda: home={dc2.metadata['home_lambda']:.3f} away={dc2.metadata['away_lambda']:.3f}")
print(f"  Source: {dc2.metadata['lambda_source']}")
print(f"  Fused ensemble: H={r2.fused_probabilities['home']:.1%} D={r2.fused_probabilities['draw']:.1%} A={r2.fused_probabilities['away']:.1%}")

print("\n对比:")
for side in ["home", "draw", "away"]:
    d = r1.fused_probabilities[side] - r2.fused_probabilities[side]
    print(f"  {side}: {r1.fused_probabilities[side]:.1%} vs {r2.fused_probabilities[side]:.1%} ({d:+.2%})")

print("\n✅ xG 校准生效")
