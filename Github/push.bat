@echo off
cd /d "%~dp0\.."
echo.
echo ===================================================
echo     Pushing changes to origin/main
echo ===================================================
echo.
git push origin main
if errorlevel 1 (
    echo.
    echo ERROR: Push failed.
    pause
    exit /b 1
)
echo.
echo Push Complete!
pause
