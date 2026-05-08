# C1 Migration Audit

Updated: 2026-04-03  
Repository: `E:\APP\ELO`

## Scope

This audit treats the current repository as legacy V24. The goal is inventory first, not refactor. Findings below are grounded in the live runtime code under `src/v24_app`, launcher scripts, persisted state, and generated reports.

## Executive Summary

The current system is operational, but the architectural center of gravity is concentrated in [`core.py`](/E:/APP/ELO/src/v24_app/core.py). That file currently owns:

- data ingestion orchestration
- market enrichment
- market snapshot persistence
- prediction assembly
- play translation
- parlay generation
- settlement
- Gate metrics
- model calibration
- backtest/report generation

This means V24 is not layered in practice. It is a working vertical slice with multiple architectural responsibilities fused into a single runtime module.

The strongest reusable assets for C1.0 are:

- standardized match carrier: `AppMatch`
- state persistence primitives in [`state_store.py`](/E:/APP/ELO/src/v24_app/storage/state_store.py)
- individual model adapters under [`models/`](/E:/APP/ELO/src/v24_app/models)
- historical sample import pipeline in [`training_samples.py`](/E:/APP/ELO/src/v24_app/training_samples.py)
- market-intent feature builder in [`market_features.py`](/E:/APP/ELO/src/v24_app/market_features.py)

The most coupled areas that should not be migrated as-is are:

- `fetch_matches_v24()`
- `_predict_match_with_inputs()`
- `settle_match_result()`
- `auto_settle_finished_matches()`
- calibration/backtest functions in `core.py`
- UI-driven operational flows in [`ui.py`](/E:/APP/ELO/src/v24_app/ui.py)

## Current Entrypoints

### Application Entrypoints

- [`launcher.py`](/E:/APP/ELO/launcher.py)
  - changes cwd to repo root
  - prepends `src/` to `sys.path`
  - imports `v24_app.ui.main`
- [`src/v24_app/__main__.py`](/E:/APP/ELO/src/v24_app/__main__.py)
  - imports and runs `ui.main`
- [`start_ai_system_fixed.bat`](/E:/APP/ELO/start_ai_system_fixed.bat)
  - Windows launcher wrapper
- [`启动器.py`](/E:/APP/ELO/启动器.py)
  - alternate launcher file

### CLI / Maintenance Entrypoints

- [`scripts/auto_fetch_results.py`](/E:/APP/ELO/scripts/auto_fetch_results.py)
  - runs `auto_settle_finished_matches()`
- [`scripts/import_historical_samples.py`](/E:/APP/ELO/scripts/import_historical_samples.py)
  - imports historical data into `xgb_training_samples.json`
  - optionally retrains XGB and syncs Elo
- [`scripts/train_xgb_v0.py`](/E:/APP/ELO/scripts/train_xgb_v0.py)
  - trains outcome XGB
- [`scripts/migrate_prediction_snapshots.py`](/E:/APP/ELO/scripts/migrate_prediction_snapshots.py)
  - snapshot migration helper
- [`scripts/fix_launcher.py`](/E:/APP/ELO/scripts/fix_launcher.py)
  - support utility, not core runtime

## Runtime Pipelines

### 1. Pre-match Runtime

Actual runtime path:

`UI -> refresh_matches() -> fetch_matches_v24() -> predict_match() -> persist_prediction_snapshot() -> UI detail/render/export`

Key observations:

- UI directly triggers data fetch and snapshot sync.
- `fetch_matches_v24()` owns source selection, stale cache fallback, fixture guards, market-intent enrichment, and market snapshot persistence.
- `predict_match()` is not pure inference. It also performs translation, play filtering, specialist takeover, and output packaging.

### 2. Result Recovery and Settlement

Actual runtime path:

`UI/button or auto task -> auto_settle_finished_matches() -> settle_match_result() -> append settlement -> append training sample -> update Elo -> auto settle parlays -> compute Gate`

Key observations:

- auto recovery uses Titan schedule stream plus snapshot fallback by `source_id`
- settlement updates both business records and training data
- Gate is derived after settlement, not upstream
- parlay settlement depends on single-settlement records

### 3. Training / Calibration / Backtest

Actual runtime path:

- outcome model: `train_xgb_v0_now()`
- play models: `train_play_models_now()`
- ensemble weights: `calibrate_ensemble_weights_now()`
- play thresholds: `calibrate_play_thresholds_now()`
- play-model policy: `calibrate_play_model_policy_now()`
- reports:
  - `run_ensemble_backtest()`
  - `run_play_model_backtest()`

Key observations:

- all of these live in `core.py`
- all of them read from the same persisted state pool
- calibration logic and runtime decision logic share data contracts but are not isolated into separate services

## Data Sources

### Primary Source

- [`match_fetcher_titan.py`](/E:/APP/ELO/src/v24_app/data_sources/match_fetcher_titan.py)
  - active source for fixture list, odds, handicap line, finished matches, and schedule-id result lookup
  - current source of truth for operational match recovery

Capabilities:

- today/upcoming fixtures
- recent finished fixtures
- result lookup by `schedule_id`
- issue-based filtering
- odds merge from separate Titan odds feed

Risks:

- external text format is brittle
- source names and comments still include mojibake
- fetch logic and source repair are embedded in one class

### Secondary / Supplemental Source

- [`market_intent_500.py`](/E:/APP/ELO/src/v24_app/data_sources/market_intent_500.py)
  - enriches matches with:
    - opening odds
    - instant odds
    - return rate
    - kelly home/draw/away

Capabilities:

- fixture matching by normalized team names
- per-fixture market snapshot aggregation over selected companies

Risks:

- team matching is heuristic
- enrichment happens inline during fetch orchestration
- current runtime only uses 500 as enrichment, not as first-class source

### Legacy / Residual Source

- [`match_fetcher_500.py`](/E:/APP/ELO/src/v24_app/data_sources/match_fetcher_500.py)
  - older scraper implementation
  - large amount of legacy text corruption
  - not the preferred runtime source anymore

Audit judgement:

- keep only as reference during migration
- do not use as C1.0 base implementation

## Feature Builders

### Explicit Feature Builders

- [`market_features.py`](/E:/APP/ELO/src/v24_app/market_features.py)
  - computes return-rate and market-intent derived features
- [`training_samples.py`](/E:/APP/ELO/src/v24_app/training_samples.py)
  - historical-row normalization
  - chronological Elo rebuild
  - recent-form aggregation
  - training sample generation

### Implicit Feature Builders Embedded in Runtime

- `_base_market_probs()` in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)
- `_recent_form_features_for_match()` in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)
- `_draw_market_score()` in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)
- `_side_market_score()` in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)
- `_handicap_specialist_blend()` in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)

Audit judgement:

- V24 does not have a single feature layer
- some features are reusable
- some are embedded in decision code and need extraction before C1.0

## Models and Inference Logic

### Base Models

- [`elo_rating.py`](/E:/APP/ELO/src/v24_app/models/elo_rating.py)
  - Elo inference and post-match update
- [`poisson.py`](/E:/APP/ELO/src/v24_app/models/poisson.py)
  - score distribution, total goals, HT/FT probabilities
- [`xgboost_v0.py`](/E:/APP/ELO/src/v24_app/models/xgboost_v0.py)
  - 1X2 XGBoost probability model
- [`play_xgboost.py`](/E:/APP/ELO/src/v24_app/models/play_xgboost.py)
  - total-goals model
  - scoreline model
  - volatile scoreline model
- [`ensemble.py`](/E:/APP/ELO/src/v24_app/models/ensemble.py)
  - weighted combination of market / elo / poisson / xgboost

### Runtime Inference Assembly

Main assembly function:

- `_predict_match_with_inputs()` in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)

What it currently does:

- resolves base market probabilities
- builds `EnsembleContext`
- applies league-specific ensemble weights
- gets component outputs
- derives Poisson play outputs
- derives handicap probabilities from score distribution
- fuses specialist probabilities
- computes draw takeover
- applies play-model takeover for total goals and scoreline
- computes indices
- applies play thresholds
- applies play policy
- packages UI/business-facing output dictionary

This is the single biggest mixed-responsibility function in the repository.

## Governance / Risk Controls

Current governance logic exists, but it is scattered and partly merged into inference.

### Explicit Governance

- `fixture_source_guard` / `fixture_page_guard` behavior in `fetch_matches_v24()`
- `get_gate_metrics()` / `_gate_metrics_from_records()` in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)
- play thresholds from `play_thresholds_v1.json`
- play model policy from `play_model_policy_v1.json`
- breaker logic based on `losing_streak`

### Embedded Governance Mixed Into Inference

- draw takeover rule in `_predict_match_with_inputs()`
- recommendation confidence thresholding
- scoreline takeover gating
- total-goals takeover gating
- parlay leg eligibility gating

This means V24 governance is not a clean “post-inference policy layer”. It is partly:

- pre-output filtering
- partly recommendation translation
- partly runtime model override

## Translation Layer (Current State)

V24 has a translation concern, but it is not isolated.

Current translation duties include:

- mapping probabilities to 1X2 pick
- mapping Poisson scores to handicap / total goals / score / HTFT outputs
- applying play policy to decide:
  - display-only
  - single eligible
  - parlay eligible
- generating parlay legs and tickets

Where it currently lives:

- mostly inside `_predict_match_with_inputs()`
- plus parlay helpers in [`core.py`](/E:/APP/ELO/src/v24_app/core.py)
- plus UI formatting in [`ui.py`](/E:/APP/ELO/src/v24_app/ui.py)

This is a direct architecture violation for C1.0. Model outputs and betting translation are currently intertwined.

## Audit Layer (Current State)

Audit artifacts exist, but the audit layer is only partially formed.

### Persisted Runtime State

- [`data/state/elo_ratings.json`](/E:/APP/ELO/data/state/elo_ratings.json)
- [`data/state/settlements.json`](/E:/APP/ELO/data/state/settlements.json)
- [`data/state/parlay_tickets.json`](/E:/APP/ELO/data/state/parlay_tickets.json)
- [`data/state/xgb_training_samples.json`](/E:/APP/ELO/data/state/xgb_training_samples.json)
- [`data/state/prediction_snapshots.json`](/E:/APP/ELO/data/state/prediction_snapshots.json)
- [`data/state/market_snapshots.json`](/E:/APP/ELO/data/state/market_snapshots.json)
- [`data/state/prediction_snapshot_migration.json`](/E:/APP/ELO/data/state/prediction_snapshot_migration.json)

### Model / Policy Outputs

- [`data/models/xgb_v0_match_outcome.json`](/E:/APP/ELO/data/models/xgb_v0_match_outcome.json)
- [`data/models/xgb_v1_total_goals.json`](/E:/APP/ELO/data/models/xgb_v1_total_goals.json)
- [`data/models/xgb_v1_scoreline.json`](/E:/APP/ELO/data/models/xgb_v1_scoreline.json)
- [`data/models/xgb_v1_scoreline_volatile.json`](/E:/APP/ELO/data/models/xgb_v1_scoreline_volatile.json)
- [`data/models/ensemble_weights_v1.json`](/E:/APP/ELO/data/models/ensemble_weights_v1.json)
- [`data/models/play_thresholds_v1.json`](/E:/APP/ELO/data/models/play_thresholds_v1.json)
- [`data/models/play_model_policy_v1.json`](/E:/APP/ELO/data/models/play_model_policy_v1.json)

### Human-readable Reports

- recommendation reports under [`reports/`](/E:/APP/ELO/reports)
- ensemble backtest reports under [`reports/`](/E:/APP/ELO/reports)
- play-threshold calibration reports under [`reports/`](/E:/APP/ELO/reports)
- play-model backtest reports under [`reports/`](/E:/APP/ELO/reports)

Audit judgement:

- audit outputs exist
- but no dedicated audit service or event schema exists
- state persistence and audit persistence are mixed

## Config Files

- [`config/500_config.json`](/E:/APP/ELO/config/500_config.json)
  - legacy 500 scraper configuration
  - not the central runtime config for the current app

Current system behavior depends more on hardcoded constants than on config:

- `DEFAULT_ENSEMBLE_WEIGHTS`
- `DEFAULT_PLAY_THRESHOLDS`
- `DEFAULT_PLAY_POLICY`
- `DEFAULT_PLAY_MODEL_POLICY`
- `LEAGUE_STRENGTH`

This is a migration concern. Runtime policy is mostly code-state, not config-state.

## Output Formats

### Runtime/UI Outputs

- Tkinter table rows
- detail text panel
- popups for:
  - XGB status
  - play model status
  - policy status
  - calibration results
  - recent settlements

### Machine-readable Outputs

- JSON state in `data/state/`
- JSON model metadata in `data/models/`

### Human-readable Reports

- Markdown recommendation report
- Markdown ensemble backtest report
- Markdown play-threshold report
- Markdown play-model backtest report

Notable finding:

- report export functions exist in multiple generations:
  - `_export_report_v2`
  - `export_report`
  - `_export_report_v3`

That is a legacy smell. Output generation evolved in place instead of being versioned by a report layer.

## Tight Couplings and Hidden Assumptions

### Tight Couplings

1. `core.py` couples data, inference, governance, translation, settlement, and reporting.
2. `predict_match()` implicitly depends on persisted Elo state and recent-form state.
3. settlement writes training samples directly into the same pool used by offline calibration.
4. parlay logic depends on prediction output structure rather than a dedicated contract.
5. UI calls calibration, backtest, training, and settlement functions directly.

### Hidden Assumptions

1. `match_id = match_date|league|home|away` is assumed stable enough for joining snapshots and settlements.
2. `source_id` is assumed to be Titan schedule id when present.
3. `xgb_features` are assumed reusable across:
   - runtime inference
   - settlement sample append
   - historical backtest reconstruction
   - play-model training
4. league names are assumed to map cleanly into `LEAGUE_STRENGTH`; current file still contains mojibake league keys.
5. recent-form features are assumed reconstructible from existing state and sample meta.

### Direct Rule-to-Decision Paths

These are the clearest violations of a future layered architecture:

- draw specialist directly changes final 1X2 recommendation
- scoreline/total-goals model takeover directly changes translated play picks
- play thresholds directly decide what is allowed as recommendation output
- play policy directly decides what is displayable, single-eligible, or parlay-eligible

In C1.0, these should become separate decisions:

- inference output
- governance decision
- translation decision

They are currently fused into one runtime payload.

## KEEP / REWRITE / SPLIT / DROP Summary

### KEEP

- `AppMatch` concept
- `StateStore` file-level persistence primitives
- base models in `models/`
- historical import logic in `training_samples.py`
- market feature builder in `market_features.py`

### REWRITE

- `fetch_matches_v24()`
- `_predict_match_with_inputs()`
- `settle_match_result()`
- `auto_settle_finished_matches()`
- report export functions
- UI orchestration methods that directly call business/runtime services

### SPLIT

- `core.py` as a whole
- policy and threshold handling
- specialist logic
- parlay generation logic
- calibration/backtest logic

### DROP

- `match_fetcher_500.py` as an active runtime dependency
- duplicated report generations (`_export_report_v2` / older export shape)
- legacy structural assumptions in UI monkey-patch style overrides

## Staged Migration Order

This is the recommended migration order after audit, without implementation yet.

1. Extract canonical contracts first.
   - `match_payload`
   - `feature_vector`
   - `inference_result`
   - `governance_decision`
   - `translation_output`
   - `audit_record`

2. Extract Data Layer.
   - move Titan and 500 enrichment behind stable adapters
   - preserve `AppMatch` semantics but formalize source records

3. Extract Feature Layer.
   - move market/recent-form/Elo-derived feature construction out of `core.py`
   - make feature generation deterministic and reusable

4. Extract Inference Layer.
   - wrap base models and specialist models behind one inference API
   - output raw inference only, no betting translation

5. Extract Governance Layer.
   - move thresholds, takeover rules, breaker logic, and policy gating out of inference
   - governance should consume inference results, not re-run inference

6. Extract Translation Layer.
   - convert approved governance decisions into 1X2 / handicap / score / HTFT / parlay products

7. Extract Audit Layer.
   - centralize snapshots, settlements, reports, and backtest records under explicit schemas

8. Reconnect UI last.
   - UI should become a client of C1.0 services, not the place where runtime orchestration lives
