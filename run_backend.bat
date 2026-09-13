@echo off
title OmniGesture AI - Backend Server
cd /d "%~dp0"
echo ========================================================
echo       Starting OmniGesture AI FastAPI Backend
echo       URL: http://127.0.0.1:8000
echo ========================================================
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Backend failed to start. Ensure Python and dependencies are installed.
    echo Try running: pip install -r backend/requirements.txt
    pause
)
