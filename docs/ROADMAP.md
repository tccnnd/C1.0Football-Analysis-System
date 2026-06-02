# Roadmap

This roadmap defines the next engineering milestones for C1.0 Football
Analysis System. It is intentionally scoped around maintainability, release
readiness, and safe C1.0 production migration.

## v0.2 Repository Governance And Collaboration Baseline

Goal: make Codex + Kiro + Cursor collaboration safe and repeatable.

Deliverables:

- `CONTRIBUTING.md`
- `docs/ROADMAP.md`
- `docs/RELEASE_PROCESS.md`
- `docs/TOOL_WORKFLOW.md`
- Clear commit and staging policy.
- GitHub issue label and milestone guidance.
- README links to review and maintenance docs.

Acceptance:

- The repository has documented branch, commit, test, and release processes.
- Future tool-driven work has a single collaboration workflow.
- No code behavior changes are required for this milestone.

## v0.3 C1.0 Production Readiness

Goal: determine whether C1.0 can safely become the primary production path.

Deliverables:

- Fresh 1000-match shadow run.
- Production readiness report under `reports/`.
- LightGBM dependency and model availability status.
- Updated validation metrics in `c1/configs/runtime_mode.yaml`.
- Runtime guard verification.

Acceptance:

- `accuracy_c1 >= accuracy_v24`
- `governance_separation >= 0.05`
- `tests/test_c1_*.py` pass.
- No direct V24 dependency exists in the production C1 inference path.
- Any switch to `c1_primary` is backed by recorded validation.

## v0.4 V24 UI And C1 Management Center

Goal: make C1 state visible and operable from the V24 application shell without
turning V24 into an unreviewable dependency sink.

Deliverables:

- Review modified `src/v24_app/*` files.
- Review new V24 support modules such as C1 center, model center, and model
  monitoring.
- UI status cards for runtime mode, guard state, shadow metrics, and release
  readiness.
- Focused UI tests for changed modules.

Acceptance:

- C1 management views show current runtime mode and guard status.
- V24 remains a fallback and comparison surface, not an uncontrolled owner of
  C1 production decisions.
- UI module tests pass for changed surfaces.

## v0.5 Data And Model Pipeline Stabilization

Goal: make import, training, calibration, xG, ELO, and foot data flows
repeatable.

Deliverables:

- Categorized `scripts/` layout.
- Script README for import, training, calibration, backtest, and validation.
- Data commit policy for `data/`.
- Model artifact health checks.
- xG and foot bridge diagnostics.

Acceptance:

- New scripts have a documented purpose and command example.
- Generated data and large dumps are not committed accidentally.
- Model training and inference artifacts have reproducible status checks.

## v0.6 Release And Monitoring

Goal: establish a release loop that can be audited and rolled back.

Deliverables:

- `docs/RELEASE_NOTES.md`
- Release checklist.
- Production monitoring report.
- Model drift and runtime health summaries.
- Rollback paths:
  - `c1_primary -> formal_list_default`
  - `formal_list_default -> shadow`

Acceptance:

- Each release has a test summary, metric summary, and rollback note.
- Production mode changes are traceable through Git and runtime config.
- Monitoring documents are kept separate from one-off debug output.

## Suggested GitHub Labels

```text
c1-runtime
v24-ui
modeling
data-bridge
testing
docs
release
bug
enhancement
blocked
needs-review
```

## Suggested Milestones

- `v0.2 Governance Baseline`
- `v0.3 C1 Production Readiness`
- `v0.4 V24 UI Integration`
- `v0.5 Data And Model Pipeline`
- `v0.6 Release And Monitoring`

