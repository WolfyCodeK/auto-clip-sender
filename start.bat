@echo off
echo Starting Auto-Clip-Sender...
set PATH=%~dp0ffmpeg;%PATH%
auto-clip-sender.exe
pause