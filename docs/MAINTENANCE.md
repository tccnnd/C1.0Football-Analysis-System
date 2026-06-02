# Maintenance And Review Workflow

This document summarizes how the C1.0 Football Analysis System repository is
maintained and what evidence is available for project review.

## Maintainer Responsibility

The repository is maintained as a single active project with a focus on:

- Preserving the V24 application path while C1.0 is migrated safely.
- Keeping C1.0 production activation behind measurable runtime guardrails.
- Separating migration commits from broad workspace snapshot commits when
  possible.
- Running focused tests before committing high-risk runtime changes.

## Change Management

Recent change management follows this pattern:

1. Inspect the working tree before staging.
2. Group changes by logical scope.
3. Stage only the approved scope when doing focused commits.
4. Run targeted tests for the affected subsystem.
5. Commit with a short message describing the scope.
6. Push to GitHub only after the local branch is clean.

Examples from the current history:

- `8964e5c Add C1 migration runtime guard and independent inference`
- `c2fa6fd Commit remaining workspace changes`
- `42726f3 Merge remote-tracking branch 'origin/main'`

## Acceptance Gates

C1.0 primary mode is guarded by `c1/runtime/mode.py`.

The runtime refuses `c1_primary` unless the recorded validation metrics satisfy:

- `accuracy_c1 >= accuracy_v24`
- `governance_separation >= 0.05`

This prevents accidental production activation when shadow-run validation has
not met the acceptance threshold.

## Test Evidence

Canonical C1 test command:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_*.py
```

Last verified result:

```text
249 passed
```

Key test areas include:

- Runtime mode guard and provider guard bypass prevention.
- XGBoost independent-engine equivalence with V24 behavior.
- Governance judge gates.
- Inference, calibration, translation, and release runtime.
- Backtest, settlement bridge, recommendation feed, and export flows.

## Issue And Review Handling

The repository currently uses commit history, tests, and local audit documents
as the main review trail. When GitHub issues or pull requests are used, the
expected handling policy is:

- Keep PRs scoped to one logical area.
- Link the relevant test command and result in the PR description.
- Classify issues by subsystem: C1 runtime, V24 UI, data bridge, model
  inference, strategy/backtest, deployment, or documentation.
- Avoid mixing production runtime changes with process documentation or scratch
  scripts.

## Version And Release Notes

Version and release state are represented through:

- `c1/configs/runtime_mode.yaml`
- `c1/configs/release_cfg.yaml`
- `docs/C1_MIGRATION_SEQUENCE.md`
- `docs/C1_RUNTIME_PATHS.md`
- Shadow-run reports in `reports/shadow_history/`

Before any production switch, update the validation metrics and rerun the
canonical C1 test scope.
