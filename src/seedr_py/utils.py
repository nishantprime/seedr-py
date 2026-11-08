"""
Utility functions for torrent parsing and formatting.
"""

import hashlib
from typing import Dict, Any, Tuple

def format_bytes(num_bytes: int) -> str:
    """Convert bytes count to human-readable string (e.g. 1.25 GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"

def bdecode(data: bytes) -> Any:
    """Minimal, pure-Python bencode decoder for .torrent files."""
    def decode_item(index: int) -> Tuple[Any, int]:
        char = chr(data[index])
        if char == 'i':
            end = data.index(b'e', index)
            return int(data[index + 1:end]), end + 1
        elif char.isdigit():
            colon = data.index(b':', index)
            length = int(data[index:colon])
            start = colon + 1
            return data[start:start + length], start + length
        elif char == 'l':
            items = []
            idx = index + 1
            while chr(data[idx]) != 'e':
                item, idx = decode_item(idx)
                items.append(item)
            return items, idx + 1
        elif char == 'd':
            items = {}
            idx = index + 1
            while chr(data[idx]) != 'e':
                key, idx = decode_item(idx)
                val, idx = decode_item(idx)
                items[key.decode('utf-8', errors='ignore')] = val
            return items, idx + 1
        raise ValueError(f"Unknown bencode type at offset {index}: {char}")

    return decode_item(0)[0]

def torrent_to_magnet(torrent_bytes: bytes) -> str:
    """
    Extracts info-hash from raw .torrent file bytes and converts to magnet link.
    """
    info_start = torrent_bytes.find(b'4:info') + 6
    if info_start < 6:
        raise ValueError("Invalid .torrent file: 'info' dictionary not found.")

    def find_end_dict(b: bytes, start: int) -> int:
        depth = 0
        i = start
        while i < len(b):
            c = chr(b[i])
            if c in ('d', 'l'):
                depth += 1
                i += 1
            elif c == 'i':
                i = b.index(b'e', i) + 1
            elif c.isdigit():
                colon = b.index(b':', i)
                length = int(b[i:colon])
                i = colon + 1 + length
            elif c == 'e':
                depth -= 1
                i += 1
                if depth == 0:
                    return i
            else:
                i += 1
        return len(b)

    info_end = find_end_dict(torrent_bytes, info_start)
    raw_info = torrent_bytes[info_start:info_end]
    sha1 = hashlib.sha1(raw_info).hexdigest()

    name = "torrent"
    try:
        decoded = bdecode(torrent_bytes)
        info_d = decoded.get('info', {})
        if 'name' in info_d:
            val = info_d['name']
            name = val.decode('utf-8', errors='ignore') if isinstance(val, bytes) else str(val)
    except Exception:
        pass

    return f"magnet:?xt=urn:btih:{sha1}&dn={name}"
