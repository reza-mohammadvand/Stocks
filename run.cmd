@echo off
setlocal

rem Always run from the project directory, even when called from elsewhere.
cd /d "%~dp0"

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [Stock] Creating the Python virtual environment...

    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        where python >nul 2>&1
        if errorlevel 1 (
            echo [Stock] Python 3 was not found. Install Python 3.10 or newer and try again.
            exit /b 1
        )
        python -m venv .venv
    )

    if errorlevel 1 (
        echo [Stock] Could not create the virtual environment.
        exit /b 1
    )
)

"%VENV_PYTHON%" -c "import flask, flask_cors, requests, jdatetime" >nul 2>&1
if errorlevel 1 (
    echo [Stock] Installing required Python packages...
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [Stock] Package installation failed.
        exit /b 1
    )
)

if not "%~1"=="" set "STOCK_DASHBOARD_PORT=%~1"
if not defined STOCK_DASHBOARD_PORT set "STOCK_DASHBOARD_PORT=5050"

echo [Stock] Starting dashboard at http://127.0.0.1:%STOCK_DASHBOARD_PORT%
echo [Stock] Press Ctrl+C to stop the server.
"%VENV_PYTHON%" app.py

set "APP_EXIT_CODE=%ERRORLEVEL%"
if not "%APP_EXIT_CODE%"=="0" echo [Stock] Server stopped with exit code %APP_EXIT_CODE%.
exit /b %APP_EXIT_CODE%
