@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo YT Downloader v1.1 - Windows EXE Build
echo ========================================
echo.

if not exist ffmpeg.exe (
  echo ERROR: ffmpeg.exe was not found.
  echo Place a Windows FFmpeg binary named ffmpeg.exe beside this file.
  exit /b 1
)

python -m pip install --upgrade pip
python -m pip install --upgrade flask yt-dlp pyinstaller

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist YT-Downloader-v1.1.spec del /q YT-Downloader-v1.1.spec

python -m PyInstaller --noconfirm --clean --onefile --console --name "YT-Downloader-v1.1" --add-data "index.html;." --add-binary "ffmpeg.exe;." launcher.py

if errorlevel 1 (
  echo.
  echo BUILD FAILED.
  exit /b 1
)

echo.
echo BUILD COMPLETE:
echo dist\YT-Downloader-v1.1.exe
endlocal
