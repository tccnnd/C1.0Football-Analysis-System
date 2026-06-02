"""
模型监控模块

提供模型性能、预测质量和系统健康的可观测性。
"""
from __future__ import annotations

import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Optional
from threading import RLock


@dataclass
class PredictionMetrics:
    """预测指标"""
    timestamp: str
    model_name: str
    latency_ms: float
    prediction: dict
    confidence: float
    features_count: int
    model_version: Optional[str] = None


@dataclass
class ModelHealthMetrics:
    """模型健康指标"""
    model_name: str
    is_loaded: bool
    last_prediction_time: Optional[str]
    total_predictions: int
    avg_latency_ms: float
    error_count: int
    error_rate: float


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: str
    memory_mb: float
    cpu_percent: float
    active_models: int
    total_predictions: int
    avg_latency_ms: float


class ModelMonitor:
    """模型监控器"""
    
    def __init__(self, project_root: Path, history_size: int = 1000):
        self.project_root = project_root
        self.history_size = history_size
        
        # 指标存储
        self.prediction_history: deque = deque(maxlen=history_size)
        self.model_stats: dict[str, dict] = defaultdict(lambda: {
            "total_predictions": 0,
            "total_latency": 0.0,
            "error_count": 0,
            "last_prediction_time": None,
            "latency_history": deque(maxlen=100),
            "confidence_history": deque(maxlen=100),
        })
        
        # 线程安全（使用可重入锁，避免同一线程内嵌套调用死锁）
        self._lock = RLock()
        
        # 日志目录
        self.log_dir = project_root / "logs" / "model_monitoring"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def record_prediction(
        self,
        model_name: str,
        latency_ms: float,
        prediction: dict,
        confidence: float,
        features_count: int,
        model_version: Optional[str] = None,
    ):
        """记录预测"""
        with self._lock:
            # 创建指标
            metrics = PredictionMetrics(
                timestamp=datetime.now().isoformat(),
                model_name=model_name,
                latency_ms=latency_ms,
                prediction=prediction,
                confidence=confidence,
                features_count=features_count,
                model_version=model_version,
            )
            
            # 添加到历史
            self.prediction_history.append(metrics)
            
            # 更新统计
            stats = self.model_stats[model_name]
            stats["total_predictions"] += 1
            stats["total_latency"] += latency_ms
            stats["last_prediction_time"] = metrics.timestamp
            stats["latency_history"].append(latency_ms)
            stats["confidence_history"].append(confidence)
            
            # 写入日志
            self._write_prediction_log(metrics)
    
    def record_error(self, model_name: str, error: str):
        """记录错误"""
        with self._lock:
            stats = self.model_stats[model_name]
            stats["error_count"] += 1
            
            # 写入错误日志
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "model_name": model_name,
                "error": error,
            }
            
            error_file = self.log_dir / "errors.jsonl"
            with open(error_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_log, ensure_ascii=False) + "\n")
    
    def get_model_health(self, model_name: str) -> ModelHealthMetrics:
        """获取模型健康指标"""
        with self._lock:
            stats = self.model_stats[model_name]
            
            total_predictions = stats["total_predictions"]
            error_count = stats["error_count"]
            
            avg_latency = (
                stats["total_latency"] / total_predictions
                if total_predictions > 0
                else 0.0
            )
            
            error_rate = (
                error_count / (total_predictions + error_count)
                if (total_predictions + error_count) > 0
                else 0.0
            )
            
            return ModelHealthMetrics(
                model_name=model_name,
                is_loaded=total_predictions > 0,
                last_prediction_time=stats["last_prediction_time"],
                total_predictions=total_predictions,
                avg_latency_ms=avg_latency,
                error_count=error_count,
                error_rate=error_rate,
            )
    
    def get_all_models_health(self) -> list[ModelHealthMetrics]:
        """获取所有模型健康指标"""
        with self._lock:
            return [
                self.get_model_health(model_name)
                for model_name in self.model_stats.keys()
            ]
    
    def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            # interval=None 使用上次调用以来的 CPU 时间，避免阻塞
            cpu_percent = process.cpu_percent(interval=None)
        except Exception:
            memory_mb = 0.0
            cpu_percent = 0.0
        
        with self._lock:
            total_predictions = sum(
                stats["total_predictions"]
                for stats in self.model_stats.values()
            )
            
            total_latency = sum(
                stats["total_latency"]
                for stats in self.model_stats.values()
            )
            
            avg_latency = (
                total_latency / total_predictions
                if total_predictions > 0
                else 0.0
            )
            
            active_models = sum(
                1 for stats in self.model_stats.values()
                if stats["total_predictions"] > 0
            )
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                active_models=active_models,
                total_predictions=total_predictions,
                avg_latency_ms=avg_latency,
            )
    
    def get_latency_percentiles(
        self,
        model_name: str,
        percentiles: list[int] = [50, 90, 95, 99],
    ) -> dict[str, float]:
        """获取延迟百分位数"""
        with self._lock:
            stats = self.model_stats[model_name]
            latencies = list(stats["latency_history"])
            
            if not latencies:
                return {f"p{p}": 0.0 for p in percentiles}
            
            latencies.sort()
            result = {}
            
            for p in percentiles:
                index = int(len(latencies) * p / 100)
                index = min(index, len(latencies) - 1)
                result[f"p{p}"] = latencies[index]
            
            return result
    
    def get_confidence_stats(self, model_name: str) -> dict[str, float]:
        """获取置信度统计"""
        with self._lock:
            stats = self.model_stats[model_name]
            confidences = list(stats["confidence_history"])
            
            if not confidences:
                return {
                    "avg": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "std": 0.0,
                }
            
            avg = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            max_conf = max(confidences)
            
            # 计算标准差
            variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
            std = variance ** 0.5
            
            return {
                "avg": avg,
                "min": min_conf,
                "max": max_conf,
                "std": std,
            }
    
    def get_recent_predictions(
        self,
        model_name: Optional[str] = None,
        limit: int = 10,
    ) -> list[PredictionMetrics]:
        """获取最近的预测"""
        with self._lock:
            predictions = list(self.prediction_history)
            
            if model_name:
                predictions = [
                    p for p in predictions
                    if p.model_name == model_name
                ]
            
            return predictions[-limit:]
    
    def get_prediction_rate(
        self,
        model_name: Optional[str] = None,
        window_seconds: int = 60,
    ) -> float:
        """获取预测速率（每秒预测数）"""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=window_seconds)
            
            predictions = [
                p for p in self.prediction_history
                if datetime.fromisoformat(p.timestamp) > cutoff
            ]
            
            if model_name:
                predictions = [
                    p for p in predictions
                    if p.model_name == model_name
                ]
            
            return len(predictions) / window_seconds if window_seconds > 0 else 0.0
    
    def get_dashboard_data(self) -> dict:
        """获取仪表板数据"""
        system_metrics = self.get_system_metrics()
        models_health = self.get_all_models_health()
        
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "system": asdict(system_metrics),
            "models": [],
        }
        
        for health in models_health:
            model_data = asdict(health)
            
            # 添加延迟百分位数
            model_data["latency_percentiles"] = self.get_latency_percentiles(
                health.model_name
            )
            
            # 添加置信度统计
            model_data["confidence_stats"] = self.get_confidence_stats(
                health.model_name
            )
            
            # 添加预测速率
            model_data["prediction_rate"] = self.get_prediction_rate(
                health.model_name
            )
            
            dashboard["models"].append(model_data)
        
        return dashboard
    
    def export_metrics(self, output_file: Optional[Path] = None) -> Path:
        """导出指标到文件"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.log_dir / f"metrics_export_{timestamp}.json"
        
        dashboard = self.get_dashboard_data()
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dashboard, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def _write_prediction_log(self, metrics: PredictionMetrics):
        """写入预测日志"""
        log_file = self.log_dir / "predictions.jsonl"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(metrics), ensure_ascii=False) + "\n")
    
    def clear_history(self):
        """清除历史数据"""
        with self._lock:
            self.prediction_history.clear()
            self.model_stats.clear()
    
    def get_alerts(self) -> list[dict]:
        """获取告警"""
        alerts = []
        
        for health in self.get_all_models_health():
            # 延迟告警
            if health.avg_latency_ms > 50.0:
                alerts.append({
                    "level": "warning" if health.avg_latency_ms < 100.0 else "critical",
                    "model": health.model_name,
                    "type": "high_latency",
                    "message": f"平均延迟过高: {health.avg_latency_ms:.2f} ms",
                    "value": health.avg_latency_ms,
                })
            
            # 错误率告警
            if health.error_rate > 0.01:
                alerts.append({
                    "level": "warning" if health.error_rate < 0.05 else "critical",
                    "model": health.model_name,
                    "type": "high_error_rate",
                    "message": f"错误率过高: {health.error_rate:.2%}",
                    "value": health.error_rate,
                })
            
            # 置信度告警
            conf_stats = self.get_confidence_stats(health.model_name)
            if conf_stats["avg"] < 0.5:
                alerts.append({
                    "level": "warning",
                    "model": health.model_name,
                    "type": "low_confidence",
                    "message": f"平均置信度过低: {conf_stats['avg']:.2%}",
                    "value": conf_stats["avg"],
                })
        
        # 系统告警
        system = self.get_system_metrics()
        
        if system.memory_mb > 1000:
            alerts.append({
                "level": "warning" if system.memory_mb < 2000 else "critical",
                "model": "system",
                "type": "high_memory",
                "message": f"内存使用过高: {system.memory_mb:.2f} MB",
                "value": system.memory_mb,
            })
        
        if system.cpu_percent > 80:
            alerts.append({
                "level": "warning" if system.cpu_percent < 95 else "critical",
                "model": "system",
                "type": "high_cpu",
                "message": f"CPU 使用过高: {system.cpu_percent:.1f}%",
                "value": system.cpu_percent,
            })
        
        return alerts


# 全局监控实例
_global_monitor: Optional[ModelMonitor] = None


def get_monitor(project_root: Optional[Path] = None) -> ModelMonitor:
    """获取全局监控实例"""
    global _global_monitor
    
    if _global_monitor is None:
        if project_root is None:
            from pathlib import Path
            project_root = Path(__file__).resolve().parents[2]
        
        _global_monitor = ModelMonitor(project_root)
    
    return _global_monitor


def record_prediction(
    model_name: str,
    latency_ms: float,
    prediction: dict,
    confidence: float,
    features_count: int,
    model_version: Optional[str] = None,
):
    """记录预测（便捷函数）"""
    monitor = get_monitor()
    monitor.record_prediction(
        model_name=model_name,
        latency_ms=latency_ms,
        prediction=prediction,
        confidence=confidence,
        features_count=features_count,
        model_version=model_version,
    )


def record_error(model_name: str, error: str):
    """记录错误（便捷函数）"""
    monitor = get_monitor()
    monitor.record_error(model_name, error)
