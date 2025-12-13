"""
Configuration settings for the Genius MCP Server
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# API Configuration
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
GENIUS_BASE_URL = "https://api.genius.com"



# Scraping Configuration
SCRAPING_TIMEOUT = float(os.getenv("SCRAPING_TIMEOUT", "30.0"))

# Cache Configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Validation Limits
MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "200"))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "20"))

# Headers for scraping
SCRAPING_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def validate_config() -> None:
    """Validate configuration on startup."""
    if not GENIUS_API_TOKEN:
        raise EnvironmentError(
            "GENIUS_API_TOKEN is required. Please set it in your environment variables."
        )

    if CACHE_TTL <= 0:
        raise ValueError("CACHE_TTL must be positive")

    if MAX_REQUESTS_PER_MINUTE <= 0:
        raise ValueError("MAX_REQUESTS_PER_MINUTE must be positive")

    if MAX_INPUT_LENGTH <= 0:
        raise ValueError("MAX_INPUT_LENGTH must be positive")


def get_config() -> Dict[str, Any]:
    """Get current configuration as dictionary."""
    return {
        "api_configured": bool(GENIUS_API_TOKEN),
        "api_base_url": GENIUS_BASE_URL,
        "cache_ttl": CACHE_TTL,
        "scraping_timeout": SCRAPING_TIMEOUT,
        "max_input_length": MAX_INPUT_LENGTH,
        "max_search_results": MAX_SEARCH_RESULTS,
        "max_requests_per_minute": MAX_REQUESTS_PER_MINUTE,
        "log_level": LOG_LEVEL,
    }
