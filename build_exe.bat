@echo off
chcp 65001 >nul
echo ============================================================
echo   pyVideoTrans - Build Portable EXE
echo ============================================================
echo.

:: Check if uv is available
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 'uv' not found! Please install uv first.
    echo   pip install uv
    echo   or visit: https://github.com/astral-sh/uv
    pause
    exit /b 1
)

:: Sync dependencies (ensure pyinstaller is installed)
echo [1/3] Syncing dependencies...
uv sync
if %errorlevel% neq 0 (
    echo [ERROR] uv sync failed!
    pause
    exit /b 1
)

:: Clean previous build
echo [2/3] Cleaning previous build...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

:: Build with PyInstaller
echo [3/3] Building EXE with PyInstaller...
echo.
echo This may take 10-30 minutes depending on your machine...
echo.

uv run pyinstaller --clean --noconfirm pyvideotrans.spec

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   BUILD SUCCESSFUL!
    echo   Output: dist\pyVideoTrans\pyVideoTrans.exe
    echo ============================================================
    echo.
    echo To run on another machine, copy the ENTIRE "dist\pyVideoTrans" folder.
    echo The target machine needs:
    echo   - Windows 10/11 64-bit
    echo   - Visual C++ Redistributable (usually already installed)
    echo   - Nothing else! Python, FFmpeg, CUDA are all bundled.
    echo.
) else (
    echo.
    echo [ERROR] Build failed! Check the output above for details.
)

pause
