"""
Simple command prompt build script for Auto-Clip-Sender.
Run this from CMD.exe (Command Prompt), not Git Bash!
"""
import os
import subprocess
import sys
import shutil

def main():
    print("=" * 60)
    print("AUTO-CLIP-SENDER BUILDER (CMD VERSION)")
    print("=" * 60)
    print("NOTE: This should be run from Command Prompt, not Git Bash!")
    
    # Make sure PyInstaller is installed (specific version)
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller==5.13.2"], check=True)
    
    # Ensure all required packages are installed
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Check for FFmpeg executables
    if not os.path.exists("ffmpeg"):
        os.makedirs("ffmpeg", exist_ok=True)
        print("FFmpeg folder created. Please place ffmpeg.exe and ffprobe.exe in the ffmpeg folder.")
    
    if not os.path.exists("ffmpeg/ffmpeg.exe") or not os.path.exists("ffmpeg/ffprobe.exe"):
        print("\nWARNING: FFmpeg executables missing!")
        print("Please download FFmpeg from https://ffmpeg.org/download.html")
        print("Extract ffmpeg.exe and ffprobe.exe to the 'ffmpeg' folder and run this script again.")
        return
        
    # Clean previous builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Removing {folder}...")
            shutil.rmtree(folder, ignore_errors=True)
    
    # Create a helper module to fix config.py loading
    os.makedirs("build_helpers", exist_ok=True)
    
    # Write the config_loader.py file
    config_loader_content = '''
# Helper module to ensure config.py is loaded correctly
import os
import sys
import importlib.util

def get_config():
    """Load config.py from the correct location when running as executable"""
    # When running as executable, look in the executable's directory
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_path = os.path.dirname(sys.executable)
        config_path = os.path.join(app_path, 'config', 'config.py')
        
        # Check if config exists in the config subfolder
        if os.path.exists(config_path):
            print(f"Loading config from: {config_path}")
            spec = importlib.util.spec_from_file_location("config", config_path)
            config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config)
            return config
            
        # Try in the main folder
        config_path = os.path.join(app_path, 'config.py')
        if os.path.exists(config_path):
            print(f"Loading config from: {config_path}")
            spec = importlib.util.spec_from_file_location("config", config_path)
            config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config)
            return config
            
        print("Could not find config.py, falling back to defaults.py")
        # Fall back to defaults
        defaults_path = os.path.join(app_path, 'config', 'defaults.py')
        if os.path.exists(defaults_path):
            spec = importlib.util.spec_from_file_location("defaults", defaults_path)
            defaults = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(defaults)
            return defaults
            
        defaults_path = os.path.join(app_path, 'defaults.py')
        if os.path.exists(defaults_path):
            spec = importlib.util.spec_from_file_location("defaults", defaults_path)
            defaults = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(defaults)
            return defaults
    
    # Regular running as script
    try:
        import config
        return config
    except ImportError:
        import defaults
        return defaults
'''
    
    with open("build_helpers/config_loader.py", "w") as f:
        f.write(config_loader_content)
    
    # Write the app_wrapper.py file
    app_wrapper_content = '''
import os
import sys

# Add the current directory to sys.path to ensure modules can be found
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = os.path.dirname(sys.executable)
    os.environ['PATH'] = application_path + os.pathsep + os.environ.get('PATH', '')
    sys.path.insert(0, application_path)
    print(f"Running as executable from: {application_path}")
    print(f"Files in directory: {os.listdir(application_path)}")

try:
    import traceback
    from PyQt5.QtWidgets import QApplication, QMessageBox

    # Set up exception hook to show errors in message boxes
    def excepthook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(f"ERROR: {tb}")
        QMessageBox.critical(None, "Unhandled Exception", 
                            f"An unhandled exception occurred:\\n\\n{tb}\\n\\nPlease report this error.")

    sys.excepthook = excepthook

    # Make sure we're in the right directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    from gui import AutoClipSenderGUI
    app = QApplication(sys.argv)
    window = AutoClipSenderGUI()
    window.show()
    sys.exit(app.exec_())
except Exception as e:
    trace = traceback.format_exc()
    print(f"Error starting application: {e}\\n{trace}")
    if 'QApplication' in globals() and QApplication.instance():
        QMessageBox.critical(None, "Startup Error", 
                            f"Error starting application:\\n\\n{e}\\n\\n{trace}")
    else:
        # If PyQt5 failed to load, try to show a basic error dialog
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, 
                                         f"Error starting application: {e}\\n{trace}", 
                                         "Startup Error", 0)
    sys.exit(1)
'''
    
    with open("build_helpers/app_wrapper.py", "w") as f:
        f.write(app_wrapper_content)
    
    # Create the spec file - FIXED to handle the 3-value tuples correctly
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree

# Explicitly disable timestamp setting which causes errors
import PyInstaller.building.api
PyInstaller.building.api.EXE._set_build_timestamp = lambda *args, **kwargs: None

block_cipher = None

# Create a cleaner organized structure
a = Analysis(
    ['build_helpers/app_wrapper.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ffmpeg/ffmpeg.exe', 'bin'),
        ('ffmpeg/ffprobe.exe', 'bin'),
        ('config.py', 'config'),
        ('defaults.py', 'config'),
        ('clip_processor.py', '.'),
        ('gui.py', '.'),
        ('ffmpeg_helper.py', '.'),
        ('README.md', 'docs'),
        ('.env', 'config'),
        ('app.py', '.'),
        ('build_helpers/config_loader.py', '.'),
    ],
    hiddenimports=[
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 
        'PyQt5.sip', 'PyQt5.QtCore', 'PyQt5.Qt', 'ffmpeg', 'dotenv',
        'watchdog', 'watchdog.observers', 'watchdog.events'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Organize PyQt5 to prevent it from cluttering the root - FIXED for 3-value tuples
# The datas structure is now (dest, source, type)
organized_datas = []
for data_tuple in a.datas:
    dest = data_tuple[0]
    if 'PyQt5' in dest:
        # Create new tuple with modified destination path
        new_dest = dest.replace('PyQt5', 'lib/PyQt5')
        organized_datas.append((new_dest, data_tuple[1], data_tuple[2]))
    else:
        organized_datas.append(data_tuple)
        
a.datas = organized_datas

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoClipSender',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

# Use more organized structure in the collection
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoClipSender',
)
'''
    
    with open("AutoClipSender.spec", "w") as f:
        f.write(spec_content)
    
    print("\nCreated custom spec file (AutoClipSender.spec)")
    print("This spec file creates a cleaner directory structure and ensures PyQt5 is included")
    print("=" * 60)
    
    # Now run PyInstaller with the spec file
    print("Running PyInstaller with custom spec file...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "AutoClipSender.spec"]
    result = subprocess.run(cmd)
    
    if result.returncode == 0 and os.path.exists("dist/AutoClipSender"):
        print("\n" + "=" * 60)
        print("✅ BUILD SUCCESSFUL!")
        print("\nThe application folder can be found at: dist/AutoClipSender")
        print("\nTo distribute, share the entire 'AutoClipSender' folder.")
        print("Users will run the application by clicking 'AutoClipSender.exe' in that folder.")
        print("=" * 60)
        
        # Create a simple batch file to run the app from the dist folder
        with open("dist/AutoClipSender/Run_AutoClipSender.bat", "w") as f:
            f.write('@echo off\n')
            f.write('echo Starting Auto-Clip-Sender...\n')
            f.write('start AutoClipSender.exe\n')
        
    else:
        print("\n" + "=" * 60)
        print("❌ BUILD FAILED!")
        print("Please try running PyInstaller directly with the spec file:")
        print("python -m PyInstaller --noconfirm AutoClipSender.spec")
        print("=" * 60)

if __name__ == "__main__":
    main() 