# Codex, Kiro, And Cursor Workflow

This project may use Codex, Kiro, and Cursor together. The workflow below keeps
responsibilities separate so that multiple AI coding tools do not overwrite or
duplicate each other's work.

## Tool Roles

## Kiro

Kiro owns planning and specification.

Use Kiro for:

- Feature specs.
- Acceptance criteria.
- Task breakdown.
- Milestone planning.
- Risk and dependency mapping.

Expected output:

- What should be built.
- Why it matters.
- What counts as complete.
- Which files or subsystems are expected to change.

## Cursor

Cursor owns small implementation slices.

Use Cursor for:

- Single-module edits.
- UI layout adjustments.
- Local bug fixes.
- Small refactors.
- Fast exploratory coding.

Constraints:

- Avoid broad cross-repository edits.
- Do not own final staging or commit for large changes.
- Hand off to Codex for review before commit.

## Codex

Codex owns review, verification, Git hygiene, and release control.

Use Codex for:

- Reading the existing codebase before editing.
- Code review and risk assessment.
- Test execution.
- Staging scope review.
- Commits and pushes.
- Release process checks.
- Documentation consistency.

Expected behavior:

- Preserve user changes.
- Avoid broad `git add .` unless explicitly requested and risk-accepted.
- Keep C1, V24, scripts, and docs commits separate when possible.

## Recommended Workflow

1. Kiro writes the spec and acceptance criteria.
2. Cursor implements a small scoped change.
3. Codex reviews the diff and runs focused tests.
4. Codex stages only the approved files.
5. Codex commits and pushes.
6. Kiro updates the roadmap or next spec if needed.

## File Ownership Guidance

```text
c1/runtime/       Codex-reviewed runtime and release safety changes
c1/inference/     Codex-reviewed model runtime changes
c1/modules/       Codex-reviewed governance changes
c1/translation/   Codex-reviewed translation changes
src/v24_app/      Cursor or Codex can edit, but Codex should review final diff
scripts/          Cursor can draft; Codex should classify and review
docs/             Kiro can draft; Codex should align with repository state
tests/            Codex should verify and keep tests close to changed behavior
```

## Handoff Template

Use this when handing work between tools:

```text
Goal:
Scope:
Files changed:
Tests run:
Known risks:
Do not touch:
Next decision needed:
```

## Rules For Mixed Tool Sessions

- Do not let two tools edit the same file at the same time.
- Commit or discard a scoped change before starting a different broad scope.
- Keep generated artifacts separate from source code commits.
- Never remove launchers, config, data files, or model artifacts without an
  explicit decision.
- Treat `runtime_mode.yaml` changes as release-affecting.

## Current Priority Order

1. v0.2 repository governance baseline.
2. v0.3 C1.0 production readiness.
3. v0.4 V24 UI and C1 management center.
4. v0.5 data/model pipeline stabilization.
5. v0.6 release and monitoring loop.

