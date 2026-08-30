# YouTube Videos Music Playlist Downloader

A YouTube video, music, and playlist downloader with **two ways to use the project**:

- **Windows EXE** — run the application normally without opening the source code.
- **HTML/Web version** — open the web interface directly in your browser.

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

Windows may display a security warning because the application may not have a commercial code-signing certificate. If you trust the source and downloaded it from the official repository/release, review the warning before continuing.

### 4. Download content

Enter the YouTube video, music, or playlist URL into the application and select the available download options.

Follow the application's prompts and wait for the download to finish.

---

## How to Use the HTML Version

The project can also be used through its HTML interface.

### Option 1 — Open the HTML file

1. Download or clone the repository.
2. Open the project folder.
3. Find the main `.html` file (usually `index.html`).
4. Double-click it to open it in your browser.
5. Enter the YouTube URL and use the available controls.

### Option 2 — Run it through a local server

For the most reliable experience, especially if the browser blocks local scripts or resources, run the project through a local HTTP server.

For example, if Python is installed:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

Open the page in your browser and use the downloader interface.

---

## EXE vs HTML

| Version | Best for | What you need |
|---|---|---|
| **Windows EXE** | Normal desktop use | Windows PC |
| **HTML** | Testing, development, or browser use | Web browser + project files |

The **EXE version is recommended for normal Windows users** because it is packaged as a desktop application.

The **HTML version is useful for development and testing** or when you want to use the web interface directly.

---

## Features

- YouTube video downloading
- Music/audio downloading
- Playlist support
- Windows EXE version
- HTML/web interface
- Local use options

Features may vary between releases and versions of the project.

---

## Requirements

### Windows EXE

- Windows PC
- Latest release of the application
- Internet connection for accessing supported online services

### HTML Version

- Modern web browser
- Project files
- Internet connection for accessing supported online services
- Python is optional if you want to run a local HTTP server

---

## Troubleshooting

### The EXE does not start

- Make sure you extracted the complete release ZIP.
- Do not move required files out of the application folder.
- Try running the EXE again from the extracted folder.
- Check Windows Security if Windows has blocked the application.

### The HTML version does not work when opened directly

Try running the project through a local server instead:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000`.

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
