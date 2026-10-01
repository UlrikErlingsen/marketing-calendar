@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo SeasonSignal needs Python 3.10 or newer.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating SeasonSignal's private Python environment...
  py -m venv .venv
)
".venv\Scripts\python.exe" -c "import streamlit, icalendar, yaml, plotly" >nul 2>&1
if errorlevel 1 (
  echo Installing SeasonSignal's open-source packages...
  ".venv\Scripts\python.exe" -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
if "%SEASONSIGNAL_PORT%"=="" set SEASONSIGNAL_PORT=8587
echo Starting SeasonSignal at http://127.0.0.1:%SEASONSIGNAL_PORT% ...
start "" "http://127.0.0.1:%SEASONSIGNAL_PORT%"
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=%SEASONSIGNAL_PORT% --server.fileWatcherType=none --browser.gatherUsageStats=false
if errorlevel 1 pause
