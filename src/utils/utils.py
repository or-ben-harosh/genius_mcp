"""
Utility functions and custom exceptions for the Genius MCP server.
"""

import json
import logging
from typing import Any
from dataclasses import dataclass
from ..core.config import MAX_INPUT_LENGTH

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
    
    if len(song_name) > MAX_INPUT_LENGTH:
        raise ValidationError(f"Song name too long (max {MAX_INPUT_LENGTH} characters)")

    if len(artist_name) > MAX_INPUT_LENGTH:
        raise ValidationError(f"Artist name too long (max {MAX_INPUT_LENGTH} characters)")


def sanitize_input(text: str) -> str:
    """Sanitize input text."""
    return text.strip()[:MAX_INPUT_LENGTH]  # Limit length and strip whitespace


def safe_json_response(data: Any, error_msg: str = "Unknown error") -> str:
    """Safely convert data to JSON response."""
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        # Fallback response in case of serialization error
        fallback_data = {
            "error": error_msg,
            "details": str(e)
        }
        return json.dumps(fallback_data, indent=2)
