"""
Helper module for configuration file handling when running as a PyInstaller executable
"""
import os
import sys
import json
import shutil
from pathlib import Path

def get_application_path():
    """Get the application path for both script and frozen executable modes"""
    if getattr(sys, 'frozen', False):
        # Running as executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def get_user_config_dir():
    """Get the directory for user configuration files
    This now always returns the application directory to keep everything in one place
    """
    return get_application_path()

def get_config_file_path(filename):
    """Get the full path for a configuration file"""
    app_dir = get_application_path()
    return os.path.join(app_dir, filename)

def load_json_config(filename):
    """Load a JSON configuration file with proper error handling"""
    try:
        config_path = get_config_file_path(filename)
        if os.path.exists(config_path):
            # Less verbose logging
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"Config file not found: {config_path}")
            return None
    except Exception as e:
        print(f"Error loading configuration file {filename}: {e}")
        return None

def save_json_config(filename, data):
    """Save data to a JSON configuration file"""
    try:
        config_path = get_config_file_path(filename)
        # Less verbose logging
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving configuration file {filename}: {e}")
        return False

def ensure_config_files():
    """Ensure that all required configuration files exist"""
    try:
        # Check if config.json exists, if not, create it from defaults.json
        config_path = get_config_file_path('config.json')
        if not os.path.exists(config_path):
            # Try to load defaults.json
            defaults = load_json_config('defaults.json')
            if defaults:
                # Save defaults as the new config
                save_json_config('config.json', defaults)
                print("Created config.json from defaults.json")
            else:
                print("Could not create config.json - defaults.json not found")
        return True
    except Exception as e:
        print(f"Error ensuring config files: {e}")
        return False

# Initialize on module import
if __name__ != "__main__":
    ensure_config_files() 