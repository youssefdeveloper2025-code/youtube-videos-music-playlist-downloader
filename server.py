#!/usr/bin/env python3
"""
YT Web Downloader — Flask backend
Serves the frontend and handles downloads via yt-dlp.
Install: pip install flask yt-dlp
Run:     python server.py   →  open http://localhost:5000
"""

import json
import os
import queue
import sys
import threading
import uuid
from pathlib import Path

# ── auto-install dependencies ─────────────────────────────────────────────────
for pkg in ("flask", "yt_dlp"):
    try:
        __import__(pkg)
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               pkg.replace("_", "-")])

from flask import Flask, Response, jsonify, request, send_from_directory
import yt_dlp

app = Flask(__name__, static_folder=".", static_url_path="")

JOBS: dict[str, dict] = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _run_download(job_id: str, url: str, fmt: str,
                  quality: str, outdir: str,
                  cookie_browser: str = "") -> None:
    job = JOBS[job_id]
    q: queue.Queue = job["queue"]

    is_playlist = "playlist" in url.lower() or "list=" in url
    outtmpl = os.path.join(
        outdir,
        "%(playlist_index)s - %(title)s.%(ext)s" if is_playlist
        else "%(title)s.%(ext)s"
    )

    state = {"track": 0, "total": 0, "current_title": ""}

    def hook(d):
        info_dict = d.get("info_dict") or {}
        n = info_dict.get("n_entries") or info_dict.get("playlist_count") or 0
        if n:
            state["total"] = n

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            dled  = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta   = d.get("eta") or 0
            pct   = round(dled / total * 100, 1) if total else 0
            track_lbl = (f"{state['track'] + 1}/{state['total']}"
                         if state["total"] else "")
            q.put({
                "type":        "progress",
                "pct":         pct,
                "speed":       round(speed / 1024, 1),
                "eta":         eta,
                "dled":        round(dled / 1024 / 1024, 2),
                "total":       round(total / 1024 / 1024, 2),
                "track":       track_lbl,
                "track_title": state["current_title"],
            })

        elif d["status"] == "finished":
            state["track"] += 1
            title = info_dict.get("title", "")
            state["current_title"] = title
            art_msg = " + embedding cover art…" if fmt == "mp3" else "…"
            msg = f"Processing{art_msg}"
            if state["total"]:
                msg = f"[{state['track']}/{state['total']}] {msg}"
            q.put({
                "type":        "processing",
                "msg":         msg,
                "track_title": title,
                "track":       f"{state['track']}/{state['total']}"
                               if state["total"] else "",
            })

        elif d["status"] == "error":
            bad = info_dict.get("title", "unknown track")
            q.put({"type": "skipped", "msg": f"Skipped (unavailable): {bad}"})

    # ── shared options ────────────────────────────────────────────────────────
    COMMON = {
        "ignoreerrors":            True,
        "sleep_interval":          2,
        "sleep_interval_requests": 1,
        "retries":                 5,
        "fragment_retries":        5,
        "outtmpl":                 outtmpl,
        "progress_hooks":          [hook],
        "quiet":                   True,
        "no_warnings":             True,
    }

    # ── cookies: borrow login from browser ───────────────────────────────────
    if cookie_browser:
        COMMON["cookiesfrombrowser"] = (cookie_browser,)   # e.g. ("chrome",)

    if fmt == "mp3":
        ydl_opts = {
            **COMMON,
            "format":         "bestaudio/best",
            "writethumbnail": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio",
                 "preferredcodec": "mp3",
                 "preferredquality": quality},
                {"key": "FFmpegMetadata",    "add_metadata": True},
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                {"key": "EmbedThumbnail",    "already_have_thumbnail": False},
            ],
        }
    else:
        fmt_str = (
            "bestvideo+bestaudio/best" if quality == "best"
            else f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
        )
        merge_ext = fmt if fmt in ("mp4", "webm") else "mp4"
        ydl_opts = {
            **COMMON,
            "format":              fmt_str,
            "merge_output_format": merge_ext,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info  = ydl.extract_info(url, download=True)
            title = (info or {}).get("title", "") or (info or {}).get("id", "Download")

        total_done = state["track"]
        suffix = f" ({total_done} tracks)" if total_done > 1 else ""
        q.put({
            "type":        "done",
            "title":       title + suffix,
            "fmt":         fmt,
            "outdir":      outdir,
            "track_count": total_done,
        })
    except Exception as exc:
        q.put({"type": "error", "msg": str(exc)})


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/start", methods=["POST"])
def start():
    data           = request.get_json(force=True)
    url            = data.get("url", "").strip()
    fmt            = data.get("format", "mp4")
    quality        = data.get("quality", "best")
    outdir         = os.path.expanduser(data.get("outdir", "~/Downloads"))
    cookie_browser = data.get("cookie_browser", "").strip().lower()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    Path(outdir).mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"queue": queue.Queue()}

    t = threading.Thread(
        target=_run_download,
        args=(job_id, url, fmt, quality, outdir, cookie_browser),
        daemon=True,
    )
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def progress(job_id):
    if job_id not in JOBS:
        return jsonify({"error": "Unknown job"}), 404

    def generate():
        q: queue.Queue = JOBS[job_id]["queue"]
        while True:
            try:
                event = q.get(timeout=60)
                yield _event(event)
                if event["type"] in ("done", "error"):
                    break
            except queue.Empty:
                yield _event({"type": "ping"})

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/info", methods=["POST"])
def info():
    data           = request.get_json(force=True) or {}
    url            = data.get("url", "").strip()
    cookie_browser = data.get("cookie_browser", "").strip().lower()
    if not url:
        return jsonify({"error": "No URL"}), 400
    try:
        opts = {
            "quiet": True, "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
        }
        if cookie_browser:
            opts["cookiesfrombrowser"] = (cookie_browser,)

        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(url, download=False)

        count = None
        if meta.get("_type") == "playlist":
            entries = meta.get("entries") or []
            count = len([e for e in entries if e])

        return jsonify({
            "title":     meta.get("title", ""),
            "thumbnail": meta.get("thumbnail", ""),
            "duration":  meta.get("duration", 0),
            "uploader":  meta.get("uploader", ""),
            "count":     count,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  🎵  YT Downloader  →  http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)