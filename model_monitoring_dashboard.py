"""
模型监控仪表板

实时显示模型性能和系统健康状态。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from v24_app.model_monitoring import get_monitor


def print_header(title: str):
    """打印标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_system_metrics(monitor):
    """打印系统指标"""
    print_header("系统指标")
    
    system = monitor.get_system_metrics()
    
    print(f"\n时间: {datetime.fromisoformat(system.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"内存使用: {system.memory_mb:.2f} MB")
    print(f"CPU 使用: {system.cpu_percent:.1f}%")
    print(f"活跃模型: {system.active_models}")
    print(f"总预测数: {system.total_predictions}")
    print(f"平均延迟: {system.avg_latency_ms:.2f} ms")


def print_model_health(monitor):
    """打印模型健康状态"""
    print_header("模型健康状态")
    
    models = monitor.get_all_models_health()
    
    if not models:
        print("\n暂无模型数据")
        return
    
    # 表头
    print(f"\n{'模型':<30} {'状态':<8} {'预测数':<10} {'平均延迟':<12} {'错误率':<10}")
    print("-" * 80)
    
    for health in models:
        status = "✅ 正常" if health.is_loaded else "❌ 未加载"
        
        # 延迟状态
        if health.avg_latency_ms < 10:
            latency_str = f"{health.avg_latency_ms:.2f} ms ⚡"
        elif health.avg_latency_ms < 50:
            latency_str = f"{health.avg_latency_ms:.2f} ms ✅"
        else:
            latency_str = f"{health.avg_latency_ms:.2f} ms ⚠️"
        
        # 错误率状态
        if health.error_rate == 0:
            error_str = "0.00% ✅"
        elif health.error_rate < 0.01:
            error_str = f"{health.error_rate:.2%} ✅"
        elif health.error_rate < 0.05:
            error_str = f"{health.error_rate:.2%} ⚠️"
        else:
            error_str = f"{health.error_rate:.2%} ❌"
        
        print(f"{health.model_name:<30} {status:<8} {health.total_predictions:<10} {latency_str:<12} {error_str:<10}")


def print_model_details(monitor):
    """打印模型详细信息"""
    print_header("模型详细信息")
    
    models = monitor.get_all_models_health()
    
    for health in models:
        if health.total_predictions == 0:
            continue
        
        print(f"\n📊 {health.model_name}")
        print("-" * 80)
        
        # 基本信息
        print(f"  总预测数: {health.total_predictions}")
        print(f"  错误数: {health.error_count}")
        print(f"  最后预测: {health.last_prediction_time}")
        
        # 延迟百分位数
        percentiles = monitor.get_latency_percentiles(health.model_name)
        print(f"\n  延迟百分位数:")
        print(f"    P50: {percentiles['p50']:.2f} ms")
        print(f"    P90: {percentiles['p90']:.2f} ms")
        print(f"    P95: {percentiles['p95']:.2f} ms")
        print(f"    P99: {percentiles['p99']:.2f} ms")
        
        # 置信度统计
        conf_stats = monitor.get_confidence_stats(health.model_name)
        print(f"\n  置信度统计:")
        print(f"    平均: {conf_stats['avg']:.2%}")
        print(f"    最小: {conf_stats['min']:.2%}")
        print(f"    最大: {conf_stats['max']:.2%}")
        print(f"    标准差: {conf_stats['std']:.4f}")
        
        # 预测速率
        rate = monitor.get_prediction_rate(health.model_name)
        print(f"\n  预测速率: {rate:.2f} 预测/秒")


def print_recent_predictions(monitor, limit: int = 5):
    """打印最近的预测"""
    print_header(f"最近 {limit} 次预测")
    
    predictions = monitor.get_recent_predictions(limit=limit)
    
    if not predictions:
        print("\n暂无预测数据")
        return
    
    for i, pred in enumerate(predictions, 1):
        timestamp = datetime.fromisoformat(pred.timestamp).strftime('%H:%M:%S')
        print(f"\n{i}. [{timestamp}] {pred.model_name}")
        print(f"   延迟: {pred.latency_ms:.2f} ms")
        print(f"   置信度: {pred.confidence:.2%}")
        print(f"   特征数: {pred.features_count}")
        
        # 显示预测结果（简化）
        if isinstance(pred.prediction, dict):
            pred_str = ", ".join(f"{k}: {v:.2%}" if isinstance(v, float) else f"{k}: {v}" 
                                for k, v in list(pred.prediction.items())[:3])
            print(f"   预测: {pred_str}")


def print_alerts(monitor):
    """打印告警"""
    print_header("系统告警")
    
    alerts = monitor.get_alerts()
    
    if not alerts:
        print("\n✅ 无告警，系统运行正常")
        return
    
    # 按级别分组
    critical = [a for a in alerts if a["level"] == "critical"]
    warning = [a for a in alerts if a["level"] == "warning"]
    
    if critical:
        print(f"\n❌ 严重告警 ({len(critical)}):")
        for alert in critical:
            print(f"  - [{alert['model']}] {alert['message']}")
    
    if warning:
        print(f"\n⚠️ 警告 ({len(warning)}):")
        for alert in warning:
            print(f"  - [{alert['model']}] {alert['message']}")


def print_dashboard(monitor, show_details: bool = False):
    """打印完整仪表板"""
    # 清屏（可选）
    # print("\033[2J\033[H")
    
    print("\n" + "="*80)
    print("  模型监控仪表板")
    print("="*80)
    print(f"  更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 系统指标
    print_system_metrics(monitor)
    
    # 模型健康
    print_model_health(monitor)
    
    # 告警
    print_alerts(monitor)
    
    # 详细信息（可选）
    if show_details:
        print_model_details(monitor)
        print_recent_predictions(monitor)
    
    print("\n" + "="*80)


def run_continuous(interval: int = 10, show_details: bool = False):
    """持续监控"""
    monitor = get_monitor(PROJECT_ROOT)
    
    print("\n开始持续监控...")
    print(f"刷新间隔: {interval} 秒")
    print("按 Ctrl+C 停止\n")
    
    try:
        while True:
            print_dashboard(monitor, show_details=show_details)
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n监控已停止。")


def run_once(show_details: bool = True):
    """运行一次"""
    monitor = get_monitor(PROJECT_ROOT)
    print_dashboard(monitor, show_details=show_details)


def export_metrics():
    """导出指标"""
    monitor = get_monitor(PROJECT_ROOT)
    output_file = monitor.export_metrics()
    
    print(f"\n✅ 指标已导出到: {output_file}")
    print(f"   文件大小: {output_file.stat().st_size / 1024:.2f} KB")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="模型监控仪表板")
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="持续监控模式",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="刷新间隔（秒），默认 10",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="显示详细信息",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="导出指标到文件",
    )
    
    args = parser.parse_args()
    
    if args.export:
        export_metrics()
    elif args.continuous:
        run_continuous(interval=args.interval, show_details=args.details)
    else:
        run_once(show_details=args.details)


if __name__ == "__main__":
    main()
