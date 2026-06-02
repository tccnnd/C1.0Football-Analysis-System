# Week 2 Integration Tasks: Track B + Track C

**Week**: 2 (2026-05-28 - 2026-06-03)  
**Status**: ⏳ READY TO START  
**Scope**: Complete Track B (Backtest) and Track C (Export) integrations  
**Parallel Execution**: Both tracks run simultaneously

---

## 📋 Overview

### Current State
- ✅ Track B Core: Strategy schema, backtest engine, settlement bridge (COMPLETE)
- ✅ Track C Core: Decision exporter, analytics exporter, recommendation feed (COMPLETE)
- ✅ All unit tests passing (10/10 backtest, 40+ export tests)
- ⏳ Integration work: Audit store, release manager hooks, end-to-end tests

### What Remains
- **Track B Integration** (B4-B5): Settlement bridge + audit integration
- **Track C Integration** (C3-C4): Recommendation feed + release manager hooks
- **End-to-End Tests**: Validate full pipelines
- **Documentation**: Integration guides and examples

---

## 🎯 Track B: Backtest Framework Integration

### B4: Settlement Bridge Integration (2 hours)

**Objective**: Integrate settlement bridge with backtest runner

**Current State**:
- ✅ `c1/strategy/settlement_bridge.py` created
- ✅ Supports 1x2, handicap, totals, htft, scoreline outcomes
- ⏳ Needs integration with backtest runner

**Tasks**:

1. **Create Settlement Bridge Tests** (30 min)
   - Test `load_settlements()` with mock data
   - Test `build_match_id_map()` with match records
   - Test `compute_outcome()` for each play type
   - Test edge cases (missing goals, void outcomes)

2. **Create Backtest + Settlement Integration** (30 min)
   - Create `BacktestSettlementRunner` class
   - Load settlements and match mappings
   - Compute outcomes for each bet
   - Generate backtest results

3. **Create Integration Test** (1 hour)
   - Load sample decisions from audit store
   - Load sample settlements
   - Run backtest with settlement outcomes
   - Verify metrics calculated correctly

**Deliverables**:
- `tests/test_c1_settlement_bridge.py` (NEW)
- `tests/test_c1_backtest_settlement_integration.py` (NEW)
- Updated `c1/strategy/backtest.py` with settlement integration

**Success Criteria**:
- ✅ All settlement bridge tests pass
- ✅ Integration test passes
- ✅ Outcomes computed correctly for all play types
- ✅ Metrics calculated accurately

---

### B5: Audit Store Integration (1 hour)

**Objective**: Store backtest results in audit trail

**Current State**:
- ✅ `c1/audit/store.py` has methods for features, predictions, governance, translation, release
- ⏳ Needs methods for backtest results

**Tasks**:

1. **Add Backtest Recording Methods** (30 min)
   - Add `record_backtest_result()` method
   - Add `read_backtest_results()` method
   - Add `record_backtest_metrics()` method
   - Add `read_backtest_metrics()` method

2. **Create Audit Integration Test** (30 min)
   - Record backtest results
   - Read backtest results
   - Verify data integrity
   - Test filtering and limits

**Deliverables**:
- Updated `c1/audit/store.py` with backtest methods
- `tests/test_c1_audit_backtest_integration.py` (NEW)

**Success Criteria**:
- ✅ Backtest results recorded correctly
- ✅ Backtest results read correctly
- ✅ Audit trail complete
- ✅ All tests pass

---

### B6: End-to-End Backtest Test (1 hour)

**Objective**: Validate full backtest pipeline

**Tasks**:

1. **Create End-to-End Test** (1 hour)
   - Load sample matches from audit store
   - Generate predictions and governance decisions
   - Translate to betting selections
   - Load settlements
   - Run backtest
   - Calculate metrics
   - Record results in audit trail
   - Verify all steps work together

**Deliverables**:
- `tests/test_c1_backtest_e2e.py` (NEW)
- `scripts/run_backtest_e2e.py` (NEW)

**Success Criteria**:
- ✅ End-to-end test passes
- ✅ All 5 play types supported
- ✅ Metrics calculated correctly
- ✅ Audit trail complete

---

## 🎯 Track C: Data Publishing Integration

### C3: Recommendation Feed Integration (1 hour)

**Objective**: Integrate recommendation feed with release manager

**Current State**:
- ✅ `c1/export/recommendation_feed.py` created
- ✅ Supports filtering by governance action and confidence
- ⏳ Needs integration with release manager

**Tasks**:

1. **Create Recommendation Feed Tests** (30 min)
   - Test `generate_feed()` with mock decisions
   - Test filtering by governance action
   - Test filtering by confidence threshold
   - Test JSONL export format

2. **Create Release Manager Integration** (30 min)
   - Add `publish_recommendations()` method to release manager
   - Export recommendations after release decision
   - Support multiple output formats (JSON, JSONL)

**Deliverables**:
- `tests/test_c1_recommendation_feed.py` (NEW)
- Updated `c1/runtime/release.py` with recommendation export

**Success Criteria**:
- ✅ Recommendation feed tests pass
- ✅ Recommendations exported correctly
- ✅ Filtering works as expected
- ✅ Multiple formats supported

---

### C4: Release Manager Export Hooks (1 hour)

**Objective**: Add export hooks to release manager

**Current State**:
- ✅ `c1/runtime/release.py` has `C1ReleaseManager` class
- ✅ `c1/export/decision_exporter.py` and `analytics_exporter.py` created
- ⏳ Needs integration hooks

**Tasks**:

1. **Add Export Methods to Release Manager** (30 min)
   - Add `export_decisions()` method
   - Add `export_analytics()` method
   - Add `export_recommendations()` method
   - Support multiple output formats

2. **Create Export Integration Test** (30 min)
   - Run release decision
   - Export decisions in JSON, JSONL, CSV
   - Export analytics
   - Export recommendations
   - Verify all exports created correctly

**Deliverables**:
- Updated `c1/runtime/release.py` with export methods
- `tests/test_c1_release_export_integration.py` (NEW)

**Success Criteria**:
- ✅ Export methods work correctly
- ✅ All formats supported
- ✅ Integration test passes
- ✅ Exports contain expected data

---

### C5: End-to-End Export Test (1 hour)

**Objective**: Validate full export pipeline

**Tasks**:

1. **Create End-to-End Test** (1 hour)
   - Load sample matches
   - Generate predictions and governance decisions
   - Translate to betting selections
   - Run release decision
   - Export decisions (JSON, JSONL, CSV)
   - Export analytics
   - Export recommendations
   - Verify all exports created and contain expected data

**Deliverables**:
- `tests/test_c1_export_e2e.py` (NEW)
- `scripts/run_export_e2e.py` (NEW)

**Success Criteria**:
- ✅ End-to-end test passes
- ✅ All export formats working
- ✅ Data integrity verified
- ✅ Exports ready for consumption

---

## 📊 Week 2 Timeline

### Day 1 (Mon-Tue): Track B Integration
```
Morning:
  - B4: Settlement Bridge Integration (2 hours)
    - Create settlement bridge tests
    - Create backtest + settlement integration
    - Create integration test

Afternoon:
  - B5: Audit Store Integration (1 hour)
    - Add backtest recording methods
    - Create audit integration test
```

### Day 2 (Wed-Thu): Track C Integration
```
Morning:
  - C3: Recommendation Feed Integration (1 hour)
    - Create recommendation feed tests
    - Create release manager integration

Afternoon:
  - C4: Release Manager Export Hooks (1 hour)
    - Add export methods to release manager
    - Create export integration test
```

### Day 3 (Fri): End-to-End Tests
```
Morning:
  - B6: End-to-End Backtest Test (1 hour)
    - Create end-to-end test
    - Create demo script

Afternoon:
  - C5: End-to-End Export Test (1 hour)
    - Create end-to-end test
    - Create demo script
```

---

## 📁 Files to Create/Modify

### Track B Files

**New Files**:
- `tests/test_c1_settlement_bridge.py` ⏳
- `tests/test_c1_backtest_settlement_integration.py` ⏳
- `tests/test_c1_audit_backtest_integration.py` ⏳
- `tests/test_c1_backtest_e2e.py` ⏳
- `scripts/run_backtest_e2e.py` ⏳

**Modified Files**:
- `c1/strategy/backtest.py` ⏳ (add settlement integration)
- `c1/audit/store.py` ⏳ (add backtest methods)

### Track C Files

**New Files**:
- `tests/test_c1_recommendation_feed.py` ⏳
- `tests/test_c1_release_export_integration.py` ⏳
- `tests/test_c1_export_e2e.py` ⏳
- `scripts/run_export_e2e.py` ⏳

**Modified Files**:
- `c1/runtime/release.py` ⏳ (add export methods)

---

## ✅ Validation Checklist

### Track B Integration
- [ ] Settlement bridge tests pass (15+ tests)
- [ ] Backtest + settlement integration works
- [ ] Audit store backtest methods work
- [ ] End-to-end backtest test passes
- [ ] All 5 play types supported in backtest
- [ ] Metrics calculated correctly
- [ ] Audit trail complete

### Track C Integration
- [ ] Recommendation feed tests pass (10+ tests)
- [ ] Release manager export methods work
- [ ] Export integration test passes
- [ ] End-to-end export test passes
- [ ] All export formats working (JSON, JSONL, CSV)
- [ ] Analytics exported correctly
- [ ] Recommendations exported correctly

### Overall
- [ ] All tests pass (50+ new tests)
- [ ] 100% code coverage for new code
- [ ] Documentation complete
- [ ] Ready for Week 3 (backtest analysis + UI integration)

---

## 🚀 Success Criteria

### Track B
- ✅ Settlement bridge maps outcomes correctly
- ✅ Backtest metrics calculated accurately
- ✅ Audit trail records all backtest data
- ✅ End-to-end pipeline works
- ✅ 100% test coverage

### Track C
- ✅ Decisions exported in 3 formats
- ✅ Analytics aggregated correctly
- ✅ Recommendations formatted properly
- ✅ Release manager integration complete
- ✅ 100% test coverage

### Overall
- ✅ Track B fully integrated
- ✅ Track C fully integrated
- ✅ All tests passing
- ✅ Ready for Week 3

---

## 📈 Expected Outcomes

### Track B
- Backtest framework enables strategy evaluation
- Performance metrics calculated accurately
- Settlement bridge maps outcomes correctly
- Audit trail enables post-hoc analysis
- Foundation for Week 3 (backtest analysis)

### Track C
- Decisions exported in multiple formats
- Analytics available for dashboards
- Recommendations available for UI
- External systems can consume data
- Foundation for Week 3 (UI integration)

---

## 🎓 Key Implementation Notes

### Track B
1. **Settlement Mapping**: Handle VOID outcomes (no-action)
2. **Outcome Computation**: Support all 5 play types
3. **Metrics Calculation**: Use consistent formulas
4. **Audit Trail**: Record all backtest data
5. **Error Handling**: Graceful handling of missing data

### Track C
1. **CSV Export**: Flatten nested dicts for compatibility
2. **JSONL Export**: One JSON per line for streaming
3. **Analytics**: Group by date for daily summaries
4. **Recommendations**: Include full decision chain
5. **Error Handling**: Graceful handling of missing data

---

## 📞 Questions for Stakeholders

1. **Backtest Period**: Minimum 1 month? 3 months? 1 year?
2. **Settlement Data**: How to handle incomplete settlements?
3. **Export Frequency**: Real-time? Daily batch? On-demand?
4. **External Systems**: Who are the primary consumers?
5. **Performance**: Any latency requirements for exports?

---

## 🏁 Completion Criteria

**Week 2 Integration is complete when**:
- ✅ Track B: Settlement bridge + audit integration complete
- ✅ Track C: Recommendation feed + release manager hooks complete
- ✅ All 5 play types supported in both tracks
- ✅ 50+ new tests created and passing
- ✅ 100% test coverage for new code
- ✅ End-to-end tests passing
- ✅ Documentation complete
- ✅ Ready for Week 3 (backtest analysis + UI integration)

---

**Status**: ⏳ READY TO START  
**Next**: Begin Day 1 (Track B Integration)

