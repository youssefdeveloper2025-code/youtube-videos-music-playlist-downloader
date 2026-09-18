@echo off
setlocal
title YT Downloader
cd /d "%~dp0"

:: Find a usable Python installation.
:: Prefer the Windows Python Launcher because it can find installed Python
:: versions even when python.exe is not on PATH.
set "PYTHON_CMD="

where py.exe >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; print(sys.executable)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

:: If the launcher is unavailable, check common per-user/system installs.
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python313\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python313\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python312\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python312\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python311\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python311\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python310\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python310\python.exe"

if not defined PYTHON_CMD (
    echo.
    echo   ERROR: Python 3 was not found.
    echo.
    echo   Install Python 3.8 or newer from:
    echo   https://www.python.org/downloads/windows/
    echo.
    echo   During installation, enable "Add python.exe to PATH".
    echo   Then run start.bat again.
    echo.
    pause
    exit /b 1
)

echo.
echo   Using Python: %PYTHON_CMD%
echo   Checking Python dependencies...
%PYTHON_CMD% -m pip install flask yt-dlp --quiet
if errorlevel 1 (
    echo.
    echo   ERROR: Could not install Python dependencies.
    echo   Make sure Python and pip are available.
    pause
    exit /b 1
)

echo   Checking FFmpeg...
%PYTHON_CMD% setup_ffmpeg.py
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
%PYTHON_CMD% server.py

pause
