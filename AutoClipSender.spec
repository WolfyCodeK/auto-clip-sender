# -*- mode: python ; coding: utf-8 -*-

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
