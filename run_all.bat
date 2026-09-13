@echo off
title OmniGesture AI - Launcher
cd /d "%~dp0"
echo =====================================================================
echo           OmniGesture AI - Production Studio Launcher
echo =====================================================================
echo.
echo [1/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "OmniGesture Backend" "%~dp0run_backend.bat"

echo [2/3] Starting Vite Frontend on http://127.0.0.1:5173 ...
start "OmniGesture Frontend" "%~dp0run_frontend.bat"

echo [3/3] Waiting for servers to initialize...
ping -n 4 127.0.0.1 >nul

echo Opening browser at http://localhost:5173 ...
start http://localhost:5173

echo.
echo =====================================================================
echo  System is running!
echo   - Frontend: http://localhost:5173
echo   - Backend API: http://127.0.0.1:8000
echo   - Interactive API Docs: http://127.0.0.1:8000/docs
echo.
echo  Privacy Note: Camera hardware is OFF by default. It activates ONLY
echo  when you view the Live Recognition feed, and releases immediately
echo  when you leave or close the page.
echo =====================================================================
