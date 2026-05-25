@echo off
cd /d "%~dp0\.."
echo.
echo ===================================================
echo     Packaging Piper Voice Cloner GUI for v1.0
echo ===================================================
echo.
python Github\pack_project.py
echo.
pause
