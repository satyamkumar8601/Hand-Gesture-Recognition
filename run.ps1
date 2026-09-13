# OmniGesture AI - PowerShell Launcher
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "          OmniGesture AI - Production Studio Launcher" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/3] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/k cd /d `"$ScriptDir`" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload" -WindowStyle Normal

Write-Host "[2/3] Starting Vite Frontend on http://127.0.0.1:5173 ..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/k cd /d `"$ScriptDir\frontend`" && npm run dev" -WindowStyle Normal

Write-Host "[3/3] Waiting for servers to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Opening browser at http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host " System is running!" -ForegroundColor Green
Write-Host "  - Frontend: http://localhost:5173"
Write-Host "  - Backend API: http://127.0.0.1:8000"
Write-Host "  - Interactive API Docs: http://127.0.0.1:8000/docs"
Write-Host "=====================================================================" -ForegroundColor Green
