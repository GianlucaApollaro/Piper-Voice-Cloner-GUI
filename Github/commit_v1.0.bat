@echo off
cd /d "%~dp0\.."
echo.
echo ===================================================
echo     Preparing Git Commit for v1.0
echo ===================================================
echo.

echo Staging all changes...
git add .

echo.
echo Changes to be committed:
git status -s

echo Checking for changes...
git diff --cached --quiet
if errorlevel 1 (
    echo Committing changes...
    git commit -m "Piper Voice Cloner GUI v1.0 - Initial Release: Complete VITS-based voice cloner GUI optimized for RTX 5070 / CUDA 12.8, local Whisper model cache, zero-shot audio translation, Correction Studio, and Piper-TTS iOS ONNX compatibility."
    if errorlevel 1 (
        echo.
        echo ERROR: Commit failed.
        pause
        exit /b 1
    )
) else (
    echo Nothing to commit, proceeding to push...
)

echo.
echo Pushing changes to remote...
git push origin main

if errorlevel 1 (
    echo.
    echo ERROR: Push failed. Make sure you set your origin remote first:
    echo        git remote add origin https://github.com/GianlucaApollaro/piper-voice-cloner-gui.git
    echo.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo     Commit and Push Complete!
echo ===================================================
pause
