"""
Genius MCP Server - Improved with FastMCP best practices
"""

import logging
import sys
from typing import List
from mcp.server import FastMCP
from mcp.server.fastmcp import Context
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


@mcp.tool(
    description="Get complete song lyrics with embedded annotation IDs for later explanation",
    structured_output=False  # Lyrics are plain text, not structured JSON
)
async def get_lyrics_with_ids(song_name: str, artist_name: str, ctx: Context) -> str:
    """
    Get song lyrics with annotation IDs inline.

    Args:
        song_name: Name of the song (max chars configurable)
        artist_name: Name of the artist (max chars configurable)
        ctx: MCP context for logging and progress

    Returns:
        Plain text lyrics with [ID: xxx] markers for annotations

    Example:
        "Look, I was gonna go easy on you" [ID: 2310153]
    """
    await ctx.info(f"Fetching lyrics for '{song_name}' by '{artist_name}'")
    return await lyrics_tool.get_lyrics_with_ids(song_name, artist_name)


@mcp.tool(
    description="Get detailed explanations for lyric annotations by their IDs (supports batch processing)",
    structured_output=True
)
async def get_annotation(annotation_ids: List[int], ctx: Context) -> str:
    """
    Get annotation explanations by IDs (batch processing up to 50 IDs).

    Args:
        annotation_ids: List of annotation IDs found in lyrics (e.g., [2310153, 1234567])
        ctx: MCP context for logging and progress

    Returns:
        JSON with annotation details: lyric, explanation, and metadata for each ID
    """
    await ctx.info(f"Fetching {len(annotation_ids)} annotations")
    if len(annotation_ids) > 1:
        await ctx.report_progress(0, len(annotation_ids), "Starting batch annotation fetch")

    result = await annotation_tool.get_annotation(annotation_ids)

    if len(annotation_ids) > 1:
        await ctx.report_progress(len(annotation_ids), len(annotation_ids), "Completed")

    return result


@mcp.tool(
    description="Search for songs on Genius by title, artist, or lyrics fragment",
    structured_output=True
)
async def search_songs(query: str, limit: int, ctx: Context) -> str:
    """
    Search for songs on Genius.

    Args:
        query: Search query (song title, artist name, or lyrics fragment)
        limit: Number of results to return (1-20, default: 5)
        ctx: MCP context for logging

    Returns:
        JSON list of matching songs with IDs, titles, artists, and URLs
    """
    await ctx.info(f"Searching for: '{query}' (limit: {limit})")
    return await search_tool.search_songs(query, limit)


@mcp.tool(
    description="Get detailed metadata about a specific song including album, stats, and media links",
    structured_output=True
)
async def get_song(song_id: int, ctx: Context) -> str:
    """
    Get detailed information about a song by its Genius ID.

    Args:
        song_id: Genius song ID (obtained from search_songs)
        ctx: MCP context for logging

    Returns:
        JSON with comprehensive song details: title, artist, album, release date,
        pageview stats, media links (YouTube, Spotify), and featured artists
    """
    await ctx.info(f"Fetching song details for ID: {song_id}")
    return await song_tool.get_song(song_id)


@mcp.tool(
    description="Get detailed artist information including bio, social links, and follower count",
    structured_output=True
)
async def get_artist(artist_id: int, ctx: Context) -> str:
    """
    Get detailed artist information by Genius artist ID.

    Args:
        artist_id: Genius artist ID (obtained from song details or search)
        ctx: MCP context for logging

    Returns:
        JSON with artist details: name, biography, follower count, social media links,
        alternate names/aliases, and profile image
    """
    await ctx.info(f"Fetching artist details for ID: {artist_id}")
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