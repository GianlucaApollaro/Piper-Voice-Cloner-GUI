@echo off
cd /d "%~dp0\.."
echo.
echo ===================================================
echo     Packaging Piper Voice Cloner GUI for v1.1
echo ===================================================
echo.
python Github\pack_project.py v1.1
echo.
pause
