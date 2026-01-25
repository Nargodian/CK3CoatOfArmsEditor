@echo off
REM Build script for CK3 Coat of Arms Editor
REM Creates both executables with shared _internal folder

echo ========================================
echo CK3 Coat of Arms Editor - Build Script
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller not found. Install with:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

REM Build CoatOfArmsEditor
echo Building CoatOfArmsEditor.exe...
pyinstaller ..\editor\editor.spec
if errorlevel 1 (
    echo ERROR: Failed to build CoatOfArmsEditor
    pause
    exit /b 1
)
echo.

REM Build AssetConverter
echo Building AssetConverter.exe...
pyinstaller ..\asset_converter\asset_converter.spec
if errorlevel 1 (
    echo ERROR: Failed to build AssetConverter
    pause
    exit /b 1
)
echo.

REM Create merged distribution folder
echo Merging distributions...
if exist dist\merged rmdir /s /q dist\merged
mkdir dist\merged

REM Copy CoatOfArmsEditor executable
copy dist\CoatOfArmsEditor\CoatOfArmsEditor.exe dist\merged\
if errorlevel 1 (
    echo ERROR: Failed to copy CoatOfArmsEditor.exe
    pause
    exit /b 1
)

REM Copy AssetConverter executable
copy dist\AssetConverter\AssetConverter.exe dist\merged\
if errorlevel 1 (
    echo ERROR: Failed to copy AssetConverter.exe
    pause
    exit /b 1
)

REM Copy _internal folder (shared libraries)
xcopy /E /I /Y dist\CoatOfArmsEditor\_internal dist\merged\_internal
if errorlevel 1 (
    echo ERROR: Failed to copy _internal folder
    pause
    exit /b 1
)

REM Copy any additional DLLs from AssetConverter if needed
REM (imageio-dds dependencies, etc.)
xcopy /E /I /Y dist\AssetConverter\_internal\* dist\merged\_internal\
if errorlevel 1 (
    echo Warning: Could not merge AssetConverter dependencies
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Executables are in: dist\merged\
echo   - CoatOfArmsEditor.exe (main editor)
echo   - AssetConverter.exe (asset extraction tool)
echo   - _internal\ (shared libraries)
echo.
echo Next steps:
echo 1. Test both executables in dist\merged\
echo 2. Run AssetConverter.exe to extract CK3 assets
echo 3. Run CoatOfArmsEditor.exe to create coat of arms
echo.
echo To create a distribution zip:
echo   - Copy dist\merged\ to desired location
echo   - Create README.txt with usage instructions
echo   - Zip the folder for distribution
echo.

REM Exit cleanly
exit /b 0
