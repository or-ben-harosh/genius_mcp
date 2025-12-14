"""
Lyrics tool for fetching song lyrics with annotation IDs
"""

import logging
import time
from src.api.scraper import LyricsScraper
from src.utils.utils import validate_input, sanitize_input, safe_json_response
from src.core.cache_manager import get_cache_key, get_cached, set_cache
from src.core.rate_limiter import check_rate_limit, get_rate_limit_info
from src.core.config import MAX_REQUESTS_PER_MINUTE

logger = logging.getLogger(__name__)


async def get_lyrics_with_ids(song_name: str, artist_name: str) -> str:
    """
    Get song lyrics with annotation IDs inline.

    Args:
        song_name: Name of the song (max chars configurable)
        artist_name: Name of the artist (max chars configurable)

    Returns:
        Plain text lyrics with [ID: xxx] markers

    Example:
        "Look, I was gonna go easy on you" [ID: 2310153]
    """
    # Rate limiting check
    if not check_rate_limit():
        return safe_json_response({
            "error": "Rate limit exceeded",
            "message": f"Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute allowed",
            "type": "rate_limit_error",
            "rate_limit_info": get_rate_limit_info()
        })

    start_time = time.time()

    try:
        # Input validation and sanitization
        validate_input(song_name, artist_name)
        song_name = sanitize_input(song_name)
        artist_name = sanitize_input(artist_name)

        # Check cache
        cache_key = get_cache_key("lyrics", song_name.lower(), artist_name.lower())
        cached_result = get_cached(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {artist_name} - {song_name}")
            return cached_result

        logger.info(f"Fetching lyrics for: {artist_name} - {song_name}")

        # Scrape lyrics
        result = await LyricsScraper.get_lyrics_with_ids(song_name, artist_name)

        # Cache successful result
        set_cache(cache_key, result)

        elapsed = time.time() - start_time
        logger.info(f"Successfully fetched lyrics in {elapsed:.2f}s")

        return result

    except ValueError as e:
        logger.warning(f"Input validation failed: {e}")
        return safe_json_response({
            "error": "Invalid input",
            "message": str(e),
            "type": "validation_error"
        })

    except (ConnectionError, RuntimeError, PermissionError, FileNotFoundError, TimeoutError) as e:
        logger.error(f"Scraping error for {artist_name} - {song_name}: {e}")
        return safe_json_response({
            "error": "Scraping failed",
            "message": str(e),
            "type": "scraping_error",
            "suggestion": "Try checking the song/artist spelling or try again later"
        })

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Unexpected error after {elapsed:.2f}s: {e}", exc_info=True)
        return safe_json_response({
            "error": "Unexpected error",
            "message": "An unexpected error occurred while fetching lyrics",
            "type": "internal_error",
            "details": str(e)
        })
