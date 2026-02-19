#!/bin/bash

echo "===================================="
echo "Starting Blaze Music Bot"
echo "===================================="
echo "Checking FFmpeg installation..."
ffmpeg -version

echo "===================================="
echo "Installing/Updating Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "===================================="
echo "Starting bot..."
python main.py
