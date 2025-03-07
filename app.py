import sys
import os
import traceback
import json
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt

# Import our config helper to ensure config files exist in the right location
import config_helper

# Hide console windows for Windows
if os.name == 'nt':
    # Try to make the app run without a console window
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    # Ensure all subprocesses are hidden
    import subprocess
    
    # Store the original Popen class
    original_popen = subprocess.Popen
    
    # Create a patched version that hides console windows
    class NoConsolePopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            # Add creationflags to hide console window
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    
    # Replace the original Popen with our patched version
    subprocess.Popen = NoConsolePopen

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

        # Patch ffmpeg to hide windows if possible
        try:
            import ffmpeg
            original_ffmpeg_run = ffmpeg._run.run
            
            def patched_ffmpeg_run(cmd, **kwargs):
                if 'creationflags' not in kwargs and os.name == 'nt':
                    kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW
                return original_ffmpeg_run(cmd, **kwargs)
            
            ffmpeg._run.run = patched_ffmpeg_run
            print("FFmpeg patched to hide console windows")
        except ImportError:
            print("ffmpeg-python not imported yet, will be patched later")

        # Import and start the GUI
        from gui import AutoClipSenderGUI
        app = QApplication(sys.argv)
        
        # Set application name and organization
        app.setApplicationName("Auto Clip Sender")
        app.setApplicationDisplayName("Auto Clip Sender")
        app.setOrganizationName("Auto Clip Sender")
        
        # Set app style to fusion for a modern look
        app.setStyle('Fusion')
        
        # Try all possible icon locations
        icon_paths = [
            os.path.join(app_dir, '_internal', '128x128.ico'),  # PyInstaller build
            os.path.join(app_dir, '128x128.ico'),              # Root directory
            os.path.join(app_dir, 'icons', '128x128.ico'),     # Icons folder
        ]
        
        app_icon = None
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                print(f"Using icon from: {icon_path}")
                app_icon = QIcon(icon_path)
                break
                
        if app_icon and not app_icon.isNull():
            app.setWindowIcon(app_icon)
            
            # Set app ID for Windows (helps with taskbar icon)
            if os.name == 'nt':
                try:
                    app_id = "autoClipSender.1.0"
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                    print(f"Set Windows Application User Model ID to: {app_id}")
                except Exception as e:
                    print(f"Error setting application ID: {e}")
        else:
            print("No valid icon file found.")
        
        # Create main window
        window = AutoClipSenderGUI()
        
        # If we set an app icon, also set it on the window
        if app_icon and not app_icon.isNull():
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