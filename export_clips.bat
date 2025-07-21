@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    Steam Clip Export Tool
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    echo.
    pause
    exit /b 1
)

:: Check if required files exist
if not exist "export.py" (
    echo [ERROR] export.py not found in current directory.
    echo Please run this batch file from the SteamClipExport folder.
    echo.
    pause
    exit /b 1
)

if not exist "appid_map.json" (
    echo [ERROR] appid_map.json not found in current directory.
    echo Please ensure all required files are present.
    echo.
    pause
    exit /b 1
)

:: Check if ffmpeg is available (required for video processing)
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] ffmpeg not found in PATH.
    echo Video processing may fail. Please install ffmpeg from https://ffmpeg.org
    echo.
    set /p "continue=Continue anyway? (y/N): "
    if /i not "!continue!"=="y" (
        echo Aborted.
        pause
        exit /b 1
    )
)

echo [INFO] Starting Steam clip export...
echo [INFO] This may take a while depending on the number of clips...
echo.

:: Run the Python script
python export.py

:: Check if the script ran successfully
if errorlevel 1 (
    echo.
    echo [ERROR] Script execution failed with error code %errorlevel%
    echo Please check the error messages above.
) else (
    echo.
    echo [SUCCESS] Script completed successfully!
)

echo.
echo Press any key to exit...
pause >nul 