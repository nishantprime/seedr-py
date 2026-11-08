"""
Core Seedr Client implementation.
"""

import os
import json
import time
import requests
from typing import Dict, Any, List, Optional, Union

from seedr_py.models import (
    AccountSettings,
    Quota,
    SeedrFile,
    SubFolder,
    Task,
    FolderContents,
    DownloadLink,
    FolderArchive,
    VideoStream
)
from seedr_py.exceptions import (
    AuthenticationError,
    APIError,
    TorrentError,
    NotFoundError
)
from seedr_py.utils import torrent_to_magnet

class SeedrClient:
    """
    Python client for Seedr.cc supporting:
    - Zero-CAPTCHA email/password authentication
    - Zero-CAPTCHA full folder ZIP archive generation
    - Browser-compatible HLS video streaming
    - Direct CDN signed file download links
    - Magnet links and .torrent file uploads
    """
    BASE_URL = "https://www.seedr.cc/api/v0.1"

    def __init__(self, session: Optional[requests.Session] = None, cookies: Optional[Dict[str, str]] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.seedr.cc/files",
        })
        self._csrf_token: Optional[str] = None

        if cookies:
            for name, value in cookies.items():
                self.session.cookies.set(name, value, domain=".seedr.cc")

    def __enter__(self) -> "SeedrClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session."""
        if self.session:
            self.session.close()

    @classmethod
    def from_password(cls, email: str, password: str) -> "SeedrClient":
        """
        Authenticate directly using Email and Password via Seedr's internal
        identity proof token (seedr_sbvt) handshake, completely bypassing
        Cloudflare Turnstile and hCaptcha.
        """
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.seedr.cc/files",
        })

        # Step 1: Handshake for bind token (sbvt)
        try:
            ptok_resp = session.get(f"{cls.BASE_URL}/auth/ptok", timeout=12)
            ptok_resp.raise_for_status()
            sbvt = ptok_resp.json().get("sbvt")
        except Exception as e:
            raise AuthenticationError(f"Failed to obtain identity proof handshake: {e}") from e

        # Step 2: Login request
        login_payload = {
            "username": email,
            "password": password,
            "rememberme": 1,
            "seedr_sbvt": sbvt
        }
        try:
            resp = session.post(f"{cls.BASE_URL}/auth/login", json=login_payload, timeout=15)
            data = resp.json()
        except Exception as e:
            raise AuthenticationError(f"Login request failed: {e}") from e

        if resp.status_code != 200 or not data.get("success"):
            reason = data.get("reason_phrase") or data.get("error") or "Authentication failed"
            raise AuthenticationError(f"Invalid credentials ({resp.status_code}): {reason}")

        # Step 3: Populate any additional cookie strings from response payload
        if "cookies" in data:
            for c_str in data["cookies"]:
                parts = c_str.split(";")[0].split("=", 1)
                if len(parts) == 2:
                    session.cookies.set(parts[0].strip(), parts[1].strip(), domain=".seedr.cc")

        return cls(session=session)

    @classmethod
    def from_cookies(cls, cookies: Dict[str, str]) -> "SeedrClient":
        """
        Authenticate using pre-existing browser cookies (e.g. seedr_ptok or RSESS_remember).
        """
        return cls(cookies=cookies)

    def _get_csrf_token(self, refresh: bool = False) -> str:
        """Fetch and cache CSRF token required for mutating API actions."""
        if not self._csrf_token or refresh:
            url = f"{self.BASE_URL}/organization/csrf-token"
            resp = self.session.get(url, timeout=12)
            resp.raise_for_status()
            self._csrf_token = resp.json().get("csrf_token")
            self.session.headers["X-CSRF-Token"] = self._csrf_token
        return self._csrf_token

    def get_account_settings(self) -> AccountSettings:
        """Fetch user profile details (email, user_id, storage quota, package type)."""
        url = f"{self.BASE_URL}/account/settings"
        resp = self.session.get(url, timeout=15)
        if resp.status_code in (401, 403):
            raise AuthenticationError("Session expired or unauthorized.")
        resp.raise_for_status()
        data = resp.json()
        acc = data.get("account", {})
        return AccountSettings(
            user_id=acc.get("user_id", 0),
            email=acc.get("email", ""),
            username=acc.get("username", ""),
            is_premium=acc.get("premium", False),
            package_name=acc.get("package_name", "Free"),
            space_used=acc.get("space_used", 0),
            space_max=acc.get("space_max", 0),
            country=data.get("country", "")
        )

    def get_quota(self) -> Quota:
        """Fetch storage space and bandwidth quota information."""
        url = f"{self.BASE_URL}/account/quota/used"
        resp = self.session.get(url, timeout=12)
        if resp.status_code in (401, 403):
            raise AuthenticationError("Session expired or unauthorized.")
        resp.raise_for_status()
        data = resp.json()
        return Quota(
            space_used=data.get("space_used", 0),
            space_max=data.get("space_max", 0),
            bandwidth_used=data.get("bandwidth_used", 0),
            is_premium=data.get("is_premium", False)
        )

    def get_folder(self, folder_id: int = 0) -> FolderContents:
        """
        Fetch subfolders, files, and active torrent tasks inside a directory.
        folder_id = 0 represents the root directory.
        """
        url = f"{self.BASE_URL}/fs/folder/{folder_id}/items"
        resp = self.session.get(url, timeout=15)
        if resp.status_code in (401, 403):
            raise AuthenticationError("Session expired or unauthorized.")
        if resp.status_code == 404:
            raise NotFoundError(f"Folder ID {folder_id} not found.")
        resp.raise_for_status()
        data = resp.json()

        folders = [
            SubFolder(
                id=fo.get("id"),
                name=fo.get("path"),
                size=fo.get("size", 0),
                last_update=fo.get("last_update", "")
            )
            for fo in data.get("folders", [])
        ]

        files = [
            SeedrFile(
                id=fi.get("id"),
                name=fi.get("name"),
                size=fi.get("size", 0),
                hash=fi.get("hash", ""),
                folder_id=fi.get("folder_id", folder_id),
                is_video=fi.get("is_video", False),
                is_audio=fi.get("is_audio", False),
                thumb=fi.get("thumb", "")
            )
            for fi in data.get("files", [])
        ]

        tasks = [
            Task(
                id=t.get("id"),
                name=t.get("name", ""),
                size=t.get("size", 0),
                progress=t.get("progress", 0.0),
                download_rate=t.get("download_rate", 0),
                seeders=t.get("seeders", 0),
                leechers=t.get("leechers", 0)
            )
            for t in (data.get("torrents", []) or data.get("tasks", []))
        ]

        return FolderContents(
            id=data.get("id", folder_id),
            path=data.get("path", "Home"),
            parent_id=data.get("parent", -1),
            folders=folders,
            files=files,
            tasks=tasks
        )

    def get_file_url(self, file_id: int) -> DownloadLink:
        """Generate a signed high-speed CDN direct download link for a file."""
        url = f"{self.BASE_URL}/download/file/{file_id}/url"
        resp = self.session.get(url, timeout=12)
        if resp.status_code == 404:
            raise NotFoundError(f"File ID {file_id} not found.")
        resp.raise_for_status()
        data = resp.json()
        return DownloadLink(url=data.get("url"), name=data.get("name", ""))

    def get_folder_zip_url(self, folder_id: int) -> FolderArchive:
        """
        Generate a signed direct ZIP archive URL for an entire folder without CAPTCHA.
        Uses POST /api/v0.1/download/archive with X-CSRF-Token.
        """
        self._get_csrf_token()
        url = f"{self.BASE_URL}/download/archive"
        payload = {
            "archive_arr": json.dumps([{"type": "folder", "id": folder_id}])
        }
        resp = self.session.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return FolderArchive(
            archive_id=str(data.get("archive_id")),
            url=data.get("url")
        )

    def download_folder_zip(self, folder_id: int, save_path: str, chunk_size: int = 128 * 1024) -> str:
        """
        Streams and saves an entire folder as a ZIP file directly to local disk.
        """
        archive = self.get_folder_zip_url(folder_id)
        with requests.get(archive.url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        return save_path

    def get_video_stream(self, file_id: int) -> VideoStream:
        """
        Fetches streaming endpoints for a video file:
        - raw_url: Direct untouched original bitrate file (1080p/4K)
        - hls_url: Browser-compatible HLS stream with converted AAC audio
        - subtitles: WebVTT multi-language subtitle tracks
        """
        dl = self.get_file_url(file_id)
        hls_url = None
        subtitles = {}

        try:
            resp = self.session.get(f"{self.BASE_URL}/media/hls/{file_id}", timeout=12)
            if resp.status_code == 200:
                h_data = resp.json()
                hls_url = h_data.get("url")
                subtitles = h_data.get("subtitles", {})
        except Exception:
            pass

        return VideoStream(
            file_id=file_id,
            name=dl.name,
            hls_url=hls_url,
            raw_url=dl.url,
            subtitles=subtitles
        )

    def add_magnet(self, magnet_link: str, folder_id: int = 0) -> Dict[str, Any]:
        """Add a magnet link download to the account."""
        self._get_csrf_token()
        url = f"{self.BASE_URL}/task"
        payload = {
            "folder_id": folder_id,
            "type": "torrent",
            "torrent_magnet": magnet_link.strip()
        }
        resp = self.session.post(url, data=payload, timeout=15)
        data = resp.json()
        if not data.get("success"):
            reason = data.get("reason_phrase") or "Failed to add magnet link."
            raise TorrentError(reason)
        return data

    def add_torrent_file(self, torrent_input: Union[str, bytes], folder_id: int = 0) -> Dict[str, Any]:
        """
        Add a .torrent file to the account.
        Accepts either a file path (str) or raw bytes.
        """
        if isinstance(torrent_input, str):
            with open(torrent_input, "rb") as f:
                torrent_bytes = f.read()
        else:
            torrent_bytes = torrent_input

        magnet = torrent_to_magnet(torrent_bytes)
        return self.add_magnet(magnet, folder_id=folder_id)

    def cancel_task(self, task_id: int) -> bool:
        """Cancel and delete an in-progress torrent task."""
        self._get_csrf_token()
        url = f"{self.BASE_URL}/tasks/{task_id}"
        resp = self.session.delete(url, timeout=12)
        resp.raise_for_status()
        return resp.json().get("success", False)

    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder and its contents."""
        return self.delete_batch([{"type": "folder", "id": folder_id}])

    def delete_file(self, file_id: int) -> bool:
        """Delete an individual file."""
        return self.delete_batch([{"type": "file", "id": file_id}])

    def delete_batch(self, items: List[Dict[str, Any]]) -> bool:
        """
        Batch delete folders and files.
        items format: [{"type": "folder", "id": 123}, {"type": "file", "id": 456}]
        """
        self._get_csrf_token()
        url = f"{self.BASE_URL}/fs/batch/delete"
        payload = {
            "delete_arr": json.dumps(items)
        }
        resp = self.session.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        return resp.json().get("success", False)
