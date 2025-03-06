import os
import time
import requests
import ffmpeg
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import ntpath
import math
from dotenv import load_dotenv
import sys
import json
import shutil
import traceback
import io
import threading
import subprocess

# Import our config helper for proper path handling
import config_helper

# Patch subprocess and ffmpeg to hide all console windows on Windows
if os.name == 'nt':
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
    
    # Also directly patch the ffmpeg run method for good measure
    original_ffmpeg_run = ffmpeg._run.run
    
    def patched_ffmpeg_run(cmd, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW
        return original_ffmpeg_run(cmd, **kwargs)
    
    ffmpeg._run.run = patched_ffmpeg_run
    
    print("Successfully patched subprocess and ffmpeg to hide console windows")

# Get application path for executable/script mode
application_path = config_helper.get_application_path()
config_dir = config_helper.get_user_config_dir()

# Constants and Configuration
CONFIG_FILE = 'config.json'
DEFAULTS_FILE = 'defaults.json'

# Set up default config
DEFAULT_CONFIG = {
    'SHADOWPLAY_FOLDER': "",
    'OUTPUT_FOLDER': "",
    'MIN_SIZE_MB': 8.0,
    'MAX_SIZE_MB': 10.0,
    'TARGET_SIZE_MB': 9.0,
    'MAX_COMPRESSION_ATTEMPTS': 5,
    'CRF_MIN': 1,
    'CRF_MAX': 30,
    'CRF_STEP': 1,
    'EXTRACT_PRESET': "fast",
    'COMPRESSION_PRESET': "medium",
    'CLIP_DURATION': 15,
    'HIGH_QUALITY_CRF': 18,
    'CLOSE_THRESHOLD': 0.9,
    'MEDIUM_THRESHOLD': 0.75,
    'FAR_THRESHOLD': 0.5,
    'WEBHOOK_URL': "",
    'COMPRESSION_METHOD': "Progressive"  # New option: "Progressive" or "Quick"
}

# Compression method constants
COMPRESSION_PROGRESSIVE = "Progressive"  # Current multi-pass approach
COMPRESSION_QUICK = "Quick"  # Simple one-pass approach with high quality

def load_config():
    """Load configuration with fallback to defaults"""
    try:
        # Load user config
        config = config_helper.load_json_config(CONFIG_FILE)
        if not config:
            print(f"Config file not found, loading defaults")
            # If no user config, try to load defaults
            config = config_helper.load_json_config(DEFAULTS_FILE)
            if not config:
                print(f"Defaults file not found, using hardcoded defaults")
                config = DEFAULT_CONFIG
        
        # Add new options if they don't exist yet
        if 'COMPRESSION_METHOD' not in config:
            config['COMPRESSION_METHOD'] = DEFAULT_CONFIG['COMPRESSION_METHOD']
            print(f"Added new configuration option: COMPRESSION_METHOD = {config['COMPRESSION_METHOD']}")
        
        # Print the loaded config for debugging (without webhook)
        debug_config = config.copy()
        if 'WEBHOOK_URL' in debug_config:
            debug_config['WEBHOOK_URL'] = '[CONFIGURED]' if debug_config['WEBHOOK_URL'] else '[NOT CONFIGURED]'
        print(f"Loaded configuration: {json.dumps(debug_config, indent=2)}")
        
        # Verify webhook URL exists
        webhook_url = config.get('WEBHOOK_URL', '')
        if not webhook_url:
            print("ERROR: No webhook URL configured. Please set the webhook URL in the application settings.")
            return None
            
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        traceback.print_exc()
        return None

# Load configuration
CONFIG = load_config()
if not CONFIG:
    print("Failed to load configuration. Exiting.")
    sys.exit(1)

# Get webhook URL from config
WEBHOOK_URL = CONFIG.get('WEBHOOK_URL', '')
if not WEBHOOK_URL:
    print("No webhook URL configured. Please set it in the application settings.")
    sys.exit(1)

# Other configuration values
SHADOWPLAY_FOLDER = CONFIG.get('SHADOWPLAY_FOLDER', '')
OUTPUT_FOLDER = CONFIG.get('OUTPUT_FOLDER', '')
MIN_SIZE_MB = CONFIG.get('MIN_SIZE_MB', 8.0)
MAX_SIZE_MB = CONFIG.get('MAX_SIZE_MB', 10.0)
TARGET_SIZE_MB = CONFIG.get('TARGET_SIZE_MB', 9.0)
MAX_COMPRESSION_ATTEMPTS = CONFIG.get('MAX_COMPRESSION_ATTEMPTS', 5)
CRF_MIN = CONFIG.get('CRF_MIN', 1)
CRF_MAX = CONFIG.get('CRF_MAX', 30)
CRF_STEP = CONFIG.get('CRF_STEP', 1)
EXTRACT_PRESET = CONFIG.get('EXTRACT_PRESET', 'fast')
COMPRESSION_PRESET = CONFIG.get('COMPRESSION_PRESET', 'medium')
CLIP_DURATION = CONFIG.get('CLIP_DURATION', 15)
HIGH_QUALITY_CRF = CONFIG.get('HIGH_QUALITY_CRF', 18)
CLOSE_THRESHOLD = CONFIG.get('CLOSE_THRESHOLD', 0.9)
MEDIUM_THRESHOLD = CONFIG.get('MEDIUM_THRESHOLD', 0.75)
FAR_THRESHOLD = CONFIG.get('FAR_THRESHOLD', 0.5)
COMPRESSION_METHOD = CONFIG.get('COMPRESSION_METHOD', COMPRESSION_PROGRESSIVE)

# Display loaded settings for debugging
print(f"Loaded SHADOWPLAY_FOLDER: {SHADOWPLAY_FOLDER}")
print(f"Loaded OUTPUT_FOLDER: {OUTPUT_FOLDER}")
print(f"Loaded COMPRESSION_METHOD: {COMPRESSION_METHOD}")
print(f"Loaded size settings: MIN={MIN_SIZE_MB}MB, MAX={MAX_SIZE_MB}MB, TARGET={TARGET_SIZE_MB}MB")

class ClipHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        # Skip files that are already in the output folder
        if OUTPUT_FOLDER.lower() in event.src_path.lower():
            print(f"Skipping file in output folder: {event.src_path}")
            return

        if event.src_path.lower().endswith(('.mp4', '.mov', '.avi')):
            print(f"New file detected: {event.src_path}")
            time.sleep(2)  # Allow file to finish writing
            try:
                process_clip(event.src_path)
            except Exception as e:
                print(f"Error processing clip {event.src_path}: {e}")

def safe_remove(filepath):
    """Safely remove a file with retries and proper error handling."""
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except PermissionError:
            print(f"File {filepath} is still in use. Waiting before retry ({attempt+1}/{max_attempts})...")
            time.sleep(2)  # Wait 2 seconds before retrying
        except Exception as e:
            print(f"Error removing file {filepath}: {e}")
            return False
    
    print(f"Could not remove file {filepath} after {max_attempts} attempts")
    return False

def process_clip(filepath):
    # Extract game folder name from the file path
    game_folder_name = os.path.basename(os.path.dirname(filepath))
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%m%d%Y-%H%M")
    
    # Final clip filename: GameName-Timestamp.mp4
    final_filename = f"{game_folder_name}-{timestamp}.mp4"
    final_filepath = os.path.join(OUTPUT_FOLDER, final_filename)
    
    # Temporary file for compression iterations
    temp_filepath = os.path.join(OUTPUT_FOLDER, f"temp_{final_filename}")
    
    # Ensure the output directory exists
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # Get video duration and original resolution
    probe = ffmpeg.probe(filepath)
    duration = float(probe['format']['duration'])
    start_time = max(0, duration - CLIP_DURATION)
    
    # Check if the file is long enough to trim
    if duration < CLIP_DURATION:  # If the file is shorter than our clip duration, skip processing
        print(f"Skipping {filepath} because it's too short to trim.")
        return

    # Get video width and height
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    original_bitrate = float(probe['format']['bit_rate']) / 1000 if 'bit_rate' in probe['format'] else 0
    
    print(f"Original video: {width}x{height}, duration: {duration:.2f}s, bitrate: {original_bitrate:.0f}kbps")

    # Trim last X seconds and save to a temporary file with high quality
    # This will be our source for compression iterations
    print(f"Extracting last {CLIP_DURATION} seconds with high quality...")
    ffmpeg.input(filepath, ss=start_time).output(
        temp_filepath, 
        vcodec='libx264', 
        acodec='aac',
        crf=HIGH_QUALITY_CRF,  # High quality source for our compression iterations
        preset=EXTRACT_PRESET
    ).run(overwrite_output=True)
    
    # Check if the temporary file is valid
    if not os.path.exists(temp_filepath) or os.path.getsize(temp_filepath) < 100 * 1024:
        print(f"Error: Failed to create valid temporary file. Skipping.")
        if os.path.exists(temp_filepath):
            safe_remove(temp_filepath)
        return
    
    temp_size_mb = os.path.getsize(temp_filepath) / (1024 * 1024)
    print(f"Extracted high-quality clip: {temp_size_mb:.2f}MB")
    
    # Choose the right compression method based on user setting
    if COMPRESSION_METHOD == COMPRESSION_QUICK:
        # Quick method: Just use a single pass with a moderate CRF value for faster processing
        print(f"Using Quick compression method (single pass with CRF=23)")
        quick_filepath = os.path.join(OUTPUT_FOLDER, f"quick_{final_filename}")
        
        try:
            # Use CRF=23 for good balance of quality and size
            ffmpeg.input(temp_filepath).output(
                quick_filepath, 
                vcodec='libx264', 
                acodec='aac', 
                crf=23,  # Changed from 1 to 23 for smaller file size
                preset=COMPRESSION_PRESET
            ).run(overwrite_output=True)
            
            if os.path.exists(quick_filepath):
                final_size_mb = os.path.getsize(quick_filepath) / (1024 * 1024)
                print(f"Quick compression complete: {final_size_mb:.2f}MB")
                
                # Rename to final filepath and clean up temp file
                if os.path.exists(final_filepath):
                    safe_remove(final_filepath)
                os.rename(quick_filepath, final_filepath)
                safe_remove(temp_filepath)
            else:
                print(f"Error: Quick compression failed to create output file.")
                # If the quick compression fails, just use the temp file
                if os.path.exists(final_filepath):
                    safe_remove(final_filepath)
                os.rename(temp_filepath, final_filepath)
        except Exception as e:
            print(f"Error during quick compression: {e}")
            # If any error occurs, use the temporary file
            if os.path.exists(quick_filepath):
                safe_remove(quick_filepath)
            if os.path.exists(final_filepath):
                safe_remove(final_filepath)
            os.rename(temp_filepath, final_filepath)
    else:
        # Progressive method (original code)
        # Store results of our compression attempts
        results = []  # Will store tuples of (crf, size_mb, filepath)
        
        # Check if our high-quality temporary file already meets our criteria
        if MIN_SIZE_MB <= temp_size_mb <= MAX_SIZE_MB:
            print(f"High-quality temporary file ({temp_size_mb:.2f}MB) already meets our size criteria. Using it.")
            os.rename(temp_filepath, final_filepath)
        else:
            # Define a simple function to try a specific CRF value and record results
            def try_crf(crf_value, label=""):
                nonlocal results
                iteration_filepath = os.path.join(OUTPUT_FOLDER, f"{label}{crf_value}_{final_filename}")
                try:
                    print(f"Trying CRF={crf_value}...")
                    ffmpeg.input(temp_filepath).output(
                        iteration_filepath, 
                        vcodec='libx264', 
                        acodec='aac', 
                        crf=crf_value,
                        preset=COMPRESSION_PRESET
                    ).run(overwrite_output=True)
                    
                    if os.path.exists(iteration_filepath):
                        size_mb = os.path.getsize(iteration_filepath) / (1024 * 1024)
                        print(f"CRF={crf_value} produced: {size_mb:.2f}MB")
                        results.append((crf_value, size_mb, iteration_filepath))
                        return size_mb
                    return None
                except Exception as e:
                    print(f"Error testing CRF={crf_value}: {e}")
                    if os.path.exists(iteration_filepath):
                        safe_remove(iteration_filepath)
                    return None
            
            # AGGRESSIVE APPROACH USING FIXED CRF VALUES
            # Try just a few widely spaced CRF values to quickly find the right range
            # CRF values have a significant impact on file size, so wide jumps work well
            
            # Start with a middle ground CRF value
            initial_crf = int(CRF_MAX * 0.75)  # 75% of max as starting point
            # If source is very large, start with more aggressive compression
            if temp_size_mb > 50:
                initial_crf = CRF_MAX
            elif temp_size_mb > 25:
                initial_crf = int(CRF_MAX * 0.9)  # 90% of max
                
            # Try initial CRF
            print(f"Starting with CRF={initial_crf}")
            size1 = try_crf(initial_crf, "init")
            
            # Based on first result, try a dramatically different value
            if size1 is not None:
                if size1 > MAX_SIZE_MB:
                    # Too big, try much more aggressive compression
                    # Calculate a large jump based on file size ratio
                    size_ratio = size1 / TARGET_SIZE_MB
                    jump_amount = min(int(size_ratio * 5), (CRF_MAX - initial_crf))  # Limit to max available range
                    second_crf = min(initial_crf + jump_amount, CRF_MAX)  # Cap at CRF_MAX
                    print(f"File too large ({size1:.2f}MB), making large jump to CRF={second_crf} (+{jump_amount})")
                else:  # size1 < MIN_SIZE_MB
                    # Too small, try much less compression
                    size_ratio = TARGET_SIZE_MB / max(size1, 0.1)  # Avoid division by zero
                    
                    # Adjust jump size based on how close we are to the target
                    # Use smaller jumps when we're getting close to the target
                    if size1 >= 6:  # If we're within 2MB of our target
                        jump_amount = CRF_STEP  # Small increment based on configured step
                    elif size1 >= 4:  # If we're within 4MB of our target
                        jump_amount = CRF_STEP * 2  # Moderate increment
                    else:
                        # We're far away, use the original calculation with a cap
                        jump_amount = min(int(size_ratio * 4), (initial_crf - CRF_MIN))  # Limit to available range
                        
                    second_crf = max(initial_crf - jump_amount, CRF_MIN)  # Lower floor to CRF_MIN
                    print(f"File too small ({size1:.2f}MB), making {jump_amount} point jump to CRF={second_crf}")
                
                # Skip if same as initial CRF
                if second_crf != initial_crf:
                    size2 = try_crf(second_crf, "jump")
                    
                    # Now we should have two very different CRF values, try something in middle
                    if size2 is not None and not (MIN_SIZE_MB <= size1 <= MAX_SIZE_MB) and not (MIN_SIZE_MB <= size2 <= MAX_SIZE_MB):
                        # Sort our CRFs for easier logic
                        crf_low = min(initial_crf, second_crf)
                        crf_high = max(initial_crf, second_crf)
                        size_low = size1 if initial_crf == crf_low else size2
                        size_high = size1 if initial_crf == crf_high else size2
                        
                        # Check if we've bracketed our target range (one file too big, one too small)
                        if (size_low > MAX_SIZE_MB and size_high < MIN_SIZE_MB) or (size_high > MAX_SIZE_MB and size_low < MIN_SIZE_MB):
                            # We need to "invert" the values to ensure proper bracketing
                            if size_low > MAX_SIZE_MB:  # Low CRF = larger file
                                crf_low, crf_high = crf_high, crf_low
                                size_low, size_high = size_high, size_low
                                
                            # Now crf_low gives file < MIN_SIZE_MB and crf_high gives file > MAX_SIZE_MB
                            # Try a third CRF in the middle with a logarithmic scale to account for CRF's non-linear effect
                            # Use weighted interpolation rather than simple midpoint
                            # This gives us a better chance of hitting the target range
                            
                            weight = (TARGET_SIZE_MB - size_low) / (size_high - size_low)
                            # Apply logarithmic interpolation (CRF effect is roughly logarithmic)
                            third_crf = int(crf_low + (crf_high - crf_low) * weight * 0.7)  # 0.7 factor to bias toward quality
                            
                            # Ensure it's different from both previous values
                            if third_crf == crf_low:
                                third_crf += 1
                            elif third_crf == crf_high:
                                third_crf -= 1
                                
                            print(f"Trying interpolated CRF={third_crf} (between {crf_low} and {crf_high})")
                            try_crf(third_crf, "mid")

            # After all attempts, select the best result (closest to our target size)
            if results:
                # Filter results that are under our max size limit (we don't want to exceed 10MB)
                valid_results = [r for r in results if r[1] <= MAX_SIZE_MB]
                
                if valid_results:
                    # First, check if any are in our desired range
                    target_results = [r for r in valid_results if r[1] >= MIN_SIZE_MB]
                    
                    if target_results:
                        # Find the one closest to the middle of our range (9MB)
                        best_result = min(target_results, key=lambda r: abs(r[1] - TARGET_SIZE_MB))
                    else:
                        # If none are in range, get the largest one that's still under our max
                        best_result = max(valid_results, key=lambda r: r[1])
                        best_crf, best_size, best_filepath = best_result
                        
                        # If no file is in target range, try a more aggressive fine-tuning approach
                        # This will attempt multiple CRF values in sequence until we reach the target range
                        if best_size < MIN_SIZE_MB:
                            print(f"Best result ({best_size:.2f}MB) below target range. Trying progressive fine-tuning.")
                            current_crf = best_crf
                            
                            # Try up to 3 more CRF values, decreasing by 1-3 each time based on how close we are
                            for i in range(3):  # We'll try up to 3 more attempts
                                if current_crf <= CRF_MIN:
                                    break  # Can't go lower than configured min
                                    
                                # Calculate how much to decrease CRF by
                                if best_size >= MIN_SIZE_MB * CLOSE_THRESHOLD:  # Very close
                                    crf_change = CRF_STEP  # Fine adjustment
                                elif best_size >= MIN_SIZE_MB * MEDIUM_THRESHOLD:  # Close
                                    crf_change = CRF_STEP * 2  # Medium adjustment
                                else:
                                    crf_change = CRF_STEP * 3  # Large adjustment
                                    
                                # Don't go below configured minimum
                                next_crf = max(current_crf - crf_change, CRF_MIN)
                                
                                # Skip if we've already tried this value
                                if any(r[0] == next_crf for r in results):
                                    next_crf = max(next_crf - CRF_STEP, CRF_MIN)  # Try one step lower
                                    if any(r[0] == next_crf for r in results):
                                        break  # We've already tried this too, give up
                                
                                print(f"Fine-tuning attempt {i+1}/3: Trying CRF={next_crf}")
                                fine_tune_filepath = os.path.join(OUTPUT_FOLDER, f"finetune{i}_{final_filename}")
                                
                                try:
                                    ffmpeg.input(temp_filepath).output(
                                        fine_tune_filepath, 
                                        vcodec='libx264', 
                                        acodec='aac', 
                                        crf=next_crf,
                                        preset=COMPRESSION_PRESET
                                    ).run(overwrite_output=True)
                                    
                                    if os.path.exists(fine_tune_filepath):
                                        fine_tune_size = os.path.getsize(fine_tune_filepath) / (1024 * 1024)
                                        print(f"Fine-tune attempt {i+1} produced: {fine_tune_size:.2f}MB")
                                        
                                        # Add to our results
                                        results.append((next_crf, fine_tune_size, fine_tune_filepath))
                                        
                                        # If we've reached target range, we can stop
                                        if MIN_SIZE_MB <= fine_tune_size <= MAX_SIZE_MB:
                                            print(f"Found file in target range! CRF={next_crf}, size={fine_tune_size:.2f}MB")
                                            best_result = (next_crf, fine_tune_size, fine_tune_filepath)
                                            break
                                        
                                        # If this is better than our previous best (closer to target), update it
                                        if fine_tune_size <= MAX_SIZE_MB and fine_tune_size > best_size:
                                            best_result = (next_crf, fine_tune_size, fine_tune_filepath)
                                            best_size = fine_tune_size  # Update for next iteration's decision
                                        
                                        # If we've gone over MAX_SIZE_MB, stop trying lower CRF values
                                        if fine_tune_size > MAX_SIZE_MB:
                                            break
                                        
                                        # Continue with the next iteration
                                        current_crf = next_crf
                                    else:
                                        break  # Something went wrong, stop fine-tuning
                                except Exception as e:
                                    print(f"Error during fine-tune attempt {i+1}: {e}")
                                    if os.path.exists(fine_tune_filepath):
                                        safe_remove(fine_tune_filepath)
                                    break
                    
                    best_crf, best_size, best_filepath = best_result
                    print(f"Using best available result: CRF={best_crf}, size={best_size:.2f}MB")
                    
                    # Rename the best file to our final filename
                    if os.path.exists(final_filepath):
                        safe_remove(final_filepath)
                    os.rename(best_filepath, final_filepath)
                else:
                    # All results are too large, use the smallest result but compress it further
                    smallest_result = min(results, key=lambda r: r[1])
                    crf, size, filepath = smallest_result
                    
                    # If this is still way too large, try one more aggressive compression
                    if size > MAX_SIZE_MB * 1.5:  # If it's more than 15MB
                        print(f"All results too large, trying one final aggressive compression (CRF={CRF_MAX})")
                        final_filepath_temp = os.path.join(OUTPUT_FOLDER, f"final_compressed_{final_filename}")
                        
                        try:
                            ffmpeg.input(filepath).output(
                                final_filepath_temp, 
                                vcodec='libx264', 
                                acodec='aac', 
                                crf=CRF_MAX,  # Very aggressive compression
                                preset=COMPRESSION_PRESET
                            ).run(overwrite_output=True)
                            
                            if os.path.exists(final_filepath_temp):
                                final_size = os.path.getsize(final_filepath_temp) / (1024 * 1024)
                                if final_size <= MAX_SIZE_MB:
                                    print(f"Final aggressive compression successful: {final_size:.2f}MB")
                                    if os.path.exists(final_filepath):
                                        safe_remove(final_filepath)
                                    os.rename(final_filepath_temp, final_filepath)
                                else:
                                    print(f"Even aggressive compression ({final_size:.2f}MB) exceeds limit. Using original trimmed file.")
                                    safe_remove(final_filepath_temp)
                                    if os.path.exists(final_filepath):
                                        safe_remove(final_filepath)
                                    os.rename(temp_filepath, final_filepath)
                                    # We're keeping the temp file so don't try to delete it later
                                    temp_filepath = None
                        except Exception as e:
                            print(f"Error during final aggressive compression: {e}")
                            if os.path.exists(final_filepath_temp):
                                safe_remove(final_filepath_temp)
                            if os.path.exists(final_filepath):
                                safe_remove(final_filepath)
                            os.rename(temp_filepath, final_filepath)
                            temp_filepath = None
                    else:
                        # Not drastically large, use original trimmed file
                        print("All results exceed size limit. Using original trimmed file.")
                        if os.path.exists(final_filepath):
                            safe_remove(final_filepath)
                        os.rename(temp_filepath, final_filepath)
                        # We're keeping the temp file so don't try to delete it later
                        temp_filepath = None
        
        # Clean up any temporary files
        if temp_filepath and os.path.exists(temp_filepath):
            safe_remove(temp_filepath)
        
        # Clean up any remaining iteration files
        for _, _, filepath in results:
            if filepath != final_filepath and os.path.exists(filepath):
                safe_remove(filepath)
    
    # Check final file size
    if os.path.exists(final_filepath):
        final_size_mb = os.path.getsize(final_filepath) / (1024 * 1024)
        print(f"Final file size: {final_size_mb:.2f}MB")
        
        # Send the final processed file to Discord via webhook
        send_to_webhook(final_filepath, game_folder_name)
    else:
        print("Error: Final file not created!")

def send_to_webhook(file_path, game_name):
    """Send a file to Discord using a webhook."""
    try:
        # Get just the filename from the path
        filename = os.path.basename(file_path)
        
        # Create a multipart form data payload
        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, 'video/mp4')
            }
            
            # You can add a message with the file
            data = {
                'content': f"New clip from {game_name}"
            }
            
            # Send the request to the webhook URL
            response = requests.post(WEBHOOK_URL, files=files, data=data)
            
            # Check if the request was successful
            if response.status_code == 204 or response.status_code == 200:
                print(f"Successfully sent clip to Discord webhook: {file_path}")
            else:
                print(f"Error sending clip to Discord webhook: HTTP {response.status_code}")
                print(f"Response content: {response.text}")
    except Exception as e:
        print(f"Error sending clip to Discord webhook: {e}")

# Global variables for the observer and stop_event
global_observer = None
global_stop_event = None

def run(stop_event=None):
    """Main function to start the monitoring process that can be called from another module"""
    global global_observer, global_stop_event, CONFIG, WEBHOOK_URL, SHADOWPLAY_FOLDER, OUTPUT_FOLDER
    global MIN_SIZE_MB, MAX_SIZE_MB, TARGET_SIZE_MB, MAX_COMPRESSION_ATTEMPTS
    global CRF_MIN, CRF_MAX, CRF_STEP, EXTRACT_PRESET, COMPRESSION_PRESET
    global CLIP_DURATION, HIGH_QUALITY_CRF, CLOSE_THRESHOLD, MEDIUM_THRESHOLD, FAR_THRESHOLD
    
    # Set the stop event
    global_stop_event = stop_event if stop_event else threading.Event()
    
    # Load configuration
    CONFIG = load_config()
    if not CONFIG:
        print("Failed to load configuration. Exiting.")
        return False

    # Get webhook URL from config
    WEBHOOK_URL = CONFIG.get('WEBHOOK_URL', '')
    if not WEBHOOK_URL:
        print("No webhook URL configured. Please set it in the application settings.")
        return False

    # Other configuration values
    SHADOWPLAY_FOLDER = CONFIG.get('SHADOWPLAY_FOLDER', '')
    OUTPUT_FOLDER = CONFIG.get('OUTPUT_FOLDER', '')
    MIN_SIZE_MB = CONFIG.get('MIN_SIZE_MB', 8.0)
    MAX_SIZE_MB = CONFIG.get('MAX_SIZE_MB', 10.0)
    TARGET_SIZE_MB = CONFIG.get('TARGET_SIZE_MB', 9.0)
    MAX_COMPRESSION_ATTEMPTS = CONFIG.get('MAX_COMPRESSION_ATTEMPTS', 5)
    CRF_MIN = CONFIG.get('CRF_MIN', 1)
    CRF_MAX = CONFIG.get('CRF_MAX', 30)
    CRF_STEP = CONFIG.get('CRF_STEP', 1)
    EXTRACT_PRESET = CONFIG.get('EXTRACT_PRESET', 'fast')
    COMPRESSION_PRESET = CONFIG.get('COMPRESSION_PRESET', 'medium')
    CLIP_DURATION = CONFIG.get('CLIP_DURATION', 15)
    HIGH_QUALITY_CRF = CONFIG.get('HIGH_QUALITY_CRF', 18)
    CLOSE_THRESHOLD = CONFIG.get('CLOSE_THRESHOLD', 0.9)
    MEDIUM_THRESHOLD = CONFIG.get('MEDIUM_THRESHOLD', 0.75)
    FAR_THRESHOLD = CONFIG.get('FAR_THRESHOLD', 0.5)
    COMPRESSION_METHOD = CONFIG.get('COMPRESSION_METHOD', COMPRESSION_PROGRESSIVE)

    # Display loaded settings for debugging
    print(f"Loaded SHADOWPLAY_FOLDER: {SHADOWPLAY_FOLDER}")
    print(f"Loaded OUTPUT_FOLDER: {OUTPUT_FOLDER}")
    print(f"Loaded COMPRESSION_METHOD: {COMPRESSION_METHOD}")
    print(f"Loaded size settings: MIN={MIN_SIZE_MB}MB, MAX={MAX_SIZE_MB}MB, TARGET={TARGET_SIZE_MB}MB")
    
    # Make sure the folders exist
    if not os.path.isdir(SHADOWPLAY_FOLDER):
        print(f"ERROR: Shadowplay folder does not exist: {SHADOWPLAY_FOLDER}")
        return False
        
    if not os.path.isdir(OUTPUT_FOLDER):
        try:
            os.makedirs(OUTPUT_FOLDER, exist_ok=True)
            print(f"Created output folder: {OUTPUT_FOLDER}")
        except Exception as e:
            print(f"ERROR: Could not create output folder: {e}")
            return False
    
    event_handler = ClipHandler()
    observer = Observer()
    global_observer = observer
    
    # Create a list to store all the game folders we want to monitor
    monitor_folders = []
    
    # Add game-specific folders to monitor, excluding output folder
    try:
        for item in os.listdir(SHADOWPLAY_FOLDER):
            folder_path = os.path.join(SHADOWPLAY_FOLDER, item)
            # Make sure we're not monitoring the output folder or any subfolders
            if os.path.isdir(folder_path) and not folder_path.lower() == OUTPUT_FOLDER.lower():
                # Check if this is a game folder (not the output folder)
                if ntpath.basename(folder_path).lower() != "auto-clips":
                    monitor_folders.append(folder_path)
                    print(f"Monitoring game folder: {folder_path}")
        
        # Monitor each game folder individually (not recursively)
        for folder in monitor_folders:
            observer.schedule(event_handler, folder, recursive=False)
        
        # Also monitor the main Shadowplay folder for recordings saved directly there
        # but make sure not to monitor the output folder
        observer.schedule(event_handler, SHADOWPLAY_FOLDER, recursive=False)
        print(f"Monitoring main folder: {SHADOWPLAY_FOLDER}")
        
        observer.start()
        
        print("Clip processor is running! Monitoring for new recordings...")
        
        # Loop until stop_event is set
        while not global_stop_event.is_set():
            time.sleep(1)
            
        # Proper shutdown
        print("Stopping clip processor...")
        observer.stop()
        observer.join()
        print("Clip processor stopped.")
        return True
        
    except Exception as e:
        print(f"Error starting clip processor: {e}")
        traceback.print_exc()
        return False

def stop():
    """Stop the monitoring process"""
    global global_observer, global_stop_event
    
    if global_stop_event:
        global_stop_event.set()
    
    if global_observer:
        try:
            global_observer.stop()
            global_observer.join(timeout=1.0)
        except Exception as e:
            print(f"Error stopping observer: {e}")

if __name__ == "__main__":
    # If run directly, create our own stop_event
    stop_event = threading.Event()
    
    try:
        run(stop_event)
    except KeyboardInterrupt:
        print("\nStopping due to keyboard interrupt...")
        stop_event.set()