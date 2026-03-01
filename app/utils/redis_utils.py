"""
Redis Cache Utilities

Provides caching decorators and Redis connection management with graceful fallback
for when Redis is unavailable. All cache operations are non-blocking and transparent.
"""
import asyncio
import functools
import json
import logging
from typing import Any, Callable, Optional, TypeVar, Union
from datetime import datetime, timedelta

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from app.utils.cache_governance import redis_set_with_ttl

logger = logging.getLogger(__name__)

# Global Redis client (lazy-initialized)
_redis_client: Optional[Redis] = None
_redis_enabled: bool = True

T = TypeVar("T")


async def get_redis_client() -> Optional[Redis]:
    """
    Get or initialize the Redis client with connection pooling.
    Returns None if Redis is disabled or connection fails.
    """
    global _redis_client, _redis_enabled

    if not _redis_enabled:
        return None

    if _redis_client is None:
        try:
            from app.config import REDIS_URL

            if not REDIS_URL:
                _redis_enabled = False
                logger.info("Redis disabled: REDIS_URL not configured")
                return None

            _redis_client = await aioredis.from_url(
                REDIS_URL,
                encoding="utf8",
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True,
            )

            # Test connection
            await _redis_client.ping()
            logger.info("Redis client initialized successfully")

        except (RedisError, RedisConnectionError) as e:
            _redis_enabled = False
            logger.warning(f"Redis connection failed: {e}. Cache disabled.")
            _redis_client = None
            return None
        except Exception as e:
            _redis_enabled = False
            logger.warning(f"Redis initialization error: {e}. Cache disabled.")
            _redis_client = None
            return None

    return _redis_client


async def close_redis():
    """Close the Redis connection."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.close()
            _redis_client = None
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


def make_cache_key(*args, prefix: str = "", **kwargs) -> str:
    """
    Generate a cache key from function arguments.

    Args:
        prefix: Cache key prefix (usually function name)
        args: Positional arguments (serializable)
        kwargs: Keyword arguments (serializable)

    Returns:
        Cache key string
    """
    parts = [prefix] if prefix else []

    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            parts.append(str(arg))
        elif arg is None:
            parts.append("None")

    # Add keyword arguments
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (str, int, float, bool)):
            parts.append(f"{key}={value}")
        elif value is None:
            parts.append(f"{key}=None")

    return ":".join(parts)


def cache_result(
    ttl_seconds: int = 300,
    key_prefix: Optional[str] = None,
    condition: Optional[Callable[..., bool]] = None,
):
    """
    Decorator to cache function results in Redis.

    Args:
        ttl_seconds: Time-to-live in seconds (default: 5 minutes)
        key_prefix: Custom cache key prefix (default: function name)
        condition: Optional callable to determine if caching should happen
                  Receives function args/kwargs, returns bool

    Example:
        @cache_result(ttl_seconds=300, key_prefix="user_projects")
        async def get_user_projects(user_id: int):
            # database query
            return projects

        # Cache key: "user_projects:123"
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        prefix = key_prefix or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Check if caching should be skipped
            if condition and not condition(*args, **kwargs):
                return await func(*args, **kwargs)

            cache_key = make_cache_key(*args, prefix=prefix, **kwargs)

            try:
                redis_client = await get_redis_client()
                if redis_client is None:
                    # Redis unavailable, call function directly
                    return await func(*args, **kwargs)

                # Try to get from cache
                cached = await redis_client.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    try:
                        return json.loads(cached)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to deserialize cache for {cache_key}")
                        await redis_client.delete(cache_key)

            except Exception as e:
                logger.warning(f"Cache retrieval error: {e}. Continuing without cache.")

            # Cache miss or error - call function
            result = await func(*args, **kwargs)

            # Try to cache result
            try:
                redis_client = await get_redis_client()
                if redis_client is not None and result is not None:
                    serialized = json.dumps(result, default=str)
                    await redis_set_with_ttl(redis_client, cache_key, serialized, ttl_seconds)
                    logger.debug(f"Cache set: {cache_key} (TTL: {ttl_seconds}s)")
            except Exception as e:
                logger.warning(f"Cache storage error: {e}. Continuing without cache.")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Check if caching should be skipped
            if condition and not condition(*args, **kwargs):
                return func(*args, **kwargs)

            cache_key = make_cache_key(*args, prefix=prefix, **kwargs)

            try:
                # For sync functions, we can't use async Redis
                # This is a fallback that just calls the function
                logger.debug(f"Sync function {func.__name__} called (no caching)")

            except Exception as e:
                logger.warning(f"Cache error in sync wrapper: {e}")

            return func(*args, **kwargs)

        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


async def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., "user_projects:*")

    Returns:
        Number of keys deleted
    """
    try:
        redis_client = await get_redis_client()
        if redis_client is None:
            return 0

        cursor = "0"
        count = 0

        while True:
            cursor, keys = await redis_client.scan(
                cursor, match=pattern, count=100
            )
            if keys:
                count += await redis_client.delete(*keys)
            if cursor == "0":
                break

        logger.info(f"Invalidated {count} cache entries matching {pattern}")
        return count

    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")
        return 0


async def invalidate_cache_single(key: str) -> bool:
    """
    Invalidate a single cache entry.

    Args:
        key: Cache key to delete

    Returns:
        True if key was deleted, False otherwise
    """
    try:
        redis_client = await get_redis_client()
        if redis_client is None:
            return False

        result = await redis_client.delete(key)
        if result:
            logger.debug(f"Cache invalidated: {key}")
        return bool(result)

    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")
        return False


async def get_cache_stats() -> dict:
    """
    Get Redis cache statistics.

    Returns:
        Dictionary with cache stats (or empty dict if Redis unavailable)
    """
    try:
        redis_client = await get_redis_client()
        if redis_client is None:
            return {"status": "disabled"}

        info = await redis_client.info()
        return {
            "status": "active",
            "memory_used": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
        }

    except Exception as e:
        logger.warning(f"Error getting cache stats: {e}")
        return {"status": "error", "error": str(e)}


async def health_check() -> dict:
    """
    Check Redis connection health.

    Returns:
        Dictionary with health status
    """
    try:
        redis_client = await get_redis_client()
        if redis_client is None:
            return {"healthy": False, "reason": "Redis disabled or not configured"}

        await redis_client.ping()
        return {"healthy": True}

    except Exception as e:
        return {"healthy": False, "reason": str(e)}
