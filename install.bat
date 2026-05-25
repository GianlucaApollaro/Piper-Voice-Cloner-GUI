@echo off
TITLE Piper Voice Cloner - Installer
CLS

echo ========================================================
echo   Piper Voice Cloner - Installation
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
python -m pip install --upgrade pip

:: Install dependencies (Lightweight UI only)
echo [INFO] Installing dependencies...
if EXIST requirements.txt (
    pip install -r requirements.txt
) else (
    echo [WARNING] requirements.txt not found!
)

:: CLEANUP: Remove Torch from local environment (handled by Docker)
echo [INFO] Removing any local Torch installations to prevent duplicates...
pip uninstall -y torch torchvision torchaudio >nul 2>&1
echo [INFO] Torch cleanup complete. Machine Learning tasks run inside Docker.

echo.
echo [INFO] Installation Complete.
echo You can now run 'run.bat' to start the application.
echo.
PAUSE
