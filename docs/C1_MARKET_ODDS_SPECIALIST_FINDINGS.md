# C1 Market/Odds Specialist Findings

Generated on: 2026-06-08

## Scope

This note records the first offline baseline for a market/odds-only C1 specialist.

No production model was modified. No runtime mode was changed. This is a research and governance-sidecar candidate only.

Inputs:

- Samples: `data/state/xgb_training_samples.json`
- Baseline: full 38-feature XGBoost feature set
- Tool: `market_odds_specialist_report.py`
- Per-window limit: 10,000
- Train/test split: 70/30
- Seeds: 17, 42, 101

Ignored local report:

- `reports/market_odds_specialist/market_odds_specialist_20260608_012022.*`

## Candidate Feature Sets

| Feature Set | Count | Features |
|---|---:|---|
| `market_implied_core` | 6 | `market_home`, `market_draw`, `market_away`, `odds_home`, `odds_draw`, `odds_away` |
| `market_movement` | 15 | core + opening odds, odds drops, `market_balance`, `return_rate`, `market_overround` |
| `market_movement_with_kelly` | 19 | movement + `kelly_home`, `kelly_draw`, `kelly_away`, `kelly_draw_edge` |

## Results

Deltas compare each specialist against the full XGBoost feature set on the same split and seed.

Negative logloss, Brier, and ECE deltas are better. Positive accuracy deltas are better.

| Window | Specialist | Logloss Delta | Accuracy Delta | Brier Delta | ECE Delta | Specialist Accuracy |
|---|---|---:|---:|---:|---:|---:|
| 2016-2018 | `market_implied_core` | -0.001474 | -0.000445 | -0.000330 | -0.001089 | 0.498111 |
| 2016-2018 | `market_movement` | -0.000095 | +0.002333 | -0.000064 | -0.003826 | 0.500889 |
| 2016-2018 | `market_movement_with_kelly` | -0.000206 | +0.002000 | -0.000071 | -0.005984 | 0.500556 |
| 2018-2020 | `market_implied_core` | -0.002483 | +0.003889 | -0.000544 | -0.005956 | 0.500889 |
| 2018-2020 | `market_movement` | -0.001664 | +0.000111 | -0.000289 | -0.002004 | 0.497111 |
| 2018-2020 | `market_movement_with_kelly` | -0.001728 | +0.001778 | -0.000241 | -0.001062 | 0.498778 |
| all-sample | `market_implied_core` | -0.001174 | +0.006445 | -0.000328 | -0.001246 | 0.492556 |
| all-sample | `market_movement` | +0.000727 | +0.007000 | +0.000188 | -0.001505 | 0.493111 |
| all-sample | `market_movement_with_kelly` | +0.000725 | +0.000667 | +0.000162 | -0.000737 | 0.486778 |

## Findings

1. `market_implied_core` is the strongest first specialist candidate.
   - It improves logloss, Brier, and ECE in every tested window.
   - Accuracy is roughly flat in 2016-2018 and improves in 2018-2020 plus all-sample.
2. Adding movement features is not uniformly better.
   - It improves accuracy and ECE, but all-sample logloss and Brier regress.
3. Adding Kelly features is not yet justified.
   - It helps some calibration windows, but the all-sample logloss/Brier regression remains.
4. The specialist should not replace C1 or V24.
   - Its best use is as a calibrated sidecar signal for governance: market agreement, market disagreement, market entropy, and high-risk downgrade logic.

## Decision

Start with `market_implied_core` as the first Market/Odds Specialist candidate.

Next implementation steps:

1. Add a pure inference-side market specialist that consumes the six implied-market features.
2. Emit:
   - `market_specialist_probabilities`,
   - `market_specialist_confidence`,
   - `market_specialist_entropy`,
   - `market_specialist_disagreement_with_c1`.
3. Keep it out of production selection until a shadow run proves:
   - no C1 accuracy regression,
   - Brier/logloss/ECE improvement or stability,
   - governance separation remains above 5%,
   - `runtime_mode.yaml` remains `formal_list_default` until release gates pass.
