# C1.0 Migration Sequence

## Phase Status

| Phase | Description | Status | Validated |
|-------|-------------|--------|-----------|
| Phase 1 | Governance skeleton | ✅ Complete | Shadow run |
| Phase 2 | Governance-ready features | ✅ Complete | Shadow run |
| Phase 3 | Audit trail | ✅ Complete | JSONL files active |
| Phase 4 | Inference migration | ⚠️ 75% (LightGBM pending) | Shadow run |
| Phase 5 | Translation layer | ✅ Complete | Shadow run |
| Phase 6 | foot (Go) integration | ✅ Complete | 300-match shadow run |
| Phase 7 | C1.0 independence | 🔲 Not started | — |
| Phase 8 | Production switch | 🔲 Not started | — |

## Completed Migrations

### Phase 1: Governance Skeleton ✅
- `c1/core/schema.py` — FeatureSnapshot, PredictionSnapshot, GovernanceDecision
- `c1/core/reason_codes.py` — 18 reason codes (including 3 foot-specific)
- `c1/modules/judge.py` — GovernanceJudge + 5 Gates
- `c1/configs/governance_cfg.yaml` — All thresholds configured

### Phase 2: Features ✅
- info_quality (5-component weighted score)
- lineup_known / freshness (with fixed temporal logic)
- missing_elo_loss
- chaos_score (7-component weighted score)
- odds_move_against_model
- line_move_against_model
- foot signal enrichment (16 raw + 4 semantic features)

### Phase 3: Audit Trail ✅
- feature_vectors.jsonl
- predictions.jsonl
- governance_decisions.jsonl
- translation_outputs.jsonl
- release_decisions.jsonl
- market_snapshots.jsonl

### Phase 4: Inference ⚠️
- ✅ Baseline (Market + ELO + Poisson ensemble)
- ✅ XGBoost adapter (wraps V24 model)
- ✅ Calibration (league-specific weights)
- ✅ EV / confidence calculation
- ❌ LightGBM (stub only)

### Phase 5: Translation ✅
- ✅ 1X2 (probability-based, governance-gated)
- ✅ Handicap (independent: rating_diff + side_strength + draw_drag)
- ✅ Totals (Poisson-based over/under)
- ✅ HT/FT (Poisson halftime matrix)
- ✅ Scoreline (Poisson score matrix)

### Phase 6: foot Integration ✅
- ✅ MySQL bridge (6555 teams, 35K matches, 190万 asia, 310万 euro)
- ✅ 16 raw features + 4 semantic features
- ✅ ConflictDetector integration (3 conflict types)
- ✅ GovernanceJudge decision influence (confirm/weak/critical)
- ✅ ELO precomputation (344K matches → 6555 teams)
- ✅ Shadow run validation (300 matches, 50% accuracy, APPROVE 52.7%)

## Remaining Migrations

### Phase 7: C1.0 Independence

**Goal**: C1.0 can run without importing from `v24_app`.

**Steps**:
1. Copy ELO engine core to `c1/inference/engines/elo.py`
2. Copy Poisson engine core to `c1/inference/engines/poisson.py`
3. Copy ensemble blending to `c1/inference/engines/ensemble.py`
4. XGBoost model loading directly from `data/models/*.json`
5. Remove all `from v24_app.*` imports in `c1/`
6. Validate: `python -c "from c1.runtime.shadow import C1ShadowRunner"` without V24

**Risk**: V24 models have accumulated patches (bayesian calibration, specialist fusion) that C1.0 doesn't replicate. Need to verify shadow run accuracy doesn't regress.

### Phase 8: Production Switch

**Prerequisites**:
- Phase 7 complete
- Shadow run accuracy >= V24 on 1000+ matches
- Governance APPROVE accuracy > 50%
- No regression in BLOCK/OBSERVE identification
- UI integration complete (C1 动作 column working)

**Steps**:
1. Switch `runtime_mode.yaml` from `formal_list_default` to `c1_primary`
2. V24 becomes fallback (shadow mode)
3. Monitor for 2 weeks
4. If stable: remove V24 from prediction path
5. V24 remains for training/calibration only

## Validation Checkpoints

| Checkpoint | Metric | Target | Current |
|-----------|--------|--------|---------|
| Accuracy (5 leagues) | 1X2 hit rate | ≥ 48% | 50.0% ✅ |
| APPROVE accuracy | Hit rate in APPROVE group | ≥ 50% | 52.7% ✅ |
| Governance separation | APPROVE acc - DOWNGRADE acc | ≥ 5% | 7.7% ✅ |
| foot signal value | No-conflict acc - conflict acc | ≥ 3% | 4.8% ✅ |
| APPROVE rate | % of matches approved | 50-75% | 62.7% ✅ |
| BLOCK rate | % of matches blocked | < 5% | 0.3% ✅ |

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| V24 model drift after independence | Medium | High | Keep shadow comparison running |
| foot MySQL service failure | Low | Medium | Graceful degradation (already implemented) |
| Governance too conservative | Low | Medium | Tunable thresholds in YAML |
| Translation naive mapping | Low | High | Independent translators (already implemented) |
| Audit storage growth | Medium | Low | JSONL rotation (not yet implemented) |
