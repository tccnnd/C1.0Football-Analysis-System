# C1.0 Football Analysis System

C1.0 Football Analysis System is a football match analysis and recommendation
platform. The repository contains a legacy V24 desktop application path and a
new C1.0 migration path with separated data, feature, inference, governance,
translation, audit, strategy, and export layers.

The project is under active development. Recent work focused on:

- C1.0 runtime guardrails for production-mode activation.
- Independent C1 inference engines, including direct XGBoost artifact loading.
- Full-chain audit records for features, predictions, governance decisions,
  translation outputs, release decisions, and market snapshots.
- Foot/Go data bridge integration and ELO/xG support.
- Backtest, settlement, recommendation feed, and export flows.
- V24 UI integration modules and model monitoring support.

## Current Status

- Main branch: `main`
- Latest C1 migration commit: `8964e5c`
- Latest workspace snapshot commit: `c2fa6fd`
- GitHub upload merge commit: `42726f3`
- Canonical C1 test scope: `tests/test_c1_*.py`
- Last verified C1 result: `249 passed`

C1.0 is not allowed to become the primary production path unless recorded
acceptance metrics pass the runtime guard:

- `accuracy_c1 >= accuracy_v24`
- `governance_separation >= 0.05`

If `runtime_mode.yaml` is manually changed to `c1_primary` while those metrics
are not satisfied, the runtime mode resolver downgrades it to
`formal_list_default`.

## Repository Layout

```text
c1/                 C1.0 migration modules
  audit/            JSONL audit storage
  configs/          runtime, governance, release, translation, foot configs
  data/             data adapters, foot bridge, ELO/xG loading
  export/           recommendation and analytics exporters
  features/         governance and foot-derived features
  inference/        baseline, XGBoost, LightGBM, calibration runtime
  modules/          governance judge and gates
  runtime/          shadow, comparison, release, and mode handling
  strategy/         backtest and settlement bridge
  translation/      1X2, handicap, totals, HT/FT, scoreline translators

src/v24_app/        V24 desktop application and integration surface
tests/              Canonical automated test suite
scripts/            Import, validation, backtest, and training helpers
docs/               Architecture, migration, integration, and progress docs
data/               Model artifacts, xG snapshots, and runtime state
reports/            Generated reports and shadow-run outputs
```

## Start The Application

On Windows, run:

```powershell
E:\APP\ELO\start_app.bat
```

The removed `启动APP.bat` launcher was only a wrapper around `start_app.bat`.
The current startup script uses `venv\Scripts\python.exe launcher.py` when the
project virtual environment exists, otherwise it falls back to `python
launcher.py`.

## Test Commands

Canonical C1 validation:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_*.py
```

Focused examples:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_mode_guard.py
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_xgboost_equivalence.py
```

## Operational Notes

- The repository includes local scripts for model training, calibration,
  history import, xG import, and production health checks.
- Some data and model artifacts are intentionally local-project assets. Review
  `.gitignore` and `data/` before adding new large files.
- `foot_0408.sql` is a local database dump and is not part of the committed
  project snapshot.

## Review And Maintenance Evidence

This project keeps development evidence in several forms:

- Git commit history with focused C1 migration and runtime guard commits.
- Automated tests under `tests/`, including C1 runtime, inference, governance,
  translation, backtest, settlement, export, and equivalence checks.
- Architecture and migration documents under `docs/`.
- Runtime acceptance guard code in `c1/runtime/mode.py`.
- Generated reports under `reports/` for shadow-run and strategy review.

See [docs/MAINTENANCE.md](docs/MAINTENANCE.md) for the maintenance and review
workflow used for this repository.
