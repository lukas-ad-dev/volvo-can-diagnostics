@echo off
setlocal
cd /d "%~dp0"

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
  echo Installiere pyserial in die lokale Umgebung...
  "%PY%" -m pip install -r "%~dp0tools\requirements.txt"
  if errorlevel 1 goto :error
)

"%PY%" tools\usb_can_logger.py %*
echo.
pause
exit /b 0

:error
echo Einrichtung fehlgeschlagen. Bitte Python 3 installieren und erneut starten.
pause
exit /b 1
