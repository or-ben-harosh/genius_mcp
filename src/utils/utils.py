"""
Utility functions and custom exceptions for the Genius MCP server.
"""

import json
import logging
from typing import Any
from src.core.config import MAX_INPUT_LENGTH

logger = logging.getLogger(__name__)


def validate_input(song_name: str, artist_name: str) -> None:
    """Validate input parameters."""
    if not song_name or not song_name.strip():
        logger.error(f"Invalid song name: '{song_name}'")
        raise ValueError(f"Invalid song name: '{song_name}'")

    if not artist_name or not artist_name.strip():
        logger.error(f"Invalid artist name: '{artist_name}'")
        raise ValueError(f"Invalid artist name: '{artist_name}'")

    if len(song_name) > MAX_INPUT_LENGTH:
        logger.error(f"Song name too long: '{song_name}'(max {MAX_INPUT_LENGTH} characters)")
        raise ValueError(f"Song name too long: '{song_name}'(max {MAX_INPUT_LENGTH} characters)")

    if len(artist_name) > MAX_INPUT_LENGTH:
        logger.error(f"Artist name too long (max {MAX_INPUT_LENGTH} characters)")
        raise ValueError(f"Artist name too long (max {MAX_INPUT_LENGTH} characters)")


def sanitize_input(text: str) -> str:
    """Sanitize input text."""
    return text.strip()[:MAX_INPUT_LENGTH]


def safe_json_response(data: Any, error_msg: str = "Unknown error") -> str:
    """Safely convert data to JSON response."""
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")

        fallback_data = {
            "error": error_msg,
            "details": str(e)
        }
        return json.dumps(fallback_data, indent=2)
