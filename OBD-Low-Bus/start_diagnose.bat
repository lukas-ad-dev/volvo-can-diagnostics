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

start "" cmd /c "timeout /t 2 >nul & start http://127.0.0.1:8765"
"%PY%" tools\local_can_diagnostics.py --profile "OBD-Low-Bus" %*
echo.
pause
exit /b 0

:error
echo Einrichtung fehlgeschlagen. Bitte Python 3 installieren und erneut starten.
pause
exit /b 1
