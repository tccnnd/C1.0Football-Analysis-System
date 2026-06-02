# Release Process

This document defines how to prepare, validate, and publish releases for the
C1.0 Football Analysis System.

## Release Principles

- Releases should be traceable through Git commits and runtime config.
- C1.0 production activation must be metric-gated.
- V24 should remain available as fallback and comparison while C1.0 is being
  proven.
- Broad workspace snapshots are allowed only when explicitly requested and
  should be labeled as such.

## Release Types

### Documentation Release

Examples:

- README updates.
- Roadmap updates.
- Release process updates.
- Tool workflow updates.

Required checks:

```powershell
git status --short
```

### C1 Runtime Release

Examples:

- Inference runtime changes.
- Governance changes.
- Translation changes.
- Release guard changes.
- Shadow/comparison/release runner changes.

Required checks:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_*.py
```

Additional checks when production mode is affected:

- Inspect `c1/configs/runtime_mode.yaml`.
- Verify `get_runtime_mode()` downgrade behavior for unmet metrics.
- Confirm latest validation metrics are recorded.

### V24 UI Release

Examples:

- `src/v24_app/ui.py`
- `src/v24_app/ai_dashboard.py`
- `src/v24_app/ui_modules/*`
- C1 center or model center UI changes.

Required checks:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_ui_*modules.py
```

Use narrower tests when only one UI module changes.

### Data Or Model Pipeline Release

Examples:

- Import scripts.
- Training scripts.
- Calibration scripts.
- xG or foot data scripts.

Required checks:

- Confirm generated data should be committed.
- Confirm no local credentials or database dumps are staged.
- Run the focused script validation test when available.

## C1 Production Switch Checklist

Do not switch to `c1_primary` unless every item below is satisfied:

1. Canonical C1 tests pass.
2. A fresh 1000-match shadow run has been completed.
3. `accuracy_c1 >= accuracy_v24`.
4. `governance_separation >= 0.05`.
5. Runtime mode guard tests pass.
6. `runtime_mode.yaml` includes the validation record.
7. Rollback path is documented.

Recommended command:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_*.py
```

## Rollback Policy

If C1.0 production behavior regresses:

1. Change runtime mode from `c1_primary` to `formal_list_default`.
2. If formal release behavior is unsafe, downgrade to `shadow`.
3. Record the rollback reason in `runtime_mode.yaml`.
4. Commit the rollback config change.
5. Open or update the relevant issue with:
   - observed failure
   - impacted subsystem
   - test evidence
   - planned fix

## Commit And Push Procedure

1. Inspect working tree:

   ```powershell
   git status --short
   git diff --stat
   ```

2. Stage intentionally:

   ```powershell
   git add <approved-files>
   ```

3. Review staged set:

   ```powershell
   git diff --cached --name-status
   git diff --cached --stat
   ```

4. Run tests.

5. Commit:

   ```powershell
   git commit -m "docs: add release workflow"
   ```

6. Push:

   ```powershell
   git push
   ```

## Release Notes Template

```text
Release:
Date:
Scope:

Changes:
- 

Validation:
- Tests:
- Shadow metrics:
- Runtime mode:

Rollback:
- 
```

