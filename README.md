# seedr-py ⚡

[![PyPI version](https://img.shields.io/pypi/v/seedr-py.svg)](https://pypi.org/project/seedr-py/)
[![Python versions](https://img.shields.io/pypi/pyversions/seedr-py.svg)](https://pypi.org/project/seedr-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A modern, high-speed Python client and API wrapper for **[Seedr.cc](https://www.seedr.cc)**.

Designed to overcome the limitations of legacy wrappers: provides **zero-CAPTCHA email/password authentication**, **one-click full folder ZIP downloads without mCaptcha**, **browser-compatible HLS video streaming**, and clean dataclass models.

---

## ✨ Features

- 🚀 **Zero-CAPTCHA Login:** Authenticates programmatically via Seedr's internal identity handshake (`seedr_sbvt`). No browser automation or CAPTCHA solving required.
- 📦 **One-Click Folder ZIP Downloads:** Download entire subfolder structures as a single ZIP archive directly from Seedr CDN with zero mCaptcha prompts.
- 🎬 **HLS Video Streaming:** Access both raw 1080p/4K bitrate files and browser-compatible HLS (`.m3u8`) streams with auto-converted AAC stereo audio (fixing silent Dolby EAC3 audio in Chrome/Firefox).
- 🧲 **Magnets & `.torrent` Files:** Supports magnet links, direct torrent URLs, and local `.torrent` file uploads.
- 📂 **Full Cloud File Management:** List directories, inspect quotas, retrieve direct CDN download links, cancel downloading tasks, and batch delete.
- 🛡️ **Fully Typed Dataclasses:** Every response returns rich, typed models (`FolderContents`, `SeedrFile`, `Quota`, `AccountSettings`, `VideoStream`).

---

## 📦 Installation

```bash
pip install seedr-py
```

---

## ⚡ Quickstart

### 1. Authenticate

```python
from seedr_py import SeedrClient

# Login with email and password (Zero CAPTCHA)
client = SeedrClient.from_password("your_email@example.com", "your_password")

# Or authenticate using cookies
client = SeedrClient.from_cookies({
    "seedr_ptok": "your_token",
    "RSESS_remember": "your_session"
})
```

### 2. Check Quota & Account

```python
quota = client.get_quota()
print(f"Storage: {quota.space_used_formatted} / {quota.space_max_formatted} ({quota.space_pct}%)")

account = client.get_account_settings()
print(f"Logged in as: {account.email} (User ID: {account.user_id})")
```

### 3. Browse Files & Folders

```python
# folder_id=0 represents the root directory
root = client.get_folder(0)

# List subfolders
for folder in root.folders:
    print(f"📁 {folder.name} (ID: {folder.id}, Size: {folder.size_formatted})")

# List files
for file in root.files:
    print(f"📄 {file.name} (ID: {file.id}, Size: {file.size_formatted})")

# List active torrent transfers
for task in root.tasks:
    print(f"⚡ {task.name}: {task.progress}% @ {task.download_rate / 1024:.1f} KB/s")
```

### 4. Download Entire Folder as a ZIP (No CAPTCHA)

```python
# 1. Get the direct signed ZIP URL from Seedr CDN
archive = client.get_folder_zip_url(folder_id=1438069680)
print("Signed ZIP Download Link:", archive.url)

# 2. Or stream it directly to disk
client.download_folder_zip(folder_id=1438069680, save_path="MyFolder.zip")
```

### 5. Add Torrents & Magnet Links

```python
# Add a magnet link
task = client.add_magnet("magnet:?xt=urn:btih:08ada5a7a6183aae1e0908bc1376f4c61b03387c...")
print(f"Transfer queued! Torrent ID: {task.get('user_torrent_id')}")

# Or upload a local .torrent file
client.add_torrent_file("ubuntu-24.04.torrent")
```

### 6. Stream Videos with Browser-Compatible Audio

```python
stream = client.get_video_stream(file_id=6018680430)

# Universal HLS stream with converted AAC audio
print("HLS Stream URL:", stream.hls_url)

# Raw untouched 1080p/4K bitrate stream (for VLC / external players)
print("Raw Stream URL:", stream.raw_url)

# Multi-language subtitle tracks (.vtt)
print("Subtitles:", stream.subtitles)
```

### 7. Delete Files, Folders, or Tasks

```python
# Cancel an active downloading torrent
client.cancel_task(task_id=200392405)

# Delete a folder
client.delete_folder(folder_id=1438069680)

# Delete a file
client.delete_file(file_id=6018680430)
```

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.
