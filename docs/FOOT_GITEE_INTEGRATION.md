# foot (Go) Gitee 项目集成方案

## 项目信息

### 仓库地址
- **主仓库**: https://gitee.com/aoe5188/foot
- **分支1**: https://gitee.com/ryvius_key/foot
- **分支2**: https://gitee.com/xuhanga/foot

### 项目特点
- **语言**: Go
- **功能**: 一体化足球数据采集与分析
- **覆盖**: 赔率收集 → 模型分析（A1/C1） → 结果推送
- **注意**: 不要与 cak/foot 混淆（功能完全不同）

---

## 集成策略

### 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **并行运行** | 互不干扰，各自独立 | 需要数据融合 | ⭐⭐⭐⭐⭐ |
| **数据共享** | 共用数据源 | 需要格式转换 | ⭐⭐⭐⭐ |
| **完全替换** | 统一架构 | 迁移成本高 | ⭐⭐ |

**推荐：并行运行 + 数据共享**

---

## 实施步骤

### 第 1 步：克隆 foot 项目

```bash
# 创建 foot 目录
cd E:\APP
mkdir foot
cd foot

# 克隆主仓库
git clone https://gitee.com/aoe5188/foot.git .

# 或者选择其他分支
# git clone https://gitee.com/ryvius_key/foot.git .
# git clone https://gitee.com/xuhanga/foot.git .
```

### 第 2 步：编译 foot

```bash
cd E:\APP\foot

# 安装依赖
go mod download

# 编译
go build -o foot.exe

# 测试运行
./foot.exe --help
```

### 第 3 步：了解 foot 的数据格式

```bash
# 运行 foot 并查看输出
./foot.exe

# 检查 foot 的配置文件
# 通常在 config.yaml 或 config.json
```

---

## 集成架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        数据采集层                            │
├─────────────────────────────────────────────────────────────┤
│  foot (Go)                    │  V24/C1.0 (Python)          │
│  - 赔率采集                    │  - Titan 详情页              │
│  - A1/C1 模型                  │  - API-Football             │
│  - 结果推送                    │  - xG 数据                   │
└──────────┬──────────────────────┴─────────────┬─────────────┘
           │                                    │
           ▼                                    ▼
    ┌─────────────┐                    ┌─────────────┐
    │ foot 输出   │                    │ C1 数据源   │
    │ (JSON/CSV)  │                    │ (YAML配置)  │
    └──────┬──────┘                    └──────┬──────┘
           │                                    │
           └────────────┬───────────────────────┘
                        ▼
              ┌──────────────────┐
              │   数据融合层      │
              │  - 格式转换       │
              │  - 去重合并       │
              │  - 质量评分       │
              └─────────┬────────┘
                        ▼
              ┌──────────────────┐
              │   统一预测引擎    │
              │  - ELO            │
              │  - XGBoost (xG)   │
              │  - Ensemble       │
              └─────────┬────────┘
                        ▼
              ┌──────────────────┐
              │   决策输出        │
              │  - 推荐列表       │
              │  - 置信度评分     │
              │  - 风险评估       │
              └──────────────────┘
```

---

## 集成方式 1: HTTP 桥接（推荐）

### foot 侧：提供 HTTP API

如果 foot 项目已经有 HTTP 服务，直接使用。如果没有，添加一个简单的 HTTP 包装器：

```go
// E:\APP\foot\bridge\http_server.go
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "os"
    "path/filepath"
)

// 假设 foot 输出到文件
func handleMatches(w http.ResponseWriter, r *http.Request) {
    date := r.URL.Query().Get("date")
    
    // 读取 foot 的输出文件
    dataFile := filepath.Join("output", date+".json")
    data, err := os.ReadFile(dataFile)
    if err != nil {
        http.Error(w, "Data not found", http.StatusNotFound)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    w.Write(data)
}

func main() {
    http.HandleFunc("/api/matches", handleMatches)
    log.Println("foot bridge server on :8081")
    log.Fatal(http.ListenAndServe(":8081", nil))
}
```

### Python 侧：配置数据源

```yaml
# e:\APP\ELO\c1\configs\availability_sources.yaml
providers:
  # foot (Go) 数据源
  - type: http_source
    enabled: true
    name: foot_go_bridge
    provider_kind: foot_go
    url: http://localhost:8081/api/matches?date={today}
    format: json
    items_key: matches  # 根据 foot 实际输出调整
    timeout_seconds: 30
    resolve_direct: false
    headers:
      Accept: application/json
```

---

## 集成方式 2: 文件共享

### foot 侧：输出标准格式

```go
// 修改 foot 的输出格式，使其兼容 C1
type Match struct {
    SourceID    string  `json:"source_id"`
    MatchDate   string  `json:"match_date"`
    MatchTime   string  `json:"match_time"`
    League      string  `json:"league"`
    HomeTeam    string  `json:"home_team"`
    AwayTeam    string  `json:"away_team"`
    HomeOdds    float64 `json:"home_odds"`
    DrawOdds    float64 `json:"draw_odds"`
    AwayOdds    float64 `json:"away_odds"`
    LineupKnown bool    `json:"lineup_known"`
}

// 输出到共享目录
func exportToC1(matches []Match) {
    data, _ := json.Marshal(map[string]interface{}{
        "items": matches,
        "timestamp": time.Now().Format(time.RFC3339),
    })
    
    os.WriteFile("E:/APP/ELO/data/foot_matches.json", data, 0644)
}
```

### Python 侧：读取文件

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

## 集成方式 3: 数据库共享

### 共享 SQLite 数据库

```go
// foot 写入数据库
import "database/sql"
import _ "github.com/mattn/go-sqlite3"

func saveToDatabase(matches []Match) {
    db, _ := sql.Open("sqlite3", "E:/APP/ELO/data/shared.db")
    defer db.Close()
    
    for _, m := range matches {
        db.Exec(`INSERT INTO matches (source_id, match_date, home_team, away_team, home_odds, draw_odds, away_odds) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)`,
                 m.SourceID, m.MatchDate, m.HomeTeam, m.AwayTeam, m.HomeOdds, m.DrawOdds, m.AwayOdds)
    }
}
```

```python
# Python 读取数据库
import sqlite3

def load_foot_matches():
    conn = sqlite3.connect('data/shared.db')
    cursor = conn.execute('SELECT * FROM matches WHERE match_date = ?', (today,))
    return cursor.fetchall()
```

---

## 模型对比：foot A1/C1 vs V24/C1.0

### foot 的 A1/C1 模型
- **A1**: 可能是基础分析模型
- **C1**: 可能是高级决策模型

### V24/C1.0 模型
- **V24**: 当前生产系统（ELO + Poisson + XGBoost + Market）
- **C1.0**: 新架构（Governance + Translation + Audit）

### 融合策略

```python
# e:\APP\ELO\c1\inference\foot_adapter.py
"""
foot (Go) 模型适配器
将 foot 的 A1/C1 模型输出转换为 C1.0 格式
"""

class FootModelAdapter:
    """适配 foot 的模型输出"""
    
    def __init__(self, foot_api_url: str = "http://localhost:8081"):
        self.api_url = foot_api_url
    
    def get_foot_prediction(self, match_id: str) -> dict:
        """获取 foot 的预测结果"""
        response = requests.get(f"{self.api_url}/api/prediction/{match_id}")
        return response.json()
    
    def convert_to_c1_format(self, foot_output: dict) -> dict:
        """转换为 C1.0 格式"""
        return {
            "model_name": "foot_go",
            "probabilities": {
                "home": foot_output.get("home_prob", 0.33),
                "draw": foot_output.get("draw_prob", 0.33),
                "away": foot_output.get("away_prob", 0.33),
            },
            "confidence": foot_output.get("confidence", 0.5),
            "metadata": {
                "foot_model": foot_output.get("model_type", "A1"),
                "foot_version": foot_output.get("version", "unknown"),
            }
        }
```

### 集成到 Ensemble

```python
# e:\APP\ELO\c1\inference\calibration.py
from .foot_adapter import FootModelAdapter

# 添加 foot 模型到集成
DEFAULT_ENSEMBLE_WEIGHTS = {
    "market": 0.20,
    "elo": 0.30,
    "poisson": 0.20,
    "xgboost": 0.15,
    "foot_go": 0.15,  # 新增 foot 模型
}

# 在 ensemble 中使用
foot_adapter = FootModelAdapter()
foot_pred = foot_adapter.get_foot_prediction(match_id)
foot_probs = foot_adapter.convert_to_c1_format(foot_pred)
```

---

## 实施计划

### 阶段 1: 环境准备（1 天）
- [ ] 克隆 foot 项目到 `E:\APP\foot`
- [ ] 编译 foot.exe
- [ ] 了解 foot 的配置和输出格式
- [ ] 测试 foot 的基本功能

### 阶段 2: 数据桥接（2-3 天）
- [ ] 选择集成方式（HTTP/文件/数据库）
- [ ] 实现数据格式转换
- [ ] 配置 C1.0 数据源
- [ ] 测试数据流通

### 阶段 3: 模型融合（3-5 天）
- [ ] 创建 foot 模型适配器
- [ ] 将 foot 预测集成到 ensemble
- [ ] 调整 ensemble 权重
- [ ] 回测对比效果

### 阶段 4: 生产部署（1-2 天）
- [ ] 配置自动启动脚本
- [ ] 设置监控和日志
- [ ] 文档和培训
- [ ] 上线观察

---

## 快速启动脚本

### 1. 克隆和编译
```powershell
# scripts/setup_foot.ps1
$footDir = "E:\APP\foot"

if (-not (Test-Path $footDir)) {
    Write-Host "Cloning foot from Gitee..."
    git clone https://gitee.com/aoe5188/foot.git $footDir
}

cd $footDir
Write-Host "Building foot..."
go build -o foot.exe

Write-Host "✓ foot setup complete"
```

### 2. 启动服务
```powershell
# scripts/start_foot.ps1
$footExe = "E:\APP\foot\foot.exe"

if (Test-Path $footExe) {
    Write-Host "Starting foot service..."
    Start-Process -FilePath $footExe -WorkingDirectory "E:\APP\foot"
    Write-Host "✓ foot service started"
} else {
    Write-Host "✗ foot.exe not found. Run setup_foot.ps1 first."
}
```

### 3. 测试集成
```python
# scripts/test_foot_integration.py
"""测试 foot 集成"""
import requests
import json

def test_foot_data():
    """测试 foot 数据可用性"""
    # 方式 1: HTTP API
    try:
        response = requests.get("http://localhost:8081/api/matches")
        data = response.json()
        print(f"✓ foot HTTP API: {len(data.get('items', []))} matches")
    except Exception as e:
        print(f"✗ foot HTTP API failed: {e}")
    
    # 方式 2: 文件
    try:
        with open("data/foot_matches.json") as f:
            data = json.load(f)
        print(f"✓ foot file: {len(data.get('items', []))} matches")
    except Exception as e:
        print(f"✗ foot file failed: {e}")

def test_foot_model():
    """测试 foot 模型预测"""
    try:
        response = requests.get("http://localhost:8081/api/prediction/12345")
        pred = response.json()
        print(f"✓ foot model: {pred}")
    except Exception as e:
        print(f"✗ foot model failed: {e}")

if __name__ == "__main__":
    test_foot_data()
    test_foot_model()
```

---

## 注意事项

### 1. 端口冲突
- foot 可能使用 8080 端口
- 如果冲突，修改为 8081 或其他端口

### 2. 数据格式
- foot 的输出格式可能与 C1.0 不同
- 需要编写适配器转换

### 3. 模型兼容性
- foot 的 A1/C1 模型可能与 V24 的 C1.0 不同
- 建议先并行运行，对比效果

### 4. 性能考虑
- foot 是 Go 编写，性能好
- Python 调用可能有延迟
- 考虑使用缓存

---

## 下一步行动

### 立即执行
```bash
# 1. 克隆 foot 项目
cd E:\APP
git clone https://gitee.com/aoe5188/foot.git

# 2. 编译
cd foot
go build -o foot.exe

# 3. 测试运行
./foot.exe --help
```

### 然后告诉我
1. foot 的配置文件在哪里？
2. foot 的输出格式是什么？
3. foot 的 A1/C1 模型如何调用？

我会根据实际情况编写适配器代码。

---

## 总结

✅ **已准备**
- 集成方案（3 种方式）
- 架构设计（并行运行）
- 实施计划（4 个阶段）

⏳ **待执行**
- 克隆 foot 项目
- 了解 foot 输出格式
- 编写数据适配器

🎯 **预期收益**
- 数据源多样化
- 模型融合（foot A1/C1 + V24 C1.0）
- 提升预测准确率

需要我帮你克隆和配置 foot 项目吗？
