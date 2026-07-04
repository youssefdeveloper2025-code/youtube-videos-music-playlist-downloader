@echo off
title YT Downloader
echo.
echo   Installing / checking dependencies...
pip install flask yt-dlp --quiet 2>nul

echo   Starting YT Downloader...
echo.

:: Start browser after 3 seconds (gives Flask time to boot)
powershell -Command "Start-Sleep 3; Start-Process 'http://localhost:5000'" &

:: Start the Flask server
python server.py

pause