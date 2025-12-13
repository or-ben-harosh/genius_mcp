"""
Rate limiting functionality for the Genius MCP Server
"""

import time
from typing import Dict, List, Any
from .config import MAX_REQUESTS_PER_MINUTE

# Request history for rate limiting
_request_history: Dict[str, List[float]] = {}


def check_rate_limit(user_id: str = "default") -> bool:
    """Check if request is within rate limit."""
    now = time.time()
    if user_id not in _request_history:
        _request_history[user_id] = []

    # Remove requests older than 1 minute
    _request_history[user_id] = [
        req_time for req_time in _request_history[user_id]
        if now - req_time < 60
    ]

    # Check if under limit
    if len(_request_history[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        return False

    # Add current request
    _request_history[user_id].append(now)
    return True


def get_rate_limit_info(user_id: str = "default") -> Dict[str, Any]:
    """Get rate limit information for a user."""
    now = time.time()
    if user_id not in _request_history:
        return {
            "requests_made": 0,
            "requests_remaining": MAX_REQUESTS_PER_MINUTE,
            "reset_time": now + 60,
            "limit": MAX_REQUESTS_PER_MINUTE
        }

    # Clean old requests
    recent_requests = [
        req_time for req_time in _request_history[user_id]
        if now - req_time < 60
    ]

    return {
        "requests_made": len(recent_requests),
        "requests_remaining": max(0, MAX_REQUESTS_PER_MINUTE - len(recent_requests)),
        "reset_time": min(recent_requests) + 60 if recent_requests else now,
        "limit": MAX_REQUESTS_PER_MINUTE
    }


def reset_rate_limit(user_id: str = "default") -> None:
    """Reset rate limit for a user (admin function)."""
    if user_id in _request_history:
        del _request_history[user_id]
