
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
