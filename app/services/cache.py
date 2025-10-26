"""Simple in-memory cache service."""
from cachetools import TTLCache
from typing import Any, Optional
from app.config import get_settings

settings = get_settings()

# Create a TTL cache with 100 items and TTL from settings
cache = TTLCache(maxsize=100, ttl=settings.cache_ttl)


def get_cached(key: str) -> Optional[Any]:
    """Get value from cache."""
    return cache.get(key)


def set_cached(key: str, value: Any) -> None:
    """Set value in cache."""
    cache[key] = value


def clear_cache() -> None:
    """Clear all cache entries."""
    cache.clear()
