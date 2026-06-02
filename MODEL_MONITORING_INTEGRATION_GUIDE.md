# 模型监控集成指南

## 概述

模型监控系统已成功集成到 V24 分析系统中，提供实时的模型性能、预测质量和系统健康监控。

## 集成状态

### ✅ 已完成

1. **监控模块** (`src/v24_app/model_monitoring.py`)
   - PredictionMetrics: 预测指标数据类
   - ModelHealthMetrics: 模型健康指标数据类
   - SystemMetrics: 系统指标数据类
   - ModelMonitor: 核心监控器类
   - 全局监控实例和便捷函数

2. **监控仪表板** (`model_monitoring_dashboard.py`)
   - 实时系统指标显示
   - 模型健康状态表格
   - 详细模型统计（延迟百分位数、置信度统计）
   - 最近预测显示
   - 告警通知系统
   - 持续监控模式
   - 指标导出功能

3. **模型集成**
   - ✅ `xgboost_v0.py`: XGBoost V0 模型（1X2 预测）
   - ✅ `play_xgboost.py`: 所有 Play 模型（总进球、比分、波动比分）

## 监控功能

### 1. 预测指标记录

每次模型预测都会自动记录：
- 时间戳
- 模型名称
- 预测延迟（毫秒）
- 预测结果
- 置信度
- 特征数量
- 模型版本

### 2. 错误追踪

自动捕获和记录：
- 预测错误
- 模型加载失败
- 特征提取异常

### 3. 健康检查

实时监控：
- 模型加载状态
- 总预测数
- 平均延迟
- 错误计数和错误率
- 最后预测时间

### 4. 性能分析

提供详细的性能统计：
- 延迟百分位数（P50, P90, P95, P99）
- 置信度统计（平均、最小、最大、标准差）
- 预测速率（每秒预测数）

### 5. 告警系统

自动检测异常情况：
- 高延迟告警（>50ms 警告，>100ms 严重）
- 高错误率告警（>1% 警告，>5% 严重）
- 低置信度告警（<50% 警告）
- 高内存使用告警（>1GB 警告，>2GB 严重）
- 高 CPU 使用告警（>80% 警告，>95% 严重）

## 使用方法

### 1. 查看实时监控

```bash
# 单次查看（包含详细信息）
python model_monitoring_dashboard.py

# 持续监控（每 10 秒刷新）
python model_monitoring_dashboard.py --continuous

# 持续监控（自定义刷新间隔）
python model_monitoring_dashboard.py --continuous --interval 5

# 持续监控（包含详细信息）
python model_monitoring_dashboard.py --continuous --details
```

### 2. 导出监控数据

```bash
# 导出当前指标到 JSON 文件
python model_monitoring_dashboard.py --export
```

导出文件位置：`logs/model_monitoring/metrics_export_YYYYMMDD_HHMMSS.json`

### 3. 查看日志文件

监控日志自动保存到：
- 预测日志：`logs/model_monitoring/predictions.jsonl`
- 错误日志：`logs/model_monitoring/errors.jsonl`

每条日志都是一个 JSON 对象，可以使用任何 JSON 工具分析。

### 4. 在代码中使用监控

```python
from v24_app.model_monitoring import get_monitor, record_prediction, record_error

# 获取监控实例
monitor = get_monitor()

# 记录预测（已自动集成到模型中）
record_prediction(
    model_name="my_model",
    latency_ms=1.23,
    prediction={"home": 0.45, "draw": 0.30, "away": 0.25},
    confidence=0.45,
    features_count=38,
    model_version="v1",
)

# 记录错误
record_error("my_model", "Model loading failed")

# 获取模型健康状态
health = monitor.get_model_health("xgboost_v0")
print(f"Total predictions: {health.total_predictions}")
print(f"Average latency: {health.avg_latency_ms:.2f} ms")
print(f"Error rate: {health.error_rate:.2%}")

# 获取系统指标
system = monitor.get_system_metrics()
print(f"Memory: {system.memory_mb:.2f} MB")
print(f"CPU: {system.cpu_percent:.1f}%")

# 获取告警
alerts = monitor.get_alerts()
for alert in alerts:
    print(f"[{alert['level']}] {alert['model']}: {alert['message']}")
```

## 监控的模型

当前已集成监控的模型：

1. **xgboost_v0** - XGBoost V0 (1X2 预测)
2. **xgb_v1_total_goals** - 总进球预测
3. **xgb_v1_scoreline** - 比分预测
4. **xgb_v1_scoreline_volatile** - 波动比分预测

## 性能影响

监控系统设计为低开销：
- 预测记录：< 0.1ms 额外延迟
- 内存占用：默认保留最近 1000 条预测（可配置）
- 线程安全：使用锁保护共享数据
- 异步日志：不阻塞预测流程
- 失败隔离：监控失败不影响预测

## 配置选项

### 历史记录大小

```python
from v24_app.model_monitoring import ModelMonitor
from pathlib import Path

# 创建自定义监控实例（保留 5000 条历史）
monitor = ModelMonitor(
    project_root=Path("."),
    history_size=5000
)
```

### 告警阈值

可以在 `src/v24_app/model_monitoring.py` 中修改告警阈值：

```python
# 延迟告警阈值
if health.avg_latency_ms > 50.0:  # 修改这里
    alerts.append({...})

# 错误率告警阈值
if health.error_rate > 0.01:  # 修改这里
    alerts.append({...})

# 置信度告警阈值
if conf_stats["avg"] < 0.5:  # 修改这里
    alerts.append({...})
```

## 故障排除

### 问题：监控数据为空

**原因**：应用程序尚未进行任何预测

**解决方案**：
1. 启动应用程序
2. 执行一些预测操作
3. 再次查看监控仪表板

### 问题：日志文件过大

**原因**：长时间运行积累了大量日志

**解决方案**：
```bash
# 清理旧日志（保留最近 7 天）
find logs/model_monitoring -name "*.jsonl" -mtime +7 -delete

# 或者手动删除
del logs\model_monitoring\predictions.jsonl
del logs\model_monitoring\errors.jsonl
```

### 问题：监控影响性能

**原因**：历史记录大小过大

**解决方案**：
减小 `history_size` 参数（默认 1000）

### 问题：psutil 未安装

**症状**：系统指标显示为 0

**解决方案**：
```bash
pip install psutil
```

## 未来增强

可能的改进方向：

1. **Web 仪表板**
   - 使用 Flask/FastAPI 提供 Web 界面
   - 实时图表和可视化
   - 历史趋势分析

2. **告警通知**
   - 邮件通知
   - 钉钉/企业微信通知
   - Slack/Discord 集成

3. **持久化存储**
   - 将指标存储到数据库
   - 支持长期趋势分析
   - 数据聚合和报表

4. **分布式监控**
   - 多实例监控聚合
   - 集中式监控服务
   - 跨节点性能对比

5. **自动调优**
   - 基于监控数据自动调整阈值
   - 异常检测和自动恢复
   - 性能优化建议

## 技术细节

### 线程安全

监控器使用 `threading.RLock` 保护所有共享数据结构，确保多线程环境下的安全性。

### 内存管理

使用 `collections.deque` 限制历史记录大小，自动丢弃最旧的记录，防止内存无限增长。

### 日志格式

所有日志使用 JSONL 格式（每行一个 JSON 对象），便于流式处理和分析。

### 缓存策略

监控数据在内存中缓存，定期写入磁盘，平衡性能和持久性。

## 总结

模型监控系统已完全集成并可用。它提供了全面的可观测性，帮助：

1. **性能优化**：识别慢速预测和瓶颈
2. **质量保证**：监控预测质量和置信度
3. **故障诊断**：快速定位和解决问题
4. **容量规划**：了解系统资源使用情况
5. **持续改进**：基于数据驱动的决策

开始使用：
```bash
python model_monitoring_dashboard.py --continuous --details
```

享受可观测的模型监控！
