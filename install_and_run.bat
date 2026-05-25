@echo off
TITLE Piper Voice Cloner - Launcher
CLS

echo ========================================================
echo   Piper Voice Cloner - Setup and Run
echo   (Press Alt+F4 to close if needed)
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found! 
    echo Please install Python 3.10 or newer from python.org
    echo and make sure to check "Add Python to PATH" during installation.
    PAUSE
    EXIT /B
)

:: Create virtual environment if it doesn't exist
IF NOT EXIST "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate

:: Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

:: Install dependencies
echo [INFO] Checking dependencies...
if EXIST requirements.txt (
    pip install -r requirements.txt
)

:: CLEANUP: Remove Torch from local environment (handled by Docker)
echo [INFO] Removing any local Torch installations...
pip uninstall -y torch torchvision torchaudio >nul 2>&1

:: Run the app
echo.
echo [INFO] Starting Application...
echo.
python main.py

PAUSE
