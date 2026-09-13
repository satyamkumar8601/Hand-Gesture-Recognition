@echo off
title OmniGesture AI Studio Launcher
cd /d "%~dp0"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"

echo =====================================================================
echo           OmniGesture AI - Production Studio Launcher
echo =====================================================================
echo.
echo Select an option:
echo   [1] Launch Complete Web Application (Frontend + Backend) [RECOMMENDED]
echo   [2] Launch FastAPI Backend Server Only (Port 8000)
echo   [3] Launch Vite React Frontend Only (Port 5173)
echo   [4] Run Native OpenCV Desktop Window (main.py)
echo   [5] Run Camera & MediaPipe Diagnostic (test_camera.py)
echo   [6] Train & Benchmark ML Models (train_model.py)
echo   [7] Exit
echo.
set /p choice="Enter choice [1-7] (default is 1): "

if "%choice%"=="" set choice=1
if "%choice%"=="1" goto opt_all
if "%choice%"=="2" goto opt_backend
if "%choice%"=="3" goto opt_frontend
if "%choice%"=="4" goto opt_desktop
if "%choice%"=="5" goto opt_diag
if "%choice%"=="6" goto opt_train
if "%choice%"=="7" goto opt_exit
if /i "%choice%"=="python main.py" goto opt_desktop
if /i "%choice%"=="main.py" goto opt_desktop
if /i "%choice%"=="desktop" goto opt_desktop
if /i "%choice%"=="web" goto opt_all
if /i "%choice%"=="all" goto opt_all
echo Invalid choice "%choice%". Launching Recommended Web Studio...
goto opt_all

:opt_all
echo.
echo Launching Complete Web Application...
call run_all.bat
goto opt_exit

:opt_backend
echo.
echo Launching FastAPI Backend...
call run_backend.bat
goto opt_exit

:opt_frontend
echo.
echo Launching React Frontend...
call run_frontend.bat
goto opt_exit

:opt_desktop
echo.
echo Launching Native OpenCV Desktop Window...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python script exited with code %errorlevel%.
    pause
)
goto opt_exit

:opt_diag
echo.
echo Running Camera & Tracking Hardware Diagnostic...
python scripts/test_camera.py
echo.
pause
goto opt_exit

:opt_train
echo.
echo Training & Benchmarking Machine Learning Models...
python backend/ml/train_model.py
echo.
pause
goto opt_exit

:opt_exit
