#!/bin/bash
echo "Installing dependencies..."
pip install flask yt-dlp --quiet
echo ""
echo "Starting YT Downloader..."
echo "Open your browser at: http://localhost:5000"
echo ""
python3 server.py