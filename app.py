import sys
import os
import traceback
import json
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt

# Import our config helper to ensure config files exist in the right location
import config_helper

# Set up exception hook to show errors in message boxes
def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"ERROR: {tb}")
    QMessageBox.critical(None, "Unhandled Exception", 
                        f"An unhandled exception occurred:\n\n{tb}\n\nPlease report this error.")

sys.excepthook = excepthook

if __name__ == '__main__':
    try:
        # Set application path - works for both script and frozen executable
        app_dir = config_helper.get_application_path()
        print(f"Application directory: {app_dir}")
        
        # Set user config directory and ensure files exist
        user_config_dir = config_helper.get_user_config_dir()
        print(f"User configuration directory: {user_config_dir}")
        
        # Ensure config files exist
        config_helper.ensure_config_files()
        
        # Add application directory to path to find modules
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
            
        # Add ffmpeg to PATH if it exists
        ffmpeg_dir = os.path.join(app_dir, 'ffmpeg')
        if os.path.exists(ffmpeg_dir) and ffmpeg_dir not in os.environ['PATH']:
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
            print(f"Added ffmpeg directory to PATH: {ffmpeg_dir}")

        # Import and start the GUI
        from gui import AutoClipSenderGUI
        app = QApplication(sys.argv)
        
        # Set application name and organization
        app.setApplicationName("Auto Clip Sender")
        app.setApplicationDisplayName("Auto Clip Sender")
        app.setOrganizationName("Auto Clip Sender")
        
        # Look for the icon in the _internal folder first (for PyInstaller build)
        # Then fallback to root directory (for development)
        internal_icon_path = os.path.join(app_dir, '_internal', '128x128.ico')
        root_icon_path = os.path.join(app_dir, '128x128.ico')
        
        print(f"Looking for icon in _internal folder: {internal_icon_path}")
        print(f"Icon exists in _internal: {os.path.exists(internal_icon_path)}")
        
        print(f"Looking for icon in root: {root_icon_path}")
        print(f"Icon exists in root: {os.path.exists(root_icon_path)}")
        
        # Choose the first available icon path
        icon_path = None
        if os.path.exists(internal_icon_path):
            icon_path = internal_icon_path
            print(f"Using icon from _internal folder")
        elif os.path.exists(root_icon_path):
            icon_path = root_icon_path
            print(f"Using icon from root directory")
        
        if icon_path:
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
            print(f"Set application icon from {icon_path}")
            
            # Set app ID for Windows (helps with taskbar icon)
            if os.name == 'nt':
                try:
                    import ctypes
                    app_id = "autoClipSender.1.0"
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                    print(f"Set Windows Application User Model ID to: {app_id}")
                except Exception as e:
                    print(f"Error setting application ID: {e}")
        else:
            print("Icon file not found in any location.")
        
        # Create main window
        window = AutoClipSenderGUI()
        
        # If we set an app icon, also set it on the window
        if 'app_icon' in locals() and not app_icon.isNull():
            window.setWindowIcon(app_icon)
            
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        trace = traceback.format_exc()
        print(f"Error starting application: {e}\n{trace}")
        if QApplication.instance():
            QMessageBox.critical(None, "Startup Error", 
                                f"Error starting application:\n\n{e}\n\n{trace}")
        sys.exit(1) 