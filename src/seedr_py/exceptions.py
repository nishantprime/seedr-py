"""
Custom exceptions for seedr-py
"""

class SeedrError(Exception):
    """Base exception for all Seedr errors."""
    pass

class AuthenticationError(SeedrError):
    """Raised when authentication fails (invalid credentials or expired session)."""
    pass

class APIError(SeedrError):
    """Raised when the Seedr API returns an error response."""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class TorrentError(SeedrError):
    """Raised when adding a magnet link or torrent fails."""
    pass

class NotFoundError(SeedrError):
    """Raised when a requested file or folder is not found."""
    pass
