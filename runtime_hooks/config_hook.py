
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
