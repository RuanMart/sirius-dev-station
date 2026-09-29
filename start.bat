@echo off
echo ==============================================
echo    Sirius Dev Station -- Local Control Plane
echo ==============================================

set PYTHON=.venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo Creating virtual environment with uv...
    uv venv
    uv pip install -r requirements.txt python-dotenv
)

set PORT=8080
if not "%~1"=="" set PORT=%~1

echo Server starting on http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop.
echo.

"%PYTHON%" server.py --host 127.0.0.1 --port %PORT%
