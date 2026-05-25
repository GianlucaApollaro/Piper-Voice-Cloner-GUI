@echo off
TITLE Docker Desktop Installation
CLS

echo ========================================================
echo   Automatic Docker Desktop Installation
echo ========================================================
echo.
echo This script will attempt to download and install Docker for you.
echo A permission request window (UAC) may appear.
echo If you hear a system sound, press Alt+S (or click Yes).
echo.
echo Press any key to start...
PAUSE >nul

echo.
echo [INFO] Starting installation via Winget...
winget install -e --id Docker.DockerDesktop

echo.
echo ========================================================
echo   Installation Completed (or finished).
echo   IMPORTANT: YOU MUST RESTART YOUR COMPUTER NOW.
echo ========================================================
echo.
echo Press any key to close this window.
PAUSE >nul
