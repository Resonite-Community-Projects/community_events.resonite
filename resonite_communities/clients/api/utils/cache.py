import asyncio
import time
from typing import Any, Optional
from fastapi import Response, Request

# Global dictionary to store locks per cache key
_cache_locks = {}
_locks_lock = asyncio.Lock()

# In-memory cache storage with TTL
_cache_store = {}
_cache_ttl = {}

async def get_cache_lock(cache_key: str) -> asyncio.Lock:
    """Get or create a lock for a specific cache key to prevent cache stampede."""
    async with _locks_lock:
        if cache_key not in _cache_locks:
            _cache_locks[cache_key] = asyncio.Lock()
        return _cache_locks[cache_key]

async def get_cached(cache_key: str) -> Optional[Any]:
    """Get a value from the in-memory cache if it exists and hasn't expired."""
    if cache_key in _cache_store:
        # Check if the cache entry has expired
        if cache_key in _cache_ttl:
            if time.time() < _cache_ttl[cache_key]:
                return _cache_store[cache_key]
            else:
                # Expired, remove it
                del _cache_store[cache_key]
                del _cache_ttl[cache_key]
    return None

async def set_cached(cache_key: str, value: Any, expire: int = 300):
    """Store a value in the in-memory cache with TTL (in seconds)."""
    _cache_store[cache_key] = value
    _cache_ttl[cache_key] = time.time() + expire

def request_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request = None,
    response: Response = None,
    **kwargs,
):
    return ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ])

def authenticated_request_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request = None,
    response: Response = None,
    user_auth = None,
    **kwargs,
):
    """Cache key builder that includes user authentication information."""
    # Build base key from request
    key_parts = [
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ]

    # Add user-specific cache key components
    if user_auth:
        if user_auth.is_superuser:
            key_parts.append("superuser")
        elif user_auth.discord_account:
            # Cache based on user's accessible communities
            communities = sorted(user_auth.discord_account.user_communities or [])
            key_parts.append(f"communities:{','.join(communities)}")
        else:
            key_parts.append("authenticated")
    else:
        key_parts.append("anonymous")

    return ":".join(key_parts)

def filtered_events_key_builder(
    func,
    namespace: str = "",
    *,
    host: str = None,
    version: str = None,
    communities: str = None,
    user_auth = None,
    **kwargs,
):
    """Cache key builder for get_filtered_events function based on filter parameters."""
    key_parts = [
        namespace,
        func.__name__,
        host or "unknown",
        version or "unknown",
        communities or "all"
    ]

    # Add user-specific cache key components
    if user_auth:
        if user_auth.is_superuser:
            key_parts.append("superuser")
        elif user_auth.discord_account:
            # Cache based on user's accessible communities
            communities = sorted(user_auth.discord_account.user_communities or [])
            key_parts.append(f"communities:{','.join(communities)}")
        else:
            key_parts.append("authenticated")
    else:
        key_parts.append("anonymous")

    return ":".join(key_parts)
