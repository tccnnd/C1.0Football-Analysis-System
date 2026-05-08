# AGENTS.md — V24 → C1.0 Migration Instructions

This repository contains a legacy football analysis system called V24.
Your mission is to migrate it into a new governed platform called C1.0.

## Primary objective
Do not keep evolving V24 in place.
Instead:
1. Treat V24 as a legacy production system.
2. Extract its capabilities.
3. Rebuild them into C1.0 layered architecture.
4. Migrate in stages with auditability and minimal production risk.

## C1.0 target architecture
C1.0 must be organized into these layers:

- Data Layer
- Feature Layer
- Inference Layer
- Governance Layer
- Translation Layer
- Audit Layer

## Architectural principles
1. Governance owns execution authority.
   - Models may output probabilities.
   - Governance decides APPROVE / DOWNGRADE / OBSERVE / BLOCK.
   - Governance must not rewrite raw model probabilities.

2. Translation is separate from inference.
   - 1X2, handicap, totals, HT/FT, and score expressions must not be derived by naive direct mapping.
   - Especially: do not translate high home-win probability directly into handicap win.

3. Experience must be structured before use.
   - Legacy heuristics must first become fields, flags, or governance conditions.
   - Do not preserve “rule prose” as direct decision logic.

4. Every decision must be auditable.
   - Preserve feature snapshot
   - Preserve raw prediction
   - Preserve governance decision
   - Preserve final expression/output
   - Preserve outcome and attribution tags

5. Migration is capability-based, not file-based.
   - Migrate behaviors and responsibilities.
   - Do not blindly port legacy files.

## Hard rules
- Do not directly refactor core V24 production logic unless explicitly asked.
- Do not change runtime behavior during audit and planning phases.
- Do not delete legacy code until replacement behavior exists in C1.0 and has been compared.
- Prefer isolated new modules under `c1/` over invasive edits to V24.
- If uncertain, inspect more files and trace the runtime path instead of guessing.
- Prefer repository-grounded findings over generic architectural advice.

## Legacy handling policy
For every discovered legacy capability, classify it as one of:
- KEEP
- REWRITE
- SPLIT
- DROP

And map it to one of:
- Data Layer
- Feature Layer
- Inference Layer
- Governance Layer
- Translation Layer
- Audit Layer

## Required migration outputs
When asked to audit or plan, produce documents under `docs/` such as:
- C1_MIGRATION_AUDIT.md
- C1_GAP_MAP.md
- C1_RUNTIME_PATHS.md
- C1_TARGET_ARCHITECTURE.md
- C1_MODULE_MAP.md
- C1_MIGRATION_SEQUENCE.md

## Required implementation priorities
When asked to implement C1.0, use this order:

### Phase 1
Governance skeleton
- c1/core/schema.py
- c1/core/reason_codes.py
- c1/modules/judge.py
- c1/configs/governance_cfg.yaml

### Phase 2
Governance-ready feature production
- info quality fields
- lineup known / freshness
- missing ELO loss
- chaos score
- odds move against model
- line move against model

### Phase 3
Audit trail
- feature_vectors
- predictions
- governance_decisions

### Phase 4
Inference migration
- baseline
- XGBoost/LightGBM
- calibration
- EV / confidence

### Phase 5
Translation layer
- 1X2 translation
- handicap translation
- totals translation
- no naive one-step mapping from 1X2 to handicap

## Governance expectations
At minimum, Governance Layer must implement:
- InfoGate
- EnvironmentGate
- ConflictDetector
- RiskGovernor
- CircuitBreaker

ConflictDetector must:
- use predicted_side rather than home-win-only logic
- separate hard conflicts and soft conflicts
- support high-confidence / low-info conflict
- support injury conflict
- support market divergence conflict
- support chaos-based risk escalation

## Data expectations
The system must eventually support and preserve these entities:
- matches
- odds_snapshots
- team_availability
- match_context
- feature_vectors
- predictions
- governance_decisions
- match_outcomes

## Testing and validation rules
When implementing code:
- add unit tests for new C1.0 modules
- avoid hidden side effects
- document source-of-truth dependencies
- do not claim a migration step is complete without tests or a traceable validation path

## Working style
- Be concrete.
- Be surgical.
- Prefer small, reviewable steps.
- Explain coupling hotspots before attempting structural changes.
- During migration, preserve comparison ability between V24 and C1.0.

## Preferred delivery style
When producing plans:
- show exact files to create
- show exact files to inspect
- show exact responsibilities to move
- show risk points
- show validation steps

When producing code:
- keep C1.0 isolated from V24 unless integration is explicitly requested
- document assumptions in code comments only when necessary
- keep naming explicit and layer-aligned

## Initial assumption
Unless instructed otherwise:
- V24 remains the legacy baseline
- C1.0 is built under a new `c1/` package
- shadow-run comparison is preferred before any production switch
