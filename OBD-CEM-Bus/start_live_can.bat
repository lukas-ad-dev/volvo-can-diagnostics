@echo off
setlocal
title Volvo CAN Live
cd /d "%~dp0"

echo.
echo Volvo CAN Live - fester 500-kbit/s-Empfang, LISTEN_ONLY
echo Kein Senden. Bei Auffaelligkeiten: CAN STOP im Browser oder USB trennen.
echo.

start "Volvo CAN Server" "%ComSpec%" /c ""%~dp0start_volvo_can_control.bat" --no-browser"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_live.ps1"
if errorlevel 1 pause
endlocal
