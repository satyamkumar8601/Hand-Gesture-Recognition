@echo off
cd /d "%~dp0"
echo ====================================================
echo    Starting OmniGesture AI Web Studio Dashboard
echo ====================================================
echo Opening browser at: http://127.0.0.1:8000
start http://127.0.0.1:8000
python web_app.py
pause
