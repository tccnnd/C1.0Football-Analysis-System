# C1.0 Runtime Paths

## 1. Shadow Run Path（当前主要路径）

```
AppMatch (V24 legacy)
    │
    ├─→ v24_app.core.predict_match()          # V24 预测
    │       → ELO + Poisson + Market + XGBoost ensemble
    │       → specialist fusion + Bayes calibration
    │       → play thresholds + strategy admission
    │       → 输出: prediction dict
    │
    └─→ c1.runtime.shadow.C1ShadowRunner.run_match()
            │
            ├─ 1. build_governance_feature_snapshot(raw_fields)
            │      → enrich_with_foot_signals()     # foot MySQL 信号注入
            │      → compute_info_quality()
            │      → compute_chaos_score()
            │      → compute_odds_move_against_model()
            │
            ├─ 2. C1InferenceEngine.infer()
            │      → BaselineInferenceEngine (Market + ELO + Poisson)
            │      → C1XGBoostAdapter (if model ready)
            │      → blend_components() → confidence + EV
            │
            ├─ 3. build_governance_feature_snapshot() (second pass with prediction)
            │      → 再次注入 foot 信号（含 model_agreement）
            │
            ├─ 4. GovernanceJudge.evaluate()
            │      → InfoGate
            │      → EnvironmentGate
            │      → ConflictDetector (+ foot euro-asia conflict)
            │      → RiskGovernor
            │      → CircuitBreaker
            │      → Decision: APPROVE / DOWNGRADE / OBSERVE / BLOCK
            │
            ├─ 5. C1TranslationEngine.translate()
            │      → 1X2 translation
            │      → handicap translation (independent)
            │      → totals translation
            │      → HT/FT translation
            │      → scoreline translation
            │
            └─ 6. C1AuditStore.record_*()
                   → feature_vectors.jsonl
                   → predictions.jsonl
                   → governance_decisions.jsonl
                   → translation_outputs.jsonl
```

## 2. Comparison Path

```
c1.runtime.comparison.run_shadow_comparison_for_legacy_matches()
    │
    ├─ For each match:
    │   ├─ V24 predict_match() → v24_prediction
    │   ├─ C1 shadow run → C1ShadowRunResult
    │   └─ Build C1ComparisonRow (side_diverged, confidence_gap, etc.)
    │
    ├─ Build summary (governance counts, reason codes, accuracy)
    └─ Write reports (Markdown + JSON)
```

## 3. Historical Shadow Run Path

```
shadow_run_history.py
    │
    ├─ 1. fetch_history_matches() → foot MySQL (t_match_his + t_asia_his + t_euro_his)
    ├─ 2. build_app_match() → AppMatch (from foot data)
    ├─ 3. For each match:
    │   ├─ V24 predict_match()
    │   ├─ enrich_with_foot_signals() → extra_fields
    │   ├─ run_shadow_for_legacy_match() → C1ShadowRunResult
    │   └─ Compare: v24_side vs c1_side vs actual_result
    ├─ 4. build_report() → accuracy, governance distribution, foot stats
    └─ 5. write_reports() → reports/shadow_history/
```

## 4. Production Path（目标，未完全实现）

```
Titan/500 fetch → AppMatch list
    │
    ├─ V24 predict_match() → display in UI
    │
    ├─ C1 shadow run (parallel) → C1ShadowRunResult
    │   ├─ Governance decision → tags in UI (C1动作 column)
    │   └─ Audit trail → data/c1_audit/
    │
    ├─ Release gate → formal_list (if APPROVE + release criteria met)
    │
    └─ Auto-settle → update ELO + training samples + gate metrics
```

## 5. foot Signal Path

```
foot MySQL (t_asia_his, t_euro_his, t_b_f_score, t_b_f_battle, t_b_f_jin)
    │
    ├─ FootBridge.get_signals_for_match()
    │   ├─ _fill_asia_signals() → asia_direction, consensus, let_ball_move
    │   ├─ _fill_euro_signals() → euro_direction, euro_asia_conflict
    │   ├─ _fill_fundamental_signals() → ranking_diff, h2h, recent_form
    │   └─ _fill_model_signals() → model_consensus, model_conflict
    │
    ├─ FootMatchSignals.as_feature_dict → 16 raw features
    │
    ├─ enrich_with_foot_signals()
    │   ├─ compute_foot_asia_signal_strength()
    │   ├─ compute_foot_euro_asia_conflict_score()
    │   ├─ compute_foot_fundamental_score()
    │   ├─ compute_foot_model_agreement()
    │   └─ enhance market_divergence + chaos_score
    │
    └─ ConflictDetector.evaluate()
        ├─ FOOT_EURO_ASIA_CONFLICT (hard/soft)
        ├─ FOOT_ASIA_SIGNAL_AGAINST_MODEL (soft)
        └─ FOOT_MODEL_DISAGREEMENT (soft)
```

## 6. ELO Precomputation Path

```
build_elo_from_foot.py
    │
    ├─ fetch_all_matches() → 344K matches from foot MySQL
    ├─ Sequential ELO update (chronological order)
    ├─ Filter: min 10 matches per team
    └─ Save: data/state/ratings.json (6555 teams)
             data/state/foot_elo_ratings.json (metadata)
```
