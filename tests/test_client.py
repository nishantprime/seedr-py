import pytest
from seedr_py import SeedrClient, format_bytes, torrent_to_magnet
from seedr_py.exceptions import AuthenticationError

def test_format_bytes():
    assert format_bytes(500) == "500.00 B"
    assert format_bytes(1024 * 1024) == "1.00 MB"
    assert format_bytes(1024 * 1024 * 1024 * 2) == "2.00 GB"

def test_invalid_login():
    with pytest.raises(AuthenticationError):
        SeedrClient.from_password("invalid@example.com", "wrongpass123")
