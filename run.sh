#!/bin/bash
echo "Installing FFmpeg..."
curl -L https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz | tar -xJ
export PATH=$PATH:$(pwd)/ffmpeg-master-latest-linux64-gpl/bin

echo "Starting Bot..."
python main.py
