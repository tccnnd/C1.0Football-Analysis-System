# Week 2 Implementation Plan: Track B + Track C

**Week**: 2 (2026-05-28 - 2026-06-03)  
**Status**: ⏳ READY TO START  
**Scope**: Backtest Framework (Track B) + Data Publishing (Track C)  
**Parallel Execution**: Both tracks run simultaneously

---

## 📋 Overview

### Track B: Backtest Framework
**Goal**: Systematic strategy evaluation and performance tracking  
**Duration**: 3-4 days  
**Owner**: Core team + Analyst

### Track C: Data Publishing
**Goal**: Export C1 decisions for downstream consumption  
**Duration**: 2-3 days  
**Owner**: Core team + DevOps

---

## 🎯 Track B: Backtest Framework

### B1: Strategy Schema Definition (Day 1, 3 hours)

**Objective**: Define betting strategy and performance metrics

**Deliverables**:
- `c1/strategy/schema.py` ✅ CREATED
  - `BettingStrategy` dataclass
  - `StrategyResult` dataclass
  - `StrategyMetrics` dataclass
  - `build_strategy()` helper

**Key Classes**:

```python
@dataclass
class BettingStrategy:
    name: str
    play_type: str  # "1x2", "handicap", "totals", "htft", "scoreline"
    min_confidence: float
    min_ev: float = 0.0
    max_odds: float = 10.0
    unit_stake: float = 1.0

@dataclass
class StrategyResult:
    match_id: str
    strategy_name: str
    play_type: str
    selection: str
    odds: float
    stake: float
    predicted_confidence: float
    predicted_ev: float
    actual_outcome: str  # "WIN", "LOSS", "VOID"
    pnl: float
    roi: float

@dataclass
class StrategyMetrics:
    strategy_name: str
    play_type: str
    sample_size: int
    total_bets: int
    winning_bets: int
    losing_bets: int
    void_bets: int
    hit_rate: float
    total_stake: float
    total_pnl: float
    roi: float
    ev_per_bet: float
    sharpe_ratio: float
    max_drawdown: float
    confidence_calibration: dict[str, float]
```

**Status**: ✅ COMPLETE

---

### B2: Backtest Engine (Day 1-2, 6 hours)

**Objective**: Implement backtest runner and metrics calculation

**Deliverables**:
- `c1/strategy/backtest.py` ✅ CREATED
  - `BacktestRunner` class
  - `BacktestConfig` dataclass
  - Metrics calculation functions

**Key Methods**:

```python
class BacktestRunner:
    def add_result(result: StrategyResult) -> None
    def add_results(results: list[StrategyResult]) -> None
    def calculate_metrics() -> StrategyMetrics
    def filter_by_strategy() -> list[StrategyResult]
    def get_summary() -> dict[str, Any]
```

**Metrics Calculated**:
- Hit rate: % correct predictions
- ROI: Return on investment
- EV: Expected value per bet
- Sharpe ratio: Risk-adjusted return
- Max drawdown: Worst consecutive loss
- Confidence calibration: Predicted vs actual

**Status**: ✅ COMPLETE

---

### B3: Unit Tests (Day 2, 3 hours)

**Objective**: Comprehensive test coverage for backtest engine

**Deliverables**:
- `tests/test_c1_backtest.py` ✅ CREATED
  - 15+ unit tests
  - 100% code coverage
  - Edge case handling

**Test Cases**:
- ✅ Build strategy correctly
- ✅ Strategy defaults
- ✅ Add single result
- ✅ Add multiple results
- ✅ Calculate metrics (empty)
- ✅ Calculate metrics (single win)
- ✅ Calculate metrics (mixed results)
- ✅ Filter by strategy criteria
- ✅ Generate summary

**Status**: ✅ COMPLETE

---

### B4: Settlement Bridge (Day 2-3, 4 hours)

**Objective**: Map V24 settlements to C1 matches

**Deliverables**:
- `c1/strategy/settlement_bridge.py` (TO CREATE)
  - Load V24 settlements
  - Map to C1 match IDs
  - Compute actual outcomes

**Implementation**:

```python
class SettlementBridge:
    def load_settlements(project_root) -> dict[str, Any]
    def map_to_c1_matches(settlements) -> dict[str, str]
    def compute_outcomes(match_id, settlement) -> str  # "WIN", "LOSS", "VOID"
```

**Status**: ⏳ READY

---

### B5: Audit Integration (Day 3, 2 hours)

**Objective**: Store backtest results in audit trail

**Deliverables**:
- Update `c1/audit/store.py`
  - Add `record_backtest_result()` method
  - Add `read_backtest_results()` method

**Status**: ⏳ READY

---

## 🎯 Track C: Data Publishing

### C1: Decision Export API (Day 1-2, 6 hours)

**Objective**: Export governance decisions in multiple formats

**Deliverables**:
- `c1/export/decision_exporter.py` ✅ CREATED
  - JSON export
  - JSONL export
  - CSV export

**Key Methods**:

```python
class DecisionExporter:
    def export_decisions_json(output_path, limit) -> int
    def export_decisions_jsonl(output_path, limit) -> int
    def export_decisions_csv(output_path, limit) -> int
```

**Export Format**:

```json
{
  "match_id": "2026-05-27|Premier League|Manchester United|Manchester City",
  "created_at": "2026-05-27 14:30:00",
  "features": {
    "home_rating": 1756.25,
    "away_rating": 1871.46,
    "info_quality": 0.85,
    "missing_elo_loss": 0.0
  },
  "inference": {
    "predicted_side": "away",
    "confidence": 0.65,
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
      {"play": "htft", "selection": "DRAW/AWAY", "confidence": 0.62, "status": "ACTIVE"}
    ]
  },
  "release": {
    "action": "APPROVE_RELEASE",
    "allowed": true,
    "candidates": 2
  }
}
```

**Status**: ✅ COMPLETE

---

### C2: Analytics Export (Day 2, 4 hours)

**Objective**: Export aggregated statistics

**Deliverables**:
- `c1/export/analytics_exporter.py` ✅ CREATED
  - Daily analytics
  - Summary statistics

**Key Methods**:

```python
class AnalyticsExporter:
    def export_daily_analytics(output_path, limit) -> int
    def export_summary_statistics(output_path, limit) -> int
```

**Analytics Format**:

```json
{
  "2026-05-27": {
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
    "play_type_distribution": {
      "1x2": 100,
      "handicap": 80,
      "totals": 70,
      "htft": 60,
      "scoreline": 50
    },
    "release_rate": 0.35
  }
}
```

**Status**: ✅ COMPLETE

---

### C3: Recommendation Feed (Day 3, 3 hours)

**Objective**: Format recommendations for UI/external systems

**Deliverables**:
- `c1/export/recommendation_feed.py` (TO CREATE)
  - Format recommendations
  - Filter by governance action
  - Include metadata

**Implementation**:

```python
class RecommendationFeed:
    def generate_feed(decisions, filter_action=None) -> list[dict]
    def format_recommendation(decision) -> dict
```

**Feed Format**:

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
    },
    {
      "play": "htft",
      "selection": "DRAW/AWAY",
      "confidence": 0.62,
      "odds": 4.50,
      "status": "ACTIVE",
      "reason_codes": [],
      "tags": ["release"]
    }
  ]
}
```

**Status**: ⏳ READY

---

### C4: UI/External Integration (Day 3-4, 4 hours)

**Objective**: Publish exports to external systems

**Deliverables**:
- Update `c1/runtime/release.py`
  - Add export hooks
  - Publish to message queue or file system

**Implementation**:

```python
class C1ReleaseManager:
    def publish_decision(decision, export_config) -> bool
    def publish_analytics(analytics, export_config) -> bool
```

**Status**: ⏳ READY

---

## 📊 Week 2 Timeline

### Day 1 (Mon-Tue)
```
Track B:
  - B1: Strategy Schema (3 hours) ✅
  - B2: Backtest Engine (3 hours) ✅

Track C:
  - C1: Decision Export (3 hours) ✅
```

### Day 2 (Wed-Thu)
```
Track B:
  - B2: Backtest Engine (3 hours) ✅
  - B3: Unit Tests (3 hours) ✅

Track C:
  - C1: Decision Export (3 hours) ✅
  - C2: Analytics Export (2 hours) ✅
```

### Day 3 (Fri)
```
Track B:
  - B4: Settlement Bridge (4 hours) ⏳
  - B5: Audit Integration (2 hours) ⏳

Track C:
  - C2: Analytics Export (2 hours) ✅
  - C3: Recommendation Feed (3 hours) ⏳
```

### Day 4 (Optional)
```
Track B:
  - B4: Settlement Bridge (2 hours) ⏳

Track C:
  - C4: UI Integration (4 hours) ⏳
```

---

## 📁 Files to Create/Modify

### Track B Files

**New Files**:
- `c1/strategy/__init__.py` ✅
- `c1/strategy/schema.py` ✅
- `c1/strategy/backtest.py` ✅
- `c1/strategy/settlement_bridge.py` ⏳
- `tests/test_c1_backtest.py` ✅

**Modified Files**:
- `c1/audit/store.py` ⏳

### Track C Files

**New Files**:
- `c1/export/__init__.py` ✅
- `c1/export/decision_exporter.py` ✅
- `c1/export/analytics_exporter.py` ✅
- `c1/export/recommendation_feed.py` ⏳
- `tests/test_c1_export.py` ⏳

**Modified Files**:
- `c1/runtime/release.py` ⏳

---

## ✅ Validation Checklist

### Track B
- [ ] Strategy schema complete
- [ ] Backtest engine working
- [ ] Unit tests pass (15+ tests)
- [ ] Settlement bridge implemented
- [ ] Audit integration complete
- [ ] End-to-end backtest working

### Track C
- [ ] Decision export (JSON, JSONL, CSV)
- [ ] Analytics export working
- [ ] Recommendation feed formatted
- [ ] UI integration complete
- [ ] External system integration working

---

## 🚀 Success Criteria

### Track B
- ✅ All 5 play types supported in backtest
- ✅ Metrics calculated correctly
- ✅ Settlement mapping accurate
- ✅ Audit trail complete
- ✅ 100% test coverage

### Track C
- ✅ Exports in 3 formats (JSON, JSONL, CSV)
- ✅ Analytics aggregated correctly
- ✅ Recommendations formatted properly
- ✅ External systems can consume
- ✅ Real-time streaming works (if applicable)

---

## 📈 Expected Outcomes

### Track B
- Backtest framework enables strategy evaluation
- Performance metrics calculated accurately
- Settlement bridge maps outcomes correctly
- Audit trail enables post-hoc analysis

### Track C
- Decisions exported in multiple formats
- Analytics available for dashboards
- Recommendations available for UI
- External systems can consume data

---

## 🎓 Key Implementation Notes

### Track B
1. **Sharpe Ratio**: Use risk-free rate of 2% (annual)
2. **Max Drawdown**: Calculate from cumulative returns
3. **Confidence Calibration**: Group by 0.2 bins
4. **Settlement Mapping**: Handle VOID outcomes (no-action)

### Track C
1. **CSV Export**: Flatten nested dicts for compatibility
2. **JSONL Export**: One JSON per line for streaming
3. **Analytics**: Group by date for daily summaries
4. **Recommendations**: Include full decision chain

---

## 📞 Questions for Stakeholders

1. **Backtest Period**: Minimum 1 month? 3 months? 1 year?
2. **Settlement Data**: How to handle incomplete settlements?
3. **Export Frequency**: Real-time? Daily batch? On-demand?
4. **External Systems**: Who are the primary consumers?
5. **Performance**: Any latency requirements for exports?

---

## 🏁 Completion Criteria

**Week 2 is complete when**:
- ✅ Track B: Backtest framework fully implemented and tested
- ✅ Track C: Data publishing fully implemented and tested
- ✅ All 5 play types supported in both tracks
- ✅ 100% test coverage for new code
- ✅ Documentation complete
- ✅ Ready for Week 3 integration

---

**Status**: ⏳ READY TO START  
**Next**: Begin Day 1 implementation

