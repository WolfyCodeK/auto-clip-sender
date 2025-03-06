"""
Simple build script for Auto-Clip-Sender
This script directly calls PyInstaller without capturing output
"""

import os
import sys
import shutil
import time

print("Starting build process for Auto-Clip-Sender...")

# Check for FFmpeg executables
ffmpeg_dir = os.path.join(os.getcwd(), "ffmpeg")
if not os.path.exists(ffmpeg_dir):
    print("ERROR: FFmpeg directory not found")
    sys.exit(1)

ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")

if not os.path.exists(ffmpeg_exe) or not os.path.exists(ffprobe_exe):
    print("ERROR: FFmpeg executables missing")
    sys.exit(1)

print(f"Found FFmpeg executables in '{ffmpeg_dir}'")

# Clean up previous build if exists
if os.path.exists("build"):
    print("Removing previous build directory...")
    try:
        shutil.rmtree("build")
        time.sleep(1)
    except Exception as e:
        print(f"Warning: {e}")

if os.path.exists("dist"):
    print("Removing previous dist directory...")
    try:
        shutil.rmtree("dist")
        time.sleep(1)
    except Exception as e:
        print(f"Warning: {e}")

print("Starting PyInstaller build process...")
print("="*50)

# Import and directly use PyInstaller's main function
try:
    import PyInstaller.__main__
    
    # Run PyInstaller directly with command line arguments
    # This should show all output directly in the console
    PyInstaller.__main__.run([
        '--name=AutoClipSender',
        '--clean',
        '--noconfirm',
        '--windowed',  # No console window in the final app
        '--add-data=config.py;.',
        '--add-data=defaults.py;.',
        '--add-data=clip_processor.py;.',
        '--add-data=gui.py;.',
        '--add-data=README.md;.',
        '--add-data=.env;.',
        '--add-data=ffmpeg/ffmpeg.exe;.',
        '--add-data=ffmpeg/ffprobe.exe;.',
        '--add-binary=ffmpeg/ffmpeg.exe;.',
        '--add-binary=ffmpeg/ffprobe.exe;.',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=watchdog.observers',
        '--hidden-import=watchdog.events',
        '--hidden-import=requests',
        '--hidden-import=dotenv',
        '--hidden-import=ffmpeg',
        '--hidden-import=psutil',
        '--hidden-import=subprocess',
        '--hidden-import=datetime',
        '--hidden-import=json',
        '--hidden-import=io',
        '--hidden-import=sys',
        '--hidden-import=os',
        '--hidden-import=time',
        '--hidden-import=traceback',
        '--hidden-import=math',
        'app.py'
    ])
    
    # Check if build was successful
    if os.path.exists(os.path.join("dist", "AutoClipSender")):
        print("\n" + "="*50)
        print("Build complete!")
        print("The executable can be found in the 'dist/AutoClipSender' folder.")
        print("To distribute the application, copy the entire 'AutoClipSender' folder.")
        print("="*50)
    else:
        print("\nBuild failed - no output directory was created.")
        
except Exception as e:
    print(f"PyInstaller error: {e}")
    import traceback
    traceback.print_exc() 