
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
