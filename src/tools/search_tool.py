"""
Search tool for finding songs on Genius
"""

import logging
from ..api.genius_api import GeniusAPI
from ..utils.utils import sanitize_input, safe_json_response
from ..core.rate_limiter import check_rate_limit, get_rate_limit_info
from ..core.config import GENIUS_API_TOKEN, MAX_REQUESTS_PER_MINUTE, MAX_SEARCH_RESULTS

logger = logging.getLogger(__name__)


async def search_songs(query: str, limit: int = MAX_SEARCH_RESULTS) -> str:
    """
    Search for songs on Genius.

    Args:
        query: Search query (song title, artist, lyrics fragment)
        limit: Number of results to return (set in config.py, default 10)

    Returns:
        JSON list of song matches with basic info
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
        if not query or not query.strip():
            logger.error("Empty search query provided")
            raise ValueError("Search query cannot be empty")

        if not 1 <= limit <= MAX_SEARCH_RESULTS:
            limit = min(max(limit, 1), MAX_SEARCH_RESULTS)  # Clamp to valid range

        query = sanitize_input(query)

        logger.info(f"Searching for: '{query}' (limit: {limit})")

        api = GeniusAPI(GENIUS_API_TOKEN)
        results = await api.search_songs(query, limit)

        return results

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return safe_json_response({
            "error": "Search failed",
            "message": str(e),
            "type": "search_error"
        })
