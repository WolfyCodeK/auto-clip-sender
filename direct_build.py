"""
Direct build script for Auto-Clip-Sender
Focuses on correct config loading and icon application
"""

import os
import sys
import shutil
import time

# Get absolute paths for all files
base_dir = os.path.abspath(os.getcwd())
config_file = os.path.join(base_dir, "config.py")
defaults_file = os.path.join(base_dir, "defaults.py")
icon_file = os.path.join(base_dir, "icon.ico")
ffmpeg_dir = os.path.join(base_dir, "ffmpeg")
ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")

print("="*70)
print("Auto-Clip-Sender Builder")
print("="*70)

# Verify all required files exist
print("\nVerifying files:")
missing_files = []

required_files = [
    (config_file, "config.py"),
    (ffmpeg_exe, "ffmpeg.exe"),
    (ffprobe_exe, "ffprobe.exe"),
]

for file_path, file_name in required_files:
    if os.path.exists(file_path):
        print(f"✓ Found {file_name}")
    else:
        print(f"✗ Missing {file_name}")
        missing_files.append(file_name)

# Check for icon file separately (not critical but good to have)
if os.path.exists(icon_file):
    print(f"✓ Found icon.ico")
else:
    print(f"⚠ Warning: icon.ico not found - executable will use default icon")
    icon_file = None

if missing_files:
    print(f"\nERROR: Missing required files: {', '.join(missing_files)}")
    print("Build cannot continue.")
    sys.exit(1)

# Clean up previous build if exists
print("\nCleaning up previous build...")
for folder in ["build", "dist", "__pycache__"]:
    if os.path.exists(folder):
        try:
            shutil.rmtree(folder)
            print(f"✓ Removed {folder} directory")
            time.sleep(0.5)  # Brief pause to ensure file handles are released
        except Exception as e:
            print(f"⚠ Warning: Could not remove {folder}: {e}")

# Create a hook file to ensure config.py is properly loaded
print("\nCreating hook file for config loading...")
hook_dir = os.path.join(base_dir, "hooks")
os.makedirs(hook_dir, exist_ok=True)

with open(os.path.join(hook_dir, "hook-app.py"), "w") as f:
    f.write("""
# PyInstaller hook to ensure config.py is properly loaded
from PyInstaller.utils.hooks import collect_data_files

# Ensure these modules are included
hiddenimports = [
    'ffmpeg_helper',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'watchdog.observers',
    'watchdog.events',
    'dotenv',
    'ffmpeg',
    'psutil'
]

# Force inclusion of our config files
datas = [
    ('config.py', '.'),
    ('defaults.py', '.'),
    ('.env', '.'),
]
""")

# Create a runtime hook to prioritize config.py
print("Creating runtime hook to prioritize config.py...")
runtime_dir = os.path.join(base_dir, "runtime_hooks")
os.makedirs(runtime_dir, exist_ok=True)

with open(os.path.join(runtime_dir, "config_hook.py"), "w") as f:
    f.write("""
# Runtime hook to ensure config.py is properly found
import os
import sys

# Add the executable's directory to the PATH so we can find config.py
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    os.environ['PATH'] = application_path + os.pathsep + os.environ.get('PATH', '')
    sys.path.insert(0, application_path)
    
    # Print for debugging
    print(f"Runtime hook: Added {application_path} to sys.path")
    print(f"Files in executable directory: {os.listdir(application_path)}")
""")

print("\nStarting PyInstaller build process...")
print("="*70)

# Build command with all needed options
cmd = [
    'pyinstaller',
    '--clean',
    '--noconfirm',
    '--windowed',
    f'--workpath={os.path.join(base_dir, "build")}',
    f'--distpath={os.path.join(base_dir, "dist")}',
    f'--specpath={base_dir}',
    f'--name=AutoClipSender',
]

# Add icon if available
if icon_file:
    cmd.append(f'--icon={icon_file}')

# Add hooks directories
cmd.append(f'--additional-hooks-dir={hook_dir}')
cmd.append(f'--runtime-hook={os.path.join(runtime_dir, "config_hook.py")}')

# Add data files
cmd.extend([
    f'--add-data={config_file};.',
    f'--add-data={defaults_file};.',
    '--add-data=clip_processor.py;.',
    '--add-data=gui.py;.',
    '--add-data=README.md;.',
    '--add-data=requirements.txt;.',
    '--add-data=ffmpeg_helper.py;.',
])

# Add .env file if it exists
env_file = os.path.join(base_dir, ".env")
if os.path.exists(env_file):
    cmd.append(f'--add-data={env_file};.')

# Add binaries
cmd.extend([
    f'--add-binary={ffmpeg_exe};.',
    f'--add-binary={ffprobe_exe};.',
])

# Add hidden imports
for module in [
    'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
    'watchdog.observers', 'watchdog.events', 'requests',
    'dotenv', 'ffmpeg', 'psutil', 'subprocess', 'ffmpeg_helper',
    'datetime', 'json', 'io', 'sys', 'os', 'time', 'traceback', 'math'
]:
    cmd.append(f'--hidden-import={module}')

# Add main script
cmd.append('app.py')

# Print the full command (useful for debugging)
print("\nRunning command:")
print(' '.join(cmd))
print("\nBuild output:")
print("-"*70)

# Run the command
import subprocess
result = subprocess.run(cmd)

# Check if build was successful
if result.returncode == 0 and os.path.exists(os.path.join("dist", "AutoClipSender", "AutoClipSender.exe")):
    print("\n" + "="*70)
    print("✅ BUILD SUCCESSFUL!")
    print("\nThe executable can be found in:")
    print(f"  {os.path.join(base_dir, 'dist', 'AutoClipSender')}")
    print("\nTo distribute the application, copy the entire 'AutoClipSender' folder.")
    
    # Check if icon was applied
    try:
        import win32gui
        import win32con
        import win32api
        exe_path = os.path.join(base_dir, 'dist', 'AutoClipSender', 'AutoClipSender.exe') 
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        if large or small:
            print("✅ Icon was successfully applied to the executable.")
            for icon in large:
                win32gui.DestroyIcon(icon)
            for icon in small:
                win32gui.DestroyIcon(icon)
        else:
            print("⚠ Icon was not applied to the executable.")
    except ImportError:
        print("Note: Could not verify icon application (pywin32 not installed)")
        
    print("="*70)
else:
    print("\n" + "="*70)
    print("❌ BUILD FAILED!")
    print("Return code:", result.returncode)
    print("\nTroubleshooting tips:")
    print("1. Ensure you have administrator privileges")
    print("2. Try disabling your antivirus temporarily")
    print("3. Run the command manually:")
    print("   " + ' '.join(cmd))
    print("="*70) 