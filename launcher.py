import os
import sys
import threading
import webbrowser


def resource_path(name):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


# Make bundled FFmpeg available to yt-dlp.
base_dir = os.path.dirname(resource_path("index.html"))
ffmpeg_dir = os.path.dirname(resource_path("ffmpeg.exe"))
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
os.chdir(base_dir)

import server  # noqa: E402


PORT = int(os.environ.get("PORT", "5000"))
URL = f"http://127.0.0.1:{PORT}"


def open_browser():
    webbrowser.open(URL)


if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    server.app.run(
        host="127.0.0.1",
        port=PORT,
        debug=False,
        threaded=True,
    )
