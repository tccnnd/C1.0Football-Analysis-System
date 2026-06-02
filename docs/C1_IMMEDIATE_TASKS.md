# C1.0 Immediate Tasks (Next 4 Weeks)

**Updated**: 2026-05-27  
**Status**: Ready to execute  
**Scope**: P0 blockers + three parallel tracks

---

## 🔴 P0 Blockers (This Week)

### Task 1: Fix release_cfg.yaml
**Priority**: P0 (CRITICAL)  
**Effort**: 30 minutes  
**Owner**: Core team  
**Status**: ⏳ READY

**Current state**:
```yaml
allowed_governance_actions:
  - APPROVE
```

**Problem**: Only APPROVE passes release gate. Most matches get DOWNGRADE → GOVERNANCE_HOLD.

**Solution**:
```yaml
allowed_governance_actions:
  - APPROVE
  - DOWNGRADE  # Add this
```

**Impact**:
- Release rate should increase from ~0% to ~30–50%
- Governance decisions now have real consequences
- Fallback candidates still available for DOWNGRADE

**Validation**:
- Run shadow comparison on 10 live matches
- Verify release_decisions.jsonl shows APPROVE_RELEASE and APPROVE_RELEASE_FALLBACK
- Check that DOWNGRADE matches are released with fallback candidates

**File**: `e:\APP\ELO\c1\configs\release_cfg.yaml`

---

### Task 2: Verify ELO Loading Works End-to-End
**Priority**: P0 (CRITICAL)  
**Effort**: 1 hour  
**Owner**: Core team  
**Status**: ✓ DONE (code), ⏳ VALIDATION PENDING

**What's done**:
- ✓ ELO loader module created
- ✓ Legacy bridge updated
- ✓ Unit tests pass
- ✓ Demo script runs

**What's needed**:
- [ ] Run shadow comparison on 5 live matches
- [ ] Verify home_rating and away_rating are populated (not 1500.0)
- [ ] Check that missing_elo_loss is 0.0
- [ ] Verify confidence scores improved
- [ ] Check governance decisions have fewer MISSING_ELO_LOSS reasons

**Validation script**:
```python
# Run this after shadow comparison
from c1.audit import C1AuditStore

store = C1AuditStore(project_root)
decisions = store.read_governance_decisions(limit=5)

for decision in decisions:
    feature_snapshot = decision['feature_snapshot']
    print(f"Match: {decision['match_id']}")
    print(f"  home_rating: {feature_snapshot['fields']['home_rating']}")
    print(f"  away_rating: {feature_snapshot['fields']['away_rating']}")
    print(f"  missing_elo_loss: {feature_snapshot['fields']['missing_elo_loss']}")
    print(f"  confidence: {decision['prediction_snapshot']['confidence']}")
    print()
```

**File**: `e:\APP\ELO\c1\runtime\legacy_bridge.py` (already updated)

---

## 🟡 Track A: Complete Translation Layer (Weeks 1–2)

### Task A1: Implement HT/FT Translation
**Priority**: P1  
**Effort**: 1 week  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/translation/htft_translator.py` (150 lines)
   - Extract HT probabilities from Poisson (first 45 min)
   - Extract FT probabilities from Poisson (full 90 min)
   - Generate 9 HT/FT outcomes
   - Apply confidence thresholds

2. `tests/test_c1_htft_translation.py` (100 lines)
   - Test HT/FT probability generation
   - Test governance gate integration
   - Test edge cases (0–0, high-scoring)

3. Update `c1/translation/schema.py`
   - Add `HTFTTranslationItem` dataclass

**Reference**: bpl-next (Dixon & Coles HT/FT logic)

**Validation**:
- [ ] HT/FT probabilities sum to 1.0
- [ ] Probabilities match Poisson distribution
- [ ] Tests pass (>90% coverage)
- [ ] Shadow run produces valid HT/FT items

---

### Task A2: Implement Scoreline Translation
**Priority**: P1  
**Effort**: 1 week  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/translation/scoreline_translator.py` (150 lines)
   - Generate score matrix (0–5 goals each)
   - Filter by confidence threshold
   - Translate to betting selections
   - Apply governance gates

2. `tests/test_c1_scoreline_translation.py` (100 lines)
   - Test score matrix generation
   - Test filtering logic
   - Test edge cases

3. Update `c1/translation/schema.py`
   - Add `ScorelineTranslationItem` dataclass

**Reference**: footBayes (Poisson scoreline)

**Validation**:
- [ ] Score matrix probabilities sum to 1.0
- [ ] Filtering reduces matrix to manageable size
- [ ] Tests pass (>90% coverage)
- [ ] Shadow run produces valid scoreline items

---

### Task A3: Integrate into C1TranslationEngine
**Priority**: P1  
**Effort**: 3 days  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. Update `c1/translation/engine.py`
   - Add `_translate_htft()` method
   - Add `_translate_scoreline()` method
   - Call both in `translate()` method

2. Update `c1/translation/schema.py`
   - Extend `TranslationResult.items` to include HT/FT and scoreline

3. Update `c1/runtime/release.py`
   - Handle new play types in release manager
   - Add to `allowed_plays` config

**Validation**:
- [ ] All play types (1X2, handicap, totals, HT/FT, scoreline) translate
- [ ] Release manager handles all types
- [ ] Shadow run produces all 5 play types
- [ ] Tests pass

---

## 🟡 Track B: Backtest Framework (Weeks 2–3)

### Task B1: Define Strategy Schema
**Priority**: P1  
**Effort**: 3 days  
**Owner**: Core team + analyst  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/strategy/schema.py` (100 lines)
   - `BettingStrategy` dataclass
   - `StrategyResult` dataclass
   - `StrategyMetrics` dataclass

2. `c1/strategy/__init__.py`
   - Export schema classes

**Schema design**:
```python
@dataclass
class BettingStrategy:
    name: str
    play_type: str  # "1x2", "handicap", "totals", "htft", "scoreline"
    min_confidence: float
    min_ev: float
    max_odds: float
    unit_stake: float
    tags: list[str]

@dataclass
class StrategyMetrics:
    hit_rate: float
    roi: float
    ev_per_bet: float
    sharpe_ratio: float
    max_drawdown: float
    confidence_calibration: dict[str, float]
    sample_size: int
```

**Validation**:
- [ ] Schema is complete and consistent
- [ ] Can be serialized to JSON
- [ ] Supports all play types

---

### Task B2: Implement Backtest Engine
**Priority**: P1  
**Effort**: 1 week  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/strategy/backtest.py` (300 lines)
   - `BacktestRunner` class
   - Load historical shadow runs
   - Apply strategy filters
   - Calculate metrics
   - Generate reports

2. `tests/test_c1_backtest.py` (150 lines)
   - Test metric calculations
   - Test edge cases
   - Validate against manual calculations

**Key metrics**:
- Hit rate: % correct predictions
- ROI: (wins - losses) / total_stake
- EV: expected value per bet
- Sharpe ratio: return / volatility
- Max drawdown: worst consecutive loss
- Confidence calibration: predicted vs actual

**Validation**:
- [ ] Metrics calculated correctly
- [ ] Results reproducible
- [ ] Tests pass (>90% coverage)
- [ ] Performance acceptable (< 1 sec per 100 matches)

---

### Task B3: Settlement Bridge
**Priority**: P1  
**Effort**: 3 days  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/strategy/settlement_bridge.py` (100 lines)
   - Load V24 settlements
   - Map to C1 match IDs
   - Compute actual outcomes

2. `tests/test_c1_settlement_bridge.py` (50 lines)
   - Test outcome mapping
   - Test edge cases

**Validation**:
- [ ] Settlements correctly mapped to matches
- [ ] Outcomes computed accurately
- [ ] Tests pass

---

### Task B4: Audit Integration
**Priority**: P1  
**Effort**: 2 days  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. Update `c1/audit/store.py`
   - Add `record_backtest_result()` method
   - Add `read_backtest_results()` method

2. Update `c1/strategy/backtest.py`
   - Call audit store to record results

**Validation**:
- [ ] Backtest results stored in audit trail
- [ ] Can be retrieved and analyzed
- [ ] Tests pass

---

## 🟡 Track C: Data Publishing (Weeks 2–3)

### Task C1: Decision Export API
**Priority**: P1  
**Effort**: 1 week  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/export/decision_exporter.py` (200 lines)
   - Export governance decisions (JSON, CSV, Parquet)
   - Export translation outputs
   - Export release decisions
   - Include full decision chain

2. `tests/test_c1_decision_exporter.py` (100 lines)
   - Test export formats
   - Test data integrity

**Export format**:
```json
{
  "match_id": "2026-05-27|Premier League|Manchester United|Manchester City",
  "created_at": "2026-05-27 14:30:00",
  "features": {
    "home_rating": 1756.25,
    "away_rating": 1871.46,
    "confidence": 0.65,
    "info_quality": 0.85
  },
  "inference": {
    "predicted_side": "away",
    "probabilities": {"home": 0.30, "draw": 0.25, "away": 0.45}
  },
  "governance": {
    "action": "APPROVE",
    "reason_codes": [],
    "tags": []
  },
  "translation": {
    "items": [
      {"play": "1x2", "selection": "AWAY_WIN", "confidence": 0.65, "status": "ACTIVE"},
      {"play": "handicap", "selection": "AWAY_HANDICAP", "line": 0.5, "confidence": 0.62, "status": "ACTIVE"}
    ]
  },
  "release": {
    "action": "APPROVE_RELEASE",
    "candidates": [...]
  }
}
```

**Validation**:
- [ ] All formats produce valid output
- [ ] Data integrity preserved
- [ ] Tests pass

---

### Task C2: Analytics Export
**Priority**: P1  
**Effort**: 3 days  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/export/analytics_exporter.py` (150 lines)
   - Daily/weekly summaries
   - Reason code distribution
   - Confidence distribution
   - Governance action distribution
   - Release rate trends

2. `tests/test_c1_analytics_exporter.py` (50 lines)

**Export format**:
```json
{
  "period": "2026-05-27",
  "total_matches": 150,
  "governance_distribution": {
    "APPROVE": 45,
    "DOWNGRADE": 60,
    "OBSERVE": 30,
    "BLOCK": 15
  },
  "reason_code_distribution": {
    "LINEUP_UNKNOWN": 40,
    "LINEUP_STALE": 25,
    "INFO_QUALITY_LOW": 20
  },
  "confidence_distribution": {
    "0.0-0.3": 10,
    "0.3-0.5": 40,
    "0.5-0.7": 60,
    "0.7-1.0": 40
  },
  "release_rate": 0.35
}
```

**Validation**:
- [ ] Distributions sum correctly
- [ ] Trends tracked over time
- [ ] Tests pass

---

### Task C3: Recommendation Feed
**Priority**: P1  
**Effort**: 3 days  
**Owner**: Core team  
**Status**: ⏳ READY

**Deliverables**:
1. `c1/export/recommendation_feed.py` (150 lines)
   - Format recommendations
   - Filter by governance action
   - Include metadata

2. `tests/test_c1_recommendation_feed.py` (50 lines)

**Feed format**:
```json
{
  "match_id": "2026-05-27|Premier League|Manchester United|Manchester City",
  "recommendations": [
    {
      "play": "1x2",
      "selection": "AWAY_WIN",
      "confidence": 0.65,
      "odds": 2.10,
      "status": "ACTIVE",
      "reason_codes": [],
      "tags": ["release"]
    }
  ]
}
```

**Validation**:
- [ ] Feed includes all necessary fields
- [ ] Filtering works correctly
- [ ] Tests pass

---

### Task C4: UI/External System Integration
**Priority**: P2  
**Effort**: 1 week  
**Owner**: Core team + DevOps  
**Status**: ⏳ READY

**Deliverables**:
1. Update `c1/runtime/release.py`
   - Add export hooks
   - Publish to message queue or file system

2. Integration documentation
   - How to consume exports
   - API specification

**Validation**:
- [ ] Exports published correctly
- [ ] External systems can consume
- [ ] Real-time streaming works (if applicable)

---

## 📊 Timeline Summary

```
Week 1:
  Mon–Tue:  P0 blockers (release_cfg, ELO validation)
  Wed–Thu:  Track A1 (HT/FT translation)
  Fri:      Track A2 start (scoreline translation)

Week 2:
  Mon–Tue:  Track A2 completion + A3 integration
  Wed–Thu:  Track B1 (strategy schema) + B2 start (backtest)
  Fri:      Track C1 start (decision export)

Week 3:
  Mon–Tue:  Track B2 completion + B3 (settlement bridge)
  Wed–Thu:  Track C1 completion + C2 (analytics export)
  Fri:      Track C3 (recommendation feed)

Week 4:
  Mon–Tue:  Track C4 (UI integration)
  Wed–Thu:  Testing and documentation
  Fri:      Review and sign-off
```

---

## Success Criteria (End of Week 4)

### P0 Blockers
- [ ] release_cfg.yaml updated and validated
- [ ] ELO loading verified end-to-end
- [ ] Release rate increased to >20%

### Track A
- [ ] All 5 play types translate correctly
- [ ] Tests pass (>90% coverage)
- [ ] Shadow run produces all play types

### Track B
- [ ] Backtest engine runs on historical data
- [ ] Metrics calculated correctly
- [ ] Settlement bridge maps outcomes accurately

### Track C
- [ ] Decision export produces valid output
- [ ] Analytics export shows correct distributions
- [ ] Recommendation feed includes full chain

---

## Resource Requirements

| Role | Weeks | Allocation |
|------|-------|-----------|
| Core Developer | 4 | 100% |
| Analyst | 2 | 50% |
| DevOps | 1 | 25% |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Poisson doesn't capture HT/FT correlation | Validate against historical data; add correlation factor |
| Settlement data incomplete | Reconcile against V24 records |
| Export format incompatible | Get feedback from consumers early |
| Performance bottleneck | Implement batching and async publishing |

---

## Next Steps

1. **Today**: Review and approve this task list
2. **Tomorrow**: Start P0 blockers (release_cfg, ELO validation)
3. **This week**: Complete Track A1 (HT/FT translation)
4. **Next week**: Start Track B and C in parallel
5. **Week 4**: Integration and sign-off

---

## Questions & Decisions Needed

1. Should HT/FT and scoreline be separate play types or grouped?
2. What's the minimum backtest period (1 month? 3 months? 1 year)?
3. Who are the primary consumers of exported data?
4. Should all three tracks feed into a unified dashboard?
5. Any constraints on export formats (JSON only? CSV? Parquet)?
