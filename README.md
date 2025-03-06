# ![Auto-Clip-Sender Logo](icons/32x32.ico) Auto-Clip-Sender

A desktop application that automatically processes NVIDIA Shadowplay recordings, trimming and compressing them to optimal sizes before sending them to Discord via webhooks.


Icon source: www.clipartmax.com

## Download

Get the latest version:

[Download Auto-Clip-Sender (Google Drive)](https://drive.google.com/file/d/1IBpbzwL30b9GBqaXevnXt0F77-_yjr5i/view?usp=sharing)

## Overview

Auto-Clip-Sender monitors your Shadowplay recording folders for new gameplay videos. When it detects a new recording, it:

1. Extracts the last 15 seconds of the video (customizable)
2. Uses an intelligent compression algorithm to target a file size between 8-10MB (Discord-friendly)
3. Sends the compressed clip to Discord via a webhook

Perfect for sharing your best gaming moments with friends without manually editing and sending them!

## System Requirements

- Windows 10 or newer
- NVIDIA Shadowplay (or compatible recording software)
- Discord server with webhook access

## Quick Start Guide

1. **Download and Extract**: 
   - Download the application from the link above
   - Extract the ZIP file to a location of your choice
   - Run `Auto-Clip-Sender.exe`

2. **Configure Settings**:
   - **Folders Tab**: Set your Shadowplay recordings folder and output folder for processed clips
   - **Discord Tab**: Enter your Discord webhook URL
   - Click "Save Configuration"

3. **Start Monitoring**:
   - Click "Start Monitoring" to begin watching for new recordings
   - The application will automatically process and send new clips as they are created

## Creating a Discord Webhook

1. Open Discord and go to the server where you want clips to be sent
2. Go to Server Settings > Integrations > Webhooks
3. Click "New Webhook" and give it a name (e.g., "Auto Clip Sender")
4. Choose the channel where clips should be sent
5. Click "Copy Webhook URL"
6. Paste this URL in the "Discord Webhook URL" field in the application

## Application Features

### Main Interface

- **Start Monitoring**: Begins watching for new recordings
- **Stop Monitoring**: Pauses the monitoring process
- **Save Configuration**: Saves your current settings
- **Restore All Defaults**: Resets all settings to default values
- **Terminal Output**: Shows live status and diagnostic information

### Configuration Tabs

1. **Folders**
   - Set Shadowplay recordings folder (where your gameplay videos are saved)
   - Set output folder for processed clips

2. **Size Limits** 
   - Minimum Size (MB): Smallest acceptable file size (default: 8MB)
   - Maximum Size (MB): Largest acceptable file size (default: 10MB)
   - Target Size (MB): Ideal file size (default: 9MB)
   - Max Compression Attempts: Number of tries to reach target size

3. **Compression**
   - CRF settings for video quality
   - Clip duration in seconds (how much to extract from the end of each recording)

4. **FFmpeg**
   - Presets for balancing encoding speed and efficiency

5. **Discord**
   - Webhook URL configuration
   - Test button to verify your webhook works

## How It Works

The application uses a sophisticated binary search compression system:

1. **Initial Extraction**: Extracts the last 15 seconds of the video at high quality (CRF 18)
2. **Smart Compression**: Uses a binary search algorithm to find the optimal compression level
3. **Quality Preservation**: Intelligently balances file size and video quality
4. **Automatic Delivery**: Sends the clip directly to your Discord server

## Troubleshooting

### Permission Errors

If the application cannot access or delete files:
- Make sure the application has write permissions to both input and output folders
- Try running the application as administrator

### Webhook Not Working

If clips aren't being sent to Discord:
- Use the "Test Webhook" button to verify your webhook URL
- Ensure the webhook has permission to send messages to the channel
- Check if the file size exceeds Discord's limit (8MB for normal users, 50MB for Nitro)

### Application Won't Start

If the application doesn't start:
- Make sure you extracted all files from the ZIP
- Try running as administrator
- Check if your antivirus is blocking the application

## For Developers

If you're interested in modifying the source code or building from source:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) and place the executables in a folder named `ffmpeg` in the project directory
4. Make your changes to the source code
5. Build with PyInstaller: `python build.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Uses [FFmpeg](https://ffmpeg.org/) for video processing (bundled with the application)
- Uses [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) for the GUI
- Uses [requests](https://requests.readthedocs.io/) for webhook integration
- Uses [watchdog](https://pypi.org/project/watchdog/) for file monitoring 
