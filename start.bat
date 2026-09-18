@echo off
setlocal
title YT Downloader
cd /d "%~dp0"

:: Find a usable Python installation. Prefer the Windows Python Launcher because
:: it can find installed Python versions even when python.exe is not on PATH.
:detect_python
set "PYTHON_CMD="
set "PYTHON_ARGS="

where py.exe >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; print(sys.executable)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py"
        set "PYTHON_ARGS=-3"
    )
)

:: If the launcher is unavailable, check standard per-user and system installs.
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python39\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python39\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python38\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python38\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python314\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python314\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python313\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python313\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python312\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python312\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python311\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python311\python.exe"
if not defined PYTHON_CMD if exist "%ProgramFiles%\Python310\python.exe" set "PYTHON_CMD=%ProgramFiles%\Python310\python.exe"

if not defined PYTHON_CMD (
    echo.
    echo   Python 3 was not found.
    echo   Checking the official Python website for the current release...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_python.ps1" -Mode InstallIfMissing
    if errorlevel 2 goto detect_python
    echo.
    echo   Python is required to run the HTML/Web version.
    echo   No installation was completed.
    echo.
    pause
    exit /b 1
)

set "PYTHON_VERSION="
for /f "delims=" %%V in ('"%PYTHON_CMD%" %PYTHON_ARGS% -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"') do set "PYTHON_VERSION=%%V"

echo.
echo   Using Python %PYTHON_VERSION%
echo   Checking for Python updates...
:: This only reads python.org. An update is never installed unless the person
:: at the computer explicitly confirms the prompt.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_python.ps1" -Mode CheckUpdate -CurrentVersion "%PYTHON_VERSION%"
if errorlevel 2 goto detect_python

echo   Checking Python dependencies...
"%PYTHON_CMD%" %PYTHON_ARGS% -m pip install flask yt-dlp --quiet
if errorlevel 1 (
    echo.
    echo   ERROR: Could not install Python dependencies.
    echo   Make sure Python and pip are available.
    pause
    exit /b 1
)

echo   Checking FFmpeg...
"%PYTHON_CMD%" %PYTHON_ARGS% setup_ffmpeg.py
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
"%PYTHON_CMD%" %PYTHON_ARGS% server.py

pause
