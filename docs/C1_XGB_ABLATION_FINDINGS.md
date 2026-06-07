# C1 XGBoost Ablation Findings

Generated on: 2026-06-08

## Scope

This note records the offline ablation matrix for the shared C1/V24 1X2 XGBoost feature set.

No production model was modified. No features were removed.

Inputs:

- Samples: `data/state/xgb_training_samples.json`
- Feature count: 38
- Tool: `xgb_ablation_matrix.py`
- Per-window limit: 10,000
- Train/test split: 70/30
- Seeds: 17, 42, 101

Ignored local report:

- `reports/feature_ablation/xgb_ablation_matrix_20260608_011914.*`

## Candidate Groups

| Group | Removed Features |
|---|---|
| `kelly_features` | `kelly_home`, `kelly_draw`, `kelly_away`, `kelly_draw_edge` |
| `match_time` | `match_minutes` |
| `recent_form_low_signal` | recent match/points/goals features from the stable bottom set |
| `market_low_signal` | `return_rate`, `market_overround` |
| `stable_bottom_40` | all 15 stable bottom-40% candidates from the importance report |

## Multi-Seed Results

Negative logloss, Brier, and ECE deltas are better. Positive accuracy deltas are better.

| Window | Group | Logloss Delta | Accuracy Delta | Brier Delta | ECE Delta |
|---|---|---:|---:|---:|---:|
| 2016-2018 | `kelly_features` | -0.000579 | -0.001445 | -0.000082 | +0.006414 |
| 2016-2018 | `match_time` | -0.000697 | +0.000333 | -0.000146 | +0.001336 |
| 2016-2018 | `recent_form_low_signal` | -0.000365 | +0.001666 | -0.000106 | +0.003601 |
| 2016-2018 | `market_low_signal` | -0.000755 | +0.001889 | -0.000132 | +0.001826 |
| 2016-2018 | `stable_bottom_40` | -0.000025 | -0.001223 | +0.000054 | +0.001398 |
| 2018-2020 | `kelly_features` | -0.000666 | +0.000667 | -0.000122 | -0.001527 |
| 2018-2020 | `match_time` | +0.000284 | -0.000333 | +0.000076 | +0.000270 |
| 2018-2020 | `recent_form_low_signal` | -0.001329 | +0.001000 | -0.000227 | -0.000131 |
| 2018-2020 | `market_low_signal` | -0.000196 | +0.001778 | +0.000012 | -0.003118 |
| 2018-2020 | `stable_bottom_40` | -0.002053 | +0.001778 | -0.000348 | +0.002704 |
| all-sample | `kelly_features` | -0.000657 | -0.001222 | -0.000135 | -0.000522 |
| all-sample | `match_time` | -0.000642 | -0.002000 | -0.000150 | +0.001273 |
| all-sample | `recent_form_low_signal` | +0.000011 | -0.000333 | +0.000050 | +0.003027 |
| all-sample | `market_low_signal` | -0.000268 | +0.001556 | -0.000137 | -0.001283 |
| all-sample | `stable_bottom_40` | +0.000269 | +0.001445 | +0.000067 | +0.001025 |

## Findings

1. The larger multi-seed run weakens the earlier "bottom 40% can be cut" hypothesis.
2. `stable_bottom_40` is not safe to remove:
   - 2016-2018 accuracy regressed.
   - all-sample logloss and Brier regressed.
   - ECE regressed in all three windows.
3. `kelly_features` are still weak candidates, but removal is not yet clean:
   - logloss and Brier improve in all windows,
   - accuracy regresses in 2016-2018 and all-sample,
   - ECE regresses materially in 2016-2018.
4. `market_low_signal` is mixed:
   - good all-sample accuracy/ECE movement,
   - but 2018-2020 Brier slightly regresses.
5. Feature deletion should remain blocked until a retrained model shows no logloss, Brier, ECE, or accuracy regression across windows.

## Decision

Do not remove any feature yet.

The correct next step is not deletion. It is specialist modeling:

1. Keep the full feature set intact.
2. Build a market/odds-only specialist as a sidecar signal.
3. Compare the specialist against full XGBoost on logloss, Brier, ECE, and accuracy.
4. Feed only proven specialist signals into governance after shadow validation.
