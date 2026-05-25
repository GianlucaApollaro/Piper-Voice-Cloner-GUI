@echo off
TITLE Piper Docker Cleanup Tool
CLS

echo ========================================================
echo   Piper Voice Cloner - Deep Cleaner
echo ========================================================
echo.
echo WARNING: This will remove:
echo  1. All STOPPED containers.
echo  2. All DANGLING images (updates that left old versions behind).
echo  3. All BUILD CACHE (This is usually where the GBs are hiding).
echo.
echo IT WILL NOT REMOVE:
echo  - The active "piper-cuda12.8:latest" image (if it is tagged correctly).
echo  - Your dataset or models (they are on your disk, not in Docker).
echo.
echo Press Ctrl+C to cancel, or any key to START CLEANING.
PAUSE >nul

echo.
echo [1/3] Pruning Containers...
docker container prune -f

echo.
echo [2/3] Pruning Dangling Images...
docker image prune -f

echo.
echo [3/3] Pruning Build Cache (The Big One)...
docker builder prune --all -f

echo.
echo ========================================================
echo   Cleanup Complete!
echo ========================================================
echo.
echo NOTE: Windows might not claim the free space immediately.
echo To reclaim disk space on the Host (C: drive), you must
echo manually shrink the WSL2 VHDX file.
echo See DOCKER_CLEANUP_GUIDE.txt for instructions.
echo.
PAUSE
