# foot (Go) 快速集成指南

## 当前状态

❌ **foot 项目不存在** - 需要创建或从 GitHub 获取

## 选项 1: 从 GitHub 获取（如果项目已存在）

```bash
cd E:\APP
git clone https://github.com/your-username/foot.git
cd foot
go build -o foot.exe
```

## 选项 2: 创建新的 foot 项目

### 步骤 1: 创建项目结构

```bash
cd E:\APP
mkdir foot
cd foot
go mod init foot
```

### 步骤 2: 创建 HTTP 服务器

创建文件 `E:\APP\foot\main.go`:

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "time"
)

type Match struct {
    SourceID     string  `json:"source_id"`
    MatchDate    string  `json:"match_date"`
    MatchTime    string  `json:"match_time"`
    League       string  `json:"league"`
    HomeTeam     string  `json:"home_team"`
    AwayTeam     string  `json:"away_team"`
    LineupKnown  bool    `json:"lineup_known"`
    HomeOdds     float64 `json:"home_odds,omitempty"`
    DrawOdds     float64 `json:"draw_odds,omitempty"`
    AwayOdds     float64 `json:"away_odds,omitempty"`
    ProviderKind string  `json:"provider_kind"`
}

type Response struct {
    Items     []Match `json:"items"`
    Count     int     `json:"count"`
    Timestamp string  `json:"timestamp"`
}

func handleMatches(w http.ResponseWriter, r *http.Request) {
    date := r.URL.Query().Get("date")
    if date == "" {
        date = time.Now().Format("2006-01-02")
    }
    
    // TODO: 实现实际的数据采集逻辑
    matches := []Match{
        {
            SourceID:     "demo_001",
            MatchDate:    date,
            MatchTime:    "20:00",
            League:       "英超",
            HomeTeam:     "曼城",
            AwayTeam:     "利物浦",
            LineupKnown:  true,
            HomeOdds:     1.85,
            DrawOdds:     3.60,
            AwayOdds:     4.20,
            ProviderKind: "foot_go",
        },
    }
    
    response := Response{
        Items:     matches,
        Count:     len(matches),
        Timestamp: time.Now().Format(time.RFC3339),
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{
        "status": "ok",
        "time":   time.Now().Format(time.RFC3339),
    })
}

func main() {
    http.HandleFunc("/api/matches", handleMatches)
    http.HandleFunc("/health", handleHealth)
    
    log.Println("foot HTTP server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

### 步骤 3: 编译和运行

```bash
cd E:\APP\foot
go build -o foot.exe
./foot.exe
```

### 步骤 4: 测试服务

```bash
# 健康检查
curl http://localhost:8080/health

# 获取今天的比赛
curl http://localhost:8080/api/matches

# 获取指定日期的比赛
curl "http://localhost:8080/api/matches?date=2026-05-28"
```

## 选项 3: 使用现有的开源项目

如果你提到的 **foot (Go)** 是指某个开源项目，请提供：
1. GitHub 仓库地址
2. 项目文档链接

我可以帮你：
- 克隆项目
- 配置集成
- 编写适配器

## 集成到 ELO 系统

### 1. 更新配置文件

编辑 `e:\APP\ELO\c1\configs\availability_sources.yaml`:

```yaml
providers:
  # foot (Go) HTTP 服务
  - type: http_source
    enabled: true
    name: foot_go_primary
    provider_kind: foot_go
    url: http://localhost:8080/api/matches?date={today}
    format: json
    items_key: items
    timeout_seconds: 30
    resolve_direct: false
    max_matches: 100
    headers:
      Accept: application/json
```

### 2. 测试集成

```bash
cd E:\APP\ELO
python scripts/test_foot_integration.py
```

## 我需要什么信息？

请告诉我：

1. **foot 项目来源**
   - [ ] GitHub 开源项目（请提供链接）
   - [ ] 自己开发的项目（在哪里？）
   - [ ] 需要从头创建

2. **foot 功能需求**
   - [ ] 抓取哪些网站的数据？
   - [ ] 需要哪些数据字段？
   - [ ] 数据更新频率？

3. **集成优先级**
   - [ ] 高优先级（立即集成）
   - [ ] 中优先级（xG 训练后集成）
   - [ ] 低优先级（未来考虑）

## 推荐方案

基于你的系统现状，我建议：

### 短期（本周）
1. ✅ 完成 xG 模型训练（已准备好）
2. ⏳ 验证 xG 模型效果
3. ⏳ 如果 foot 项目存在，创建 HTTP 适配器

### 中期（本月）
1. 集成 foot (Go) 作为额外数据源
2. 对比不同数据源的质量
3. 优化数据采集策略

### 长期（本季度）
1. 建立多数据源融合机制
2. 实现数据质量监控
3. 自动化数据采集流程

---

**下一步行动：**

请告诉我 foot 项目的具体情况，我可以：
1. 帮你从 GitHub 克隆并集成
2. 帮你创建新的 foot 项目
3. 帮你编写适配器代码

或者，我们可以先完成 xG 模型训练，然后再处理 foot 集成？
