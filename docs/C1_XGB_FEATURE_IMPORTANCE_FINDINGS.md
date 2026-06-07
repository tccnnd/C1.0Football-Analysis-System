# C1 XGBoost Feature Importance Findings

Generated on: 2026-06-08

## Scope

This note summarizes the first XGBoost feature-importance pass for the C1/V24 shared 1X2 XGBoost feature set.

Inputs:

- Model: `data/models/xgb_v0_match_outcome.json`
- Samples: `data/state/xgb_training_samples.json`
- Feature count: 38
- Tool: `xgb_feature_importance_report.py`

Reports were generated under ignored local output:

- `reports/feature_importance/xgb_feature_importance_20260608_005311.*`
- `reports/feature_importance/xgb_feature_importance_20260608_005349.*`
- `reports/feature_importance/xgb_feature_importance_20260608_005350.*`

## Windows

| Window | Sample Limit | Baseline Logloss | Baseline Accuracy |
|---|---:|---:|---:|
| first 5,000 samples | 5,000 | 0.998780 | 49.98% |
| 2016-2018 | 5,000 | 0.993075 | 50.12% |
| 2018-2020 | 5,000 | 0.975097 | 52.38% |

## Strongest Signals

The strongest features are market/odds features. The top features in the first report were:

| Feature | Note |
|---|---|
| `market_home` | highest gain and positive permutation impact |
| `market_away` | high gain and strongest permutation accuracy impact |
| `odds_away` | strong built-in gain |
| `odds_home` | strong built-in gain |
| `market_balance` | strong built-in gain |
| `odds_draw` | meaningful, but weaker than home/away market signals |

This supports the expected domain view: market-implied probabilities and closing/opening odds carry most of the signal.

## Stable Bottom 40% Candidates

The same 15 features appeared in the bottom 40% across all three windows:

- `away_recent_goals_for_pg`
- `home_recent_goal_diff_pg`
- `home_recent_goals_for_pg`
- `home_recent_match_count`
- `home_recent_points_pg`
- `is_weekend`
- `kelly_away`
- `kelly_draw`
- `kelly_draw_edge`
- `kelly_home`
- `market_overround`
- `match_minutes`
- `recent_goal_diff_diff`
- `recent_points_diff`
- `return_rate`

Important: these are **review candidates only**, not removal decisions.

## Data Quality Flags

Several features are constant in the 5,000-sample report:

| Feature | Issue |
|---|---|
| `match_minutes` | `zero_rate=1.0`, `unique_count=1` |
| `kelly_home` | `zero_rate=1.0`, `unique_count=1` |
| `kelly_draw` | `zero_rate=1.0`, `unique_count=1` |
| `kelly_away` | `zero_rate=1.0`, `unique_count=1` |
| `kelly_draw_edge` | `zero_rate=1.0`, `unique_count=1` |

These features are likely not contributing under the current sample construction. The first fix may be upstream data population rather than deletion.

## Decision

Do not remove features yet.

Next step should be a windowed ablation matrix:

1. Train/evaluate an offline baseline on fixed windows.
2. Compare candidate feature sets against the full 38-feature model.
3. Use logloss, Brier, accuracy, and calibration drift as acceptance metrics.
4. Only remove a feature if multiple windows show no regression after retraining.

Candidate ablation groups:

- Kelly features: `kelly_home`, `kelly_draw`, `kelly_away`, `kelly_draw_edge`
- Time feature: `match_minutes`
- Recent-form low-impact group: recent points/goals/match-count features
- Market derived low-impact group: `return_rate`, `market_overround`

