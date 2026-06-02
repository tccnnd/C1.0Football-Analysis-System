# 系统完整审查与改进方案

**审查日期**: 2026-05-29  
**审查范围**: V24 + C1.0 + foot (Go) 集成全链路

---

## 一、当前系统状态总览

### 架构完成度

| C1.0 层 | 完成度 | 状态 |
|---------|--------|------|
| Data Layer | 95% | ✅ 完整（含 foot 桥接） |
| Feature Layer | 90% | ✅ 完整（含 foot 信号增强） |
| Inference Layer | 75% | ⚠️ LightGBM 未实现 |
| Governance Layer | 100% | ✅ 5 个 Gate 全部就绪 |
| Translation Layer | 100% | ✅ 5 种玩法独立翻译 |
| Audit Layer | 100% | ✅ 全链路审计 |

### 关键指标（Shadow Run 200 场）

| 指标 | 数值 | 评估 |
|------|------|------|
| V24 准确率 | 41.0% | ⚠️ 偏低 |
| C1.0 准确率 | 40.5% | ⚠️ 偏低 |
| APPROVE 率 | 0% | 🔴 严重问题 |
| DOWNGRADE 率 | 68% | 过高 |
| OBSERVE 率 | 31% | 过高 |
| BLOCK 率 | 1% | 正常 |
| 分歧率 | 9% | 正常 |

---

## 二、发现的问题（按优先级排序）

### P0 — 安全问题（立即修复）

| # | 问题 | 位置 | 风险 |
|---|------|------|------|
| 1 | MySQL 密码硬编码 | `c1/configs/foot_bridge_cfg.yaml` | 泄露风险 |
| 2 | API-Football Key 硬编码 | `c1/configs/availability_sources.yaml` | 泄露风险 |
| 3 | 测试脚本含明文密码 | `shadow_run_history.py`, `test_real_data.py` | 泄露风险 |
| 4 | .gitignore 未排除含密钥的 yaml | `.gitignore` | 推送风险 |

**修复方案**：
- 所有密码/密钥改用环境变量 `FOOT_MYSQL_PASSWORD`、`API_FOOTBALL_KEY`
- 配置文件中用占位符 `${FOOT_MYSQL_PASSWORD}`
- `.gitignore` 加入 `**/secrets.yaml`、`**/*.env`

---

### P1 — 0% APPROVE 率（系统无法产出有效建议）

**根因分析**：
1. `LINEUP_UNKNOWN` 在 200/200 场触发 → 历史数据无阵容信息
2. 即使排除 `LINEUP_UNKNOWN`，`FOOT_ASIA_SIGNAL_AGAINST_MODEL` 在 55/200 场触发
3. `observe_min_soft_conflicts=3`，但 2 个软冲突就已经触发 DOWNGRADE
4. 没有任何场次能通过所有 Gate 达到 APPROVE

**改进方案**：

```yaml
# 方案 A：对历史数据放宽 lineup 要求
thresholds:
  lineup_required_within_hours: 0.5  # 仅在开赛前 30 分钟才要求阵容
  # 或者：当 kickoff_hours_to_match > 24 时不触发 LINEUP_UNKNOWN

# 方案 B：降低 LINEUP_UNKNOWN 的严重性
# 当前是 SOFT，但它几乎总是触发，导致所有场次至少有 1 个软冲突
# 改为：仅在 kickoff_hours_to_match <= 2 时才触发

# 方案 C：调整 observe 阈值
decision_rules:
  observe_min_soft_conflicts: 4  # 从 3 提高到 4
```

**推荐**：方案 B + C 组合。`LINEUP_UNKNOWN` 应该只在临场（开赛前 2 小时内）才触发，而不是对所有比赛都触发。

---

### P1 — 准确率偏低（41%）

**根因分析**：
1. 样本偏差：200 场主要来自 2020 年小联赛（尼加拉瓜、白俄罗斯、布隆迪）
2. V24 没有这些联赛的 ELO 数据 → 使用默认评分 1500
3. 欧赔数据来自伟德（CompId=81），可能不是这些联赛的最佳参考
4. 三选一随机基线是 33%，41% 仅比随机高 8 个百分点

**改进方案**：
1. **扩大样本**：用主流联赛数据（英超、西甲、德甲）重新跑 shadow run
2. **联赛过滤**：shadow run 只选 `league_strength >= 0.90` 的联赛
3. **ELO 预热**：用 foot 历史数据预计算各队 ELO 评分
4. **多公司赔率**：用 Bet365（CompId=281）替代伟德作为欧赔参考

---

### P2 — LightGBM 未实现

**当前状态**：`c1/inference/lightgbm_adapter.py` 是空壳，返回 `not_implemented_phase4`

**改进方案**：
- 用 foot 历史数据（35 万场）训练 LightGBM 模型
- 特征集：foot 16 个信号 + V24 38 个特征 = 54 维
- 目标：1X2 分类（home/draw/away）
- 验证：与 XGBoost 对比准确率

---

### P2 — 缺失的迁移文档

AGENTS.md 要求 6 个文档，目前只有 2 个：

| 文档 | 状态 |
|------|------|
| C1_MIGRATION_AUDIT.md | ✅ 存在 |
| C1_GAP_MAP.md | ✅ 存在（详细） |
| C1_RUNTIME_PATHS.md | ❌ 缺失 |
| C1_TARGET_ARCHITECTURE.md | ❌ 缺失 |
| C1_MODULE_MAP.md | ❌ 缺失 |
| C1_MIGRATION_SEQUENCE.md | ❌ 缺失 |

---

### P2 — C1.0 仍然包裹 V24 模型

**当前状态**：
- `c1/inference/baseline.py` 直接 import `v24_app.models.elo_rating`
- `c1/inference/xgb_adapter.py` 直接 import `v24_app.models.xgboost_v0`
- C1.0 无法独立于 V24 运行

**改进方案**：
1. 将 ELO/Poisson/Ensemble 核心算法复制到 `c1/inference/engines/`
2. XGBoost 模型文件直接由 C1.0 加载（不经过 V24 包装）
3. 最终目标：`c1/` 可以独立 `import` 和运行

---

### P3 — 性能问题

| 问题 | 影响 | 方案 |
|------|------|------|
| foot_bridge 每场 6+ 次 MySQL 查询 | shadow run 慢 | 合并为 1-2 次 JOIN 查询 |
| shadow_run_history.py 串行执行 | 200 场需 44s | 用 ThreadPoolExecutor 并行 |
| MySQL 服务不稳定（频繁停止） | 测试中断 | 已注册为 Windows 服务（已修复） |

---

### P3 — 仓库卫生

**应删除的文件**：
- `do_import.bat`, `do_import2.bat` — 一次性导入脚本
- `foot_schema_err.txt`, `foot_schema_out.txt`, `import_err.txt`, `import_out.txt` — 导入日志
- `foot_0408.zip` — 2GB 压缩包不应在仓库中
- `mysql_my.ini` — MySQL 配置不属于项目
- `src/v24_app/ui.py.backup_phase1` — 备份文件
- `c1/configs/availability_sources.yaml.bak_canary_api` — 备份配置

---

## 三、改进路线图

### 阶段 1：安全修复 + APPROVE 率修复（1-2 天）

1. 密码外部化（环境变量）
2. 修复 `LINEUP_UNKNOWN` 触发逻辑（仅临场触发）
3. 调整 `observe_min_soft_conflicts` 为 4
4. 重新跑 shadow run 验证 APPROVE 率 > 0

### 阶段 2：准确率提升（3-5 天）

1. 用主流联赛数据重新跑 shadow run
2. 用 foot 历史数据预计算 ELO 评分
3. 实现 LightGBM 模型（用 foot 54 维特征训练）
4. 对比 XGBoost vs LightGBM vs Ensemble 准确率

### 阶段 3：独立化 + 文档（3-5 天）

1. 将 ELO/Poisson 核心算法复制到 `c1/inference/engines/`
2. C1.0 独立运行验证
3. 补齐 4 个缺失的迁移文档
4. 清理仓库（删除临时文件、备份文件）

### 阶段 4：性能优化 + UI 完善（2-3 天）

1. foot_bridge 查询合并（6 次 → 2 次）
2. shadow run 并行化
3. 模型中心 UI 按钮功能实现
4. 监控仪表板接入实时数据

---

## 四、架构建议

### 4.1 LINEUP_UNKNOWN 逻辑重构

当前逻辑：
```python
if not lineup_known and lineup_required_now:
    # 触发 LINEUP_UNKNOWN
```

建议改为：
```python
# 仅在开赛前 2 小时内且阵容未知时触发
lineup_required_now = (
    kickoff_hours_to_match is not None
    and 0 < kickoff_hours_to_match <= lineup_required_within_hours
)
```

这样历史数据（`kickoff_hours_to_match=None` 或已过期）不会触发此 Gate。

### 4.2 foot 信号权重自适应

当前 foot 信号权重是固定的。建议：
- 用 shadow run 结果反馈调整权重
- 当 `foot_euro_asia_conflict` 场次准确率 < 35% 时，提升其 chaos 贡献
- 当 `foot_model_confirmed` 场次准确率 > 50% 时，降低 observe 阈值

### 4.3 数据源多样化

当前 foot 数据源（win007）已失效。建议：
- 接入 V24 的 500.com 数据到 foot MySQL（写转换脚本）
- 或接入 Titan 数据到 foot MySQL
- 保持 foot MySQL 作为统一的历史数据仓库

### 4.4 模型训练闭环

当前缺失：foot 历史数据 → 训练 → 模型更新 → 验证 的闭环。

建议新增：
```
foot MySQL (35万场) → 特征提取 → 训练集
    → XGBoost/LightGBM 训练
    → 模型文件 → C1.0 Inference
    → Shadow Run 验证 → 反馈
```

---

## 五、总结

**系统整体健康度：7/10**

优势：
- C1.0 架构完整，6 层全部实现
- Governance 层设计精良，5 个 Gate 逻辑清晰
- foot 集成完整，从 MySQL 到 Feature 到 Governance 全链路打通
- 审计层完善，全链路可追溯
- Shadow run 基础设施就绪

劣势：
- 0% APPROVE 率 = 系统无法产出有效建议（最紧急）
- 准确率偏低（样本偏差 + 缺少 ELO 预热）
- 安全隐患（硬编码密码）
- C1.0 仍依赖 V24（未独立化）

**下一步最高优先级**：修复 LINEUP_UNKNOWN 逻辑，让系统能产出 APPROVE 决策。
