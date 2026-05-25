@echo off
echo.
echo ===================================================
echo     Preparing Git Commit for v1.4
echo ===================================================
echo.

echo Staging all changes...
git add .

echo.
echo Changes to be committed:
git status -s

echo.
echo Committing changes...
git commit -m "Music Separator v1.4 - The Workflow Update: Peak Normalization, Stereo Downmix, Only Drums Preset, Subfolder Toggle with smart naming, Silent Stem Deletion, Instant Playback, UI Polish + Add 5 new anvuew BS-Roformer models (karaoke, standard, ft1, magnitude, dereverb) and fix duplicate model entries"

if errorlevel 1 (
    echo.
    echo ERROR: Commit failed or nothing to commit.
    pause
    exit /b 1
)

echo.
echo Pushing changes to remote...
git push

if errorlevel 1 (
    echo.
    echo ERROR: Push failed. Please check your connection or remote repository.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo     Commit and Push Complete!
echo ===================================================
pause
