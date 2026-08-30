# YouTube Videos Music Playlist Downloader

A YouTube video, music, and playlist downloader with **two ways to use the project**:

- **Windows EXE** — run the packaged desktop application.
- **HTML/Web version** — run the project's Python backend with `start.bat`, then use the HTML interface in your browser.

> **Important:** Only download content you have the right to download. You are responsible for complying with applicable laws, copyright rules, and YouTube/platform terms.

---

## How to Use the Windows EXE

### 1. Download the EXE release

Go to the project's **Releases** page and download the latest Windows release.

### 2. Extract the release

If the release is provided as a `.zip` file, extract the entire ZIP folder first.

Do **not** run the EXE directly from inside the ZIP archive.

### 3. Start the application

Open the extracted folder and run the `.exe` file.

### 4. Download content

Enter the YouTube video, music, or playlist URL into the application and select the available download options.

Follow the application's prompts and wait for the download to finish.

---

## How to Use the HTML/Web Version

**Do not open `index.html` directly.** The HTML interface requires the project's Python/Flask backend to be running in order for downloads to work.

The easiest way to start everything on Windows is the included **`start.bat`** file.

### 1. Download or clone the repository

Download the project or clone it with Git:

```bash
git clone https://github.com/youssefdeveloper2025-code/youtube-videos-music-playlist-downloader.git
```

### 2. Make sure Python is installed

The HTML version uses Python, Flask, and yt-dlp for the backend.

### 3. Run `start.bat`

Open the project folder and **double-click `start.bat`**.

The batch file will:

1. Check/install the required Python packages (`flask` and `yt-dlp`).
2. Start the Python/Flask server using `server.py`.
3. Automatically open the downloader in your browser at:

```text
http://localhost:5000
```

### 4. Use the downloader

Once the browser opens, enter the YouTube video, music, or playlist URL and use the downloader interface.

**Keep the `start.bat` command window open while using the downloader.** Closing it stops the backend server and downloads will no longer work.

### Important

Opening `index.html` by double-clicking it **is not a supported way to download**. The browser interface needs the Flask backend started by `start.bat` and `server.py`.

---

## EXE vs HTML/Web

| Version | Best for | How to start |
|---|---|---|
| **Windows EXE** | Normal desktop use | Run the `.exe` |
| **HTML/Web** | Source/development use | Run `start.bat`, then use the browser |

The **EXE version is recommended for normal Windows users** because it is packaged as a desktop application.

The **HTML/Web version requires the Python backend** and is intended for users who want to run the project from its source files.

---

## Features

- YouTube video downloading
- Music/audio downloading
- Playlist support
- Windows EXE version
- HTML/web interface
- Python/Flask backend
- yt-dlp integration

Features may vary between releases and versions of the project.

---

## Requirements

### Windows EXE

- Windows PC
- Latest release of the application
- Internet connection for accessing supported online services

### HTML/Web Version

- Windows PC
- Python installed and available through `python`/`pip`
- Modern web browser
- Internet connection
- The complete project folder, including `start.bat` and `server.py`

`start.bat` automatically runs the package installation command for Flask and yt-dlp.

---

## Troubleshooting

### The EXE does not start

- Make sure you extracted the complete release ZIP.
- Do not move required files out of the application folder.
- Try running the EXE again from the extracted folder.
- Check Windows Security if Windows has blocked the application.

### The HTML page does not download anything

Make sure you **did not open `index.html` directly**.

Instead:

1. Close the directly opened HTML page.
2. Return to the project folder.
3. Double-click **`start.bat`**.
4. Wait for the browser to open `http://localhost:5000`.
5. Keep the command window open while downloading.

### `start.bat` closes or Python is not recognized

Make sure Python is installed and added to your Windows PATH. Then run `start.bat` again.

### Downloads do not work

Make sure the URL is valid and that you have permission to download the content. Online services can also change their APIs, restrictions, or behavior, which may affect the application.

---

## License

This project is protected by the **YouTube Downloader Custom License** in [`LICENSE`](LICENSE).

The license restricts unauthorized copying, redistribution, selling, sublicensing, and incorporation of substantial portions of the project without permission.

Third-party components remain subject to their own licenses.

---

## Developer

**Youssef developer**  
GitHub: **YoussefDeveloper2025-code**

Original repository:
https://github.com/youssefdeveloper2025-code/youtube-videos-music-playlist-downloader

---

# Terms of Use & Developer Notice

## 1. Developer Rights

This project was created and developed by **YoussefDeveloper2025-code**.

By using, copying, modifying, redistributing, or incorporating this project into another project, you acknowledge the original developer and agree to the terms below.

## 2. Prohibited Use

I do **not** authorize the use of this project for purposes that I consider harmful, abusive, malicious, illegal, or otherwise inappropriate.

This includes, but is not limited to:

* Malicious or harmful activities.
* Unauthorized access to accounts, systems, or data.
* Fraud, scams, or deception.
* Harassment or abuse.
* Any illegal activity.
* Any use intended to harm another person, organization, or service.
* Any use that violates the rights of others.

If you choose to use this project in such a way, **you are acting independently and without my authorization.**

## 3. No Responsibility for Third-Party Use

I am **not responsible or liable for how other people use, modify, distribute, or integrate this project**.

If someone uses this project or a modified version of it for a purpose that I do not approve of, that use is **not endorsed, authorized, or supported by me**.

The person or organization using the project is solely responsible for their own actions and their consequences.

## 4. Modification and Reuse

You may modify or build upon this project where permitted by the project's license.

However, if you use substantial parts of this project, its source code, or modified versions of it in your own project, you **must provide clear credit to the original developer**.

Credit should identify:

**Original Developer:** YoussefDeveloper2025-code

and should include a link to the original project repository where practical.

## 5. Redistribution

If you redistribute a modified or derived version of this project, you must not claim that you originally created the underlying work.

You must retain the applicable copyright and attribution notices.

## 6. No Endorsement

Using this project does not imply that the original developer supports, sponsors, approves, or is affiliated with any project that uses or modifies it.

## 7. Your Responsibility

**You are responsible for your own use of this project.**

If you modify the project, add functionality, redistribute it, or integrate it into another application, you are responsible for those changes and their consequences.

## 8. Final Notice

This project is provided as a development tool.

**Use it responsibly, respect the rights of others, and give credit where credit is due.**

Unauthorized, harmful, malicious, or illegal use is not permitted by the original developer and is not endorsed by the original developer.
