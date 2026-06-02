"""
测试模型预测效果

测试所有训练好的模型的预测能力和性能。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
from v24_app.models.xgboost_xg import XGBoostWithXGModel
from v24_app.models.play_xgboost import (
    TotalGoalsXGBoostModel,
    ScorelineXGBoostModel,
    VolatileScorelineXGBoostModel,
)
from v24_app.models.ensemble import EnsembleContext


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test_1x2_models():
    """测试 1X2 预测模型"""
    print_section("测试 1X2 预测模型")
    
    # 初始化模型
    model_v0 = XGBoostProbabilityModel(PROJECT_ROOT)
    model_xg = XGBoostWithXGModel(PROJECT_ROOT)
    
    # 检查模型状态
    status_v0 = model_v0.get_training_status()
    status_xg = model_xg.get_training_status()
    
    print("\n📊 模型状态:")
    print(f"  XGBoost V0: {'✅ 就绪' if status_v0['model_ready'] else '❌ 未就绪'}")
    print(f"    - 样本数: {status_v0['sample_count']:,}")
    print(f"    - 更新时间: {status_v0['model_updated_at']}")
    
    print(f"\n  XGBoost XG: {'✅ 就绪' if status_xg['model_ready'] else '❌ 未就绪'}")
    print(f"    - 样本数: {status_xg['sample_count']:,}")
    print(f"    - 更新时间: {status_xg['model_updated_at']}")
    
    # 创建测试场景
    test_scenarios = [
        {
            "name": "强队主场 vs 弱队",
            "context": EnsembleContext(
                home_rating=1800.0,
                away_rating=1400.0,
                league_strength=0.75,
                market_probs=(0.65, 0.25, 0.10),
                market_draw_prob=0.25,
                metadata={
                    "odds_home": 1.50,
                    "odds_draw": 4.00,
                    "odds_away": 7.00,
                    "opening_odds_home": 1.55,
                    "opening_odds_draw": 4.20,
                    "opening_odds_away": 6.50,
                    "return_rate": 0.93,
                    "kelly_home": 0.05,
                    "kelly_draw": -0.02,
                    "kelly_away": -0.03,
                    "match_time": "15:00",
                    "match_date": "2026-05-29",
                    "home_team": "Manchester City",
                    "away_team": "Burnley",
                }
            ),
            "expected": "主胜"
        },
        {
            "name": "势均力敌",
            "context": EnsembleContext(
                home_rating=1600.0,
                away_rating=1580.0,
                league_strength=0.70,
                market_probs=(0.40, 0.30, 0.30),
                market_draw_prob=0.30,
                metadata={
                    "odds_home": 2.40,
                    "odds_draw": 3.20,
                    "odds_away": 2.80,
                    "opening_odds_home": 2.50,
                    "opening_odds_draw": 3.10,
                    "opening_odds_away": 2.70,
                    "return_rate": 0.92,
                    "kelly_home": 0.01,
                    "kelly_draw": 0.02,
                    "kelly_away": 0.01,
                    "match_time": "19:45",
                    "match_date": "2026-05-29",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                }
            ),
            "expected": "主胜或平局"
        },
        {
            "name": "弱队主场 vs 强队",
            "context": EnsembleContext(
                home_rating=1350.0,
                away_rating=1850.0,
                league_strength=0.80,
                market_probs=(0.15, 0.25, 0.60),
                market_draw_prob=0.25,
                metadata={
                    "odds_home": 6.50,
                    "odds_draw": 4.20,
                    "odds_away": 1.45,
                    "opening_odds_home": 7.00,
                    "opening_odds_draw": 4.00,
                    "opening_odds_away": 1.40,
                    "return_rate": 0.94,
                    "kelly_home": -0.02,
                    "kelly_draw": 0.01,
                    "kelly_away": 0.04,
                    "match_time": "20:00",
                    "match_date": "2026-05-29",
                    "home_team": "Southampton",
                    "away_team": "Liverpool",
                }
            ),
            "expected": "客胜"
        },
    ]
    
    print("\n🎯 预测测试:")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n场景 {i}: {scenario['name']}")
        print(f"  预期结果: {scenario['expected']}")
        print(f"  主队评分: {scenario['context'].home_rating:.0f}")
        print(f"  客队评分: {scenario['context'].away_rating:.0f}")
        print(f"  市场概率: 主 {scenario['context'].market_probs[0]:.2%} | "
              f"平 {scenario['context'].market_probs[1]:.2%} | "
              f"客 {scenario['context'].market_probs[2]:.2%}")
        
        # V0 预测
        start = time.time()
        output_v0 = model_v0.predict(scenario['context'])
        elapsed_v0 = (time.time() - start) * 1000
        
        probs_v0 = output_v0.probabilities
        print(f"\n  XGBoost V0 预测:")
        print(f"    主胜: {probs_v0[0]:.2%} | 平局: {probs_v0[1]:.2%} | 客胜: {probs_v0[2]:.2%}")
        print(f"    推荐: {['主胜', '平局', '客胜'][probs_v0.index(max(probs_v0))]} (置信度: {max(probs_v0):.2%})")
        print(f"    预测时间: {elapsed_v0:.2f} ms")
        print(f"    使用回退: {'是' if output_v0.metadata.get('xgb_fallback') else '否'}")
        
        # XG 预测
        start = time.time()
        output_xg = model_xg.predict(scenario['context'])
        elapsed_xg = (time.time() - start) * 1000
        
        probs_xg = output_xg.probabilities
        print(f"\n  XGBoost XG 预测:")
        print(f"    主胜: {probs_xg[0]:.2%} | 平局: {probs_xg[1]:.2%} | 客胜: {probs_xg[2]:.2%}")
        print(f"    推荐: {['主胜', '平局', '客胜'][probs_xg.index(max(probs_xg))]} (置信度: {max(probs_xg):.2%})")
        print(f"    预测时间: {elapsed_xg:.2f} ms")
        print(f"    使用回退: {'是' if output_xg.metadata.get('xgb_fallback') else '否'}")
        
        # 对比
        diff = [abs(probs_v0[i] - probs_xg[i]) for i in range(3)]
        print(f"\n  模型差异: 主 {diff[0]:.2%} | 平 {diff[1]:.2%} | 客 {diff[2]:.2%}")


def test_play_models():
    """测试玩法模型"""
    print_section("测试玩法预测模型")
    
    # 初始化模型
    model_total = TotalGoalsXGBoostModel(PROJECT_ROOT)
    model_score = ScorelineXGBoostModel(PROJECT_ROOT)
    model_volatile = VolatileScorelineXGBoostModel(PROJECT_ROOT)
    
    # 检查状态
    status_total = model_total.get_training_status()
    status_score = model_score.get_training_status()
    status_volatile = model_volatile.get_training_status()
    
    print("\n📊 模型状态:")
    print(f"  Total Goals: {'✅ 就绪' if status_total['model_ready'] else '❌ 未就绪'}")
    print(f"    - 样本数: {status_total['sample_count']:,}")
    print(f"    - 类别数: {len(status_total.get('class_names', []))}")
    
    print(f"\n  Scoreline: {'✅ 就绪' if status_score['model_ready'] else '❌ 未就绪'}")
    print(f"    - 样本数: {status_score['sample_count']:,}")
    print(f"    - 类别数: {len(status_score.get('class_names', []))}")
    
    print(f"\n  Volatile Scoreline: {'✅ 就绪' if status_volatile['model_ready'] else '❌ 未就绪'}")
    print(f"    - 样本数: {status_volatile['sample_count']:,}")
    print(f"    - 可用样本: {status_volatile.get('usable_count', 0):,}")
    print(f"    - 类别数: {len(status_volatile.get('class_names', []))}")
    
    # 创建测试特征
    test_features = {
        "market_home": 0.65,
        "market_draw": 0.25,
        "market_away": 0.10,
        "odds_home": 1.50,
        "odds_draw": 4.00,
        "odds_away": 7.00,
        "home_rating": 1800.0,
        "away_rating": 1400.0,
        "rating_diff": 400.0,
        "rating_gap_abs": 400.0,
        "league_strength": 0.75,
        "match_minutes": 900.0,
        "is_weekend": 0.0,
        "opening_odds_home": 1.55,
        "opening_odds_draw": 4.20,
        "opening_odds_away": 6.50,
        "return_rate": 0.93,
        "market_overround": 1.07,
        "home_odds_drop": 0.05,
        "draw_odds_drop": -0.20,
        "away_odds_drop": 0.50,
        "kelly_home": 0.05,
        "kelly_draw": -0.02,
        "kelly_away": -0.03,
        "kelly_draw_edge": -0.02,
        "market_balance": 0.55,
        "home_recent_match_count": 5.0,
        "away_recent_match_count": 5.0,
        "home_recent_points_pg": 2.2,
        "away_recent_points_pg": 1.0,
        "recent_points_diff": 1.2,
        "home_recent_goal_diff_pg": 1.4,
        "away_recent_goal_diff_pg": -0.6,
        "recent_goal_diff_diff": 2.0,
        "home_recent_goals_for_pg": 2.4,
        "away_recent_goals_for_pg": 1.0,
        "home_recent_win_rate": 0.80,
        "away_recent_win_rate": 0.20,
    }
    
    print("\n🎯 预测测试 (强队主场 vs 弱队):")
    
    # Total Goals 预测
    print("\n  📈 总进球数预测:")
    start = time.time()
    result_total = model_total.predict_from_features(test_features)
    elapsed_total = (time.time() - start) * 1000
    
    if result_total['model_ready']:
        print(f"    推荐: {result_total['label']} 球 (置信度: {result_total['confidence']:.2%})")
        print(f"    预测时间: {elapsed_total:.2f} ms")
        
        # 显示 Top 5 概率
        probs = result_total['probabilities']
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"    Top 5 概率:")
        for goal, prob in sorted_probs:
            print(f"      {goal} 球: {prob:.2%}")
    else:
        print(f"    ❌ 模型未就绪")
    
    # Scoreline 预测
    print("\n  ⚽ 比分预测:")
    start = time.time()
    result_score = model_score.predict_from_features(test_features)
    elapsed_score = (time.time() - start) * 1000
    
    if result_score['model_ready']:
        print(f"    推荐: {result_score['label']} (置信度: {result_score['confidence']:.2%})")
        print(f"    预测时间: {elapsed_score:.2f} ms")
        
        # 显示 Top 5 概率
        probs = result_score['probabilities']
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"    Top 5 概率:")
        for score, prob in sorted_probs:
            print(f"      {score}: {prob:.2%}")
    else:
        print(f"    ❌ 模型未就绪")
    
    # Volatile Scoreline 预测
    print("\n  💥 大比分预测:")
    start = time.time()
    result_volatile = model_volatile.predict_from_features(test_features)
    elapsed_volatile = (time.time() - start) * 1000
    
    if result_volatile['model_ready']:
        print(f"    推荐: {result_volatile['label']} (置信度: {result_volatile['confidence']:.2%})")
        print(f"    预测时间: {elapsed_volatile:.2f} ms")
        
        # 显示 Top 5 概率
        probs = result_volatile['probabilities']
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"    Top 5 概率:")
        for score, prob in sorted_probs:
            print(f"      {score}: {prob:.2%}")
    else:
        print(f"    ❌ 模型未就绪")


def test_prediction_speed():
    """测试预测速度"""
    print_section("预测速度基准测试")
    
    model_v0 = XGBoostProbabilityModel(PROJECT_ROOT)
    
    # 创建测试上下文
    context = EnsembleContext(
        home_rating=1600.0,
        away_rating=1600.0,
        league_strength=0.70,
        market_probs=(0.40, 0.30, 0.30),
        market_draw_prob=0.30,
        metadata={
            "odds_home": 2.40,
            "odds_draw": 3.20,
            "odds_away": 2.80,
            "match_time": "15:00",
            "match_date": "2026-05-29",
        }
    )
    
    # 预热
    for _ in range(10):
        model_v0.predict(context)
    
    # 基准测试
    iterations = 1000
    print(f"\n执行 {iterations} 次预测...")
    
    start = time.time()
    for _ in range(iterations):
        model_v0.predict(context)
    elapsed = time.time() - start
    
    avg_time = (elapsed / iterations) * 1000
    qps = iterations / elapsed
    
    print(f"\n📊 性能指标:")
    print(f"  总耗时: {elapsed:.2f} 秒")
    print(f"  平均延迟: {avg_time:.2f} ms")
    print(f"  吞吐量: {qps:.0f} QPS (每秒查询数)")
    print(f"  单核理论峰值: ~{qps:.0f} 预测/秒")


def main():
    """主测试流程"""
    print("\n" + "="*70)
    print("  模型预测效果测试")
    print("="*70)
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  项目路径: {PROJECT_ROOT}")
    
    try:
        # 测试 1X2 模型
        test_1x2_models()
        
        # 测试玩法模型
        test_play_models()
        
        # 测试预测速度
        test_prediction_speed()
        
        print("\n" + "="*70)
        print("  ✅ 所有测试完成")
        print("="*70)
        print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as exc:
        print(f"\n❌ 测试失败: {exc}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
