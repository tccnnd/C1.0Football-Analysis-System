# C1 Gap Map

Updated: 2026-04-03  
Repository: `E:\APP\ELO`

## Purpose

This document maps existing V24 capabilities into the target C1.0 layers:

- Data Layer
- Feature Layer
- Inference Layer
- Governance Layer
- Translation Layer
- Audit Layer

Each item is marked as:

- `KEEP`: migrate with minimal structural change
- `REWRITE`: keep capability, replace implementation shape
- `SPLIT`: current unit spans multiple layers and must be separated
- `DROP`: do not carry forward as an active C1.0 component

## Gap Map Table

| Existing Item | Current Location | Current Responsibility | Target C1.0 Layer | Action | Notes |
|---|---|---|---|---|---|
| `AppMatch` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | normalized match carrier | Data Layer | KEEP | Good seed for C1 match contract |
| `FetchDiagnostics` / `FetchResult` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | fetch result wrapper | Audit Layer | KEEP | Re-scope as fetch audit/event outputs |
| `MatchFetcherTitan` | [match_fetcher_titan.py](/E:/APP/ELO/src/v24_app/data_sources/match_fetcher_titan.py) | primary fixture/result source | Data Layer | REWRITE | Keep source capability, replace ad hoc parsing/orchestration interface |
| `MarketIntentFetcher500` | [market_intent_500.py](/E:/APP/ELO/src/v24_app/data_sources/market_intent_500.py) | market intent enrichment | Data Layer | KEEP | Keep capability; isolate as enrichment adapter |
| `MatchFetcher500` | [match_fetcher_500.py](/E:/APP/ELO/src/v24_app/data_sources/match_fetcher_500.py) | legacy 500 fetcher | Data Layer | DROP | Too legacy/corrupted for active migration base |
| `fetch_matches_v24()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | source selection, guards, enrichment, snapshot persistence | Data + Governance + Audit | SPLIT | Current orchestration violates target layering |
| market snapshot key helpers | [core.py](/E:/APP/ELO/src/v24_app/core.py) | snapshot identity construction | Audit Layer | KEEP | Should move to audit/state package |
| `persist_market_snapshot*()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | save pre-match market context | Audit Layer | KEEP | Keep behavior, move out of core runtime |
| `StateStore` | [state_store.py](/E:/APP/ELO/src/v24_app/storage/state_store.py) | JSON persistence for ratings, snapshots, settlements, samples | Audit Layer | KEEP | Good primitive; likely split into repositories/stores |
| `build_market_intent_feature_map()` | [market_features.py](/E:/APP/ELO/src/v24_app/market_features.py) | market-derived features | Feature Layer | KEEP | Already close to target shape |
| historical row normalization | [training_samples.py](/E:/APP/ELO/src/v24_app/training_samples.py) | raw history to normalized records | Data + Feature | SPLIT | normalization and feature derivation should be separate services |
| recent-form builders | [training_samples.py](/E:/APP/ELO/src/v24_app/training_samples.py) | rolling team form features | Feature Layer | KEEP | Reusable, deterministic logic |
| historical import pipeline | [training_samples.py](/E:/APP/ELO/src/v24_app/training_samples.py) | build XGB samples from files | Feature + Audit | SPLIT | feature generation and sample persistence should be separated |
| `EloRatingEngine` | [elo_rating.py](/E:/APP/ELO/src/v24_app/models/elo_rating.py) | rating inference/update | Inference Layer | KEEP | Keep engine, separate update side-effects |
| `PoissonScoreEngine` | [poisson.py](/E:/APP/ELO/src/v24_app/models/poisson.py) | score/goal/HTFT distribution | Inference Layer | KEEP | Strong reusable inference component |
| `XGBoostProbabilityModel` | [xgboost_v0.py](/E:/APP/ELO/src/v24_app/models/xgboost_v0.py) | 1X2 probability model | Inference Layer | KEEP | Keep adapter, remove training/persistence coupling later |
| play XGB models | [play_xgboost.py](/E:/APP/ELO/src/v24_app/models/play_xgboost.py) | total goals / scoreline / volatile scoreline models | Inference Layer | KEEP | Keep models, isolate policy from model output |
| `WeightedEnsembleEngine` | [ensemble.py](/E:/APP/ELO/src/v24_app/models/ensemble.py) | blend model probabilities | Inference Layer | KEEP | Good core primitive |
| `_draw_market_score()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | draw specialist score | Governance or Inference Specialist | SPLIT | scoring logic may stay inference-side; takeover rule must move to governance |
| `_side_market_score()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | side specialist score | Inference Layer | KEEP | move into specialist inference package |
| `_specialist_probability_fusion()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | specialist fusion | Inference Layer | KEEP | keep capability, move out of core |
| `_handicap_specialist_blend()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | handicap specialist adjustment | Inference + Translation | SPLIT | output shaping currently mixed with product translation |
| `_predict_match_with_inputs()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | full prediction assembly and play packaging | Inference + Governance + Translation | SPLIT | highest-priority split target |
| `predict_match()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | runtime prediction entrypoint | Inference Layer | REWRITE | keep entrypoint concept; make it return inference only |
| play thresholds | [`play_thresholds_v1.json`](/E:/APP/ELO/data/models/play_thresholds_v1.json) + [core.py](/E:/APP/ELO/src/v24_app/core.py) | recommendation gating | Governance Layer | KEEP | move to dedicated governance service/config |
| play model policy | [`play_model_policy_v1.json`](/E:/APP/ELO/data/models/play_model_policy_v1.json) + [core.py](/E:/APP/ELO/src/v24_app/core.py) | takeover/override policy | Governance Layer | KEEP | important artifact, wrong current placement |
| play policy (`DEFAULT_PLAY_POLICY`) | [core.py](/E:/APP/ELO/src/v24_app/core.py) | what can display/single/parlay | Translation Layer | KEEP | belongs to translation/productization, not inference |
| parlay leg generation | [core.py](/E:/APP/ELO/src/v24_app/core.py) | build mixed parlay legs | Translation Layer | KEEP | convert from dict helpers to explicit ticket builder |
| `generate_mix_parlay_recommendations()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | build parlay tickets | Translation + Audit | SPLIT | product translation and persistence are fused |
| `get_gate_metrics()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | hit rate / EV bias / streak / breaker | Governance Layer | KEEP | close to target; should consume formal settlement records |
| `persist_prediction_snapshot()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | save pre-match prediction bundle | Audit Layer | KEEP | good audit behavior, move out of prediction core |
| snapshot migration | [core.py](/E:/APP/ELO/src/v24_app/core.py) | bind old snapshots to Titan ids | Audit Layer | KEEP | migration-only utility |
| `settle_match_result()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | settle plays, update Elo, append training sample, pop snapshot | Governance + Audit + Feature | SPLIT | current settlement has too many side-effects |
| `auto_settle_finished_matches()` | [core.py](/E:/APP/ELO/src/v24_app/core.py) | result recovery, settlement orchestration, gate update | Data + Governance + Audit | SPLIT | another major orchestration hotspot |
| XGB training status/train-now | [core.py](/E:/APP/ELO/src/v24_app/core.py) | model ops | Audit + Inference Ops | REWRITE | keep ops capability; separate from runtime core |
| play model training status/train-now | [core.py](/E:/APP/ELO/src/v24_app/core.py) | model ops | Audit + Inference Ops | REWRITE | same as above |
| ensemble calibration | [core.py](/E:/APP/ELO/src/v24_app/core.py) | offline weight calibration | Audit + Governance Research | SPLIT | output used by runtime governance/inference, logic should not live in runtime core |
| play threshold calibration | [core.py](/E:/APP/ELO/src/v24_app/core.py) | offline play gating calibration | Governance Layer | KEEP | move to governance calibration module |
| play model policy calibration | [core.py](/E:/APP/ELO/src/v24_app/core.py) | offline takeover calibration | Governance Layer | KEEP | move to governance calibration module |
| ensemble backtest | [core.py](/E:/APP/ELO/src/v24_app/core.py) | offline evaluation and markdown report | Audit Layer | KEEP | good capability, separate from runtime |
| play model backtest | [core.py](/E:/APP/ELO/src/v24_app/core.py) | play-model evaluation and markdown report | Audit Layer | KEEP | same as above |
| recommendation reports | [core.py](/E:/APP/ELO/src/v24_app/core.py) | markdown export | Translation + Audit | SPLIT | report rendering should not live in core runtime |
| `ui.py` app shell | [ui.py](/E:/APP/ELO/src/v24_app/ui.py) | desktop UI and direct orchestration | Translation Client | REWRITE | UI should consume services; not own orchestration |
| UI background task wrappers | [ui.py](/E:/APP/ELO/src/v24_app/ui.py) | operational dispatch | Translation Client | KEEP | concept is fine, service calls need cleanup |
| UI cleanup patches / final overrides | [ui.py](/E:/APP/ELO/src/v24_app/ui.py) | legacy stabilization layer | Translation Client | DROP | inventory only; do not preserve this structure |
| docs under `docs/` | [docs/](/E:/APP/ELO/docs) | architecture / schema notes | Audit Layer | KEEP | continue producing migration artifacts here |

## Capability-by-Layer View

### Data Layer

Should contain in C1.0:

- source adapters
- normalization into canonical match/source records
- source diagnostics
- source-specific ids and recovery lookup

Current gaps:

- fetch orchestration mixed with governance and audit writes
- stale-cache fallback is inside runtime fetch path
- source guards are embedded, not formalized

### Feature Layer

Should contain in C1.0:

- market feature builders
- recent-form builders
- historical sample builders
- reproducible feature-vector generation

Current gaps:

- feature computation is split across `training_samples.py`, `market_features.py`, and `core.py`
- runtime and offline feature generation are coupled by convention, not by explicit interface
- there is no canonical `feature_vector` contract object

### Inference Layer

Should contain in C1.0:

- base models
- ensemble engine
- specialist models
- probability and distribution outputs only

Current gaps:

- inference currently emits translated betting outputs directly
- runtime takeover logic changes recommendations before governance separation
- model adapters also own training status/persistence concerns

### Governance Layer

Should contain in C1.0:

- approval/deny/override decisions
- breaker logic
- play thresholds
- takeover policy
- parlay eligibility policy

Current gaps:

- governance is partly in `predict_match()`
- Gate is partly post-settlement, partly pre-product gating
- no explicit `governance_decision` record exists

### Translation Layer

Should contain in C1.0:

- product-facing play translation
- single/parlay packaging
- UI-facing rendering payloads
- human-readable recommendation reports

Current gaps:

- translation is embedded in `predict_match()`
- parlay generation and persistence are fused
- UI still contains runtime formatting assumptions from legacy V24

### Audit Layer

Should contain in C1.0:

- snapshots
- settlement records
- model policy artifacts
- backtest outputs
- migration logs

Current gaps:

- audit writes are spread across core and state store
- sample generation side-effects occur during settlement
- no central event schema exists

## Most Important Structural Gaps

1. No canonical boundary between inference and governance.
2. No canonical boundary between governance and translation.
3. `core.py` acts as both runtime kernel and offline research harness.
4. UI still talks directly to low-level runtime functions.
5. state files serve as:
   - source-of-truth
   - cache
   - training pool
   - audit log
   - policy storage
   without separation.

## Proposed C1.0 Extraction Targets

These are the first explicit contracts C1.0 should introduce.

### 1. `data_match`

Base canonical match from source adapters.

### 2. `feature_vector`

All reusable numeric features, with provenance and feature version.

### 3. `inference_result`

Pure model outputs:

- 1X2 probabilities
- score distributions
- play-model outputs
- specialist scores

No product recommendation fields.

### 4. `governance_decision`

Should contain:

- approved / blocked
- reason codes
- threshold checks
- breaker status
- allowed play types
- allowed parlay uses

### 5. `translation_output`

Should contain:

- user-facing picks
- parlay tickets
- report rows
- UI summary payloads

### 6. `audit_record`

Should contain:

- snapshot
- settlement
- backtest row
- migration event

## Recommended Migration Sequence

1. Define the six contracts above.
2. Move source adapters behind the Data Layer.
3. Move reusable feature builders behind the Feature Layer.
4. Extract a pure inference API from `_predict_match_with_inputs()`.
5. Extract governance decisions from:
   - draw takeover
   - play thresholds
   - play model policy
   - parlay eligibility
6. Move pick/parlay/report shaping into Translation Layer.
7. Move snapshots/settlements/reports/backtests into Audit Layer services.
8. Rebind UI to the new service boundaries.
