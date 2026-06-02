"""测试 xG 校准 Dixon-Coles lambda"""
import sys
sys.path.insert(0, "src")

from c1.inference.baseline import BaselineInferenceEngine
from c1.inference.schema import InferenceInput

engine = BaselineInferenceEngine()

print("=== xG 校准 Dixon-Coles 测试 ===\n")

# 场景 1：有 xG 数据（曼城 vs 利物浦）
print("1. 有 xG 数据（曼城 vs 利物浦 2023/24）:")
inp1 = InferenceInput(
    match_id="test_xg",
    odds_home=1.85, odds_draw=3.60, odds_away=4.20,
    home_rating=2005.0, away_rating=1982.0,
    league_strength=1.0,
    feature_fields={
        "xg_home_for_avg": 2.088,       # 曼城场均 xG
        "xg_away_for_avg": 1.770,       # 利物浦场均 xG
        "xg_home_against_avg": 1.223,   # 曼城场均失球 xG
        "xg_away_against_avg": 1.418,   # 利物浦场均失球 xG
    },
    metadata={},
)
result1 = engine.infer(inp1, weights={"market": 0.35, "elo": 0.25, "poisson": 0.15, "dixon_coles": 0.25})
dc1 = next(c for c in result1.components if c.name == "dixon_coles")
print(f"  Dixon-Coles: H={dc1.probabilities['home']:.1%} D={dc1.probabilities['draw']:.1%} A={dc1.probabilities['away']:.1%}")
print(f"  Lambda source: {dc1.metadata.get('lambda_source')}")
print(f"  home_lambda={dc1.metadata.get('home_lambda'):.3f}  away_lambda={dc1.metadata.get('away_lambda'):.3f}")
print(f"  Fused: H={result1.raw_probabilities['home']:.1%} D={result1.raw_probabilities['draw']:.1%} A={result1.raw_probabilities['away']:.1%}")
print(f"  Predicted: {result1.predicted_side} ({result1.confidence:.1%})")

# 场景 2：无 xG 数据（降级到 ELO）
print("\n2. 无 xG 数据（降级到 ELO 估算）:")
inp2 = InferenceInput(
    match_id="test_no_xg",
    odds_home=1.85, odds_draw=3.60, odds_away=4.20,
    home_rating=2005.0, away_rating=1982.0,
    league_strength=1.0,
    feature_fields={},  # 无 xG
    metadata={},
)
result2 = engine.infer(inp2, weights={"market": 0.35, "elo": 0.25, "poisson": 0.15, "dixon_coles": 0.25})
dc2 = next(c for c in result2.components if c.name == "dixon_coles")
print(f"  Dixon-Coles: H={dc2.probabilities['home']:.1%} D={dc2.probabilities['draw']:.1%} A={dc2.probabilities['away']:.1%}")
print(f"  Lambda source: {dc2.metadata.get('lambda_source')}")
print(f"  home_lambda={dc2.metadata.get('home_lambda'):.3f}  away_lambda={dc2.metadata.get('away_lambda'):.3f}")
print(f"  Fused: H={result2.raw_probabilities['home']:.1%} D={result2.raw_probabilities['draw']:.1%} A={result2.raw_probabilities['away']:.1%}")

# 对比
print("\n3. xG 校准 vs ELO 降级对比:")
print(f"  {'指标':<20} {'有xG':<15} {'无xG':<15} {'差异'}")
print(f"  {'-'*55}")
for side in ["home", "draw", "away"]:
    v1 = result1.raw_probabilities[side]
    v2 = result2.raw_probabilities[side]
    print(f"  {side:<20} {v1:.1%}          {v2:.1%}          {v1-v2:+.1%}")
print(f"  {'confidence':<20} {result1.confidence:.1%}          {result2.confidence:.1%}          {result1.confidence-result2.confidence:+.1%}")

# 场景 3：弱队 vs 强队（xG 差异大）
print("\n4. 弱队 vs 强队（xG 差异大）:")
inp3 = InferenceInput(
    match_id="test_weak",
    odds_home=5.50, odds_draw=3.80, odds_away=1.60,
    home_rating=1400.0, away_rating=1800.0,
    league_strength=0.95,
    feature_fields={
        "xg_home_for_avg": 0.9,
        "xg_away_for_avg": 2.3,
        "xg_home_against_avg": 1.8,
        "xg_away_against_avg": 0.7,
    },
    metadata={},
)
result3 = engine.infer(inp3, weights={"market": 0.35, "elo": 0.25, "poisson": 0.15, "dixon_coles": 0.25})
dc3 = next(c for c in result3.components if c.name == "dixon_coles")
print(f"  Dixon-Coles: H={dc3.probabilities['home']:.1%} D={dc3.probabilities['draw']:.1%} A={dc3.probabilities['away']:.1%}")
print(f"  Lambda: home={dc3.metadata.get('home_lambda'):.2f} away={dc3.metadata.get('away_lambda'):.2f}")
print(f"  Fused: H={result3.raw_probabilities['home']:.1%} D={result3.raw_probabilities['draw']:.1%} A={result3.raw_probabilities['away']:.1%}")

print("\n✅ xG 校准测试完成")
