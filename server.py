#!/usr/bin/env python3
"""
YT Web Downloader — Flask backend
Uses yt-dlp + ffmpeg.
Supports public videos/playlists and browser-login cookies.
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


def _run_download(
    job_id,
    url,
    fmt,
    quality,
    outdir,
    cookie_browser="",
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

            title = info.get("title") or state["current_title"]
            state["current_title"] = title

    
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


    if not url:
        return jsonify({
            "error": "No URL provided",
        }), 400

    if fmt not in ("mp3", "mp4", "webm"):
        return jsonify({
            "error": "Invalid format",
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
