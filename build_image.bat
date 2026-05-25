TITLE Build Piper Docker Image (Universal / CUDA 12.8)


echo ========================================================
echo   Docker Image Build (Piper Universal)
echo ========================================================
echo.
echo This script will build the image "piper-cuda12.8:latest"
echo compatible with RTX 30xx/40xx and 50xx (PyTorch Nightly).
echo.
echo Ensure Docker Desktop is open and running!
echo.
echo Press any key to start...
PAUSE >nul

echo.
echo [INFO] Building in progress... (this may take a few minutes)
docker build -t piper-cuda12.8:latest .

echo.
if %ERRORLEVEL% EQU 0 (
    echo [OK] Image built successfully!
    echo You can now run "install_and_run.bat".
) else (
    echo [ERROR] Something went wrong. Ensure Docker is active.
)
echo.
echo Press any key to exit.
PAUSE >nul
