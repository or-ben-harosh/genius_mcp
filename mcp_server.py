#!/usr/bin/env python3
"""
Genius Lyrics MCP Server

Features:
- Comprehensive error handling
- Input validation
- Rate limiting awareness
- Better logging
- Caching support
"""

import logging
import sys
import os
import asyncio
import time
from typing import Optional, Dict, Any
from mcp.server import FastMCP
from scraper import LyricsScraper
from genius_api import GeniusAPI
from utils import (
    ScrapingError, APIError, ValidationError,
    validate_input, sanitize_input, safe_json_response
)
from dotenv import load_dotenv

load_dotenv()

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP("genius-lyrics")

# Configuration
API_TOKEN = os.getenv("GENIUS_API_TOKEN")
if not API_TOKEN:
    logger.error("GENIUS_API_TOKEN environment variable not set")
    sys.exit(1)

# Simple in-memory cache
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 3600  # 1 hour


def _get_cache_key(prefix: str, *args: str) -> str:
    """Generate cache key."""
    return f"{prefix}::{':'.join(args)}"


def _get_cached(key: str) -> Optional[Any]:
    """Get cached value if not expired."""
    if key in _cache:
        data, timestamp = _cache[key]['data'], _cache[key]['timestamp']
        if time.time() - timestamp < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data: Any) -> None:
    """Cache data with timestamp."""
    _cache[key] = {
        'data': data,
        'timestamp': time.time()
    }


@mcp.tool()
async def get_lyrics_with_ids(song_name: str, artist_name: str) -> str:
    """
    Get song lyrics with annotation IDs inline.
        
    Args:
        song_name: Name of the song (max 200 chars)
        artist_name: Name of the artist (max 200 chars)
    
    Returns:
        Plain text lyrics with [ID: xxx] markers
        
    Example:
        "Look, I was gonna go easy on you" [ID: 2310153]
    """
    start_time = time.time()
    
    try:
        # Input validation and sanitization
        validate_input(song_name, artist_name)
        song_name = sanitize_input(song_name)
        artist_name = sanitize_input(artist_name)
        
        # Check cache
        cache_key = _get_cache_key("lyrics", song_name.lower(), artist_name.lower())
        cached_result = _get_cached(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {artist_name} - {song_name}")
            return cached_result
        
        logger.info(f"Fetching lyrics for: {artist_name} - {song_name}")
        
        # Scrape lyrics
        result = await LyricsScraper.get_lyrics_with_ids(song_name, artist_name)
        
        # Cache successful result
        _set_cache(cache_key, result)
        
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
        cache_key = _get_cache_key("annotation", annotation_id)
        cached_result = _get_cached(cache_key)
        if cached_result:
            logger.info(f"Cache hit for annotation {annotation_id}")
            return cached_result
        
        logger.info(f"Fetching annotation: {annotation_id}")
        
        api = GeniusAPI(API_TOKEN)
        result = await api.get_annotation_explanation(annotation_id)
        
        # Cache successful result
        _set_cache(cache_key, result)
        
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
        limit: Number of results to return (1-20, default 5)
    
    Returns:
        JSON list of song matches with basic info
    """
    try:
        # Input validation
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")
        
        if not 1 <= limit <= 20:
            limit = min(max(limit, 1), 20)  # Clamp to valid range
        
        query = sanitize_input(query)
        
        logger.info(f"Searching for: '{query}' (limit: {limit})")
        
        api = GeniusAPI(API_TOKEN)
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
async def get_server_stats() -> str:
    """
    Get server statistics and health info (NEW FEATURE).
    
    Returns:
        JSON with cache stats, uptime, etc.
    """
    try:
        stats = {
            "cache_size": len(_cache),
            "cache_keys": list(_cache.keys())[:10],  # First 10 keys
            "server_status": "healthy",
            "features": ["lyrics_scraping", "annotation_lookup", "caching", "search"]
        }
        
        return safe_json_response(stats)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return safe_json_response({"error": "Failed to get stats"})


def main():
    """Main entry point with enhanced startup info."""
    logger.info("Starting Genius MCP Server")
    
    try:
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
