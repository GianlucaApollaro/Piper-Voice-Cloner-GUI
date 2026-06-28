@echo off
cd /d "%~dp0\.."
setlocal EnableDelayedExpansion

echo.
echo ===================================================
echo     Publishing Piper Voice Cloner GUI v1.1
echo ===================================================
echo.

echo Verifying release files for v1.1...
set "FILES_TO_UPLOAD="

if exist "Piper_Voice_Cloner_GUI_v1.1.zip" (
    set "FILES_TO_UPLOAD="Piper_Voice_Cloner_GUI_v1.1.zip""
    echo Found: Piper_Voice_Cloner_GUI_v1.1.zip
) else (
    echo ERROR: Piper_Voice_Cloner_GUI_v1.1.zip NOT FOUND!
    echo        Please run Github\pack_project_v1.1.bat first.
    pause
    exit /b 1
)

if not exist "Github\release_notes_v1.1.md" (
    echo.
    echo ERROR: Github\release_notes_v1.1.md NOT FOUND!
    pause
    exit /b 1
)

echo.
echo Creating release using GitHub CLI...
gh release create v1.1 %FILES_TO_UPLOAD% --title "Piper Voice Cloner GUI v1.1" --notes-file "Github\release_notes_v1.1.md"

if errorlevel 1 (
    echo.
    echo ERROR: GitHub release creation failed.
    echo        Make sure you push your commit first, and are logged in via: gh auth login
    pause
    exit /b 1
)

echo.
echo ===================================================
echo     Publishing Complete!
echo ===================================================
pause
endlocal
