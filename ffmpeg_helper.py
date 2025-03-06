"""
FFmpeg helper module to manage bundled FFmpeg executables.
This ensures the application uses its own FFmpeg instead of relying on system PATH.
"""

import os
import sys
import subprocess
import ffmpeg

# Original ffmpeg-python run method that we'll patch
original_run = ffmpeg.run

def get_ffmpeg_path():
    """Get the path to the bundled FFmpeg executable"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # PyInstaller puts the bundled executables in the same directory as the main exe
        app_dir = os.path.dirname(sys.executable)
        ffmpeg_path = os.path.join(app_dir, "ffmpeg.exe")
        
        # Check if FFmpeg executable exists at the expected location
        if os.path.exists(ffmpeg_path):
            return ffmpeg_path
    
    # Either running as script or bundled ffmpeg.exe not found
    # Try to use FFmpeg from PATH as fallback
    return "ffmpeg"

def get_ffprobe_path():
    """Get the path to the bundled FFprobe executable"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = os.path.dirname(sys.executable)
        ffprobe_path = os.path.join(app_dir, "ffprobe.exe")
        
        # Check if FFprobe executable exists at the expected location
        if os.path.exists(ffprobe_path):
            return ffprobe_path
    
    # Either running as script or bundled ffprobe.exe not found
    # Try to use FFprobe from PATH as fallback
    return "ffprobe"

def patch_ffmpeg_python():
    """
    Patch the ffmpeg-python library to use our bundled FFmpeg
    """
    # Store original paths
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()
    
    # Define a new run function that uses our paths
    def patched_run(*args, **kwargs):
        # Make sure 'cmd' is not in kwargs
        if 'cmd' in kwargs:
            raise ValueError("'cmd' argument conflicts with patched ffmpeg run method")
        
        # Call original run but with our custom ffmpeg path
        kwargs['cmd'] = ffmpeg_path
        return original_run(*args, **kwargs)
    
    # Replace the ffmpeg.run with our patched version
    ffmpeg.run = patched_run
    
    # Patch ffmpeg._probe function
    original_probe = ffmpeg._probe
    
    def patched_probe(*args, **kwargs):
        if 'cmd' in kwargs:
            raise ValueError("'cmd' argument conflicts with patched ffmpeg probe method")
        
        kwargs['cmd'] = ffprobe_path
        return original_probe(*args, **kwargs)
    
    ffmpeg._probe = patched_probe
    
    print(f"FFmpeg patched to use bundled executables:")
    print(f"  - FFmpeg: {ffmpeg_path}")
    print(f"  - FFprobe: {ffprobe_path}")

# Apply the patch when this module is imported
patch_ffmpeg_python() 