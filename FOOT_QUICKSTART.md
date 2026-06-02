# foot (Go) 快速启动指南

## 项目信息

- **仓库**: https://gitee.com/aoe5188/foot
- **语言**: Go
- **功能**: 足球数据采集 + A1/C1 模型分析 + 结果推送

---

## 快速开始（3 步）

### 步骤 1: 安装 foot

```powershell
# 在 PowerShell 中运行
cd E:\APP\ELO
powershell -ExecutionPolicy Bypass -File scripts\setup_foot.ps1
```

**这个脚本会：**
- ✓ 检查 Git 和 Go 是否安装
- ✓ 从 Gitee 克隆 foot 项目到 `E:\APP\foot`
- ✓ 下载 Go 依赖
- ✓ 编译 `foot.exe`
- ✓ 测试运行

**预计时间**: 2-5 分钟（取决于网络速度）

---

### 步骤 2: 测试 foot

```bash
# 测试 foot 是否正确安装
python scripts\test_foot_integration.py
```

**这个脚本会检查：**
- ✓ foot.exe 是否存在
- ✓ foot.exe 是否可执行
- ✓ 配置文件是否存在
- ✓ 输出文件是否存在
- ✓ HTTP API 是否运行

---

### 步骤 3: 了解 foot

```bash
# 查看 foot 帮助
cd E:\APP\foot
.\foot.exe --help

# 查看配置文件
notepad config.yaml  # 或 config.json

# 运行 foot
.\foot.exe
```

---

## 集成选项

### 选项 A: HTTP API 模式（推荐）

**如果 foot 提供 HTTP 服务：**

1. 启动 foot 服务
2. 配置 C1.0 数据源：

```yaml
# e:\APP\ELO\c1\configs\availability_sources.yaml
providers:
  - type: http_source
    enabled: true
    name: foot_go_primary
    url: http://localhost:8080/api/matches?date={today}
    format: json
    items_key: matches
```

---

### 选项 B: 文件共享模式

**如果 foot 输出到文件：**

1. 配置 foot 输出到 `E:\APP\ELO\data\foot_matches.json`
2. 配置 C1.0 读取文件：

```yaml
# e:\APP\ELO\c1\configs\availability_sources.yaml
providers:
  - type: file_source
    enabled: true
    name: foot_go_file
    path: data/foot_matches.json
    format: json
    items_key: items
```

---

### 选项 C: 模型融合模式

**使用 foot 的 A1/C1 模型预测：**

```python
# 将 foot 模型加入 ensemble
DEFAULT_ENSEMBLE_WEIGHTS = {
    "market": 0.20,
    "elo": 0.25,
    "poisson": 0.20,
    "xgboost": 0.20,
    "foot_go": 0.15,  # foot 的 A1/C1 模型
}
```

---

## 故障排除

### 问题 1: Git 未安装

```
✗ Git not found
```

**解决方案**: 下载并安装 Git
- https://git-scm.com/download/win

---

### 问题 2: Go 未安装

```
✗ Go not found
```

**解决方案**: 下载并安装 Go
- https://go.dev/dl/

---

### 问题 3: 克隆失败

```
✗ Clone failed: connection timeout
```

**解决方案**: 
1. 检查网络连接
2. 尝试使用 VPN
3. 或手动下载：https://gitee.com/aoe5188/foot/repository/archive/master.zip

---

### 问题 4: 编译失败

```
✗ Build failed: missing dependencies
```

**解决方案**:
```bash
cd E:\APP\foot
go mod tidy
go build -o foot.exe
```

---

## 文档

- **完整集成方案**: `docs/FOOT_GITEE_INTEGRATION.md`
- **架构设计**: 并行运行 + 数据融合
- **实施计划**: 4 个阶段，7-10 天

---

## 当前进度

### ✅ 已完成
- xG 特征集成（17,910 条记录，15 个特征）
- XGBoost 增强模型（53 个特征）
- 测试套件（898 个测试通过）
- foot 集成方案和脚本

### ⏳ 待执行
- [ ] 安装 foot 项目
- [ ] 了解 foot 输出格式
- [ ] 选择集成方式
- [ ] 配置数据桥接
- [ ] 测试数据流

### 🎯 优先级建议

**选项 1: 先完成 xG 训练（推荐）**
```bash
# 1. 训练 xG 增强模型（预期 75% → 78-80%）
python scripts/train_xgb_with_xg.py

# 2. 验证效果
python scripts/run_full_backtest.py

# 3. 然后集成 foot
powershell scripts/setup_foot.ps1
```

**选项 2: 同时进行**
```bash
# 终端 1: 训练 xG 模型
python scripts/train_xgb_with_xg.py

# 终端 2: 安装 foot
powershell scripts/setup_foot.ps1
```

---

## 下一步

### 立即执行（推荐）

```powershell
# 1. 安装 foot
cd E:\APP\ELO
powershell -ExecutionPolicy Bypass -File scripts\setup_foot.ps1

# 2. 测试 foot
python scripts\test_foot_integration.py

# 3. 查看 foot 功能
cd E:\APP\foot
.\foot.exe --help
```

### 然后告诉我

1. **foot 的配置文件是什么格式？**
   - config.yaml?
   - config.json?
   - 其他？

2. **foot 如何输出数据？**
   - HTTP API?
   - 文件输出?
   - 数据库?

3. **foot 的 A1/C1 模型如何调用？**
   - 命令行参数?
   - API 接口?
   - 配置文件?

我会根据实际情况编写适配器代码。

---

## 联系方式

如果遇到问题：
1. 查看 `docs/FOOT_GITEE_INTEGRATION.md`
2. 运行 `python scripts/test_foot_integration.py`
3. 检查 foot 项目的 README

---

**准备好了吗？** 运行 `powershell scripts/setup_foot.ps1` 开始！
