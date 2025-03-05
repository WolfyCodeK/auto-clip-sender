# Auto-Clip-Sender

A Python application that automatically processes NVIDIA Shadowplay recordings, trimming and compressing them to optimal sizes before sending them to you via Discord.

## Executable Version

Google Drive Link:

https://drive.google.com/file/d/1zzClBQsXkF50f0BUXjc-CITzKw6WnFNH/view?usp=sharing

## Overview

Auto-Clip-Sender monitors your Shadowplay recording folders for new gameplay videos. When it detects a new recording, it:

1. Extracts the last 15 seconds of the video
2. Uses an intelligent compression algorithm to target a file size between 8-10MB
3. Sends the compressed clip to you via Discord DM

Perfect for sharing your best gaming moments with friends without manually editing and sending them!

## Features

- **Automatic Processing**: No manual intervention needed - just save your Shadowplay recordings
- **Smart Compression**: Adaptive algorithm targets 8-10MB file size for Discord compatibility
- **Game-Based Organization**: Automatically recognizes game folders
- **High Quality Preservation**: Uses intelligent CRF-based compression to maintain visual quality
- **Secure Configuration**: Keeps sensitive information in environment variables

## Requirements

- Python 3.8+
- FFmpeg (must be installed and accessible in your system PATH)
- NVIDIA Shadowplay (or compatible recording software)
- Discord Bot Token
- Discord User ID

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/auto-clip-sender.git
   cd auto-clip-sender
   ```

2. Install required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Discord credentials (see Configuration section)

4. Update the `config.py` file with your folder paths and preferences

## Configuration

### Environment Variables (`.env`)

Create a `.env` file in the project root with the following:

```
# Discord configuration
BOT_TOKEN=your_discord_bot_token_here
USER_ID=your_discord_user_id_here

# Optional: Override configuration paths if needed
SHADOWPLAY_FOLDER=D:/YOUR/SHADOWPLAY/FOLDER
OUTPUT_FOLDER=D:/YOUR/OUTPUT/FOLDER
```

> **Note**: Never commit your `.env` file to version control! It contains sensitive information.

### Application Settings (`config.py`)

The `config.py` file contains non-sensitive configuration settings:

```python
# Folder configuration (defaults, can be overridden in .env)
SHADOWPLAY_FOLDER = "C:/Users/put-name-here/Documents/Shadowplay Recordings"
OUTPUT_FOLDER = "C:/Users/put-name-here/Documents/Shadowplay Recordings/auto-clips"

# Size limits (MB)
MIN_SIZE_MB = 8      # Minimum target size
MAX_SIZE_MB = 10     # Maximum size allowed by Discord
TARGET_SIZE_MB = 9   # Target size in the middle of our range
MAX_COMPRESSION_ATTEMPTS = 5  # Maximum number of compression iterations

# Compression settings
CRF_MIN = 1          # Minimum CRF value (highest quality)
CRF_MAX = 30         # Maximum CRF value (lowest quality)
CRF_STEP = 1         # Step size for CRF adjustments

# FFmpeg presets
EXTRACT_PRESET = "fast"
COMPRESSION_PRESET = "medium"

# File processing settings
CLIP_DURATION = 15       # Duration in seconds to extract from the end of videos
HIGH_QUALITY_CRF = 18    # CRF value for initial high-quality extraction

# Thresholds for adjustment size logic
CLOSE_THRESHOLD = 0.9    # 90% of target
MEDIUM_THRESHOLD = 0.75  # 75% of target
FAR_THRESHOLD = 0.5      # 50% of target
```

## Getting a Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a New Application
3. Navigate to the "Bot" tab and click "Add Bot"
4. Click "Reset Token" to reveal your bot token
5. Copy the token to your `.env` file

## Inviting Your Bot to a Server

1. In the [Discord Developer Portal](https://discord.com/developers/applications), select your application
2. Navigate to the "OAuth2" tab and select "URL Generator"
3. Select the following scopes:
   - `bot`
4. Select the following bot permissions:
   - "Send Messages"
   - "Attach Files"
   - "Read Message History"
5. Copy the generated URL at the bottom of the page
6. Paste the URL in your browser and select the server you want to add the bot to
7. Complete the authorization process

> **Note**: The bot only needs to send direct messages to you, but these permissions are required for the bot to function correctly.

## Finding Your Discord User ID

1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click on your username and click "Copy ID"
3. Paste this ID in your `.env` file

## Running the Application

Start the bot with:

```
python bot.py
```

The bot will:
1. Log in to Discord using your bot token
2. Start monitoring your Shadowplay folders for new recordings
3. Process and send clips automatically when new recordings are detected

## How the Compression System Works

The application uses a sophisticated binary search style compression system:

1. **Initial Extraction**: Extracts the last 15 seconds of the video at high quality (CRF 18)
2. **Initial Testing Phase**: Makes an initial compression attempt at a moderate CRF value (23)
3. **Binary Search Strategy**: 
   - Makes dramatic jumps in compression levels based on initial results
   - If first attempt is too large/small, jumps significantly in the opposite direction
   - Establishes upper and lower bounds for optimal compression value
   - Efficiently narrows down to the optimal CRF value using binary search principles
4. **Smart Interpolation**: Uses size ratio and logarithmic interpolation to account for CRF's non-linear effect on file size
5. **Final Fine-Tuning**: If needed, performs additional fine-tuning to reach the target size range
6. **Result Selection**: Selects the file closest to the target size (9MB) from all attempts

This binary search approach is significantly more efficient than testing CRF values sequentially, allowing the system to quickly converge on the optimal compression level with fewer attempts, even with files that vary greatly in compressibility.

## Troubleshooting

### FFmpeg Not Found

Ensure FFmpeg is installed and added to your system PATH. Download it from [ffmpeg.org](https://ffmpeg.org/download.html).

### Permission Errors

If you see permission errors when the bot tries to delete files, it may be because:
- The files are still being used by another process
- The bot doesn't have write permissions for the folders

### Bot Not Sending Messages

Ensure your bot:
- Has been invited to your server with proper permissions
- Has the "message content" intent enabled in the Discord Developer Portal

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Uses [FFmpeg](https://ffmpeg.org/) for video processing
- Uses [discord.py](https://discordpy.readthedocs.io/) for Discord integration
- Uses [watchdog](https://pypi.org/project/watchdog/) for file monitoring 