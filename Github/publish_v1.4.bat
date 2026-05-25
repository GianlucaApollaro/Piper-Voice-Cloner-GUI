@echo off
setlocal EnableDelayedExpansion

echo Verifying release files for v1.4...
set "FILES_TO_UPLOAD="

if exist "Music_Separator_GUI_v1.4_Mac.zip" (
    set "FILES_TO_UPLOAD=!FILES_TO_UPLOAD! "Music_Separator_GUI_v1.4_Mac.zip""
    echo Found: Music_Separator_GUI_v1.4_Mac.zip
) else (
    echo WARNING: Music_Separator_GUI_v1.4_Mac.zip NOT FOUND!
)

if exist "Music_Separator_GUI_v1.4_Windows_GPU.7z" (
    set "FILES_TO_UPLOAD=!FILES_TO_UPLOAD! "Music_Separator_GUI_v1.4_Windows_GPU.7z""
    echo Found: Music_Separator_GUI_v1.4_Windows_GPU.7z
) else (
    echo WARNING: Music_Separator_GUI_v1.4_Windows_GPU.7z NOT FOUND!
)

if exist "Music_Separator_GUI_v1.4_Windows_CPU.7z" (
    set "FILES_TO_UPLOAD=!FILES_TO_UPLOAD! "Music_Separator_GUI_v1.4_Windows_CPU.7z""
    echo Found: Music_Separator_GUI_v1.4_Windows_CPU.7z
) else (
    echo WARNING: Music_Separator_GUI_v1.4_Windows_CPU.7z NOT FOUND!
)

if "%FILES_TO_UPLOAD%"=="" (
    echo.
    echo ERROR: No files found to upload.
    pause
    exit /b 1
)

if not exist "release_notes_v1.4.md" (
    echo.
    echo ERROR: release_notes_v1.4.md NOT FOUND!
    pause
    exit /b 1
)

echo.
echo Creating release using GitHub CLI...
gh release create v1.4 %FILES_TO_UPLOAD% --title "Music Separator v1.4 - The Workflow Update!" --notes-file "release_notes_v1.4.md"

if errorlevel 1 (
    echo.
    echo ERROR: GitHub release creation failed.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo     Publishing Complete!
echo ===================================================
pause
endlocal
