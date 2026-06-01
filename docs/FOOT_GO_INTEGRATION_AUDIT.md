# foot (Go) 项目集成审计

## 1. 仓库概况

| 仓库 | 地址 | 特点 |
|------|------|------|
| aoe5188/foot | https://gitee.com/aoe5188/foot | 主仓库，结构最精简，无 foot-robot |
| ryvius_key/foot | https://gitee.com/ryvius_key/foot | 最完整分支，含 A1~Q1 全部模型、盈利分析文档、SQL 查询集 |
| xuhanga/foot | https://gitee.com/xuhanga/foot | 含大小球/必发交易量爬虫，功能介于两者之间 |

**结论：以 ryvius_key 为主要参考源**（模型最全、文档最完整）。

---

## 2. foot 项目架构

```
foot-parent (Go monorepo)
├── foot-api        实体类 (struct/pojo)，无业务逻辑
├── foot-core       核心业务：CRUD + 分析模型 + 推送
│   └── module/
│       ├── analy/service/   ← 所有分析模型在此
│       ├── match/service/   赛事数据库操作
│       ├── odds/service/    赔率数据库操作
│       ├── elem/service/    联赛/球队基础数据
│       ├── leisu/           雷速推送
│       └── wechat/          微信公众号推送
├── foot-spider     爬虫：win007 数据源
├── foot-gui        Windows 桌面 GUI（walk 框架）
├── foot-robot      窗口自动化机器人
└── foot-web        Web API（未完成）
```

**数据流：**
```
win007 爬虫 → MySQL(foot库) → 分析模型 → t_analy_result → 雷速/微信推送
```

---

## 3. 分析模型清单

| 模型 | 文件 | 核心逻辑 | 输出 |
|------|------|----------|------|
| **A1** | A1Service.go | 欧赔(81/616)与亚赔方向相反时触发 | 主(3) / 客(0) |
| A2 | A2Service.go | 亚赔为基准，复杂逻辑，开发中 | 主/客 |
| A3 | A3Service.go | 亚赔变化分析 | 主/客 |
| **C1** | C1Service.go | 纯基本面：积分榜+对战历史+近期战绩+未来赛事 → 计算BF让球，与盘口对比 | 主(3) |
| C2 | C2Service.go | C1变体 | 主/客 |
| C3 | C3Service.go | C1变体 | 主/客 |
| C4 | C4Service.go | C1变体 | 主/客 |
| **E1** | E1Service.go | 欧赔变化分析 | 主/客 |
| **E2** | E2Service.go | 欧赔616与104即时/初盘差异，单边防平双选 | 主(3) |
| E3 | E3Service.go | E2变体 | 主/客 |
| Q1 | Q1Service.go | 竞彩官方 vs 波菜即时盘对比 | 主/客 |

**核心模型（已验证有盈利区间）：C1、C2、E2**

---

## 4. 数据库表结构（MySQL `foot` 库）

| 表名 | 说明 | 行数级别 |
|------|------|----------|
| t_match_last | 当日比赛临时表 | ~3K |
| t_match_his | 历史比赛表 | ~400K |
| t_asia_his | 亚赔历史（初/即时） | ~2M |
| t_asia_track | 亚赔变化过程 | ~2.7M |
| t_euro_his | 欧赔历史（初/即时） | ~2.2M |
| t_euro_track | 欧赔变化过程 | ~900K |
| t_euro_last | 欧赔临时表 | ~36 |
| t_asia_last | 亚赔临时表 | ~155 |
| t_b_f_score | 积分榜 | ~1.5M |
| t_b_f_battle | 主客队对战历史 | ~360K |
| t_b_f_jin | 近期战绩 | ~500K |
| t_b_f_future_event | 未来赛事 | ~1M |
| t_analy_result | 分析预测结果 | ~124K |
| t_league | 联赛表 | ~1.1K |
| t_comp | 波菜公司表 | ~40 |

**关键赔率公司 ID：**
- `81` = 伟德
- `616` = 888Sport  
- `104` = Interwetten
- `281` = Bet365
- `18` = 18Bet / Crown / 明陞 / 金宝博（亚赔参考）

---

## 5. 与 V24/C1.0 的能力对比

### foot (Go) 提供的能力

| 能力 | 状态 | 对应 V24/C1.0 |
|------|------|---------------|
| 亚赔爬取（初盘+即时+变化） | ✅ 完整 | V24 部分有，C1.0 缺 |
| 欧赔爬取（多公司+变化） | ✅ 完整 | V24 部分有 |
| 积分榜/对战历史/近期战绩 | ✅ 完整 | V24 无 |
| 未来赛事 | ✅ 完整 | V24 无 |
| A1 模型（欧亚联动） | ✅ 完整 | V24 无 |
| C1 模型（BF让球基本面） | ✅ 完整 | C1.0 有同名但逻辑不同 |
| E2 模型（欧赔单边防平） | ✅ 完整 | V24 无 |
| 结果自动回填 | ✅ 完整 | V24 有 |
| 微信/雷速推送 | ✅ 完整 | V24 无 |
| XGBoost/ELO 模型 | ❌ 无 | V24/C1.0 核心 |
| 治理层（Governance） | ❌ 无 | C1.0 核心 |
| 置信度/EV 计算 | ❌ 无 | V24/C1.0 有 |

### 关键差异

1. **foot 的 C1 ≠ C1.0 的 C1**
   - foot C1 = 基本面让球计算（积分榜+战绩+未来赛事 → BF让球 vs 盘口让球）
   - C1.0 = 整个治理平台架构（Governance/Translation/Audit 层）
   - 命名冲突，需要在文档中明确区分

2. **foot 是数据采集+规则模型，V24/C1.0 是统计学习模型**
   - foot 的模型是手工规则（if/else 逻辑）
   - V24/C1.0 是 XGBoost + ELO + Poisson 概率模型
   - 两者互补，不互斥

3. **foot 依赖 MySQL，V24 依赖 JSON 文件状态存储**
   - 集成需要数据桥接层

---

## 6. 集成策略

### 方案：数据桥接 + 信号输入

**不直接运行 foot 的 Go 代码**，而是：

```
foot (Go) 运行 → MySQL t_analy_result
                        ↓
              Python 桥接层（读取 MySQL）
                        ↓
              C1.0 Feature Layer（作为信号特征）
                        ↓
              C1.0 Governance Layer（决策）
```

### 具体集成点

#### 集成点 1：亚赔变化信号 → Feature Layer
- foot 的 `AsiaDirection()` 逻辑 → 转为 `asia_direction_signal` 特征字段
- 亚赔初盘/即时盘差异 → `asia_odds_move` 特征

#### 集成点 2：欧亚联动信号 → Feature Layer  
- foot A1 模型的 `EuroDirection()` + `AsiaDirectionMulti()` → `euro_asia_conflict` 特征
- 直接映射为 C1.0 ConflictDetector 的输入

#### 集成点 3：基本面数据 → Feature Layer
- 积分榜排名差 → `ranking_diff` 特征（C1 模型核心）
- 近期战绩胜率 → `recent_win_rate_home/away`（V24 已有，可对齐）
- 对战历史 → `h2h_win_rate` 特征

#### 集成点 4：foot 模型结论 → Governance 信号
- `t_analy_result` 中的 A1/C1/E2 结论 → 作为 `external_signal` 输入 Governance
- 多模型一致性 → ConflictDetector 的 `market_divergence_conflict`

---

## 7. 实施路线图

### Phase 1：数据桥接（优先）
- [ ] 创建 `c1/data/foot_bridge.py`：连接 MySQL foot 库，读取 `t_analy_result`
- [ ] 创建 `c1/data/foot_schema.py`：定义 foot 数据的 Python 数据类
- [ ] 配置 `c1/configs/foot_bridge_cfg.yaml`：MySQL 连接配置

### Phase 2：特征提取
- [ ] 将 foot A1/C1/E2 结论映射为 C1.0 特征字段
- [ ] 将亚赔变化方向映射为 `asia_move_signal` 特征
- [ ] 将欧亚联动信号映射为 `euro_asia_signal` 特征

### Phase 3：Governance 集成
- [ ] 在 ConflictDetector 中增加 `foot_signal_conflict` 检测
- [ ] 多模型一致时提升置信度，冲突时触发 OBSERVE/DOWNGRADE

### Phase 4：Shadow Run 对比
- [ ] 并行运行 foot 模型结论 vs V24/C1.0 结论
- [ ] 记录一致率和分歧点
- [ ] 在 C1.0 审计层记录 foot 信号来源

---

## 8. 风险点

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| MySQL 依赖 | foot 需要独立 MySQL 实例 | 可用 SQLite 做本地镜像，或直接读 CSV 导出 |
| 数据时效性 | foot 爬虫需要持续运行才有数据 | 先用历史数据验证，再接实时 |
| 命名冲突 | foot C1 ≠ C1.0 架构 | 在代码中统一用 `foot_c1` 区分 |
| Go 未安装 | 无法直接编译运行 foot | 通过 MySQL 桥接，不需要编译 Go |
| 爬虫合规 | win007 数据爬取 | 仅用于个人研究，不商业化 |

---

## 9. 下一步行动

**立即可做（不需要 Go 环境）：**
1. 安装 MySQL，导入 foot 历史数据（百度网盘链接在 README 中）
2. 创建 `c1/data/foot_bridge.py` 数据桥接模块
3. 将 C1/A1/E2 模型逻辑用 Python 重写为特征提取函数

**需要 Go 环境后：**
4. 安装 Go 1.13+，配置 GOPATH
5. 运行 foot 爬虫采集实时数据
6. 接入 C1.0 实时特征流

---

## 10. 三仓库差异对比

| 功能 | aoe5188 | ryvius_key | xuhanga |
|------|---------|------------|---------|
| 基础模型 A1/C1/E2 | ✅ | ✅ | ✅ |
| Q1 模型 | ❌ | ✅ | ❌ |
| A2/A3 模型 | ❌ | ✅ | ❌ |
| 大小球指数爬虫 | ❌ | ❌ | ✅ |
| 必发交易量 | ❌ | ❌ | ✅ |
| 盈利区间文档 | ❌ | ✅ | ❌ |
| SQL 查询集 | ❌ | ✅ | ❌ |
| foot-robot | ❌ | ✅ | ✅ |
| blog 目录 | ❌ | ✅ | ❌ |

**推荐：以 ryvius_key 为集成基础，补充 xuhanga 的大小球/必发爬虫。**
