# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Define the main script (entry point)
a = Analysis(
    ['app.py'],  # Main script
    pathex=[],
    binaries=[
        # Include FFmpeg executables
        ('ffmpeg/ffmpeg.exe', '.'),
        ('ffmpeg/ffprobe.exe', '.'),
    ],
    datas=[
        # Include configuration files and other important assets
        ('config.py', '.'),
        ('defaults.py', '.'),
        ('clip_processor.py', '.'),
        ('gui.py', '.'),
        ('README.md', '.'),
        # Include .env file if it exists (comment out if you don't want to include sensitive info)
        ('.env', '.')
    ],
    hiddenimports=[
        'PyQt5.QtCore', 
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'watchdog.observers',
        'watchdog.events',
        'requests',
        'dotenv',
        'ffmpeg',
        'psutil',
        'subprocess',
        'datetime',
        'json',
        'io',
        'sys',
        'os',
        'time',
        'traceback',
        'math',
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

# Create the executable (EXE)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # This creates a directory-based build (not a single file)
    name='AutoClipSender',  # Removed spaces from executable name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True if you want a console window to show
    icon='icon.ico' if os.path.exists('icon.ico') else None,  # Only use icon if it exists
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Collect all files into a directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoClipSender',  # Removed spaces from folder name
)
