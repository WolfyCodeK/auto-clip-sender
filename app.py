import sys
import os
import traceback
import json
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

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
        
        # Create a composite icon from multiple sizes in the icons folder
        app_icon = QIcon()
        
        # --- DETAILED ICON DEBUGGING ---
        print(f"Is running as executable: {getattr(sys, 'frozen', False)}")
        
        # Check for icons folder
        icons_folder = os.path.join(app_dir, 'icons')
        print(f"Looking for icons folder at: {icons_folder}")
        print(f"Icons folder exists: {os.path.exists(icons_folder)}")
        
        # List contents of app directory to help debugging
        print(f"Contents of application directory ({app_dir}):")
        try:
            for item in os.listdir(app_dir):
                item_path = os.path.join(app_dir, item)
                if os.path.isdir(item_path):
                    print(f"  DIR: {item}")
                else:
                    print(f"  FILE: {item}")
        except Exception as e:
            print(f"Error listing directory contents: {e}")
        
        # Also check parent directory (in case icons is one level up)
        parent_dir = os.path.dirname(app_dir)
        icons_folder_parent = os.path.join(parent_dir, 'icons')
        print(f"Alternative icons path: {icons_folder_parent}")
        print(f"Alternative icons folder exists: {os.path.exists(icons_folder_parent)}")
        
        # Check for single icon file as fallback
        single_icon_path = os.path.join(app_dir, 'icon.ico')
        print(f"Fallback icon path: {single_icon_path}")
        print(f"Fallback icon exists: {os.path.exists(single_icon_path)}")
        
        # Try looking for icons in multiple locations
        possible_icon_locations = [
            icons_folder,                               # Standard location
            icons_folder_parent,                        # Parent directory
            os.path.join(os.path.dirname(sys.executable), 'icons') if getattr(sys, 'frozen', False) else None,  # Executable directory
            os.path.join(os.getcwd(), 'icons'),         # Current working directory
            single_icon_path                            # Single icon file
        ]
        
        # Find first valid icon location
        valid_icon_location = None
        for location in possible_icon_locations:
            if location and os.path.exists(location):
                print(f"Found valid icon location: {location}")
                valid_icon_location = location
                break
                
        if valid_icon_location:
            # Load icons from the found location
            if os.path.isdir(valid_icon_location):
                # It's a directory, look for multiple icon files
                print(f"Loading icons from directory: {valid_icon_location}")
                print(f"Directory contents:")
                try:
                    for item in os.listdir(valid_icon_location):
                        print(f"  {item}")
                except Exception as e:
                    print(f"Error listing icons directory: {e}")
                
                # Add each icon size to the QIcon
                icon_sizes = ['16x16.ico', '32x32.ico', '48x48.ico', '64x64.ico', '128x128.ico']
                for icon_file in icon_sizes:
                    icon_path = os.path.join(valid_icon_location, icon_file)
                    if os.path.exists(icon_path):
                        # Extract size from filename (e.g., "16x16.ico" -> 16)
                        try:
                            size = int(icon_file.split('x')[0])
                            app_icon.addFile(icon_path, QSize(size, size))
                            print(f"Added icon size {size}x{size} from {icon_path}")
                        except Exception as e:
                            print(f"Error adding icon {icon_file}: {e}")
            else:
                # It's a single file
                print(f"Loading single icon file: {valid_icon_location}")
                app_icon.addFile(valid_icon_location)
                
            # Set the application icon
            app.setWindowIcon(app_icon)
            print(f"Icon set successfully: {not app_icon.isNull()}")
            
            # Set application ID (Windows only)
            if os.name == 'nt':
                try:
                    import ctypes
                    # This helps Windows properly associate the icon with the application
                    app_id = "autoClipSender.1.0"
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                    print(f"Set Windows Application User Model ID to: {app_id}")
                except Exception as e:
                    print(f"Error setting application ID: {e}")
        else:
            print("No valid icon location found.")
        
        # --- END ICON DEBUGGING ---
        
        # Create main window
        window = AutoClipSenderGUI()
        
        # If we created an icon, also set it on the window explicitly
        if not app_icon.isNull():
            window.setWindowIcon(app_icon)
            print("Set window icon from app_icon")
        
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        trace = traceback.format_exc()
        print(f"Error starting application: {e}\n{trace}")
        if QApplication.instance():
            QMessageBox.critical(None, "Startup Error", 
                                f"Error starting application:\n\n{e}\n\n{trace}")
        sys.exit(1) 