# foot (Go) 集成方案

## 概述

**foot** 是一个 Go 语言开发的足球数据采集工具，支持：
- 联赛数据抓取
- 球队信息采集
- 欧亚指数获取
- 近期战绩分析

本文档说明如何将 foot 集成到当前的 V24/C1.0 系统中。

---

## 当前数据采集架构

### 现有数据源
1. **titan_detail_primary** - Titan 详情页（主要）
2. **api_football_primary** - API-Football（已暂停）
3. **crawler_fallback** - 爬虫备用（未启用）
4. **external_availability_file** - 手动导入（未启用）
5. **local_snapshots** - 本地快照（备用）

### 数据流
```
数据源 → AvailabilityProvider → ProviderChain → C1 Runtime → 预测
```

---

## foot (Go) 集成方案

### 方案 A: HTTP 服务模式（推荐）

**架构：**
```
foot (Go) HTTP Server → Python HTTP Client → CrawlerAvailabilityProvider
```

**优点：**
- 解耦：Go 和 Python 独立运行
- 灵活：可以独立更新 foot
- 标准：使用 HTTP/JSON 通信

**实现步骤：**

#### 1. foot 提供 HTTP API
```go
// foot/main.go
package main

import (
    "encoding/json"
    "net/http"
)

type Match struct {
    SourceID     string `json:"source_id"`
    MatchDate    string `json:"match_date"`
    League       string `json:"league"`
    HomeTeam     string `json:"home_team"`
    AwayTeam     string `json:"away_team"`
    LineupKnown  bool   `json:"lineup_known"`
    ProviderKind string `json:"provider_kind"`
}

func handleMatches(w http.ResponseWriter, r *http.Request) {
    date := r.URL.Query().Get("date")
    
    // 调用 foot 的数据采集逻辑
    matches := fetchMatchesForDate(date)
    
    response := map[string]interface{}{
        "items": matches,
        "count": len(matches),
    }
    
    json.NewEncoder(w).Encode(response)
}

func main() {
    http.HandleFunc("/api/matches", handleMatches)
    http.ListenAndServe(":8080", nil)
}
```

#### 2. 配置 Python 客户端
```yaml
# c1/configs/availability_sources.yaml
providers:
  - type: http_source
    enabled: true
    name: foot_go_primary
    provider_kind: foot_go
    url: http://localhost:8080/api/matches?date={today}
    format: json
    items_key: items
    timeout_seconds: 30
    resolve_direct: false
    headers:
      Accept: application/json
```

#### 3. 启动 foot 服务
```bash
# 启动 foot HTTP 服务
cd foot
go run main.go

# 或编译后运行
go build -o foot.exe
./foot.exe
```

---

### 方案 B: CLI 模式

**架构：**
```
Python → subprocess → foot CLI → JSON 输出 → Python 解析
```

**优点：**
- 简单：不需要 HTTP 服务
- 直接：Python 直接调用 Go 程序

**缺点：**
- 耦合：每次调用都启动新进程
- 性能：启动开销较大

**实现步骤：**

#### 1. foot 提供 CLI 接口
```go
// foot/main.go
package main

import (
    "encoding/json"
    "flag"
    "fmt"
    "os"
)

func main() {
    date := flag.String("date", "", "Match date (YYYY-MM-DD)")
    flag.Parse()
    
    matches := fetchMatchesForDate(*date)
    
    output := map[string]interface{}{
        "items": matches,
        "count": len(matches),
    }
    
    json.NewEncoder(os.Stdout).Encode(output)
}
```

#### 2. Python 调用
```python
# c1/data/providers.py
import subprocess
import json

class FootGoProvider(AvailabilityProvider):
    provider_name = "foot_go_cli"
    
    def __init__(self, foot_exe_path: str, **kwargs):
        super().__init__(**kwargs)
        self.foot_exe = foot_exe_path
    
    def fetch_availability_snapshot(self, match_date: str) -> list[dict]:
        result = subprocess.run(
            [self.foot_exe, "--date", match_date],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"foot failed: {result.stderr}")
        
        data = json.loads(result.stdout)
        return data.get("items", [])
```

---

### 方案 C: 文件交换模式

**架构：**
```
foot (Go) → JSON 文件 → Python 读取 → FileAvailabilityProvider
```

**优点：**
- 最简单：不需要网络或进程通信
- 可靠：文件持久化

**缺点：**
- 延迟：需要定时任务
- 同步：需要文件锁

**实现步骤：**

#### 1. foot 输出 JSON 文件
```go
// foot/main.go
package main

import (
    "encoding/json"
    "os"
)

func main() {
    matches := fetchMatchesForToday()
    
    output := map[string]interface{}{
        "items": matches,
        "timestamp": time.Now().Format(time.RFC3339),
    }
    
    file, _ := os.Create("data/foot_matches.json")
    defer file.Close()
    
    json.NewEncoder(file).Encode(output)
}
```

#### 2. Python 读取文件
```yaml
# c1/configs/availability_sources.yaml
providers:
  - type: file_source
    enabled: true
    name: foot_go_file
    path: data/foot_matches.json
    format: json
    items_key: items
```

#### 3. 定时任务
```bash
# Windows 任务计划程序
# 每小时运行一次
schtasks /create /tn "FootDataFetch" /tr "E:\APP\foot\foot.exe" /sc hourly
```

---

## 推荐方案：HTTP 服务模式

### 完整实现

#### 1. foot HTTP 服务器
```go
// foot/server/main.go
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
    
    // 调用 foot 的数据采集逻辑
    matches := fetchMatchesForDate(date)
    
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

func fetchMatchesForDate(date string) []Match {
    // TODO: 实现实际的数据采集逻辑
    // 这里应该调用 foot 的核心采集功能
    return []Match{
        {
            SourceID:     "1234567",
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
}
```

#### 2. Python 配置
```yaml
# c1/configs/availability_sources.yaml
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
    request_delay_ms: 0
    headers:
      Accept: application/json
      User-Agent: V24-C1-Client/1.0
```

#### 3. 启动脚本
```powershell
# scripts/start_foot_server.ps1
$footPath = "E:\APP\foot\foot.exe"

if (Test-Path $footPath) {
    Write-Host "Starting foot HTTP server..."
    Start-Process -FilePath $footPath -WindowStyle Hidden
    Write-Host "foot server started on http://localhost:8080"
} else {
    Write-Host "Error: foot.exe not found at $footPath"
}
```

#### 4. 测试脚本
```python
# scripts/test_foot_integration.py
import requests
from datetime import datetime

def test_foot_server():
    """测试 foot HTTP 服务"""
    url = "http://localhost:8080/health"
    
    try:
        response = requests.get(url, timeout=5)
        print(f"✓ foot server is running: {response.json()}")
    except Exception as e:
        print(f"✗ foot server not responding: {e}")
        return False
    
    # 测试获取比赛数据
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"http://localhost:8080/api/matches?date={today}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        print(f"✓ Fetched {data['count']} matches for {today}")
        
        if data['items']:
            print("\nSample match:")
            match = data['items'][0]
            print(f"  {match['home_team']} vs {match['away_team']}")
            print(f"  League: {match['league']}")
            print(f"  Date: {match['match_date']} {match['match_time']}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to fetch matches: {e}")
        return False

if __name__ == "__main__":
    test_foot_server()
```

---

## 数据映射

### foot 输出 → C1 格式

```python
# c1/data/adapters.py
def normalize_foot_go_record(raw: dict) -> dict:
    """将 foot (Go) 的数据格式转换为 C1 标准格式"""
    return {
        "source_id": str(raw.get("source_id", "")),
        "match_date": str(raw.get("match_date", "")),
        "match_time": str(raw.get("match_time", "")),
        "league": str(raw.get("league", "")),
        "home_team": str(raw.get("home_team", "")),
        "away_team": str(raw.get("away_team", "")),
        "lineup_known": bool(raw.get("lineup_known", False)),
        "provider_kind": "foot_go",
        "metadata": {
            "home_odds": raw.get("home_odds"),
            "draw_odds": raw.get("draw_odds"),
            "away_odds": raw.get("away_odds"),
        },
    }
```

---

## 部署步骤

### 1. 编译 foot
```bash
cd E:\APP\foot
go build -o foot.exe server/main.go
```

### 2. 启动 foot 服务
```bash
./foot.exe
```

### 3. 更新配置
```bash
# 编辑 c1/configs/availability_sources.yaml
# 启用 foot_go_primary
```

### 4. 测试集成
```bash
python scripts/test_foot_integration.py
```

### 5. 验证数据流
```bash
python scripts/test_c1_availability_flow.py
```

---

## 监控和维护

### 健康检查
```python
# 定期检查 foot 服务状态
import requests

def check_foot_health():
    try:
        r = requests.get("http://localhost:8080/health", timeout=5)
        return r.status_code == 200
    except:
        return False
```

### 日志
```go
// foot 服务应该记录日志
log.Printf("[INFO] Fetched %d matches for %s", len(matches), date)
log.Printf("[ERROR] Failed to fetch data: %v", err)
```

### 重启策略
```powershell
# 监控脚本：如果 foot 服务挂了，自动重启
while ($true) {
    $process = Get-Process -Name "foot" -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host "foot service down, restarting..."
        Start-Process -FilePath "E:\APP\foot\foot.exe"
    }
    Start-Sleep -Seconds 60
}
```

---

## 性能优化

### 1. 缓存
```go
// foot 服务端缓存
var cache = make(map[string]CacheEntry)

type CacheEntry struct {
    Data      []Match
    Timestamp time.Time
}

func getCachedMatches(date string) ([]Match, bool) {
    entry, ok := cache[date]
    if !ok {
        return nil, false
    }
    
    // 缓存 5 分钟
    if time.Since(entry.Timestamp) > 5*time.Minute {
        return nil, false
    }
    
    return entry.Data, true
}
```

### 2. 并发控制
```python
# Python 客户端限流
import time
from threading import Lock

class FootGoClient:
    def __init__(self):
        self.last_request = 0
        self.lock = Lock()
    
    def fetch_matches(self, date):
        with self.lock:
            # 限制请求频率：每秒最多 1 次
            elapsed = time.time() - self.last_request
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
            
            response = requests.get(f"http://localhost:8080/api/matches?date={date}")
            self.last_request = time.time()
            return response.json()
```

---

## 总结

### 推荐方案
**HTTP 服务模式** - 最灵活、最标准

### 实施优先级
1. ✅ 编译 foot HTTP 服务器
2. ✅ 配置 availability_sources.yaml
3. ✅ 测试数据流
4. ✅ 部署到生产环境

### 预期收益
- **数据源多样化** - 不依赖单一 API
- **成本降低** - 自建采集，无 API 费用
- **灵活性** - Go 性能好，易于扩展
- **可靠性** - 多数据源备份

---

## 下一步

1. 检查 foot (Go) 项目是否已经存在
2. 如果存在，添加 HTTP 服务器代码
3. 如果不存在，从 GitHub 克隆或创建新项目
4. 集成到 C1.0 数据采集链

需要我帮你实现具体的集成代码吗？
