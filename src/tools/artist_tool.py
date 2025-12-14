"""
Artist tool for getting detailed artist information
"""

import logging
from src.api.genius_api import GeniusAPI
from src.utils.utils import safe_json_response
from src.core.cache_manager import get_cache_key, get_cached, set_cache
from src.core.rate_limiter import check_rate_limit, get_rate_limit_info
from src.core.config import GENIUS_API_TOKEN, MAX_REQUESTS_PER_MINUTE

logger = logging.getLogger(__name__)


async def get_artist(artist_id: int) -> str:
    """
    Get detailed artist information.

    Args:
        artist_id: Genius artist ID (from song details or search)

    Returns:
        JSON with artist details including bio, followers, social links, and alternate names
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
        if not isinstance(artist_id, int) or artist_id <= 0:
            logger.error(f"Invalid artist ID: {artist_id}")
            raise ValueError(f"Artist ID must be a positive integer, got: {artist_id}")

        # Check cache
        cache_key = get_cache_key("artist", str(artist_id))
        cached_result = get_cached(cache_key)
        if cached_result:
            logger.info(f"Cache hit for artist {artist_id}")
            return cached_result

        logger.info(f"Fetching artist details for ID: {artist_id}")

        api = GeniusAPI(GENIUS_API_TOKEN)
        result = await api.get_artist(artist_id)

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
        logger.error(f"Error fetching artist {artist_id}: {e}", exc_info=True)
        return safe_json_response({
            "error": "Failed to fetch artist",
            "message": str(e),
            "type": "api_error"
        })