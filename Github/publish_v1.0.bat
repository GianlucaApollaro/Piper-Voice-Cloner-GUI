@echo off
cd /d "%~dp0\.."
setlocal EnableDelayedExpansion

echo.
echo ===================================================
echo     Publishing Piper Voice Cloner GUI v1.0
echo ===================================================
echo.

echo Verifying release files for v1.0...
set "FILES_TO_UPLOAD="

if exist "Piper_Voice_Cloner_GUI_v1.0.zip" (
    set "FILES_TO_UPLOAD="Piper_Voice_Cloner_GUI_v1.0.zip""
    echo Found: Piper_Voice_Cloner_GUI_v1.0.zip
) else (
    echo ERROR: Piper_Voice_Cloner_GUI_v1.0.zip NOT FOUND!
    echo        Please run Github\pack_project.bat first.
    pause
    exit /b 1
)

if not exist "Github\release_notes_v1.0.md" (
    echo.
    echo ERROR: Github\release_notes_v1.0.md NOT FOUND!
    pause
    exit /b 1
)

echo.
echo Creating release using GitHub CLI...
gh release create v1.0 %FILES_TO_UPLOAD% --title "Piper Voice Cloner GUI v1.0" --notes-file "Github\release_notes_v1.0.md"

if errorlevel 1 (
    echo.
    echo ERROR: GitHub release creation failed.
    echo        Make sure you have created the remote repository, push your commit,
    echo        and are logged in via: gh auth login
    pause
    exit /b 1
)

echo.
echo ===================================================
echo     Publishing Complete!
echo ===================================================
pause
endlocal
