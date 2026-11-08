"""
Dataclass models representing Seedr resources.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from seedr_py.utils import format_bytes

@dataclass
class AccountSettings:
    user_id: int
    email: str
    username: str
    is_premium: bool
    package_name: str
    space_used: int
    space_max: int
    country: str = ""

    @property
    def space_used_formatted(self) -> str:
        return format_bytes(self.space_used)

    @property
    def space_max_formatted(self) -> str:
        return format_bytes(self.space_max)

    @property
    def space_pct(self) -> float:
        return round((self.space_used / self.space_max) * 100, 1) if self.space_max > 0 else 0.0

@dataclass
class Quota:
    space_used: int
    space_max: int
    bandwidth_used: int
    is_premium: bool

    @property
    def space_used_formatted(self) -> str:
        return format_bytes(self.space_used)

    @property
    def space_max_formatted(self) -> str:
        return format_bytes(self.space_max)

    @property
    def space_pct(self) -> float:
        return round((self.space_used / self.space_max) * 100, 1) if self.space_max > 0 else 0.0

@dataclass
class SeedrFile:
    id: int
    name: str
    size: int
    hash: str
    folder_id: int
    is_video: bool = False
    is_audio: bool = False
    thumb: str = ""

    @property
    def size_formatted(self) -> str:
        return format_bytes(self.size)

@dataclass
class SubFolder:
    id: int
    name: str
    size: int
    last_update: str = ""

    @property
    def size_formatted(self) -> str:
        return format_bytes(self.size)

@dataclass
class Task:
    id: int
    name: str
    size: int
    progress: float
    download_rate: int
    seeders: int = 0
    leechers: int = 0

    @property
    def size_formatted(self) -> str:
        return format_bytes(self.size)

@dataclass
class FolderContents:
    id: int
    path: str
    parent_id: int
    folders: List[SubFolder] = field(default_factory=list)
    files: List[SeedrFile] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

@dataclass
class DownloadLink:
    url: str
    name: str

@dataclass
class FolderArchive:
    archive_id: str
    url: str

@dataclass
class VideoStream:
    file_id: int
    name: str
    hls_url: Optional[str]
    raw_url: str
    subtitles: Dict[str, str] = field(default_factory=dict)
