@echo off
title OmniGesture AI - Frontend Dev Server
cd /d "%~dp0frontend"
echo ========================================================
echo       Starting OmniGesture AI React Studio (Vite)
echo       URL: http://127.0.0.1:5173
echo ========================================================
npm run dev
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Frontend failed to start. Ensure Node.js and npm dependencies are installed.
    echo Try running: cd frontend ^&^& npm install
    pause
)
