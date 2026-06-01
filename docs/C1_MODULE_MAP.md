# C1.0 Module Map

## Directory Structure

```
c1/
├── core/                    # 核心 schema 和 reason codes
│   ├── schema.py            # FeatureSnapshot, PredictionSnapshot, GovernanceDecision
│   └── reason_codes.py      # DecisionAction, ReasonCode, ReasonSeverity
│
├── data/                    # 数据层
│   ├── contracts.py         # CanonicalMatch, OddsSnapshot, TeamAvailability, MatchContext
│   ├── adapters.py          # V24 AppMatch → C1.0 contracts 适配器
│   ├── providers.py         # 可用性数据提供者链（HTTP/File/API-Football/Titan）
│   ├── provider_normalizers.py  # 提供者数据标准化
│   ├── availability.py      # 构建 TeamAvailability / MatchContext
│   ├── availability_store.py    # 可用性快照存储
│   ├── availability_templates.py # CSV 模板导出
│   ├── elo_loader.py        # ELO 评分加载
│   ├── fact_contracts.py    # MatchFact / ActionFact / SourceProvenance
│   ├── foot_bridge.py       # ★ foot MySQL 桥接器
│   └── foot_schema.py       # ★ foot 数据结构定义
│
├── features/                # 特征层
│   ├── governance_features.py   # 治理特征计算（info_quality, chaos_score 等）
│   └── foot_features.py    # ★ foot 信号特征提取和增强
│
├── inference/               # 推理层
│   ├── runtime.py           # C1InferenceEngine（主入口）
│   ├── baseline.py          # 基线推理（Market + ELO + Poisson）
│   ├── xgb_adapter.py       # XGBoost 适配器
│   ├── lightgbm_adapter.py  # LightGBM 适配器（待实现）
│   ├── calibration.py       # 集成权重校准
│   └── schema.py            # InferenceInput, InferenceResult, InferenceComponent
│
├── modules/                 # 治理层
│   └── judge.py             # GovernanceJudge + 5 Gates:
│                            #   InfoGate, EnvironmentGate, ConflictDetector,
│                            #   RiskGovernor, CircuitBreaker
│
├── translation/             # 翻译层
│   ├── engine.py            # C1TranslationEngine（5 种玩法）
│   ├── htft_translator.py   # HT/FT 翻译器
│   ├── scoreline_translator.py  # 比分翻译器
│   └── schema.py            # TranslationRequest, TranslationResult, TranslationItem
│
├── audit/                   # 审计层
│   └── store.py             # C1AuditStore（JSONL 记录）
│
├── runtime/                 # 运行时
│   ├── shadow.py            # C1ShadowRunner（完整管线）
│   ├── comparison.py        # V24 vs C1.0 对比框架
│   ├── legacy_bridge.py     # V24 AppMatch → C1.0 shadow run 桥接
│   ├── release.py           # 放行门控
│   ├── release_bridge.py    # 放行桥接
│   └── mode.py              # 运行模式管理
│
├── strategy/                # 策略层
│   ├── backtest.py          # 回测框架
│   ├── settlement_bridge.py # 结算桥接
│   └── schema.py            # 策略 schema
│
├── export/                  # 导出层
│   ├── analytics_exporter.py    # 分析导出
│   ├── decision_exporter.py     # 决策导出
│   └── recommendation_feed.py   # 推荐 feed
│
├── governance/              # 治理配置（空，逻辑在 modules/judge.py）
│
└── configs/                 # 配置文件
    ├── governance_cfg.yaml
    ├── translation_cfg.yaml
    ├── foot_bridge_cfg.yaml
    ├── runtime_mode.yaml
    ├── release_cfg.yaml
    ├── availability_sources.yaml
    └── source_bridge_cfg.json
```

## Key Dependencies

```
core/schema.py ← 被所有层引用
    ↑
data/ ← features/ ← inference/ ← modules/judge.py ← translation/
                                                          ↓
                                                     audit/store.py
                                                          ↓
                                                     runtime/shadow.py
```

## External Dependencies

| Module | Depends On | Notes |
|--------|-----------|-------|
| `data/foot_bridge.py` | pymysql, MySQL service | 可选，失败时静默降级 |
| `inference/baseline.py` | v24_app.models.* | ⚠️ 待独立化 |
| `inference/xgb_adapter.py` | v24_app.models.xgboost_v0 | ⚠️ 待独立化 |
| `features/governance_features.py` | data/foot_bridge (间接) | 通过 foot_features.py |

## ★ = foot (Go) 集成模块（本次新增）
