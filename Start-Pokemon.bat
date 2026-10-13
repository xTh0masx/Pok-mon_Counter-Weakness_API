@echo off
setlocal
cd /d "%~dp0"
title Pokemon Counter Lab

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version >nul 2>&1
    if not errorlevel 1 (
        ".venv\Scripts\python.exe" scripts\start_local.py %*
        goto finished
    )
)
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    py -3.12 scripts\start_local.py %*
    goto finished
)
python --version >nul 2>&1
if not errorlevel 1 (
    python scripts\start_local.py %*
    goto finished
)
echo Python was not found. Install Python 3.12 from https://www.python.org/downloads/
echo Enable the Python launcher or Add Python to PATH, then try again.

:finished
echo.
pause
