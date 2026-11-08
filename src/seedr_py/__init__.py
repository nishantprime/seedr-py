"""
seedr-py: A modern, reverse-engineered Python wrapper for Seedr.cc
"""

from seedr_py.client import SeedrClient
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
    SeedrError,
    AuthenticationError,
    APIError,
    TorrentError,
    NotFoundError
)
from seedr_py.utils import format_bytes, torrent_to_magnet

__version__ = "0.1.0"
__all__ = [
    "SeedrClient",
    "AccountSettings",
    "Quota",
    "SeedrFile",
    "SubFolder",
    "Task",
    "FolderContents",
    "DownloadLink",
    "FolderArchive",
    "VideoStream",
    "SeedrError",
    "AuthenticationError",
    "APIError",
    "TorrentError",
    "NotFoundError",
    "format_bytes",
    "torrent_to_magnet",
]
