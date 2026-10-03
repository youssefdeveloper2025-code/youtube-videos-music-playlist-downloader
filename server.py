#!/usr/bin/env python3
"""
YT Web Downloader — Flask backend
Uses yt-dlp + ffmpeg.
Supports public videos/playlists, browser-login cookies, and optional
Demucs vocal/instrumental separation for MP3 downloads.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import uuid
from pathlib import Path

try:
    from setup_ffmpeg import install as ensure_ffmpeg
except ImportError:
    ensure_ffmpeg = None

try:
    from separation import separate_track
except ImportError:
    separate_track = None


# ── dependencies ──────────────────────────────────────────────────────────────

def ensure_package(import_name, package_name):
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            package_name,
        ])


ensure_package("flask", "flask")
ensure_package("yt_dlp", "yt-dlp")

from flask import Flask, Response, jsonify, request, send_from_directory
import yt_dlp

app = Flask(__name__, static_folder=".", static_url_path="")

JOBS = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _event(data):
    return f"data: {json.dumps(data)}\n\n"


def _send(job, data):
    job["queue"].put(data)


def _inject_separation_ui(html):
    """
    Add the separation controls without requiring a second HTML template.
    The existing UI remains the source of truth for all normal download
    controls; this only adds the optional MP3 stem-separation control.
    """
    marker = "  <!-- save path -->"
    card = r"""
  <!-- optional vocal/instrumental separation -->
  <div class="card" id="separation-card" style="display:none">
    <div class="card-label">04 &nbsp; Audio Separation</div>
    <div style="display:flex;align-items:center;gap:12px">
      <div id="separation-toggle"
           onclick="toggleSeparation()"
           style="width:42px;height:24px;border-radius:999px;background:var(--s3);
                  border:1px solid var(--border2);cursor:pointer;position:relative;
                  transition:all .2s;flex-shrink:0">
        <span id="separation-knob"
              style="position:absolute;left:3px;top:3px;width:16px;height:16px;
                     border-radius:50%;background:var(--grey);
                     transition:all .2s"></span>
      </div>
      <div>
        <div style="font-size:.82rem;font-weight:600">Separate vocals and instrumental</div>
        <div style="font-family:var(--mono);font-size:.66rem;color:var(--grey);
                    margin-top:3px">
          Creates two MP3 files using Demucs source separation.
        </div>
      </div>
    </div>
  </div>
"""
    if marker in html and 'id="separation-card"' not in html:
        html = html.replace(marker, card + "
" + marker, 1)

    script = r"""
<script>
(function () {
  let separationEnabled = false;

  function updateSeparationVisibility() {
    const card = document.getElementById('separation-card');
    if (!card) return;
    card.style.display = (typeof currentFmt !== 'undefined' && currentFmt === 'mp3')
      ? 'block' : 'none';

    if (typeof currentFmt !== 'undefined' && currentFmt !== 'mp3') {
      separationEnabled = false;
      updateSeparationToggle();
    }
  }

  window.toggleSeparation = function () {
    separationEnabled = !separationEnabled;
    updateSeparationToggle();
  };

  function updateSeparationToggle() {
    const toggle = document.getElementById('separation-toggle');
    const knob = document.getElementById('separation-knob');
    if (!toggle || !knob) return;

    toggle.style.background = separationEnabled ? 'var(--red)' : 'var(--s3)';
    toggle.style.borderColor = separationEnabled ? 'var(--red)' : 'var(--border2)';
    knob.style.left = separationEnabled ? '21px' : '3px';
    knob.style.background = separationEnabled ? '#fff' : 'var(--grey)';
  }

  // The original setFmt function remains responsible for all existing
  // format/quality behavior; this wrapper only updates the new control.
  if (typeof window.setFmt === 'function') {
    const originalSetFmt = window.setFmt;
    window.setFmt = function (el) {
      originalSetFmt(el);
      updateSeparationVisibility();
    };
  }

  // The existing startDownload() already sends its normal payload.
  // Add the one optional field transparently so no existing UI logic changes.
  const originalFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';

    if (url === '/api/start' && init && typeof init.body === 'string') {
      try {
        const payload = JSON.parse(init.body);
        payload.separate = separationEnabled &&
          payload.format === 'mp3';
        init = Object.assign({}, init, {
          body: JSON.stringify(payload)
        });
      } catch (_) {
        // Keep the original request untouched if it is not JSON.
      }
    }

    return originalFetch(input, init);
  };

  updateSeparationVisibility();
  updateSeparationToggle();
})();
</script>
"""
    if "</body>" in html and "separationEnabled" not in html:
        html = html.replace("</body>", script + "
</body>", 1)

    return html


def _run_download(
    job_id,
    url,
    fmt,
    quality,
    outdir,
    cookie_browser="",
    separate=False,
):
    job = JOBS[job_id]

    state = {
        "track": 0,
        "total": 0,
        "current_title": "",
        "downloaded": [],
    }

    outdir = os.path.abspath(os.path.expanduser(outdir))
    Path(outdir).mkdir(parents=True, exist_ok=True)

    playlist_template = os.path.join(
        outdir,
        "%(playlist_index)s - %(title)s.%(ext)s",
    )

    single_template = os.path.join(
        outdir,
        "%(title)s.%(ext)s",
    )

    def progress_hook(d):
        info = d.get("info_dict") or {}

        playlist_count = (
            info.get("n_entries")
            or info.get("playlist_count")
            or 0
        )

        if playlist_count:
            state["total"] = playlist_count

        title = info.get("title") or state["current_title"]

        if title:
            state["current_title"] = title

        if d.get("status") == "downloading":
            total = (
                d.get("total_bytes")
                or d.get("total_bytes_estimate")
                or 0
            )

            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0

            pct = round(downloaded / total * 100, 1) if total else 0

            track = (
                f"{state['track'] + 1}/{state['total']}"
                if state["total"]
                else ""
            )

            _send(job, {
                "type": "progress",
                "pct": pct,
                "speed": round(speed / 1024, 1) if speed else 0,
                "eta": eta,
                "dled": round(downloaded / 1024 / 1024, 2),
                "total": round(total / 1024 / 1024, 2) if total else 0,
                "track": track,
                "track_title": state["current_title"],
            })

        elif d.get("status") == "finished":
            filename = d.get("filename") or ""

            if filename:
                state["track"] += 1

                # Separation mode deliberately downloads the source audio
                # without yt-dlp's MP3 postprocessors. Keep the exact source
                # filename so Demucs can process it after yt-dlp finishes.
                if separate and fmt == "mp3":
                    state["downloaded"].append({
                        "filename": filename,
                        "title": info.get("title") or state["current_title"],
                        "info": dict(info),
                    })

            title = info.get("title") or state["current_title"]
            state["current_title"] = title

            if separate and fmt == "mp3":
                msg = "Downloaded audio — preparing source separation..."
            elif fmt == "mp3":
                msg = "Processing audio + embedding cover art..."
            else:
                msg = "Processing..."

            if state["total"]:
                msg = f"[{state['track']}/{state['total']}] " + msg

            _send(job, {
                "type": "processing",
                "msg": msg,
                "track_title": title,
                "track": (
                    f"{state['track']}/{state['total']}"
                    if state["total"]
                    else ""
                ),
            })

        elif d.get("status") == "error":
            title = info.get("title") or "unknown track"
            _send(job, {
                "type": "skipped",
                "msg": f"Skipped: {title}",
            })

    # ── local/system FFmpeg detection ─────────────────────────────────────────

    ffmpeg_location = None

    if ensure_ffmpeg:
        try:
            ffmpeg_location = ensure_ffmpeg() or None
        except Exception as exc:
            _send(job, {
                "type": "error",
                "msg": f"FFmpeg is required for this download. {exc}",
            })
            return

    COMMON = {
        "ignoreerrors": False,
        "retries": 10,
        "fragment_retries": 10,
        "sleep_interval": 1,
        "sleep_interval_requests": 1,
        "outtmpl": single_template,
        "progress_hooks": [progress_hook],
        "quiet": False,
        "no_warnings": False,
        "continuedl": True,
        "nopart": False,
        "noplaylist": False,
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "web",
                ],
            },
        },
    }

    if ffmpeg_location:
        COMMON["ffmpeg_location"] = ffmpeg_location

    if cookie_browser:
        browser = cookie_browser.strip().lower()

        valid_browsers = {
            "chrome",
            "edge",
            "firefox",
            "brave",
            "opera",
            "vivaldi",
        }

        if browser in valid_browsers:
            COMMON["cookiesfrombrowser"] = (browser,)

    is_playlist = "list=" in url.lower()
    output_template = playlist_template if is_playlist else single_template

    # ── MP3 ───────────────────────────────────────────────────────────────────

    if fmt == "mp3":
        if separate:
            # Keep the original downloaded audio intact for Demucs.
            ydl_opts = {
                **COMMON,
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "writethumbnail": True,
                "postprocessors": [],
            }
        else:
            ydl_opts = {
                **COMMON,
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "writethumbnail": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": quality,
                    },
                    {
                        "key": "FFmpegMetadata",
                        "add_metadata": True,
                    },
                    {
                        "key": "FFmpegThumbnailsConvertor",
                        "format": "jpg",
                    },
                    {
                        "key": "EmbedThumbnail",
                        "already_have_thumbnail": False,
                    },
                ],
            }

    # ── MP4 / WebM ────────────────────────────────────────────────────────────

    else:
        if quality == "best":
            fmt_string = "bestvideo+bestaudio/best"
        else:
            fmt_string = (
                f"bestvideo[height<={quality}]+bestaudio/"
                f"best[height<={quality}]"
            )

        merge_ext = "webm" if fmt == "webm" else "mp4"

        ydl_opts = {
            **COMMON,
            "format": fmt_string,
            "outtmpl": output_template,
            "merge_output_format": merge_ext,
        }

    # ── download ──────────────────────────────────────────────────────────────

    try:
        _send(job, {
            "type": "processing",
            "msg": (
                "Connecting to YouTube..."
                + (" Separation enabled." if separate and fmt == "mp3" else "")
            ),
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            _send(job, {
                "type": "error",
                "msg": "yt-dlp returned no media information.",
            })
            return

        if separate and fmt == "mp3":
            if separate_track is None:
                raise RuntimeError(
                    "The separation module could not be loaded."
                )

            tracks = state["downloaded"]

            if not tracks:
                raise RuntimeError(
                    "No downloaded audio files were available for separation."
                )

            total = len(tracks)

            for index, item in enumerate(tracks, start=1):
                title = item["title"] or "Track"
                input_path = Path(item["filename"])

                # A thumbnail written by yt-dlp normally has the same base
                # filename as the source audio. Try the common image formats.
                thumbnail = None
                for ext in (".jpg", ".jpeg", ".png", ".webp"):
                    candidate = input_path.with_suffix(ext)
                    if candidate.exists():
                        thumbnail = candidate
                        break

                metadata = item["info"]

                def separation_progress(message, index=index, total=total):
                    _send(job, {
                        "type": "processing",
                        "msg": f"[{index}/{total}] {message}",
                        "track_title": title,
                        "track": f"{index}/{total}",
                    })

                separation_progress("Separating vocals and instrumental...")

                separate_track(
                    input_path=input_path,
                    output_dir=outdir,
                    title=title,
                    quality=quality,
                    ffmpeg_location=ffmpeg_location,
                    artist=metadata.get("artist")
                    or metadata.get("uploader")
                    or "",
                    album=metadata.get("album") or "",
                    thumbnail_path=thumbnail,
                    progress_callback=separation_progress,
                )

                if thumbnail:
                    try:
                        thumbnail.unlink()
                    except OSError:
                        pass

        # Playlist result
        if info.get("_type") == "playlist":
            entries = [
                e for e in (info.get("entries") or [])
                if e
            ]

            successful = len(entries)

            playlist_title = (
                info.get("title")
                or "Playlist"
            )

            if successful == 0:
                _send(job, {
                    "type": "error",
                    "msg": (
                        "The playlist was found, but no songs "
                        "could be downloaded."
                    ),
                })
                return

            _send(job, {
                "type": "done",
                "title": (
                    f"{playlist_title} "
                    f"({successful} tracks)"
                ),
                "fmt": fmt,
                "outdir": outdir,
                "track_count": successful,
                "separated": bool(separate and fmt == "mp3"),
            })

        else:
            title = (
                info.get("title")
                or info.get("id")
                or "Download"
            )

            _send(job, {
                "type": "done",
                "title": title,
                "fmt": fmt,
                "outdir": outdir,
                "track_count": 1,
                "separated": bool(separate and fmt == "mp3"),
            })

    except Exception as exc:
        error_text = str(exc)

        if (
            "cookies" in error_text.lower()
            or "cookie" in error_text.lower()
        ):
            error_text = (
                "Browser login cookies could not be read.\n\n"
                f"{error_text}\n\n"
                "Try closing the selected browser completely "
                "and downloading again."
            )

        _send(job, {
            "type": "error",
            "msg": error_text,
        })


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    index_path = Path("index.html")

    try:
        html = index_path.read_text(encoding="utf-8")
        return Response(
            _inject_separation_ui(html),
            mimetype="text/html",
        )
    except Exception:
        return send_from_directory(".", "index.html")


@app.route("/api/start", methods=["POST"])
def start():
    data = request.get_json(force=True) or {}

    url = data.get("url", "").strip()
    fmt = data.get("format", "mp4").lower()
    quality = data.get("quality", "best")

    outdir = os.path.expanduser(
        data.get("outdir", "~/Downloads")
    )

    cookie_browser = data.get(
        "cookie_browser",
        "",
    ).strip().lower()

    separate = bool(data.get("separate", False))

    if not url:
        return jsonify({
            "error": "No URL provided",
        }), 400

    if fmt not in ("mp3", "mp4", "webm"):
        return jsonify({
            "error": "Invalid format",
        }), 400

    if separate and fmt != "mp3":
        return jsonify({
            "error": "Audio separation is only available for MP3 downloads.",
        }), 400

    if separate and quality not in ("128", "192", "320"):
        return jsonify({
            "error": "Invalid MP3 separation quality.",
        }), 400

    try:
        Path(outdir).mkdir(
            parents=True,
            exist_ok=True,
        )
    except Exception as exc:
        return jsonify({
            "error": (
                "Could not create output folder: "
                + str(exc)
            ),
        }), 400

    job_id = str(uuid.uuid4())

    JOBS[job_id] = {
        "queue": queue.Queue(),
    }

    thread = threading.Thread(
        target=_run_download,
        args=(
            job_id,
            url,
            fmt,
            quality,
            outdir,
            cookie_browser,
            separate,
        ),
        daemon=True,
    )

    thread.start()

    return jsonify({
        "job_id": job_id,
    })


@app.route("/api/progress/<job_id>")
def progress(job_id):
    if job_id not in JOBS:
        return jsonify({
            "error": "Unknown job",
        }), 404

    def generate():
        q = JOBS[job_id]["queue"]

        while True:
            try:
                event = q.get(timeout=60)

                yield _event(event)

                if event["type"] in ("done", "error"):
                    break

            except queue.Empty:
                yield _event({
                    "type": "ping",
                })

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/info", methods=["POST"])
def info():
    data = request.get_json(force=True) or {}

    url = data.get("url", "").strip()

    cookie_browser = data.get(
        "cookie_browser",
        "",
    ).strip().lower()

    if not url:
        return jsonify({
            "error": "No URL",
        }), 400

    opts = {
        "quiet": False,
        "no_warnings": False,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "ignoreerrors": False,
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "web",
                ],
            },
        },
    }

    if cookie_browser:
        opts["cookiesfrombrowser"] = (
            cookie_browser,
        )

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(
                url,
                download=False,
            )

        if not meta:
            return jsonify({
                "error": "Could not extract video information.",
            }), 400

        count = None

        if meta.get("_type") == "playlist":
            entries = meta.get("entries") or []
            count = len([
                e for e in entries
                if e
            ])

        return jsonify({
            "title": meta.get("title", ""),
            "thumbnail": meta.get("thumbnail", ""),
            "duration": meta.get("duration", 0),
            "uploader": meta.get("uploader", ""),
            "count": count,
        })

    except Exception as exc:
        return jsonify({
            "error": str(exc),
        }), 400


@app.route("/api/browse", methods=["GET"])
def browse():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes(
            "-topmost",
            True,
        )

        folder_path = filedialog.askdirectory(
            parent=root,
            title="Choose download folder",
        )

        root.destroy()

        if folder_path:
            return jsonify({
                "path": folder_path,
            })

        return jsonify({
            "error": "No folder selected",
        }), 400

    except Exception as exc:
        return jsonify({
            "error": str(exc),
        }), 500


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            5000,
        )
    )

    print()
    print("  YT Downloader")
    print(f"  http://127.0.0.1:{port}")
    print()

    app.run(
        host="127.0.0.1",
        port=port,
        debug=False,
        threaded=True,
    )
