@echo off
echo ==========================================
echo Building Auto Clip Sender Application 
echo ==========================================

rem Set working directory to the script location
cd /d "%~dp0"

echo Installing compatible versions of PyInstaller and pefile...
pip uninstall -y pefile pyinstaller
pip install "pefile==2023.2.7" "pyinstaller==6.1.0"

echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo Checking for icon file in root directory...
if not exist "128x128.ico" (
    if exist "icons\128x128.ico" (
        echo Copying icon from icons folder to root directory for build...
        copy "icons\128x128.ico" "128x128.ico" > nul
        echo Icon copied to root directory.
    ) else (
        echo ERROR: Icon file not found in icons folder or root directory!
        echo The build may fail or have no icon.
    )
) else (
    echo Found icon file in root directory.
)

echo Creating a simplified build with compatible pefile version...
pyinstaller --noconfirm --clean ^
    --name="AutoClipSender" ^
    --windowed ^
    --icon=128x128.ico ^
    --add-data="128x128.ico;_internal" ^
    --add-data="clip_processor.py;." ^
    app.py

if %errorlevel% equ 0 (
    echo ==========================================
    echo Build completed successfully!
    
    rem Add the ffmpeg folder to the distribution
    if exist "ffmpeg" (
        echo Copying ffmpeg folder to distribution...
        xcopy /E /I /Y "ffmpeg" "dist\AutoClipSender\ffmpeg" > nul
    )
    
    rem Verify icon is in the _internal directory
    if exist "dist\AutoClipSender\_internal\128x128.ico" (
        echo Icon verified in _internal directory.
    ) else (
        echo WARNING: Icon was not found in _internal directory.
        echo Creating _internal directory and copying icon...
        if not exist "dist\AutoClipSender\_internal" mkdir "dist\AutoClipSender\_internal"
        copy "128x128.ico" "dist\AutoClipSender\_internal\128x128.ico" /Y > nul
    )
    
    rem Copy config files to root directory only
    echo Copying configuration files to root directory...
    if exist "defaults.json" (
        echo Copying defaults.json to root directory...
        copy "defaults.json" "dist\AutoClipSender\defaults.json" /Y > nul
    )
    
    if exist "config.json" (
        echo Copying config.json to root directory...
        copy "config.json" "dist\AutoClipSender\config.json" /Y > nul
    ) else (
        echo Creating new config.json in root directory...
        copy "defaults.json" "dist\AutoClipSender\config.json" /Y > nul
    )
    
    rem Copy README to distribution folder
    if exist "dist_readme.txt" (
        echo Copying README file to distribution folder...
        copy "dist_readme.txt" "dist\AutoClipSender\README.txt" > nul
    )
    
    echo ==========================================
    echo Application is ready!
    echo Location: %cd%\dist\AutoClipSender
    echo ==========================================
    echo Users can run AutoClipSender.exe directly
    echo ==========================================
) else (
    echo ==========================================
    echo Build failed with error %errorlevel%
    echo ==========================================
)

pause 