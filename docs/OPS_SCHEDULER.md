# Ops Scheduler

## Purpose

This scheduler runs production operations in a loop:
1. auto-settle finished matches
2. write heartbeat status
3. generate daily handicap shadow report (14-day table)

## Entrypoints

- Script: `E:\APP\ELO\scripts\run_ops_scheduler.py`
- Batch launcher: `E:\APP\ELO\start_ops_scheduler.bat`

## Run once (manual check)

```powershell
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\run_ops_scheduler.py --run-once --force-daily-report
```

## API-Football bridge refresh (recommended before C1 release review)

```powershell
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\sync_c1_availability_sources.py
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\build_c1_source_bridge.py
```

## Run loop (15 minutes)

```powershell
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\run_ops_scheduler.py --interval-minutes 15 --lookback-days 2 --gate-window 30 --report-days 14 --report-hour 8 --report-minute 5
```

## Outputs

- Scheduler state:
  - `E:\APP\ELO\data\state\ops_scheduler_state.json`
- Heartbeat:
  - `E:\APP\ELO\reports\ops_scheduler_heartbeat.json`
- Daily report:
  - `E:\APP\ELO\reports\handicap_shadow_daily_YYYYMMDD.md`

## Recommended Task Scheduler setup

1. Trigger: At startup
2. Action:
   - Program: `E:\APP\ELO\venv\Scripts\python.exe`
   - Arguments: `E:\APP\ELO\scripts\run_ops_scheduler.py --interval-minutes 15 --lookback-days 2 --gate-window 30 --report-days 14 --report-hour 8 --report-minute 5`
   - Start in: `E:\APP\ELO`
3. Enable "Run whether user is logged on or not"
