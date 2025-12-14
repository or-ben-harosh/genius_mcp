import time
from typing import Optional, Dict, Any
from src.core.config import CACHE_TTL

# Simple in-memory cache
_cache: Dict[str, Dict[str, Any]] = {}


def get_cache_key(prefix: str, *args: str) -> str:
    """Generate cache key."""
    return f"{prefix}::{':'.join(args)}"


def get_cached(key: str) -> Optional[Any]:
    """Get cached value if not expired."""
    if key in _cache:
        data, timestamp = _cache[key]['data'], _cache[key]['timestamp']
        if time.time() - timestamp < CACHE_TTL:
            return data
        del _cache[key]
    return None


def set_cache(key: str, data: Any) -> None:
    """Cache data with timestamp."""
    _cache[key] = {
        'data': data,
        'timestamp': time.time()
    }


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return {
        "total_entries": len(_cache),
        "cache_ttl": CACHE_TTL
    }
