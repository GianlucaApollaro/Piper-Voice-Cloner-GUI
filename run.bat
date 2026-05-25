@echo off
TITLE Piper Voice Cloner
CLS

echo ========================================================
echo   Piper Voice Cloner
echo ========================================================
echo.

:: Check if venv exists
IF NOT EXIST "venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run 'install.bat' first to set up the environment.
    PAUSE
    EXIT /B
)

:: Activate venv
call venv\Scripts\activate

:: Run the app
echo [INFO] Starting Application...
echo.
python main.py

PAUSE
