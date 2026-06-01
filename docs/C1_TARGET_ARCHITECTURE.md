# C1.0 Target Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        C1.0 Platform                            │
├─────────────┬─────────────┬─────────────┬──────────────────────┤
│  Data Layer │Feature Layer│  Inference  │    Translation       │
│             │             │    Layer    │       Layer          │
│ foot MySQL  │ governance  │  baseline   │  1X2 / handicap     │
│ providers   │ features    │  xgboost    │  totals / htft      │
│ adapters    │ foot signals│  lightgbm   │  scoreline          │
│ contracts   │ chaos/info  │  calibration│                      │
├─────────────┴─────────────┴──────┬──────┴──────────────────────┤
│                                  │                              │
│         Governance Layer         │        Audit Layer           │
│                                  │                              │
│  InfoGate                        │  feature_vectors.jsonl       │
│  EnvironmentGate                 │  predictions.jsonl           │
│  ConflictDetector (+ foot)       │  governance_decisions.jsonl  │
│  RiskGovernor                    │  translation_outputs.jsonl   │
│  CircuitBreaker                  │  release_decisions.jsonl     │
│                                  │  market_snapshots.jsonl      │
└──────────────────────────────────┴──────────────────────────────┘
```

## Layer Responsibilities

### Data Layer (`c1/data/`)
- **Input**: Raw match data, odds, availability, foot MySQL signals
- **Output**: Canonical contracts (CanonicalMatch, OddsSnapshot, TeamAvailability)
- **Principle**: No business logic. Pure data access and normalization.

### Feature Layer (`c1/features/`)
- **Input**: Raw fields from Data Layer
- **Output**: Computed governance features (info_quality, chaos_score, etc.)
- **Principle**: Deterministic. Same input → same output. No side effects.

### Inference Layer (`c1/inference/`)
- **Input**: Feature snapshot + model weights
- **Output**: Probabilities, predicted_side, confidence, EV
- **Principle**: Models output probabilities only. No decision authority.

### Governance Layer (`c1/modules/`)
- **Input**: Feature snapshot + Prediction snapshot + State
- **Output**: APPROVE / DOWNGRADE / OBSERVE / BLOCK + reasons
- **Principle**: Owns execution authority. Does NOT rewrite probabilities.

### Translation Layer (`c1/translation/`)
- **Input**: Inference result + Governance decision
- **Output**: Play-specific recommendations (1X2, handicap, totals, htft, score)
- **Principle**: Independent per play type. No naive 1X2→handicap mapping.

### Audit Layer (`c1/audit/`)
- **Input**: All artifacts from all layers
- **Output**: JSONL audit trail
- **Principle**: Record everything. Enable post-hoc analysis.

## Data Flow

```
Match Data → Data Layer → Feature Layer → Inference Layer
                                              ↓
                              Governance Layer ← Feature Snapshot
                                              ↓
                              Translation Layer
                                              ↓
                              Audit Layer (records all)
```

## External Integrations

| System | Role | Connection |
|--------|------|-----------|
| foot MySQL | Historical odds + fundamentals | `c1/data/foot_bridge.py` |
| V24 Legacy | Production predictions | `c1/runtime/legacy_bridge.py` |
| 500.com | Real-time odds | `src/v24_app/data_sources/` |
| Titan | Fixture source | `src/v24_app/data_sources/match_fetcher_titan.py` |

## Configuration

All configuration in `c1/configs/`:
- `governance_cfg.yaml` — Gate thresholds + decision rules
- `translation_cfg.yaml` — Play type thresholds
- `foot_bridge_cfg.yaml` — MySQL connection + signal mapping
- `runtime_mode.yaml` — Operational mode
- `release_cfg.yaml` — Release gate rules
