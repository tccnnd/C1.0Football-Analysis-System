# C1 XGBoost Ablation Findings

Generated on: 2026-06-08

## Scope

This note records the first offline ablation matrix for the shared C1/V24 1X2 XGBoost feature set.

No production model was modified. No features were removed.

Inputs:

- Samples: `data/state/xgb_training_samples.json`
- Feature count: 38
- Tool: `xgb_ablation_matrix.py`
- Per-window limit: 5,000
- Train/test split: 70/30
- Seed: 42

Ignored local report:

- `reports/feature_ablation/xgb_ablation_matrix_20260608_010812.*`

## Candidate Groups

| Group | Removed Features |
|---|---|
| `kelly_features` | `kelly_home`, `kelly_draw`, `kelly_away`, `kelly_draw_edge` |
| `match_time` | `match_minutes` |
| `recent_form_low_signal` | recent match/points/goals features from the stable bottom set |
| `market_low_signal` | `return_rate`, `market_overround` |
| `stable_bottom_40` | all 15 stable bottom-40% candidates from the importance report |

## Results

| Window | Group | Logloss Delta | Accuracy Delta |
|---|---|---:|---:|
| 2016-2018 | `kelly_features` | +0.000537 | -0.006667 |
| 2016-2018 | `match_time` | +0.001363 | +0.000000 |
| 2016-2018 | `recent_form_low_signal` | +0.001472 | +0.002666 |
| 2016-2018 | `market_low_signal` | +0.002267 | +0.001333 |
| 2016-2018 | `stable_bottom_40` | -0.001021 | +0.000666 |
| 2018-2020 | `kelly_features` | +0.002026 | -0.002000 |
| 2018-2020 | `match_time` | +0.002224 | -0.012000 |
| 2018-2020 | `recent_form_low_signal` | -0.002251 | -0.003334 |
| 2018-2020 | `market_low_signal` | -0.000849 | -0.000667 |
| 2018-2020 | `stable_bottom_40` | -0.001917 | -0.004000 |
| all-sample | `kelly_features` | -0.000234 | +0.002000 |
| all-sample | `match_time` | +0.000753 | +0.002666 |
| all-sample | `recent_form_low_signal` | -0.004230 | +0.004000 |
| all-sample | `market_low_signal` | -0.002676 | +0.006000 |
| all-sample | `stable_bottom_40` | -0.001976 | +0.013333 |

Negative logloss delta is better. Positive accuracy delta is better.

## Findings

1. The full `stable_bottom_40` group improved logloss in all three windows.
2. The same group slightly reduced accuracy in the 2018-2020 window, so it is not yet a safe removal.
3. Single-group removals are not uniformly safe:
   - `kelly_features` worsened logloss in two windows despite being constant in the importance sample.
   - `match_time` worsened logloss in all three windows and materially hurt 2018-2020 accuracy.
   - `recent_form_low_signal` and `market_low_signal` were mixed by window.
4. This suggests interactions between weak features matter after retraining, and feature deletion should be validated as grouped model design, not single-column cleanup.

## Decision

Do not remove any feature yet.

The next validation step should add:

1. Multiple seeds.
2. Larger sample limits.
3. Brier and calibration drift metrics in the ablation matrix.
4. A formal acceptance rule, for example:
   - no window has worse logloss by more than 0.001,
   - no window has worse accuracy by more than 0.002,
   - C1 calibration ECE/Brier does not regress,
   - production `runtime_mode.yaml` remains unchanged.
