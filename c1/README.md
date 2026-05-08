# C1.0 Workspace

This folder is the isolated workspace for the C1.0 migration.

Rules:

- Do not add new production logic to `src/v24_app` unless integration is explicitly requested.
- New layered architecture work should land under `c1/`.
- V24 remains the legacy baseline for comparison.

Current status:

- `core/`: shared contracts and reason codes
- `modules/`: Phase 1 governance judge skeleton
- `configs/`: governance and translation configuration
- `data/`: placeholder for future Data Layer
- `features/`: governance-ready feature production
- `inference/`: raw inference contract and model adapters
- `governance/`: placeholder for future Governance Layer assembly
- `translation/`: independent play translation layer
- `audit/`: feature/prediction/governance/translation audit storage
- `runtime/`: shadow-run orchestration across C1 layers

Open todo:

- Primary availability source integration is tracked in [C1_TODO.md](/E:/APP/ELO/docs/C1_TODO.md)
