# C1.0 Roadmap: Phase 5+ (Multi-Track Development)

**Date**: 2026-05-27  
**Status**: Planning  
**Scope**: Three parallel tracks to address P0 blockers and expand capabilities

---

## Current State (as of 2026-05-27)

### P0 Blockers (Immediate)
1. ✓ ELO loading bridge (DONE)
2. ⏳ Release gate policy (release_cfg.yaml) - NEXT
3. ⏳ Availability data coverage - IN PROGRESS

### Completed Phases
- Phase 1: Governance skeleton ✓
- Phase 2: Governance-ready features ✓
- Phase 3: Audit trail ✓
- Phase 4: Inference migration ✓
- Phase 5: Translation layer ✓ (partial - missing HT/FT, scoreline)

---

## Three-Track Development Plan

### Track A: Complete Translation Layer (Phase 5 Completion)
**Goal**: Full betting product coverage (1X2, Handicap, Totals, HT/FT, Scoreline)  
**Timeline**: 2–3 weeks  
**Reference**: bpl-next (Dixon & Coles), footBayes

#### A1: HT/FT Translation
- **Input**: Poisson score distribution (already available)
- **Output**: HT/FT probabilities (HT 1X2 + FT 1X2 combinations)
- **Implementation**:
  - Extract HT probabilities from Poisson (first 45 min)
  - Extract FT probabilities from Poisson (full 90 min)
  - Combine into 9 HT/FT outcomes
  - Apply governance gates
  - Translate to betting selections

**Files to create**:
- `c1/translation/htft_translator.py`
- `tests/test_c1_htft_translation.py`

#### A2: Scoreline Translation
- **Input**: Poisson score distribution
- **Output**: Exact scoreline probabilities
- **Implementation**:
  - Use Poisson to generate score matrix (0–5 goals each)
  - Filter by confidence threshold
  - Translate to betting selections (e.g., "Home 2–1 Away")
  - Apply governance gates

**Files to create**:
- `c1/translation/scoreline_translator.py`
- `tests/test_c1_scoreline_translation.py`

#### A3: Integrate into C1TranslationEngine
- Add HT/FT and scoreline to `translate()` method
- Update `TranslationResult` schema to include new items
- Update release manager to handle new play types

**Files to modify**:
- `c1/translation/engine.py`
- `c1/translation/schema.py`
- `c1/runtime/release.py`

---

### Track B: Strategy Evaluation & Backtest Framework (Phase 6)
**Goal**: Systematic strategy assessment and performance tracking  
**Timeline**: 3–4 weeks  
**Reference**: sports-betting, existing V24 backtest logic

#### B1: Strategy Definition Schema
- **Input**: Governance decision + translation output
- **Output**: Betting strategy specification

**Create**:
- `c1/strategy/schema.py`
  - `BettingStrategy` (unit, stake, odds threshold, etc.)
  - `StrategyResult` (win/loss, ROI, confidence calibration)
  - `StrategyMetrics` (hit rate, EV, Sharpe ratio, max drawdown)

#### B2: Backtest Engine
- **Input**: Historical matches + outcomes + strategy
- **Output**: Performance metrics

**Create**:
- `c1/strategy/backtest.py`
  - `BacktestRunner` class
  - Replay shadow runs with historical outcomes
  - Calculate metrics per strategy
  - Generate performance reports

**Key metrics**:
- Hit rate (% correct predictions)
- ROI (return on investment)
- EV (expected value per bet)
- Sharpe ratio (risk-adjusted return)
- Max drawdown (worst consecutive loss)
- Confidence calibration (predicted vs actual)

#### B3: Settlement Integration
- **Input**: Match outcomes from V24
- **Output**: Actual results for backtest

**Create**:
- `c1/strategy/settlement_bridge.py`
  - Load V24 settlements
  - Map to C1 match IDs
  - Compute actual outcomes

#### B4: Audit Integration
- Store backtest results in audit trail
- Link to governance decisions and translations
- Enable post-hoc analysis

**Files to modify**:
- `c1/audit/store.py` (add backtest record type)

---

### Track C: Data Publishing & Distribution (Phase 6+)
**Goal**: Export C1 decisions and analysis for downstream consumption  
**Timeline**: 2–3 weeks  
**Reference**: foot (Go), data publishing patterns

#### C1: Decision Export API
- **Output formats**: JSON, CSV, Parquet
- **Consumers**: UI, external systems, analytics

**Create**:
- `c1/export/decision_exporter.py`
  - Export governance decisions
  - Export translation outputs
  - Export release decisions
  - Include full decision chain (features → inference → governance → translation)

#### C2: Analytics Export
- **Output**: Aggregated statistics for dashboards

**Create**:
- `c1/export/analytics_exporter.py`
  - Daily/weekly summaries
  - Reason code distribution
  - Confidence distribution
  - Governance action distribution
  - Release rate trends

#### C3: Recommendation Feed
- **Output**: Structured betting recommendations

**Create**:
- `c1/export/recommendation_feed.py`
  - Format: `{ match_id, play, selection, confidence, odds, status }`
  - Filter by governance action (APPROVE, DOWNGRADE, OBSERVE)
  - Include metadata (reason codes, tags, audit trail)

#### C4: Integration with UI/External Systems
- **Modify**: `c1/runtime/release.py`
  - Add export hooks
  - Publish to message queue or file system
  - Support real-time streaming

---

## Implementation Sequence

### Week 1: P0 Blockers + Track A Start
```
Mon–Tue:  Fix release_cfg.yaml (allow DOWNGRADE)
Wed–Thu:  Implement HT/FT translation (A1)
Fri:      Implement scoreline translation (A2)
```

### Week 2: Track A Completion + Track B Start
```
Mon–Tue:  Integrate HT/FT + scoreline into engine (A3)
Wed–Thu:  Define strategy schema (B1)
Fri:      Implement backtest engine (B2)
```

### Week 3: Track B + Track C Start
```
Mon–Tue:  Settlement bridge (B3)
Wed–Thu:  Decision export API (C1)
Fri:      Analytics export (C2)
```

### Week 4: Track C Completion + Integration
```
Mon–Tue:  Recommendation feed (C3)
Wed–Thu:  UI/external system integration (C4)
Fri:      Testing and documentation
```

---

## Dependency Graph

```
P0 Blockers (ELO + release_cfg)
    ↓
Track A (Complete Translation)
    ├─→ Track B (Backtest Framework)
    │       ├─→ Settlement Bridge
    │       └─→ Audit Integration
    │
    └─→ Track C (Data Publishing)
            ├─→ Decision Export
            ├─→ Analytics Export
            └─→ Recommendation Feed
```

**Key insight**: Track A is prerequisite for B and C (need complete translations to backtest/export).

---

## Success Criteria

### Track A
- [ ] HT/FT translation produces valid probabilities
- [ ] Scoreline translation produces valid probabilities
- [ ] All new play types pass governance gates
- [ ] Release manager handles new play types
- [ ] Tests pass (>90% coverage)

### Track B
- [ ] Backtest engine runs on historical data
- [ ] Metrics calculated correctly (validated against manual calculation)
- [ ] Settlement bridge maps V24 outcomes to C1 matches
- [ ] Backtest results stored in audit trail
- [ ] Performance reports generated

### Track C
- [ ] Decision export produces valid JSON/CSV
- [ ] Analytics export shows correct distributions
- [ ] Recommendation feed includes full decision chain
- [ ] External systems can consume exports
- [ ] Real-time streaming works (if applicable)

---

## Resource Allocation

| Track | Effort | Priority | Owner |
|-------|--------|----------|-------|
| A | 2–3 weeks | P0 | Core team |
| B | 3–4 weeks | P1 | Core team + analyst |
| C | 2–3 weeks | P1 | Core team + DevOps |

**Parallelization**: A can start immediately. B and C can start after A is 50% complete.

---

## Risk Mitigation

### Track A Risks
- **Risk**: Poisson distribution doesn't capture HT/FT correlation
- **Mitigation**: Validate against historical data; add correlation factor if needed

- **Risk**: Scoreline probabilities too granular (81 outcomes)
- **Mitigation**: Filter by confidence; group low-probability outcomes

### Track B Risks
- **Risk**: Settlement data incomplete or misaligned
- **Mitigation**: Validate settlement bridge against V24 records; add reconciliation

- **Risk**: Backtest results don't match live performance
- **Mitigation**: Track confidence calibration; adjust governance thresholds

### Track C Risks
- **Risk**: Export format incompatible with downstream systems
- **Mitigation**: Define schema early; get feedback from consumers

- **Risk**: Real-time streaming creates bottleneck
- **Mitigation**: Use async publishing; implement batching

---

## Documentation Plan

### Track A
- `docs/C1_HTFT_TRANSLATION.md`
- `docs/C1_SCORELINE_TRANSLATION.md`

### Track B
- `docs/C1_BACKTEST_FRAMEWORK.md`
- `docs/C1_STRATEGY_METRICS.md`

### Track C
- `docs/C1_DATA_EXPORT.md`
- `docs/C1_RECOMMENDATION_FEED.md`

---

## Next Immediate Actions

1. **Today**: Approve this roadmap
2. **Tomorrow**: Fix release_cfg.yaml (P0 blocker #2)
3. **This week**: Start Track A (HT/FT translation)
4. **Next week**: Start Track B (backtest framework)
5. **Week 3**: Start Track C (data publishing)

---

## Open Questions

1. **Track A**: Should HT/FT and scoreline be separate play types or grouped?
2. **Track B**: What's the minimum backtest period (1 month? 3 months? 1 year)?
3. **Track C**: Who are the primary consumers of exported data?
4. **Integration**: Should all three tracks feed into a unified dashboard?

---

## References

- **Track A**: bpl-next (Dixon & Coles), footBayes (Poisson)
- **Track B**: sports-betting (backtest framework), V24 existing logic
- **Track C**: foot (Go data pipeline), data publishing patterns

---

## Approval & Sign-Off

- [ ] Architecture review
- [ ] Resource allocation confirmed
- [ ] Timeline agreed
- [ ] Success criteria accepted
