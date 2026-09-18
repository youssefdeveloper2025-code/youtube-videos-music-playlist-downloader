#!/usr/bin/env python3
"""
Download a local FFmpeg build for the source/web version when the host
does not already have ffmpeg and ffprobe available on PATH.
"""
from __future__ import annotations
import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
FFMPEG_ROOT = ROOT / ".ffmpeg"
BIN_DIR = FFMPEG_ROOT / "bin"
FFMPEG_EXE = BIN_DIR / "ffmpeg.exe"
FFPROBE_EXE = BIN_DIR / "ffprobe.exe"

DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
CHECKSUM_URL = DOWNLOAD_URL + ".sha256"

def on_path(name: str) -> Optional[str]:
    return shutil.which(name)

def valid_local_install() -> bool:
    return FFMPEG_EXE.is_file() and FFPROBE_EXE.is_file()

def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "YT-Downloader/1.1"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0") or 0)
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if total:
                print(f"\r  Downloading FFmpeg... {downloaded * 100 // total:3d}%", end="", flush=True)
    print()

def read_expected_sha256(checksum_file: Path) -> Optional[str]:
    text = checksum_file.read_text(encoding="utf-8", errors="replace").strip()
    for token in text.replace("=", " ").split():
        if len(token) == 64 and all(c in "0123456789abcdefABCDEF" for c in token):
            return token.lower()
    return None

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def safe_extract(zip_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if os.path.commonpath([str(destination), str(target)]) != str(destination):
                raise RuntimeError("The FFmpeg archive contains an unsafe path.")
        archive.extractall(destination)

def find_bin(root: Path) -> Optional[Path]:
    for ffmpeg in root.rglob("ffmpeg.exe"):
        candidate = ffmpeg.parent
        if (candidate / "ffprobe.exe").is_file():
            return candidate
    return None

def install() -> str:
    if valid_local_install():
        return str(BIN_DIR)
    if on_path("ffmpeg") and on_path("ffprobe"):
        return ""
    if sys.platform != "win32":
        raise RuntimeError(
            "FFmpeg is not installed. Install ffmpeg and ffprobe using your "
            "Linux/macOS package manager, then run the downloader again."
        )

    FFMPEG_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="yt-downloader-ffmpeg-") as temp:
        temp_dir = Path(temp)
        zip_path = temp_dir / "ffmpeg.zip"
        checksum_path = temp_dir / "ffmpeg.zip.sha256"
        extracted = temp_dir / "extracted"

        print("  FFmpeg was not found on this computer.")
        print("  Downloading the local FFmpeg runtime (first run only)...")
        download(DOWNLOAD_URL, zip_path)

        try:
            download(CHECKSUM_URL, checksum_path)
            expected = read_expected_sha256(checksum_path)
        except Exception:
            expected = None

        if expected and sha256(zip_path).lower() != expected.lower():
            raise RuntimeError("FFmpeg download failed checksum verification.")

        print("  Extracting FFmpeg...")
        extracted.mkdir(parents=True, exist_ok=True)
        safe_extract(zip_path, extracted)

        source_bin = find_bin(extracted)
        if source_bin is None:
            raise RuntimeError(
                "The FFmpeg archive was downloaded, but ffmpeg.exe/ffprobe.exe "
                "could not be found."
            )

        if FFMPEG_ROOT.exists():
            for child in FFMPEG_ROOT.iterdir():
                if child.name != ".gitkeep":
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()

        BIN_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_bin / "ffmpeg.exe", FFMPEG_EXE)
        shutil.copy2(source_bin / "ffprobe.exe", FFPROBE_EXE)

    if not valid_local_install():
        raise RuntimeError("FFmpeg installation did not complete correctly.")
    print("  FFmpeg is ready.")
    return str(BIN_DIR)

if __name__ == "__main__":
    try:
        install()
    except Exception as exc:
        print()
        print("ERROR: Could not install FFmpeg automatically.")
        print(f"       {exc}")
        print()
        sys.exit(1)
