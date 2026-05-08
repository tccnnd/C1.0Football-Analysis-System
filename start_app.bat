@echo off
setlocal
chcp 65001 >nul
title 智能赛事分析系统

cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" launcher.py
) else (
    python launcher.py
)

if errorlevel 1 (
    echo.
    echo Launcher exited with an error.
)

pause
