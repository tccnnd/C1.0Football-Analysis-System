# C1.0 TODO

## P1 Pending

### API-Football availability integration

Status:
- In progress (key connected and sync validated on 2026-04-05)

Goal:
- Use `API-Football` as the primary C1 availability source.
- Keep `crawler_source` as supplement.
- Keep `stored_snapshots` as final fallback.

Current repo readiness:
- Provider chain supports `http_source -> crawler_source -> stored_snapshots`
- `api_football` normalizer is implemented
- Sync script is available:
  - `E:\APP\ELO\scripts\sync_c1_availability_sources.py`
- Config template is ready:
  - `E:\APP\ELO\c1\configs\availability_sources.yaml`

Remaining work:
1. Add cross-source match mapping (`Titan source_id / 中文队名` -> `API-Football fixture/team`) so C1 can hit live APP matches
2. Upgrade from fixture-list ingestion to lineup/injury enriched ingestion (current rows are mostly lineup_unknown)
3. Verify returned payload shape for the purchased plan
4. Keep daily sync and confirm rows are written into:
   - `E:\APP\ELO\data\c1_state\availability_snapshots.json`
5. Re-run `C1` comparison and release review on live matches after mapping is enabled

Acceptance:
- `Provider Status` shows `api_football_primary = ready`
- `Sync Availability Sources` imports usable rows
- `C1` comparison no longer depends mainly on manual availability imports for covered matches

Latest validation (2026-04-05):
- API key auth check: `200 OK`
- Sync result:
  - `api_football_primary rows=965, written_keys=2895`
- Source bridge:
  - built via `E:\APP\ELO\scripts\build_c1_source_bridge.py`
  - output `E:\APP\ELO\data\c1_state\source_id_bridge.json`
  - current coverage against APP match list: `31/31`

### C1 availability production chain hardening

Status:
- Pending (scheduled for tomorrow, 2026-04-06)

Goal:
- Promote availability sync from manual operations to stable production flow.

Remaining work:
1. Add retry/backoff and provider-level failure reason persistence for sync runs
2. Define fail-open/fail-close policy per provider in `runtime_mode` guard rails
3. Add quality gates on imported rows (coverage, freshness, key completeness)
4. Add post-sync smoke checks before running release review

Acceptance:
- Sync failures are visible in heartbeat logs and UI status
- Release review is skipped automatically when availability quality gate fails

## P1 Completed

### Step 3 - operations scheduler (settlement + daily report)

Status:
- Completed (2026-04-05)

What was added:
- Scheduler script:
  - `E:\APP\ELO\scripts\run_ops_scheduler.py`
- Scheduler core:
  - `E:\APP\ELO\src\v24_app\ops\scheduler.py`
- Start shortcut:
  - `E:\APP\ELO\start_ops_scheduler.bat`

Current behavior:
1. Auto-settle finished matches on each cycle
2. Persist heartbeat to:
   - `E:\APP\ELO\reports\ops_scheduler_heartbeat.json`
3. Emit daily handicap shadow report (14-day table) once per day after configured trigger time
4. Persist scheduler state to:
   - `E:\APP\ELO\data\state\ops_scheduler_state.json`
