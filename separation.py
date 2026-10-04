#!/usr/bin/env python3
"""
Audio source separation helpers.

Uses Demucs to create:
- <title> - Vocals.mp3
- <title> - Instrumental.mp3

Demucs is installed lazily so normal MP3/MP4/WebM downloads do not pay the
PyTorch/Demucs installation cost unless separation is actually requested.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _pip_install(*packages):
    """Install runtime packages into the same Python environment as the app."""
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        *packages,
    ])


def ensure_demucs():
    """Install/repair Demucs and its NumPy runtime dependency on first use."""
    # Some Python builds/environments can have Demucs and PyTorch installed
    # while NumPy is missing. Demucs imports NumPy during startup, so check it
    # explicitly instead of assuming the Demucs install is complete.
    try:
        import numpy  # noqa: F401
    except ImportError:
        _pip_install("numpy")

    try:
        import demucs  # noqa: F401
    except ImportError:
        _pip_install("demucs")

    # Demucs can fall back to torchaudio/SoundFile when FFmpeg cannot decode
    # a source directly. Install SoundFile as part of the separation runtime.
    try:
        import soundfile  # noqa: F401
    except ImportError:
        _pip_install("soundfile")


def _run_ffmpeg(ffmpeg_location, args):
    """Run ffmpeg from the app's bundled/system FFmpeg location."""
    if ffmpeg_location:
        ffmpeg = Path(ffmpeg_location) / (
            "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        )
    else:
        ffmpeg = "ffmpeg"

    try:
        result = subprocess.run(
            [str(ffmpeg), "-y", *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            "FFmpeg failed while creating the separated MP3."
            + (f"\n\n{detail[-3000:]}" if detail else "")
        ) from exc


def _safe_title(value):
    title = str(value or "Track").strip()
    invalid = '<>:"/\\|?*'
    for char in invalid:
        title = title.replace(char, "_")
    return title.rstrip(". ") or "Track"


def separate_track(
    input_path,
    output_dir,
    title,
    quality="192",
    ffmpeg_location=None,
    artist="",
    album="",
    thumbnail_path=None,
    progress_callback=None,
):
    """
    Separate one downloaded audio file into vocals and accompaniment.

    Returns:
        (vocals_path, instrumental_path)
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ensure_demucs()

    if progress_callback:
        progress_callback("Running Demucs source separation...")

    work_dir = output_dir / ".separation"
    # Remove stale temporary output from a previous interrupted separation.
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Demucs writes:
    #   <work_dir>/htdemucs/<track>/vocals.mp3
    #   <work_dir>/htdemucs/<track>/no_vocals.mp3
    #
    # --two-stems=vocals produces the vocal stem plus a mixed accompaniment
    # stem, which is exactly what the downloader needs.
    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--mp3",
        "--mp3-bitrate",
        str(quality),
        "--two-stems=vocals",
        "-n",
        "htdemucs",
        "-o",
        str(work_dir),
        str(input_path),
    ]

    # Demucs invokes FFmpeg internally and only searches PATH for it.
    # The downloader may keep FFmpeg in its private permanent install, so make
    # that directory visible to Demucs without requiring a global FFmpeg install.
    env = os.environ.copy()
    if ffmpeg_location:
        ffmpeg_dir = str(Path(ffmpeg_location).resolve())
        ffmpeg_exe = Path(ffmpeg_dir) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        ffprobe_exe = Path(ffmpeg_dir) / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if not ffmpeg_exe.is_file() or not ffprobe_exe.is_file():
            raise RuntimeError(
                "The configured FFmpeg installation is incomplete: "
                f"{ffmpeg_dir}"
            )
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
        env["FFMPEG_BINARY"] = str(ffmpeg_exe)
        env["FFPROBE_BINARY"] = str(ffprobe_exe)

        # Verify the exact environment that will be inherited by Demucs.
        # Demucs itself invokes the literal commands "ffmpeg" and "ffprobe",
        # so merely checking that the files exist is not enough.
        probe_env = env.copy()
        probe_env["PATHEXT"] = probe_env.get("PATHEXT", ".COM;.EXE;.BAT;.CMD")
        resolved_ffmpeg = shutil.which("ffmpeg", path=probe_env["PATH"])
        resolved_ffprobe = shutil.which("ffprobe", path=probe_env["PATH"])
        if not resolved_ffmpeg or not resolved_ffprobe:
            raise RuntimeError(
                "FFmpeg was installed, but the Demucs process cannot resolve "
                "ffmpeg/ffprobe from PATH. "
                f"FFmpeg directory: {ffmpeg_dir}"
            )

        try:
            subprocess.run(
                [str(ffmpeg_exe), "-version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=probe_env,
            )
            subprocess.run(
                [str(ffprobe_exe), "-version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=probe_env,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "The bundled FFmpeg/ffprobe executables could not be started. "
                f"FFmpeg directory: {ffmpeg_dir}"
            ) from exc

        env = probe_env

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        output = (exc.stdout or "").strip()
        raise RuntimeError(
            "Demucs separation failed."
            + (f"\n\n{output[-4000:]}" if output else "")
        ) from exc

    demucs_track = work_dir / "htdemucs" / input_path.stem
    vocals_src = demucs_track / "vocals.mp3"
    instrumental_src = demucs_track / "no_vocals.mp3"

    if not vocals_src.exists() or not instrumental_src.exists():
        raise RuntimeError(
            "Demucs finished but did not produce both vocals and instrumental files."
        )

    base = _safe_title(title)
    vocals_path = output_dir / f"{base} - Vocals.mp3"
    instrumental_path = output_dir / f"{base} - Instrumental.mp3"

    # FFmpeg's MP3 muxer expects embedded artwork as an ID3 APIC image.
    # YouTube often supplies WebP thumbnails, so normalize the thumbnail to
    # one JPEG frame first. This avoids relying on the MP3 muxer to interpret
    # WebP directly and also handles animated WebP safely.
    cover_jpg = None

    def encode(src, dst, stem_name):
        if progress_callback:
            progress_callback(f"Creating {stem_name} MP3...")

        # FFmpeg requires every input (-i) to be declared before output
        # options such as -map. Keep the cover input beside the audio input,
        # then map both streams after all inputs have been opened.
        args = [
            "-i",
            str(src),
        ]

        if cover_jpg and cover_jpg.exists():
            args += [
                "-i",
                str(cover_jpg),
            ]

        args += [
            "-map",
            "0:a:0",
            "-c:a",
            "libmp3lame",
            "-b:a",
            f"{quality}k",
            "-id3v2_version",
            "3",
            "-metadata",
            f"title={title} - {stem_name}",
        ]

        if artist:
            args += ["-metadata", f"artist={artist}"]
        if album:
            args += ["-metadata", f"album={album}"]

        if cover_jpg and cover_jpg.exists():
            args += [
                "-map",
                "1:v:0",
                "-c:v",
                "copy",
                "-disposition:v:0",
                "attached_pic",
            ]

        args.append(str(dst))
        _run_ffmpeg(ffmpeg_location, args)

    try:
        if thumbnail_path and Path(thumbnail_path).exists():
            cover_jpg = work_dir / "cover.jpg"
            _run_ffmpeg(
                ffmpeg_location,
                [
                    "-i",
                    str(thumbnail_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(cover_jpg),
                ],
            )

        encode(vocals_src, vocals_path, "Vocals")
        encode(instrumental_src, instrumental_path, "Instrumental")
    finally:
        # Do not leave large temporary Demucs outputs in the download folder,
        # even if thumbnail conversion or either MP3 encode fails.
        shutil.rmtree(work_dir, ignore_errors=True)

    # The original downloaded source is no longer needed after both stems
    # have been encoded.
    try:
        input_path.unlink()
    except OSError:
        pass

    return vocals_path, instrumental_path
