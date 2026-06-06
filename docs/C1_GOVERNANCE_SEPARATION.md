# C1.0 治理分离度（Governance Separation）验证记录

## 验收门槛
- 定义：`governance_separation = APPROVE 组准确率 - DOWNGRADE 组准确率`
- 门槛：`>= 0.05`（5%），由 `c1/runtime/mode.py` 中 `C1_PRIMARY_MIN_GOVERNANCE_SEPARATION` 强制。
- 该指标用于验证治理层是否真正"挑出"了更可靠的预测：APPROVE 组应显著优于被降级组。

## 背景：rollback_log 记录的 0.049 是测量假象（非阈值问题）

`c1/configs/runtime_mode.yaml` 的 rollback_log 记录治理分离度为 `0.049 < 0.05`，
据此回退到 `formal_list_default`。

本次复核发现，该读数是**采样污染**导致的测量假象，而非治理阈值需要调整：

- `t_match_his` 含两类数据：
  - **foot 原生数据**：358,434 场，2006-05 ~ 2020-04。带 `t_asia_his` / `t_euro_his`
    亚赔明细，可驱动 `FOOT_ASIA_SIGNAL_AGAINST_MODEL`、`FOOT_EURO_ASIA_CONFLICT`
    等治理冲突信号。
  - **football-data.co.uk 导入（`fdu_` 前缀）**：7,155 场，2021-2025。**没有**任何
    foot 信号表，亚赔/模型信号全部缺失。
- `shadow_run_history.py` 默认 `ORDER BY MatchDate DESC LIMIT N`，即"最新优先"。
  由于 `fdu_` 数据更新（2021-2025），默认采样会**全部命中 `fdu_` 数据**：
  - foot 信号可用率 0/1000
  - 治理冲突从不触发 → 100% APPROVE、0 DOWNGRADE
  - separation = N/A（被某些汇总口径记为 ~0）
- 此外 `t_analy_result`（foot 模型输出表）当前 **0 行**，因此
  `foot_model_agreement` 的 confirmed/weak/critical 标签结构性失效，
  只有亚赔/欧赔冲突信号可用。

## 在带信号的 foot 原生数据上的真实读数

新增 `--foot-native-only` 开关（排除 `fdu_%`），在带信号数据上复跑：

| 样本 | foot 信号可用 | APPROVE | DOWNGRADE | BLOCK | APPROVE acc | DOWNGRADE acc | separation | C1 acc | V24 acc |
|------|--------------|---------|-----------|-------|-------------|---------------|------------|--------|---------|
| 1000 | 894/1000 | 67.4% | 31.8% | 0.8% | 49.3% | 31.1% | **+18.1%** | 43.5% | 43.0% |
| 2000 | 1741/2000 | 71.7% | 26.9% | 1.5% | 47.0% | 34.1% | **+13.0%** | 43.5% | 43.2% |

结论：**现有治理阈值在带信号的数据上已稳定产生 13-18% 的分离度，远超 5% 门槛。无需调整任何阈值。**

## 报告项

按要求记录治理调整对各指标的影响。本次未改任何治理阈值（仅修正测量口径），对比如下：

- **APPROVE rate**：未因调整而下降（无阈值调整）。foot 原生数据上为 67-72%，
  落在验收期望的 50-75% 区间内。
- **DOWNGRADE/BLOCK 数量**：1000 场 → DOWNGRADE 318 / BLOCK 8；
  2000 场 → DOWNGRADE 537 / BLOCK 30。治理层确实在分流。
- **separation 是否超过 5%**：是，+13.0% ~ +18.1%。
- **是否牺牲整体 C1 准确率**：未牺牲。C1 在 foot 原生数据上为 43.5%，
  与 V24（43.0-43.2%）持平或略高（+0.4 ~ +0.5pp）。

## 对 c1_primary 切换的影响（重要）

- **治理分离度门槛在正确测量下已达标**（且无需调阈值）。
- 但 **accuracy 仍是硬阻断**：在 foot 原生数据上 C1 ≈ V24（+0.4pp），优势极小且样本相关；
  在 `fdu_` 数据上 C1 略低于 V24（-0.6pp）。accuracy re-fit 尚未进行。
- **结论：保持 `runtime_mode.yaml` = `formal_list_default`，不切 `c1_primary`。**
  即使分离度达标，accuracy 门槛未过，禁止切换。

## 复现命令

```powershell
$env:FOOT_MYSQL_PASSWORD='<password>'
$env:PYTHONIOENCODING='utf-8'
# 带信号的 foot 原生数据（用于治理分离度验证）
python shadow_run_history.py --limit 2000 --foot-native-only
# 默认采样（会命中无信号的 fdu_ 数据，分离度会塌为 N/A —— 不可用于验收）
python shadow_run_history.py --limit 2000
```

## 后续建议（accuracy re-fit 阶段处理，本次不做）
- 正式验收 shadow run 必须使用带信号的数据（`--foot-native-only` 或等价过滤），
  否则治理指标无意义。建议把这一约束写进验收脚本。
- `t_analy_result` 为空使 foot 模型共识信号失效。若要启用 `foot_model_agreement`
  的 confirmed/critical 路径，需要重新填充该表或改用其它模型输出来源。
