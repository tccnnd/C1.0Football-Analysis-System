# Contributing

This repository is maintained with a scoped-change workflow. The main goal is
to keep C1.0 migration work, V24 integration work, model/data scripts, and
documentation changes reviewable as separate units.

## Branch And Commit Policy

- `main` is the stable branch.
- Use short-lived branches for new work when possible:
  - `feature/c1-runtime-*`
  - `feature/v24-ui-*`
  - `feature/modeling-*`
  - `fix/*`
  - `docs/*`
- Keep commits scoped to one logical area.
- Do not mix C1 runtime changes, V24 UI changes, process docs, and scratch
  scripts in one commit unless the explicit goal is a full workspace snapshot.

Recommended commit prefixes:

```text
feat: add a new capability
fix: correct a bug or regression
test: add or update tests
docs: update documentation
chore: repository maintenance
```

## Review Checklist

Before committing:

1. Inspect the working tree:

   ```powershell
   git status --short
   git diff --stat
   ```

2. Confirm the staged set:

   ```powershell
   git diff --cached --name-status
   git diff --cached --stat
   ```

3. Run the relevant tests.

4. Confirm no ignored or generated artifacts were staged accidentally.

## Testing

Canonical C1 validation:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_*.py
```

Use focused tests for narrower changes. Examples:

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_mode_guard.py
.\venv\Scripts\python.exe -m pytest -q tests/test_c1_xgboost_equivalence.py
.\venv\Scripts\python.exe -m pytest -q tests/test_ui_user_center_modules.py
```

## C1 Production Safety

C1.0 must not be switched to `c1_primary` unless acceptance metrics pass:

- `accuracy_c1 >= accuracy_v24`
- `governance_separation >= 0.05`

The runtime guard in `c1/runtime/mode.py` enforces this rule. If validation is
missing or fails, `c1_primary` is downgraded to `formal_list_default`.

## Tooling Expectations

The project may use Codex, Kiro, and Cursor together:

- Kiro owns specs, acceptance criteria, and task breakdowns.
- Cursor owns small local implementation tasks.
- Codex owns code review, test verification, Git staging, commits, and release
  hygiene.

See `docs/TOOL_WORKFLOW.md` for the detailed collaboration model.

## Do Not Commit By Default

Avoid committing these without explicit review:

- Root-level scratch scripts and ad hoc `test_*.py` files.
- Local database dumps.
- Temporary reports.
- IDE files.
- Large generated data files.
- Runtime caches and `__pycache__` directories.

