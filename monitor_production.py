"""
生产环境监控脚本

监控关键性能指标和系统健康状态。
"""
from __future__ import annotations

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from collections import deque

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class ProductionMonitor:
    """生产监控器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.metrics_history = {
            "prediction_latency": deque(maxlen=100),
            "memory_usage": deque(maxlen=100),
            "cpu_usage": deque(maxlen=100),
        }
        self.alert_count = 0
    
    def check_model_status(self) -> dict:
        """检查模型状态"""
        try:
            from v24_app import core
            
            models = {
                "XGBoost V0": core.XGBOOST_MODEL,
                "Total Goals": core.TOTAL_GOALS_MODEL,
                "Scoreline": core.SCORELINE_MODEL,
                "Volatile Scoreline": core.VOLATILE_SCORELINE_MODEL,
            }
            
            status = {}
            for name, model in models.items():
                with model._model_lock:
                    loaded = model._model is not None
                status[name] = "✅ 已加载" if loaded else "❌ 未加载"
            
            return status
        
        except Exception as exc:
            return {"error": str(exc)}
    
    def check_prediction_latency(self) -> dict:
        """检查预测延迟"""
        try:
            from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
            from v24_app.models.ensemble import EnsembleContext
            
            model = XGBoostProbabilityModel(self.project_root)
            
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
                }
            )
            
            # 测试 10 次取平均
            latencies = []
            for _ in range(10):
                start = time.time()
                model.predict(context)
                latency = (time.time() - start) * 1000
                latencies.append(latency)
            
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            self.metrics_history["prediction_latency"].append(avg_latency)
            
            return {
                "avg": avg_latency,
                "min": min_latency,
                "max": max_latency,
                "status": "✅" if avg_latency < 10.0 else "⚠️" if avg_latency < 50.0 else "❌",
            }
        
        except Exception as exc:
            return {"error": str(exc)}
    
    def check_system_resources(self) -> dict:
        """检查系统资源"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # 内存使用
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)
            
            # CPU 使用
            cpu_percent = process.cpu_percent(interval=0.1)
            
            self.metrics_history["memory_usage"].append(mem_mb)
            self.metrics_history["cpu_usage"].append(cpu_percent)
            
            return {
                "memory_mb": mem_mb,
                "memory_status": "✅" if mem_mb < 500 else "⚠️" if mem_mb < 1000 else "❌",
                "cpu_percent": cpu_percent,
                "cpu_status": "✅" if cpu_percent < 50 else "⚠️" if cpu_percent < 80 else "❌",
            }
        
        except Exception as exc:
            return {"error": str(exc)}
    
    def check_model_files(self) -> dict:
        """检查模型文件"""
        model_dir = self.project_root / "data" / "models"
        required_models = [
            "xgb_v0_match_outcome.json",
            "xgb_xg_match_outcome.json",
            "xgb_v1_total_goals.json",
            "xgb_v1_scoreline.json",
            "xgb_v1_scoreline_volatile.json",
        ]
        
        status = {}
        for model_file in required_models:
            model_path = model_dir / model_file
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                status[model_file] = f"✅ {size_mb:.2f} MB"
            else:
                status[model_file] = "❌ 不存在"
        
        return status
    
    def print_dashboard(self):
        """打印监控仪表板"""
        print("\n" + "="*70)
        print(f"  生产环境监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 模型状态
        print("\n📊 模型状态:")
        model_status = self.check_model_status()
        for name, status in model_status.items():
            print(f"  {name}: {status}")
        
        # 预测延迟
        print("\n⚡ 预测延迟:")
        latency = self.check_prediction_latency()
        if "error" in latency:
            print(f"  ❌ 错误: {latency['error']}")
        else:
            print(f"  {latency['status']} 平均: {latency['avg']:.2f} ms")
            print(f"     最小: {latency['min']:.2f} ms")
            print(f"     最大: {latency['max']:.2f} ms")
        
        # 系统资源
        print("\n💻 系统资源:")
        resources = self.check_system_resources()
        if "error" in resources:
            print(f"  ❌ 错误: {resources['error']}")
        else:
            print(f"  {resources['memory_status']} 内存: {resources['memory_mb']:.2f} MB")
            print(f"  {resources['cpu_status']} CPU: {resources['cpu_percent']:.1f}%")
        
        # 模型文件
        print("\n📁 模型文件:")
        files = self.check_model_files()
        for name, status in files.items():
            print(f"  {status} {name}")
        
        # 历史趋势
        if len(self.metrics_history["prediction_latency"]) > 1:
            print("\n📈 历史趋势 (最近 100 次):")
            
            latencies = list(self.metrics_history["prediction_latency"])
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                print(f"  预测延迟平均: {avg_latency:.2f} ms")
            
            memories = list(self.metrics_history["memory_usage"])
            if memories:
                avg_memory = sum(memories) / len(memories)
                print(f"  内存使用平均: {avg_memory:.2f} MB")
            
            cpus = list(self.metrics_history["cpu_usage"])
            if cpus:
                avg_cpu = sum(cpus) / len(cpus)
                print(f"  CPU 使用平均: {avg_cpu:.1f}%")
        
        # 告警
        alerts = []
        if "error" not in latency and latency["avg"] > 50.0:
            alerts.append("预测延迟过高")
        if "error" not in resources and resources["memory_mb"] > 1000:
            alerts.append("内存使用过高")
        if "error" not in resources and resources["cpu_percent"] > 80:
            alerts.append("CPU 使用过高")
        
        if alerts:
            print("\n⚠️ 告警:")
            for alert in alerts:
                print(f"  - {alert}")
            self.alert_count += 1
        else:
            print("\n✅ 系统运行正常")
        
        print("\n" + "="*70)
    
    def save_metrics(self):
        """保存指标到文件"""
        metrics_file = self.project_root / "logs" / "production_metrics.jsonl"
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "model_status": self.check_model_status(),
            "prediction_latency": self.check_prediction_latency(),
            "system_resources": self.check_system_resources(),
        }
        
        with open(metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    
    def run_continuous(self, interval: int = 60):
        """持续监控"""
        print("\n开始持续监控...")
        print(f"监控间隔: {interval} 秒")
        print("按 Ctrl+C 停止\n")
        
        try:
            while True:
                self.print_dashboard()
                self.save_metrics()
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\n监控已停止。")
            print(f"总告警次数: {self.alert_count}")
    
    def run_once(self):
        """运行一次检查"""
        self.print_dashboard()
        self.save_metrics()


def main():
    """主监控流程"""
    import argparse
    
    parser = argparse.ArgumentParser(description="生产环境监控")
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="持续监控模式",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="监控间隔（秒），默认 60",
    )
    
    args = parser.parse_args()
    
    monitor = ProductionMonitor(PROJECT_ROOT)
    
    if args.continuous:
        monitor.run_continuous(interval=args.interval)
    else:
        monitor.run_once()


if __name__ == "__main__":
    main()
