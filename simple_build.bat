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

echo Creating a simplified build with compatible pefile version...
pyinstaller --noconfirm --clean ^
    --name="AutoClipSender" ^
    --windowed ^
    --icon=icons\64x64.ico ^
    --add-data "icons;icons" ^
    --add-data="clip_processor.py;." ^
    --add-data="defaults.json;." ^
    --add-data="config.json;." ^
    app.py

if %errorlevel% equ 0 (
    echo ==========================================
    echo Build completed successfully!
    
    rem Add the ffmpeg folder to the distribution
    if exist "ffmpeg" (
        echo Copying ffmpeg folder to distribution...
        xcopy /E /I /Y "ffmpeg" "dist\AutoClipSender\ffmpeg" > nul
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