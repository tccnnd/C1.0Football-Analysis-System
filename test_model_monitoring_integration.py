"""
测试模型监控集成

验证监控系统是否正确集成到模型预测中。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from v24_app.models.ensemble import EnsembleContext
from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
from v24_app.models.play_xgboost import (
    TotalGoalsXGBoostModel,
    ScorelineXGBoostModel,
    VolatileScorelineXGBoostModel,
)
from v24_app.model_monitoring import get_monitor


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_xgboost_v0_monitoring():
    """测试 XGBoost V0 模型监控"""
    print_section("测试 XGBoost V0 模型监控")
    
    # 创建测试上下文
    context = EnsembleContext(
        market_probs=(0.45, 0.30, 0.25),
        home_rating=1500.0,
        away_rating=1450.0,
        market_draw_prob=0.30,
        league_strength=0.95,
        metadata={
            "odds_home": 2.20,
            "odds_draw": 3.10,
            "odds_away": 2.80,
            "match_time": "20:00",
            "match_date": "2026-05-29",
            "opening_odds_home": 2.15,
            "opening_odds_draw": 3.20,
            "opening_odds_away": 2.90,
            "return_rate": 0.93,
            "kelly_home": 0.02,
            "kelly_draw": -0.01,
            "kelly_away": 0.01,
        },
    )
    
    # 创建模型实例
    model = XGBoostProbabilityModel(PROJECT_ROOT)
    
    # 执行预测
    print("\n执行 3 次预测...")
    for i in range(3):
        result = model.predict(context)
        print(f"  预测 {i+1}: {result.probabilities}")
        time.sleep(0.1)
    
    # 检查监控数据
    monitor = get_monitor()
    health = monitor.get_model_health("xgboost_v0")
    
    print(f"\n监控数据:")
    print(f"  模型名称: xgboost_v0")
    print(f"  总预测数: {health.total_predictions}")
    print(f"  平均延迟: {health.avg_latency_ms:.2f} ms")
    print(f"  错误数: {health.error_count}")
    print(f"  错误率: {health.error_rate:.2%}")
    print(f"  最后预测: {health.last_prediction_time}")
    
    # 获取延迟百分位数
    percentiles = monitor.get_latency_percentiles("xgboost_v0")
    print(f"\n延迟百分位数:")
    print(f"  P50: {percentiles['p50']:.2f} ms")
    print(f"  P90: {percentiles['p90']:.2f} ms")
    print(f"  P95: {percentiles['p95']:.2f} ms")
    print(f"  P99: {percentiles['p99']:.2f} ms")
    
    # 获取置信度统计
    conf_stats = monitor.get_confidence_stats("xgboost_v0")
    print(f"\n置信度统计:")
    print(f"  平均: {conf_stats['avg']:.2%}")
    print(f"  最小: {conf_stats['min']:.2%}")
    print(f"  最大: {conf_stats['max']:.2%}")
    print(f"  标准差: {conf_stats['std']:.4f}")
    
    # 验证
    assert health.total_predictions >= 3, "预测数应该 >= 3"
    assert health.avg_latency_ms > 0, "平均延迟应该 > 0"
    assert health.error_rate == 0, "错误率应该为 0"
    
    print("\n✅ XGBoost V0 监控测试通过")


def test_play_models_monitoring():
    """测试 Play 模型监控"""
    print_section("测试 Play 模型监控")
    
    # 创建测试特征
    feature_map = {
        "market_home": 0.45,
        "market_draw": 0.30,
        "market_away": 0.25,
        "odds_home": 2.20,
        "odds_draw": 3.10,
        "odds_away": 2.80,
        "home_rating": 1500.0,
        "away_rating": 1450.0,
        "rating_diff": 50.0,
        "rating_gap_abs": 50.0,
        "league_strength": 0.95,
        "match_minutes": 1200.0,
        "is_weekend": 1.0,
        "opening_odds_home": 2.15,
        "opening_odds_draw": 3.20,
        "opening_odds_away": 2.90,
        "return_rate": 0.93,
        "market_overround": 1.07,
        "home_odds_drop": 0.05,
        "draw_odds_drop": -0.10,
        "away_odds_drop": -0.10,
        "kelly_home": 0.02,
        "kelly_draw": -0.01,
        "kelly_away": 0.01,
        "kelly_draw_edge": -0.01,
        "market_balance": 0.20,
        "home_recent_match_count": 5.0,
        "away_recent_match_count": 5.0,
        "home_recent_points_pg": 1.8,
        "away_recent_points_pg": 1.6,
        "recent_points_diff": 0.2,
        "home_recent_goal_diff_pg": 0.6,
        "away_recent_goal_diff_pg": 0.4,
        "recent_goal_diff_diff": 0.2,
        "home_recent_goals_for_pg": 1.8,
        "away_recent_goals_for_pg": 1.5,
        "home_recent_win_rate": 0.60,
        "away_recent_win_rate": 0.50,
    }
    
    # 测试总进球模型
    print("\n测试总进球模型...")
    total_goals_model = TotalGoalsXGBoostModel(PROJECT_ROOT)
    for i in range(2):
        result = total_goals_model.predict_from_features(feature_map)
        print(f"  预测 {i+1}: 标签={result.get('label')}, 置信度={result.get('confidence', 0):.2%}")
        time.sleep(0.1)
    
    # 测试比分模型
    print("\n测试比分模型...")
    scoreline_model = ScorelineXGBoostModel(PROJECT_ROOT)
    for i in range(2):
        result = scoreline_model.predict_from_features(feature_map)
        print(f"  预测 {i+1}: 标签={result.get('label')}, 置信度={result.get('confidence', 0):.2%}")
        time.sleep(0.1)
    
    # 测试波动比分模型
    print("\n测试波动比分模型...")
    volatile_model = VolatileScorelineXGBoostModel(PROJECT_ROOT)
    for i in range(2):
        result = volatile_model.predict_from_features(feature_map)
        print(f"  预测 {i+1}: 标签={result.get('label')}, 置信度={result.get('confidence', 0):.2%}")
        time.sleep(0.1)
    
    # 检查监控数据
    monitor = get_monitor()
    
    models = [
        "xgb_v1_total_goals",
        "xgb_v1_scoreline",
        "xgb_v1_scoreline_volatile",
    ]
    
    print("\n监控数据汇总:")
    for model_name in models:
        health = monitor.get_model_health(model_name)
        print(f"\n  {model_name}:")
        print(f"    总预测数: {health.total_predictions}")
        print(f"    平均延迟: {health.avg_latency_ms:.2f} ms")
        print(f"    错误率: {health.error_rate:.2%}")
        
        # 验证
        assert health.total_predictions >= 2, f"{model_name} 预测数应该 >= 2"
        assert health.avg_latency_ms > 0, f"{model_name} 平均延迟应该 > 0"
    
    print("\n✅ Play 模型监控测试通过")


def test_system_metrics():
    """测试系统指标"""
    print_section("测试系统指标")
    
    monitor = get_monitor()
    system = monitor.get_system_metrics()
    
    print(f"\n系统指标:")
    print(f"  时间戳: {system.timestamp}")
    print(f"  内存使用: {system.memory_mb:.2f} MB")
    print(f"  CPU 使用: {system.cpu_percent:.1f}%")
    print(f"  活跃模型: {system.active_models}")
    print(f"  总预测数: {system.total_predictions}")
    print(f"  平均延迟: {system.avg_latency_ms:.2f} ms")
    
    # 验证
    assert system.active_models > 0, "活跃模型数应该 > 0"
    assert system.total_predictions > 0, "总预测数应该 > 0"
    
    print("\n✅ 系统指标测试通过")


def test_alerts():
    """测试告警系统"""
    print_section("测试告警系统")
    
    monitor = get_monitor()
    alerts = monitor.get_alerts()
    
    print(f"\n当前告警数: {len(alerts)}")
    
    if alerts:
        print("\n告警详情:")
        for alert in alerts:
            level_icon = "❌" if alert["level"] == "critical" else "⚠️"
            print(f"  {level_icon} [{alert['model']}] {alert['message']}")
    else:
        print("\n✅ 无告警，系统运行正常")
    
    print("\n✅ 告警系统测试通过")


def test_recent_predictions():
    """测试最近预测记录"""
    print_section("测试最近预测记录")
    
    monitor = get_monitor()
    predictions = monitor.get_recent_predictions(limit=5)
    
    print(f"\n最近 {len(predictions)} 次预测:")
    for i, pred in enumerate(predictions, 1):
        print(f"\n  {i}. {pred.model_name}")
        print(f"     时间: {pred.timestamp}")
        print(f"     延迟: {pred.latency_ms:.2f} ms")
        print(f"     置信度: {pred.confidence:.2%}")
        print(f"     特征数: {pred.features_count}")
    
    # 验证
    assert len(predictions) > 0, "应该有预测记录"
    
    print("\n✅ 最近预测记录测试通过")


def test_export_metrics():
    """测试指标导出"""
    print_section("测试指标导出")
    
    monitor = get_monitor()
    output_file = monitor.export_metrics()
    
    print(f"\n指标已导出到: {output_file}")
    print(f"文件大小: {output_file.stat().st_size / 1024:.2f} KB")
    
    # 验证文件存在
    assert output_file.exists(), "导出文件应该存在"
    assert output_file.stat().st_size > 0, "导出文件应该有内容"
    
    print("\n✅ 指标导出测试通过")


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("  模型监控集成测试")
    print("=" * 80)
    print(f"\n项目根目录: {PROJECT_ROOT}")
    
    try:
        # 运行所有测试
        test_xgboost_v0_monitoring()
        test_play_models_monitoring()
        test_system_metrics()
        test_alerts()
        test_recent_predictions()
        test_export_metrics()
        
        # 总结
        print_section("测试总结")
        print("\n✅ 所有测试通过！")
        print("\n监控系统已成功集成到模型预测中。")
        print("\n下一步:")
        print("  1. 启动应用程序进行实际预测")
        print("  2. 运行监控仪表板查看实时数据:")
        print("     python model_monitoring_dashboard.py --continuous --details")
        print("  3. 查看日志文件:")
        print("     logs/model_monitoring/predictions.jsonl")
        print("     logs/model_monitoring/errors.jsonl")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
