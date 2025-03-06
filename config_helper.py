"""
Helper module for configuration file handling when running as a PyInstaller executable
"""
import os
import sys
import json
import shutil
from pathlib import Path

def get_application_path():
    """Get the application path, works for both script and executable"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def get_user_config_dir():
    """
    Get the configuration directory - now always uses the application directory
    to make the app portable with all data in one place
    """
    # Simply return the application path to make the app fully portable
    return get_application_path()

def get_config_file_path(filename):
    """Get the full path to a configuration file"""
    # Just use the application directory for config files
    app_path = os.path.join(get_application_path(), filename)
    return app_path

def ensure_config_files():
    """
    Ensure that necessary configuration files exist
    """
    app_dir = get_application_path()
    
    # List of configuration files to check
    config_files = ['config.json', 'defaults.json']
    
    for filename in config_files:
        app_path = os.path.join(app_dir, filename)
        
        # If file doesn't exist, we'll create it when needed
        if not os.path.exists(app_path):
            print(f"Configuration file not found: {app_path}")

def load_json_config(filename):
    """
    Load a JSON configuration file
    """
    try:
        config_path = get_config_file_path(filename)
        print(f"Loading configuration from: {config_path}")
        
        if not os.path.exists(config_path):
            print(f"Configuration file not found: {config_path}")
            return {}
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        print(f"Error loading configuration from {filename}: {e}")
        return {}

def save_json_config(config, filename):
    """
    Save a configuration to a JSON file in the application directory
    """
    try:
        # Save the config to the application directory
        config_path = get_config_file_path(filename)
        
        # Save the config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"Saved configuration to {config_path}")
        return True
    except Exception as e:
        print(f"Error saving configuration to {filename}: {e}")
        return False

# Initialize on module import
if __name__ != "__main__":
    ensure_config_files() 