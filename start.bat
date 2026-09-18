@echo off
setlocal
title YT Downloader
cd /d "%~dp0"

echo.
echo   Checking Python dependencies...
python -m pip install flask yt-dlp --quiet
if errorlevel 1 (
    echo.
    echo   ERROR: Could not install Python dependencies.
    echo   Make sure Python and pip are installed and available in PATH.
    pause
    exit /b 1
)

echo   Checking FFmpeg...
python setup_ffmpeg.py
if errorlevel 1 (
    echo.
    echo   ERROR: FFmpeg setup failed. The downloader cannot process MP3
    echo   files or merge separate video/audio streams without FFmpeg.
    pause
    exit /b 1
)

echo   Starting YT Downloader...
echo.

:: Start browser after 3 seconds (gives Flask time to boot)
powershell -NoProfile -Command "Start-Sleep 3; Start-Process 'http://localhost:5000'" &

:: Start the Flask server
python server.py

pause
