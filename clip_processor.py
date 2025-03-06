import os
import time
import requests
import ffmpeg
import ffmpeg_helper  # Import our helper to patch ffmpeg-python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import ntpath
import math
from dotenv import load_dotenv
import sys
import importlib

# Force reload of config to ensure we're using the most recent version
if 'config' in sys.modules:
    importlib.reload(sys.modules['config'])
else:
    import config

# Add debugging to identify where settings are coming from
print(f"Bot is loading configuration from: {config.__file__}")

# Load environment variables from .env file - only for webhook URL
load_dotenv()

# Load folder paths directly from config.py
SHADOWPLAY_FOLDER = config.SHADOWPLAY_FOLDER
OUTPUT_FOLDER = config.OUTPUT_FOLDER

# Display loaded settings for debugging
print(f"Loaded SHADOWPLAY_FOLDER: {SHADOWPLAY_FOLDER}")
print(f"Loaded OUTPUT_FOLDER: {OUTPUT_FOLDER}")

# Get webhook URL from environment variables
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Verify webhook URL is available
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL not found in environment variables or .env file")

# Size configuration from config.py
MIN_SIZE_MB = config.MIN_SIZE_MB
MAX_SIZE_MB = config.MAX_SIZE_MB
MAX_COMPRESSION_ATTEMPTS = config.MAX_COMPRESSION_ATTEMPTS
TARGET_SIZE_MB = config.TARGET_SIZE_MB

# Display additional loaded settings for debugging
print(f"Loaded size settings: MIN={MIN_SIZE_MB}MB, MAX={MAX_SIZE_MB}MB, TARGET={TARGET_SIZE_MB}MB")

# Compression settings from config.py
CRF_MIN = config.CRF_MIN
CRF_MAX = config.CRF_MAX
CRF_STEP = config.CRF_STEP

# FFmpeg presets from config.py
EXTRACT_PRESET = config.EXTRACT_PRESET
COMPRESSION_PRESET = config.COMPRESSION_PRESET

# File processing settings from config.py
CLIP_DURATION = config.CLIP_DURATION
HIGH_QUALITY_CRF = config.HIGH_QUALITY_CRF

# Thresholds for adjustment sizing from config.py
CLOSE_THRESHOLD = config.CLOSE_THRESHOLD
MEDIUM_THRESHOLD = config.MEDIUM_THRESHOLD
FAR_THRESHOLD = config.FAR_THRESHOLD

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
        
        # Last attempt if needed - try one more value based on best results so far
        if results and not any(MIN_SIZE_MB <= r[1] <= MAX_SIZE_MB for r in results):
            # Sort by size
            results.sort(key=lambda r: r[1])
            
            # Find the closest results below and above our target range
            below_target = [r for r in results if r[1] < MIN_SIZE_MB]
            above_target = [r for r in results if r[1] > MAX_SIZE_MB]
            
            final_attempt_crf = None
            
            if below_target and above_target:
                # We have results on both sides of target range
                best_below = max(below_target, key=lambda r: r[1])
                best_above = min(above_target, key=lambda r: r[1])
                
                # Interpolate one more time with finer adjustment
                below_crf, below_size, _ = best_below
                above_crf, above_size, _ = best_above
                
                # Calculate interpolation point (weighted closer to the minimum size)
                weight = (MIN_SIZE_MB - below_size) / (above_size - below_size)
                final_attempt_crf = int(below_crf + (above_crf - below_crf) * weight)
                
                # Make sure it's a new value
                while any(r[0] == final_attempt_crf for r in results):
                    if final_attempt_crf < below_crf + (above_crf - below_crf) / 2:
                        final_attempt_crf += 1
                    else:
                        final_attempt_crf -= 1
                
                print(f"Final attempt with interpolated CRF={final_attempt_crf}")
                
            elif below_target:
                # All files too small, try higher quality
                best_below = max(below_target, key=lambda r: r[1])
                below_crf, below_size, _ = best_below
                
                # Adjust change amount based on how close we are to MIN_SIZE_MB
                if below_size >= MIN_SIZE_MB * CLOSE_THRESHOLD:  # Very close
                    # Very close - tiny adjustment
                    crf_change = CRF_STEP
                elif below_size >= MIN_SIZE_MB * MEDIUM_THRESHOLD:  # Close
                    # Close - small adjustment
                    crf_change = CRF_STEP * 2
                elif below_size >= MIN_SIZE_MB * FAR_THRESHOLD:  # Moderately close
                    # Moderately close - medium adjustment
                    crf_change = CRF_STEP * 3
                else:
                    # Far away - aggressive adjustment
                    size_ratio = MIN_SIZE_MB / below_size
                    crf_change = max(int(math.log2(size_ratio) * 6), CRF_STEP * 4)  # At least 4 steps
                
                final_attempt_crf = max(below_crf - crf_change, CRF_MIN)  # Lower floor to configured min
                
                # Skip if we've already tried this value
                if any(r[0] == final_attempt_crf for r in results):
                    # Try an even more extreme value if possible
                    if below_size >= MIN_SIZE_MB * MEDIUM_THRESHOLD and final_attempt_crf > CRF_MIN:
                        # We're close, try one more small step down
                        final_attempt_crf = max(final_attempt_crf - CRF_STEP, CRF_MIN)
                    elif final_attempt_crf > CRF_MIN:
                        final_attempt_crf = CRF_MIN  # Try maximum quality as last resort
                    else:
                        final_attempt_crf = None
                
                if final_attempt_crf:
                    print(f"Final attempt with decreased CRF={final_attempt_crf} (from {below_crf})")
                
            elif above_target:
                # All files too large, try more compression
                best_above = min(above_target, key=lambda r: r[1])
                above_crf, above_size, _ = best_above
                
                # Increase CRF by calculated amount
                size_ratio = above_size / MAX_SIZE_MB
                crf_change = max(int(math.log2(size_ratio) * 5), CRF_STEP * 2)  # Ensure at least 2 steps
                final_attempt_crf = min(above_crf + crf_change, CRF_MAX)  # Cap at configured max
                
                # Skip if we've already tried this value
                if any(r[0] == final_attempt_crf for r in results):
                    final_attempt_crf = None
                else:
                    print(f"Final attempt with increased CRF={final_attempt_crf} (from {above_crf})")
                
            # Try our final attempt if we have a new value
            if final_attempt_crf:
                try_crf(final_attempt_crf, "final")
        
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

if __name__ == "__main__":
    event_handler = ClipHandler()
    observer = Observer()
    
    # Create a list to store all the game folders we want to monitor
    monitor_folders = []
    
    # Add game-specific folders to monitor, excluding output folder
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
    
    try:
        print("Clip processor is running! Monitoring for new recordings...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()