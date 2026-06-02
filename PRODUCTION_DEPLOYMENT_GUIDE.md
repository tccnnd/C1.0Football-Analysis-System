# 生产部署指南

**部署日期**: 2026-05-29  
**版本**: V24 + C1.0 模型优化版  
**状态**: 准备就绪

---

## 📋 部署前检查清单

### 1. 代码检查 ✅

- [x] 所有模型已训练完成
- [x] 预加载优化已实施
- [x] 所有测试通过
- [x] 代码已提交到版本控制

### 2. 环境检查

- [ ] Python 版本: 3.10+
- [ ] 依赖包已安装
- [ ] 磁盘空间充足（至少 1GB）
- [ ] 内存充足（至少 2GB）

### 3. 数据检查

- [ ] 训练样本文件存在
- [ ] 模型文件存在（5 个）
- [ ] 配置文件正确

### 4. 备份检查

- [ ] 代码已备份
- [ ] 数据已备份
- [ ] 配置已备份

---

## 🚀 部署步骤

### 步骤 1: 环境准备

#### 1.1 检查 Python 环境

```bash
# 检查 Python 版本
python --version
# 应该显示: Python 3.10+ 或 3.14

# 检查虚拟环境
python -c "import sys; print(sys.prefix)"
```

#### 1.2 检查依赖包

```bash
# 检查关键依赖
python -c "import xgboost; print(f'XGBoost: {xgboost.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import pandas; print(f'Pandas: {pandas.__version__}')"
```

#### 1.3 检查磁盘空间

```bash
# Windows
dir "E:\APP\ELO\data\models"

# 应该看到以下文件:
# - xgb_v0_match_outcome.json (~2 MB)
# - xgb_xg_match_outcome.json (~2.5 MB)
# - xgb_v1_total_goals.json (~3 MB)
# - xgb_v1_scoreline.json (~4 MB)
# - xgb_v1_scoreline_volatile.json (~2 MB)
```

---

### 步骤 2: 代码部署

#### 2.1 备份当前版本

```bash
# 创建备份目录
mkdir E:\APP\ELO_BACKUP_20260529

# 备份代码
xcopy E:\APP\ELO E:\APP\ELO_BACKUP_20260529 /E /I /H /Y

# 或使用 Git
cd E:\APP\ELO
git add .
git commit -m "Backup before model preload deployment"
git tag v24-preload-optimization-20260529
```

#### 2.2 验证新代码

```bash
cd E:\APP\ELO

# 验证预加载模块存在
python -c "from v24_app.model_preloader import preload_models; print('✅ 预加载模块正常')"

# 验证自动预加载
python -c "from v24_app import core; print('✅ Core 模块正常')"

# 运行完整验证
python verify_preload_optimization.py
```

---

### 步骤 3: 模型验证

#### 3.1 检查模型文件

```bash
# 检查模型文件是否存在
python -c "
from pathlib import Path
models = [
    'xgb_v0_match_outcome.json',
    'xgb_xg_match_outcome.json',
    'xgb_v1_total_goals.json',
    'xgb_v1_scoreline.json',
    'xgb_v1_scoreline_volatile.json',
]
model_dir = Path('E:/APP/ELO/data/models')
for model in models:
    path = model_dir / model
    if path.exists():
        size = path.stat().st_size / (1024*1024)
        print(f'✅ {model}: {size:.2f} MB')
    else:
        print(f'❌ {model}: 不存在')
"
```

#### 3.2 测试模型预测

```bash
# 快速预测测试
python -c "
import sys
from pathlib import Path
sys.path.insert(0, 'E:/APP/ELO/src')

from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
from v24_app.models.ensemble import EnsembleContext

model = XGBoostProbabilityModel(Path('E:/APP/ELO'))
context = EnsembleContext(
    home_rating=1600.0,
    away_rating=1600.0,
    league_strength=0.70,
    market_probs=(0.40, 0.30, 0.30),
    market_draw_prob=0.30,
    metadata={'odds_home': 2.40, 'odds_draw': 3.20, 'odds_away': 2.80}
)

output = model.predict(context)
print(f'✅ 预测成功: 主胜 {output.probabilities[0]:.2%}')
"
```

---

### 步骤 4: 性能基准测试

#### 4.1 运行预加载测试

```bash
cd E:\APP\ELO
python test_cold_start_improvement.py
```

**预期结果**:
- 不预加载: ~44 ms
- 预加载: ~1 ms
- 改善: >90%

#### 4.2 运行预测性能测试

```bash
python test_model_predictions.py
```

**预期结果**:
- 平均延迟: < 1 ms
- 吞吐量: > 2000 QPS
- 所有模型预测正常

---

### 步骤 5: 启动应用

#### 5.1 停止当前服务（如果运行中）

```bash
# 如果使用 Windows 服务
# 停止服务（根据实际服务名调整）
# sc stop ELOService

# 如果使用进程
# 找到并终止 Python 进程
tasklist | findstr python
# taskkill /PID <进程ID> /F
```

#### 5.2 启动新版本

```bash
cd E:\APP\ELO

# 方式 1: 直接启动
python launcher.py

# 方式 2: 使用启动脚本
start_app.bat

# 方式 3: 后台启动（推荐生产环境）
start /B python launcher.py > logs\app.log 2>&1
```

#### 5.3 验证启动成功

```bash
# 检查进程
tasklist | findstr python

# 检查日志（如果有）
type logs\app.log

# 测试预测接口（如果有 HTTP 接口）
# curl http://localhost:8000/health
```

---

### 步骤 6: 监控验证

#### 6.1 检查预加载日志

启动时应该看到类似输出：
```
============================================================
模型预加载
============================================================

预加载 XGBoost V0...
  ✅ 成功 (0.042 秒)

预加载 XGBoost XG...
  ✅ 成功 (0.110 秒)

...

============================================================
预加载完成，总耗时: 1.26 秒
============================================================
```

#### 6.2 测试首次预测

```bash
# 发送测试请求（根据实际接口调整）
python -c "
import requests
import time

# 测试首次预测延迟
start = time.time()
# response = requests.post('http://localhost:8000/predict', json={...})
elapsed = (time.time() - start) * 1000
print(f'首次预测延迟: {elapsed:.2f} ms')

# 预期: < 10 ms
"
```

#### 6.3 监控关键指标

**启动阶段**:
- [ ] 预加载总耗时 < 2 秒
- [ ] 所有模型预加载成功
- [ ] 应用启动成功

**运行阶段**:
- [ ] 首次预测延迟 < 10 ms
- [ ] 平均预测延迟 < 2 ms
- [ ] 内存使用正常（增加 ~21 MB）
- [ ] CPU 使用正常

---

## 🔍 故障排查

### 问题 1: 预加载失败

**症状**: 启动时看到预加载错误

**排查步骤**:
```bash
# 1. 检查模型文件是否存在
dir E:\APP\ELO\data\models\*.json

# 2. 检查文件权限
# 确保应用有读取权限

# 3. 检查 XGBoost 版本
python -c "import xgboost; print(xgboost.__version__)"

# 4. 手动测试预加载
python -c "
from pathlib import Path
from v24_app.model_preloader import preload_models
results = preload_models(Path('E:/APP/ELO'), verbose=True)
"
```

**解决方案**:
- 如果模型文件不存在: 运行 `python train_all_models.py`
- 如果权限问题: 调整文件权限
- 如果版本问题: 更新 XGBoost

### 问题 2: 首次预测仍然慢

**症状**: 首次预测延迟 > 20 ms

**排查步骤**:
```bash
# 1. 检查预加载是否生效
python -c "
from v24_app import core
with core.XGBOOST_MODEL._model_lock:
    loaded = core.XGBOOST_MODEL._model is not None
print(f'模型已加载: {loaded}')
"

# 2. 检查是否禁用了预加载
python -c "
import os
print(f'SKIP_MODEL_PRELOAD: {os.environ.get(\"SKIP_MODEL_PRELOAD\", \"未设置\")}')
"

# 3. 运行冷启动测试
python test_cold_start_improvement.py
```

**解决方案**:
- 确保没有设置 `SKIP_MODEL_PRELOAD=1`
- 重启应用
- 检查磁盘 I/O 性能

### 问题 3: 内存占用过高

**症状**: 内存使用超过预期

**排查步骤**:
```bash
# 检查进程内存
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE

# 使用 Python 检查
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
mem = process.memory_info().rss / (1024*1024)
print(f'内存使用: {mem:.2f} MB')
"
```

**解决方案**:
- 预加载增加 ~21 MB 是正常的
- 如果超过 100 MB，检查是否有内存泄漏
- 考虑使用模型量化

### 问题 4: 启动时间过长

**症状**: 启动时间 > 5 秒

**排查步骤**:
```bash
# 测量预加载时间
python -c "
import time
from pathlib import Path
from v24_app.model_preloader import preload_models

start = time.time()
results = preload_models(Path('E:/APP/ELO'), verbose=False)
elapsed = time.time() - start

print(f'预加载耗时: {elapsed:.2f} 秒')
for name, result in results.items():
    print(f'  {name}: {result[\"elapsed\"]:.3f} 秒')
"
```

**解决方案**:
- 正常预加载时间: 1-2 秒
- 如果 > 5 秒，检查磁盘性能
- 考虑实施并行预加载

---

## 🔄 回滚方案

如果部署后出现问题，可以快速回滚：

### 方案 1: 禁用预加载

```bash
# 设置环境变量
set SKIP_MODEL_PRELOAD=1

# 重启应用
python launcher.py
```

### 方案 2: 恢复备份

```bash
# 停止应用
# taskkill /F /IM python.exe

# 恢复备份
xcopy E:\APP\ELO_BACKUP_20260529 E:\APP\ELO /E /I /H /Y

# 重启应用
cd E:\APP\ELO
python launcher.py
```

### 方案 3: Git 回滚

```bash
cd E:\APP\ELO

# 查看提交历史
git log --oneline

# 回滚到之前的版本
git reset --hard <commit-hash>

# 或回滚到标签
git reset --hard v24-preload-optimization-20260529^

# 重启应用
python launcher.py
```

---

## 📊 监控指标

### 关键性能指标 (KPI)

| 指标 | 目标值 | 告警阈值 |
|------|--------|----------|
| 预加载总耗时 | < 2s | > 5s |
| 预加载成功率 | 100% | < 80% |
| 首次预测延迟 | < 5ms | > 20ms |
| 平均预测延迟 | < 2ms | > 10ms |
| 预测吞吐量 | > 1000 QPS | < 500 QPS |
| 内存使用 | < 100 MB | > 500 MB |
| CPU 使用率 | < 50% | > 80% |

### 监控脚本

创建 `monitor_performance.py`:

```python
"""
性能监控脚本

定期检查关键性能指标。
"""
import time
import psutil
import os
from pathlib import Path

def monitor():
    # 检查进程
    process = psutil.Process(os.getpid())
    
    # 内存使用
    mem_mb = process.memory_info().rss / (1024*1024)
    
    # CPU 使用
    cpu_percent = process.cpu_percent(interval=1)
    
    print(f"内存: {mem_mb:.2f} MB | CPU: {cpu_percent:.1f}%")
    
    # 告警
    if mem_mb > 500:
        print("⚠️ 内存使用过高")
    if cpu_percent > 80:
        print("⚠️ CPU 使用过高")

if __name__ == "__main__":
    while True:
        monitor()
        time.sleep(60)  # 每分钟检查一次
```

---

## 📝 部署检查表

### 部署前

- [ ] 代码已备份
- [ ] 数据已备份
- [ ] 所有测试通过
- [ ] 文档已更新

### 部署中

- [ ] 停止旧版本
- [ ] 部署新代码
- [ ] 验证模型文件
- [ ] 启动新版本

### 部署后

- [ ] 验证预加载成功
- [ ] 测试首次预测
- [ ] 检查性能指标
- [ ] 监控运行状态

### 24 小时后

- [ ] 收集性能数据
- [ ] 对比预期指标
- [ ] 记录问题和改进
- [ ] 更新文档

---

## 🎯 成功标准

部署成功的标准：

1. ✅ 应用启动成功（< 5 秒）
2. ✅ 所有模型预加载成功（5/5）
3. ✅ 首次预测延迟 < 10 ms
4. ✅ 平均预测延迟 < 2 ms
5. ✅ 无异常或错误
6. ✅ 内存使用正常（< 100 MB）
7. ✅ CPU 使用正常（< 50%）

---

## 📞 支持联系

如遇到问题，请参考：

1. **文档**: `docs/` 目录下的详细报告
2. **测试脚本**: 项目根目录的测试脚本
3. **日志**: `logs/` 目录（如果配置了）
4. **备份**: `E:\APP\ELO_BACKUP_20260529`

---

## 📅 部署时间表

**建议部署时间**: 低峰期（如凌晨 2-4 点）

**部署流程**:
1. 00:00 - 准备备份
2. 01:00 - 停止服务
3. 01:05 - 部署新版本
4. 01:10 - 启动服务
5. 01:15 - 验证测试
6. 01:30 - 监控观察
7. 02:00 - 确认成功

**预计停机时间**: 5-10 分钟

---

**部署状态**: 准备就绪 ✅  
**风险等级**: 低（可快速回滚）  
**建议**: 立即部署
