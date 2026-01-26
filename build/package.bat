@echo off
REM Standalone packaging script - just creates zip from existing build
REM Run this after build.bat if you just want to re-package

echo ========================================
echo CK3 Coat of Arms Editor - Package Only
echo ========================================
echo.

python package.py

if errorlevel 1 (
    echo.
    echo ERROR: Packaging failed!
    pause
    exit /b 1
)

echo.
pause
