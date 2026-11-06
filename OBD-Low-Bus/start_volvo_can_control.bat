@echo off
setlocal
title Volvo CAN Control - OBD-Low-Bus
cd /d "%~dp0"

echo.
echo Volvo CAN Control - lokaler Diagnoseserver
echo Dieses Fenster offen lassen, solange die Weboberflaeche genutzt wird.
echo Minimieren ist ok. Beenden mit Strg+C oder Fenster schliessen.
echo.

set "VENV=%~dp0.venv"
set "PY=%VENV%\Scripts\python.exe"

if not exist "%PY%" (
  echo Erstelle lokale Python-Umgebung...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv "%VENV%"
  ) else (
    python -m venv "%VENV%"
  )
  if errorlevel 1 goto :error
)

"%PY%" -c "import serial" >nul 2>nul
if errorlevel 1 (
  echo Installiere benoetigte Python-Pakete...
  "%PY%" -m pip install -r "%~dp0tools\requirements.txt"
  if errorlevel 1 goto :error
)

"%PY%" "%~dp0tools\volvo_can_control.py" --profile "OBD-Low-Bus" %*
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Volvo CAN Control konnte nicht gestartet werden.
echo Bitte Python 3 installieren und dieses Fenster erneut oeffnen.
pause
exit /b 1
