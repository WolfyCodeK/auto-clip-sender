"""
Default configuration settings for the auto-clip-sender application.
Do not modify this file directly. Changes to settings should be made in config.py.
"""

# Folder configuration 
SHADOWPLAY_FOLDER = "C:/Users/put-name-here/Documents/Shadowplay Recordings"
OUTPUT_FOLDER = "C:/Users/put-name-here/Documents/Shadowplay Recordings/auto-clips"

# Size limits (MB)
MIN_SIZE_MB = 8.0      # Minimum target size (we want files to be at least this large)
MAX_SIZE_MB = 10.0     # Maximum size allowed by Discord
TARGET_SIZE_MB = 9.0   # Target size in the middle of our range
MAX_COMPRESSION_ATTEMPTS = 5  # Maximum number of compression iterations

# Compression settings
CRF_MIN = 1          # Minimum CRF value (highest quality)
CRF_MAX = 30         # Maximum CRF value (lowest quality)
CRF_STEP = 1         # Step size for CRF adjustments

# FFmpeg presets
# Options: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
EXTRACT_PRESET = "fast"
COMPRESSION_PRESET = "medium"

# File processing settings
CLIP_DURATION = 15       # Duration in seconds to extract from the end of videos
HIGH_QUALITY_CRF = 18    # CRF value for initial high-quality extraction

# Thresholds for adjustment size logic
CLOSE_THRESHOLD = 0.9    # 90% of target
MEDIUM_THRESHOLD = 0.75  # 75% of target
FAR_THRESHOLD = 0.5      # 50% of target 
