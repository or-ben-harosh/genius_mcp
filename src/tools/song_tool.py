"""
Song tool for getting detailed song information
"""

import logging
from src.api.genius_api import GeniusAPI
from src.utils.utils import safe_json_response
from src.core.cache_manager import get_cache_key, get_cached, set_cache
from src.core.rate_limiter import check_rate_limit, get_rate_limit_info
from src.core.config import GENIUS_API_TOKEN, MAX_REQUESTS_PER_MINUTE

logger = logging.getLogger(__name__)


async def get_song(song_id: int) -> str:
    """
    Get detailed information about a song by ID.

    Args:
        song_id: Genius song ID (from search results)

    Returns:
        JSON with song metadata including title, artist, album, release date, stats
    """
    # Rate limiting check
    if not check_rate_limit():
        return safe_json_response({
            "error": "Rate limit exceeded",
            "message": f"Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute allowed",
            "type": "rate_limit_error",
            "rate_limit_info": get_rate_limit_info()
        })

    try:
        # Input validation
        if not isinstance(song_id, int) or song_id <= 0:
            logger.error(f"Invalid song ID: {song_id}")
            raise ValueError(f"Song ID must be a positive integer, got: {song_id}")

        # Check cache
        cache_key = get_cache_key("song", str(song_id))
        cached_result = get_cached(cache_key)
        if cached_result:
            logger.info(f"Cache hit for song {song_id}")
            return cached_result

        logger.info(f"Fetching song details for ID: {song_id}")

        api = GeniusAPI(GENIUS_API_TOKEN)
        result = await api.get_song(song_id)

        # Cache successful result
        set_cache(cache_key, result)

        return result

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return safe_json_response({
            "error": "Invalid input",
            "message": str(e),
            "type": "validation_error"
        })

    except Exception as e:
        logger.error(f"Error fetching song {song_id}: {e}", exc_info=True)
        return safe_json_response({
            "error": "Failed to fetch song",
            "message": str(e),
            "type": "api_error"
        })