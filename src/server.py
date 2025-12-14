"""
Genius MCP Server
"""

import logging
import sys
from typing import List
from mcp.server import FastMCP
from src.tools import lyrics_tool, annotation_tool, search_tool, song_tool, artist_tool
from src.core.config import validate_config, get_config
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
    return await lyrics_tool.get_lyrics_with_ids(song_name, artist_name)


@mcp.tool()
async def get_annotation(annotation_ids: List[int]) -> str:
    """
    Get annotation explanations by IDs (batch processing).

    Enhanced with validation, caching, and rate limiting for multiple annotations.

    Args:
        annotation_ids: List of annotation IDs (e.g., [2310153, 1234567])
                       Maximum of 50 IDs per request (configurable)

    Returns:
        JSON: List of annotation results with {"annotation_id", "lyric", "explanation", "success"} for each
    """
    return await annotation_tool.get_annotation(annotation_ids)


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
    return await search_tool.search_songs(query, limit)


@mcp.tool()
async def get_song(song_id: int) -> str:
    """
    Get detailed information about a song by ID.

    Args:
        song_id: Genius song ID (from search results)

    Returns:
        JSON with song metadata including title, artist, album, release date, stats, media, and featured artists
    """
    return await song_tool.get_song(song_id)


@mcp.tool()
async def get_artist(artist_id: int) -> str:
    """
    Get detailed artist information.

    Args:
        artist_id: Genius artist ID (from song details or search)

    Returns:
        JSON with artist details including bio, followers, social links, and alternate names
    """
    return await artist_tool.get_artist(artist_id)


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