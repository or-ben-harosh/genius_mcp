"""
Genius Lyrics MCP Server
"""

import logging
import sys
import time
from mcp.server import FastMCP
from src.api.scraper import LyricsScraper
from src.api.genius_api import GeniusAPI
from src.utils.utils import ScrapingError, APIError, ValidationError
from src.utils.utils import validate_input, sanitize_input, safe_json_response
from src.core.config import GENIUS_API_TOKEN, MAX_SEARCH_RESULTS, MAX_REQUESTS_PER_MINUTE, validate_config, get_config
from src.core.cache_manager import get_cache_key, get_cached, set_cache, get_cache_stats
from src.core.rate_limiter import check_rate_limit, get_rate_limit_info
from dotenv import load_dotenv

load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate configuration on startup
try:
    validate_config()
    logger.info("Configuration validated successfully")
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    sys.exit(1)

mcp = FastMCP("genius-lyrics")


@mcp.tool()
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
        
    except ValidationError as e:
        logger.warning(f"Input validation failed: {e}")
        return safe_json_response({
            "error": "Invalid input",
            "message": str(e),
            "type": "validation_error"
        })
        
    except ScrapingError as e:
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
            "details": str(e) if logger.level <= logging.DEBUG else None
        })


@mcp.tool()
async def get_annotation(annotation_id: str) -> str:
    """
    Get annotation explanation by ID.
    
    Enhanced with validation, caching, and retry logic.
    
    Args:
        annotation_id: The annotation ID (e.g., "2310153")
    
    Returns:
        JSON: {"annotation_id", "lyric", "explanation", "success"}
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
        # Input validation
        if not annotation_id or not annotation_id.strip():
            raise ValidationError("Annotation ID cannot be empty")
        
        annotation_id = annotation_id.strip()
        
        # Validate ID format (should be numeric)
        if not annotation_id.isdigit():
            raise ValidationError("Annotation ID should be numeric")
        
        # Check cache
        cache_key = get_cache_key("annotation", annotation_id)
        cached_result = get_cached(cache_key)
        if cached_result:
            logger.info(f"Cache hit for annotation {annotation_id}")
            return cached_result
        
        logger.info(f"Fetching annotation: {annotation_id}")
        
        api = GeniusAPI(GENIUS_API_TOKEN)
        result = await api.get_annotation_explanation(annotation_id)
        
        # Cache successful result
        set_cache(cache_key, result)

        elapsed = time.time() - start_time
        logger.info(f"Successfully fetched annotation {annotation_id} in {elapsed:.2f}s")
        
        return result
        
    except ValidationError as e:
        logger.warning(f"Validation error for annotation {annotation_id}: {e}")
        return safe_json_response({
            "error": "Invalid input",
            "message": str(e),
            "type": "validation_error",
            "annotation_id": annotation_id
        })
        
    except APIError as e:
        logger.error(f"API error for annotation {annotation_id}: {e}")
        return safe_json_response({
            "error": "API error",
            "message": str(e),
            "type": "api_error",
            "annotation_id": annotation_id,
            "suggestion": "Check if the annotation ID is correct"
        })
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Unexpected error for annotation {annotation_id} after {elapsed:.2f}s: {e}", exc_info=True)
        return safe_json_response({
            "error": "Unexpected error",
            "message": "An unexpected error occurred while fetching annotation",
            "type": "internal_error",
            "annotation_id": annotation_id,
            "details": str(e) if logger.level <= logging.DEBUG else None
        })


@mcp.tool()
async def search_songs(query: str, limit: int = 5) -> str:
    """
    Search for songs on Genius.
    
    Args:
        query: Search query (song title, artist, lyrics fragment)
        limit: Number of results to return (1-configurable max, default 5)

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
            raise ValidationError("Search query cannot be empty")
        
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


@mcp.tool()
async def get_server_status() -> str:
    """
    Get server status, configuration, and statistics.

    Returns:
        JSON with server configuration, cache stats, and rate limiting info
    """
    try:
        config_info = get_config()
        cache_stats = get_cache_stats()
        rate_limit_info = get_rate_limit_info()

        return safe_json_response({
            "server_status": "running",
            "configuration": config_info,
            "cache_statistics": cache_stats,
            "rate_limit_status": rate_limit_info,
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"Error getting server status: {e}", exc_info=True)
        return safe_json_response({
            "error": "Status check failed",
            "message": str(e),
            "type": "server_error"
        })


def main():
    """Main entry point."""
    logger.info("Starting Genius MCP Server")
    logger.info(f"Configuration: {get_config()}")

    try:
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
