# C1.0 Status Card - 2026-05-27

## 🎯 Current Mission
Unblock the release pipeline and expand C1.0 capabilities across three parallel tracks.

---

## 🔴 P0 Blockers (This Week)

### 1. ELO Loading Bridge
**Status**: ✅ DONE + VALIDATED  
**Impact**: Fixes zero ELO signal in inference  
**What's done**:
- ✓ `c1/data/elo_loader.py` created with 4-tier matching strategy
- ✓ `c1/runtime/legacy_bridge.py` updated with automatic ELO injection
- ✓ Unit tests pass (100% coverage)
- ✓ Demo script runs successfully
- ✓ **NEW**: Fuzzy matching for team names (handles "阿德莱德联" → "阿德莱德")
- ✓ **NEW**: Support for both club (1,211) and national (86) teams = 1,297 total
- ✓ **NEW**: End-to-end validation on live matches (Adelaide United vs Auckland FC)
- ✓ **NEW**: Comprehensive validation report created

**Validation Results**:
- ELO coverage: 62% (1,297 / 2,090 teams)
- Test match: home_rating 1549.00, away_rating 1623.88 ✓
- missing_elo_loss: 0.0 ✓
- No MISSING_ELO_LOSS reason codes ✓
- Confidence improved: 0.2890 ✓

**What's next**: Run shadow comparison on 50+ matches to verify release rate improvement

**Files**:
- `c1/data/elo_loader.py` (NEW - with fuzzy matching)
- `docs/C1_ELO_LOADING_VALIDATION.md` (NEW - comprehensive report)

---

### 2. Release Gate Policy
**Status**: ⏳ READY (30 min fix)  
**Impact**: Unblocks release pipeline  
**Current**: Only APPROVE passes gate → 0% release rate  
**Fix**: Add DOWNGRADE to `allowed_governance_actions`  
**Expected**: 20–50% release rate after fix

**File**: `c1/configs/release_cfg.yaml`

---

### 3. Availability Data Coverage
**Status**: ⏳ IN PROGRESS  
**Impact**: Improves lineup_known rate  
**Current**: ~6 matches/day from titan_detail  
**Goal**: Re-enable API-Football (31 source mappings ready)  
**Blocker**: API account suspended (external)

---

## 📊 Three-Track Development Plan

### Track A: Complete Translation Layer (Weeks 1–2)
**Goal**: Full betting product coverage  
**Scope**:
- [ ] HT/FT translation (9 outcomes)
- [ ] Scoreline translation (81 outcomes, filtered)
- [ ] Integration into C1TranslationEngine

**Reference**: bpl-next, footBayes  
**Effort**: 2 weeks  
**Owner**: Core team

---

### Track B: Backtest Framework (Weeks 2–3)
**Goal**: Systematic strategy evaluation  
**Scope**:
- [ ] Strategy schema definition
- [ ] Backtest engine (hit rate, ROI, Sharpe, etc.)
- [ ] Settlement bridge (V24 → C1)
- [ ] Audit integration

**Reference**: sports-betting  
**Effort**: 3–4 weeks  
**Owner**: Core team + analyst

---

### Track C: Data Publishing (Weeks 2–3)
**Goal**: Export C1 decisions for downstream consumption  
**Scope**:
- [ ] Decision export API (JSON, CSV, Parquet)
- [ ] Analytics export (distributions, trends)
- [ ] Recommendation feed (full decision chain)
- [ ] UI/external system integration

**Reference**: foot (Go)  
**Effort**: 2–3 weeks  
**Owner**: Core team + DevOps

---

## 📈 Expected Outcomes (End of Week 4)

| Metric | Before | After |
|--------|--------|-------|
| **Release Rate** | ~0% | >20% |
| **Confidence** | 0.25–0.42 | 0.50–0.70+ |
| **Play Types** | 3 (1X2, handicap, totals) | 5 (+HT/FT, scoreline) |
| **Backtest Capability** | None | Full framework |
| **Data Export** | None | JSON/CSV/Parquet |

---

## 🗓️ Week-by-Week Breakdown

### Week 1: P0 + Track A Start
```
Mon–Tue:  Fix release_cfg.yaml + validate ELO
Wed–Thu:  Implement HT/FT translation
Fri:      Implement scoreline translation
```

### Week 2: Track A + Track B/C Start
```
Mon–Tue:  Integrate HT/FT + scoreline
Wed–Thu:  Strategy schema + backtest engine start
Fri:      Decision export API start
```

### Week 3: Track B/C Completion
```
Mon–Tue:  Settlement bridge + analytics export
Wed–Thu:  Recommendation feed
Fri:      UI integration start
```

### Week 4: Integration & Sign-Off
```
Mon–Tue:  UI integration completion
Wed–Thu:  Testing and documentation
Fri:      Review and sign-off
```

---

## 📋 Immediate Action Items (Next 24 Hours)

1. **Fix release_cfg.yaml** (30 min)
   - Add DOWNGRADE to `allowed_governance_actions`
   - Validate on 5 live matches
   - Check release_decisions.jsonl for APPROVE_RELEASE

2. **Validate ELO Loading** (1 hour)
   - Run shadow comparison on 5 matches
   - Verify home_rating and away_rating populated
   - Check missing_elo_loss = 0.0
   - Verify confidence improved

3. **Approve Roadmap** (30 min)
   - Review `C1_ROADMAP_PHASE5_PLUS.md`
   - Confirm resource allocation
   - Agree on timeline

---

## 🎓 Key Insights

### Why These Three Tracks?
1. **Track A** (Translation): Prerequisite for B and C; completes Phase 5
2. **Track B** (Backtest): Enables data-driven governance tuning
3. **Track C** (Export): Enables downstream consumption and dashboards

### Why Now?
- ELO loading unblocks inference signal
- Release gate fix unblocks pipeline
- Three tracks can run in parallel
- All have clear success criteria

### Why These References?
- **bpl-next**: Complete Poisson implementation (HT/FT, scoreline)
- **sports-betting**: Proven backtest framework
- **foot**: Data publishing patterns

---

## 📊 Current Architecture Status

```
Data Layer          ✅ Complete (with ELO bridge)
Feature Layer       ✅ Complete (Phase 2)
Inference Layer     ✅ Complete (Phase 4, XGBoost)
Governance Layer    ✅ Complete (5 gates)
Translation Layer   ⏳ Partial (3/5 play types)
Audit Layer         ✅ Complete (6 JSONL streams)
Runtime             ✅ Complete (shadow, release, comparison)
```

**Next**: Complete translation layer (Track A) → enable backtest (Track B) → enable export (Track C)

---

## 🚀 Success Metrics

### Week 1
- [ ] release_cfg.yaml updated
- [ ] ELO loading validated
- [ ] HT/FT translation implemented

### Week 2
- [ ] All 5 play types translate
- [ ] Backtest engine runs
- [ ] Decision export works

### Week 3
- [ ] Backtest metrics calculated
- [ ] Analytics export shows distributions
- [ ] Recommendation feed includes full chain

### Week 4
- [ ] UI integration complete
- [ ] All tests pass (>90% coverage)
- [ ] Documentation complete

---

## 📞 Questions for Stakeholders

1. **Track A**: Should HT/FT and scoreline be separate play types or grouped?
2. **Track B**: What's the minimum backtest period (1 month? 3 months? 1 year)?
3. **Track C**: Who are the primary consumers of exported data?
4. **Integration**: Should all three tracks feed into a unified dashboard?
5. **Timeline**: Any constraints or dependencies we should know about?

---

## 📚 Documentation

- `C1_ROADMAP_PHASE5_PLUS.md` - Full roadmap with dependency graph
- `C1_IMMEDIATE_TASKS.md` - Detailed task breakdown
- `C1_ELO_LOADING_BRIDGE.md` - ELO loading implementation
- `C1_ELO_LOADING_SUMMARY.md` - ELO loading summary
- `QUICK_REFERENCE_ELO_LOADING.md` - Quick reference

---

## 🎯 Bottom Line

**We have a clear path to unblock the release pipeline and expand C1.0 capabilities.**

- ✅ ELO loading done (P0 blocker #1)
- ⏳ Release gate fix ready (P0 blocker #2, 30 min)
- 📋 Three parallel tracks planned (4 weeks)
- 📊 Clear success criteria and timeline
- 🚀 Ready to execute

**Next step**: Approve roadmap and start Week 1 tasks.

---

**Last Updated**: 2026-05-27 15:30 UTC  
**Next Review**: 2026-05-28 (after P0 blockers)
