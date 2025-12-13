"""
Configuration settings for the Genius MCP Server
"""

import os
from typing import Dict, Any

# API Configuration
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
GENIUS_BASE_URL = "https://api.genius.com"

# Scraping Configuration
SCRAPING_TIMEOUT = float(os.getenv("SCRAPING_TIMEOUT", "30.0"))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

# Cache Configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Feature Flags
ENABLE_SEARCH = os.getenv("ENABLE_SEARCH", "true").lower() == "true"
ENABLE_STATS = os.getenv("ENABLE_STATS", "true").lower() == "true"

# Validation Limits
MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "200"))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "20"))

# Headers for scraping
SCRAPING_HEADERS: Dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def get_config() -> Dict[str, Any]:
    """Get current configuration as dictionary."""
    return {
        "api_configured": bool(GENIUS_API_TOKEN),
        "cache_enabled": ENABLE_CACHE,
        "cache_ttl": CACHE_TTL,
        "timeout": SCRAPING_TIMEOUT,
        "max_input_length": MAX_INPUT_LENGTH,
        "features": {
            "search": ENABLE_SEARCH,
            "stats": ENABLE_STATS,
            "caching": ENABLE_CACHE
        }
    }
