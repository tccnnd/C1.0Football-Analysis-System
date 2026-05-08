@echo off
setlocal
chcp 65001 >nul
title V24 Ops Scheduler

cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" scripts\run_ops_scheduler.py --interval-minutes 15 --lookback-days 2 --gate-window 30 --report-days 14 --report-hour 8 --report-minute 5
) else (
    python scripts\run_ops_scheduler.py --interval-minutes 15 --lookback-days 2 --gate-window 30 --report-days 14 --report-hour 8 --report-minute 5
)

if errorlevel 1 (
    echo.
    echo Ops scheduler exited with an error.
)

pause
