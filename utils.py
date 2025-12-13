"""
Utility functions and custom exceptions for the Genius MCP server.
"""

import logging
from typing import Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class GeniusError(Exception):
    """Base exception for Genius-related errors."""
    pass


class ScrapingError(GeniusError):
    """Exception raised when scraping fails."""
    pass


class APIError(GeniusError):
    """Exception raised when API calls fail."""
    pass


class ValidationError(GeniusError):
    """Exception raised when input validation fails."""
    pass


@dataclass
class LyricsResult:
    """Result model for lyrics with metadata."""
    title: str
    artist: str
    lyrics: str
    url: str
    has_annotations: bool = False
    annotation_count: int = 0


@dataclass
class AnnotationResult:
    """Result model for annotation data."""
    annotation_id: str
    lyric_fragment: str
    explanation: str
    url: str


def validate_input(song_name: str, artist_name: str) -> None:
    """Validate input parameters."""
    if not song_name or not song_name.strip():
        raise ValidationError("Song name cannot be empty")
    
    if not artist_name or not artist_name.strip():
        raise ValidationError("Artist name cannot be empty")
    
    if len(song_name) > 200:
        raise ValidationError("Song name too long (max 200 characters)")
    
    if len(artist_name) > 200:
        raise ValidationError("Artist name too long (max 200 characters)")


def sanitize_input(text: str) -> str:
    """Sanitize input text."""
    return text.strip()[:200]  # Limit length and strip whitespace


def safe_json_response(data: Any, error_msg: str = "Unknown error") -> str:
    """Safely convert data to JSON response."""
    try:
        import json
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        return json.dumps({
            "error": error_msg,
            "details": str(e)
        }, indent=2)
