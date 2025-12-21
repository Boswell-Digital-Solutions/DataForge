"""
Rate Limiter - Sliding window rate limiting with Redis backend.

Implements a distributed rate limiting system that prevents API abuse
by tracking request rates per user, endpoint, or IP address. Uses Redis
for fast, distributed state management.

Features:
- Sliding window algorithm (per-second, per-minute, per-hour)
- Per-user, per-endpoint, per-IP rate limits
- Configurable thresholds and window sizes
- Graceful degradation when Redis unavailable
- Metrics tracking and monitoring
- Admin overrides for specific users/IPs
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple
import json
import logging
import time
from functools import lru_cache


logger = logging.getLogger(__name__)


class RateLimitWindow(str, Enum):
    """Time windows for rate limiting."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class RateLimitScope(str, Enum):
    """Scope of rate limiting."""
    USER = "user"  # Per authenticated user
    IP = "ip"  # Per IP address
    ENDPOINT = "endpoint"  # Per API endpoint
    COMBINED = "combined"  # User + endpoint or IP + endpoint


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    name: str
    scope: RateLimitScope
    window: RateLimitWindow
    max_requests: int
    description: str = ""
    enabled: bool = True
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "scope": self.scope.value,
            "window": self.window.value,
            "max_requests": self.max_requests,
            "description": self.description,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class RateLimitMetrics:
    """Metrics for rate limiting system."""
    total_requests: int = 0  # Total requests processed
    rate_limited_requests: int = 0  # Requests that hit rate limit
    allowed_requests: int = 0  # Requests allowed through
    exceeded_by_scope: Dict[str, int] = field(default_factory=dict)  # Breakdown by scope
    redis_errors: int = 0  # Redis connection errors
    active_limits: int = 0  # Currently enforced limits

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class SlidingWindowLimiter:
    """
    Sliding window rate limiter using Redis.

    Algorithm:
    1. For each request, use Redis ZSET with timestamp as score
    2. Remove expired entries (older than window)
    3. Count remaining entries
    4. If count >= limit: reject (rate limited)
    5. Otherwise: add request, accept
    
    Redis Key Structure:
    - `ratelimit:{scope}:{identifier}:{window}`: Sorted set of request timestamps
    - `ratelimit:config:{name}`: Rate limit configuration
    - `ratelimit:whitelist:{identifier}`: Whitelist set (unlimited requests)
    """

    def __init__(self, redis_client: Any, key_prefix: str = "ratelimit"):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance (duck-typed)
            key_prefix: Prefix for all Redis keys
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self._metrics = RateLimitMetrics()
        self._configs: Dict[str, RateLimitConfig] = {}
        self._redis_available = self._check_redis_connection()
        self._register_defaults()

    def _check_redis_connection(self) -> bool:
        """Check if Redis is available."""
        try:
            self.redis.ping()
            logger.info("Rate limiter connected to Redis")
            return True
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting: {e}")
            return False

    def _redis_key(self, scope: str, identifier: str, window: str) -> str:
        """Generate Redis key."""
        return f"{self.key_prefix}:{scope}:{identifier}:{window}"

    def _window_seconds(self, window: RateLimitWindow) -> int:
        """Get window size in seconds."""
        return {
            RateLimitWindow.SECOND: 1,
            RateLimitWindow.MINUTE: 60,
            RateLimitWindow.HOUR: 3600,
            RateLimitWindow.DAY: 86400,
        }[window]

    def _register_defaults(self) -> None:
        """Register default rate limit configurations."""
        defaults = [
            RateLimitConfig(
                name="public_api",
                scope=RateLimitScope.IP,
                window=RateLimitWindow.MINUTE,
                max_requests=60,
                description="Public API: 60 requests per minute per IP",
            ),
            RateLimitConfig(
                name="authenticated_api",
                scope=RateLimitScope.USER,
                window=RateLimitWindow.MINUTE,
                max_requests=300,
                description="Auth API: 300 requests per minute per user",
            ),
            RateLimitConfig(
                name="search_endpoint",
                scope=RateLimitScope.USER,
                window=RateLimitWindow.MINUTE,
                max_requests=30,
                description="Search: 30 requests per minute per user",
            ),
            RateLimitConfig(
                name="embeddings_endpoint",
                scope=RateLimitScope.USER,
                window=RateLimitWindow.MINUTE,
                max_requests=50,
                description="Embeddings: 50 requests per minute per user",
            ),
            RateLimitConfig(
                name="login_endpoint",
                scope=RateLimitScope.IP,
                window=RateLimitWindow.MINUTE,
                max_requests=5,
                description="Login: 5 attempts per minute per IP",
            ),
        ]

        for config in defaults:
            self.register_limit(config)

    def register_limit(self, config: RateLimitConfig) -> None:
        """Register a rate limit configuration."""
        self._configs[config.name] = config
        logger.info(f"Registered rate limit: {config.name}")

    def get_limit(self, name: str) -> Optional[RateLimitConfig]:
        """Get rate limit configuration by name."""
        return self._configs.get(name)

    def get_all_limits(self) -> Dict[str, RateLimitConfig]:
        """Get all rate limit configurations."""
        return {k: v for k, v in self._configs.items()}

    def is_whitelisted(self, identifier: str) -> bool:
        """Check if identifier is whitelisted."""
        if not self._redis_available:
            return False

        try:
            key = f"{self.key_prefix}:whitelist"
            return self.redis.sismember(key, identifier) > 0
        except Exception as e:
            logger.error(f"Failed to check whitelist: {e}")
            return False

    def whitelist_identifier(self, identifier: str, ttl_hours: int = 24) -> bool:
        """Add identifier to whitelist (unlimited requests)."""
        if not self._redis_available:
            return False

        try:
            key = f"{self.key_prefix}:whitelist"
            self.redis.sadd(key, identifier)
            if ttl_hours > 0:
                self.redis.expire(key, ttl_hours * 3600)
            logger.info(f"Whitelisted identifier: {identifier}")
            return True
        except Exception as e:
            logger.error(f"Failed to whitelist identifier: {e}")
            return False

    def remove_from_whitelist(self, identifier: str) -> bool:
        """Remove identifier from whitelist."""
        if not self._redis_available:
            return False

        try:
            key = f"{self.key_prefix}:whitelist"
            self.redis.srem(key, identifier)
            logger.info(f"Removed from whitelist: {identifier}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove from whitelist: {e}")
            return False

    def is_rate_limited(
        self,
        limit_name: str,
        identifier: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request should be rate limited.

        Args:
            limit_name: Name of the rate limit configuration
            identifier: User ID, IP, endpoint, or combined identifier

        Returns:
            (is_limited, info_dict) where:
            - is_limited: bool (True if request should be rejected)
            - info_dict: {'allowed': count, 'limit': max, 'window': window_name, 'reset_at': timestamp}
        """
        self._metrics.total_requests += 1

        config = self.get_limit(limit_name)
        if not config or not config.enabled:
            return False, {"message": "Limit not configured or disabled"}

        # Check whitelist
        if self.is_whitelisted(identifier):
            return False, {"message": "Identifier whitelisted", "unlimited": True}

        if not self._redis_available:
            # Fail open: allow requests if Redis unavailable
            logger.warning(f"Redis unavailable, allowing request for {identifier}")
            return False, {"message": "Redis unavailable, allowing request"}

        try:
            key = self._redis_key(
                config.scope.value,
                identifier,
                config.window.value,
            )
            window_seconds = self._window_seconds(config.window)
            now = time.time()
            cutoff = now - window_seconds

            # Remove old entries outside the window
            self.redis.zremrangebyscore(key, 0, cutoff)

            # Count requests in current window
            request_count = self.redis.zcard(key) or 0

            # Check if limit exceeded
            if request_count >= config.max_requests:
                self._metrics.rate_limited_requests += 1
                self._metrics.exceeded_by_scope[config.scope.value] = \
                    self._metrics.exceeded_by_scope.get(config.scope.value, 0) + 1

                # Calculate reset time
                oldest = self.redis.zrange(key, 0, 0, withscores=True)
                reset_at = oldest[0][1] + window_seconds if oldest else now + window_seconds

                return True, {
                    "limit_name": limit_name,
                    "allowed": config.max_requests,
                    "used": request_count,
                    "window": config.window.value,
                    "reset_in_seconds": int(reset_at - now),
                    "reset_at": int(reset_at),
                }

            # Add current request to the window
            self.redis.zadd(key, {str(now): now})
            self.redis.expire(key, window_seconds + 1)

            self._metrics.allowed_requests += 1

            return False, {
                "limit_name": limit_name,
                "allowed": config.max_requests,
                "used": request_count + 1,
                "remaining": config.max_requests - request_count - 1,
                "window": config.window.value,
                "reset_in_seconds": window_seconds,
            }

        except Exception as e:
            logger.error(f"Rate limit check failed for {identifier}: {e}")
            self._metrics.redis_errors += 1
            # Fail open: allow request
            return False, {"error": str(e), "message": "Rate limit check failed"}

    def get_current_usage(
        self,
        limit_name: str,
        identifier: str,
    ) -> Dict[str, Any]:
        """Get current usage for a limit without adding a request."""
        config = self.get_limit(limit_name)
        if not config:
            return {"error": "Limit not configured"}

        if not self._redis_available:
            return {"message": "Redis unavailable"}

        try:
            key = self._redis_key(
                config.scope.value,
                identifier,
                config.window.value,
            )
            window_seconds = self._window_seconds(config.window)
            now = time.time()
            cutoff = now - window_seconds

            # Count requests without removing
            request_count = self.redis.zcount(key, cutoff, now) or 0

            return {
                "limit_name": limit_name,
                "allowed": config.max_requests,
                "used": request_count,
                "remaining": max(0, config.max_requests - request_count),
                "window": config.window.value,
                "reset_in_seconds": window_seconds,
            }

        except Exception as e:
            logger.error(f"Failed to get usage for {identifier}: {e}")
            return {"error": str(e)}

    def reset_identifier_limit(self, limit_name: str, identifier: str) -> bool:
        """Manually reset rate limit counter for an identifier."""
        config = self.get_limit(limit_name)
        if not config:
            return False

        if not self._redis_available:
            return False

        try:
            key = self._redis_key(
                config.scope.value,
                identifier,
                config.window.value,
            )
            deleted = self.redis.delete(key) > 0
            logger.info(f"Reset limit {limit_name} for {identifier}")
            return deleted

        except Exception as e:
            logger.error(f"Failed to reset limit: {e}")
            return False

    def clear_all_limits(self) -> int:
        """Clear all rate limit data (careful with this!)."""
        if not self._redis_available:
            return 0

        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            logger.warning(f"Cleared {len(keys) or 0} rate limit keys")
            return len(keys) or 0
        except Exception as e:
            logger.error(f"Failed to clear limits: {e}")
            return 0

    def get_metrics(self) -> RateLimitMetrics:
        """Get rate limiting metrics."""
        if self._redis_available:
            try:
                self._metrics.active_limits = len(self._configs)
            except Exception:
                pass
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset metrics to zero."""
        self._metrics = RateLimitMetrics()

    def is_redis_available(self) -> bool:
        """Check if Redis is available."""
        return self._redis_available


# Global singleton instance
_rate_limiter: Optional[SlidingWindowLimiter] = None


def get_rate_limiter(redis_client: Any) -> SlidingWindowLimiter:
    """
    Get or create rate limiter singleton.

    Args:
        redis_client: Redis client instance

    Returns:
        SlidingWindowLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowLimiter(redis_client)
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reset the singleton (for testing)."""
    global _rate_limiter
    _rate_limiter = None
