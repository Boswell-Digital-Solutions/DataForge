"""
Simple in-memory rate limiter for API endpoints.

For production use, consider using Redis-backed rate limiting.
"""
import os
import time
import logging
from collections import defaultdict
from fastapi import HTTPException, Request
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Number of trusted reverse-proxy hops in front of this service. The
# X-Forwarded-For header is appended to by each proxy, so the rightmost
# entries are the trustworthy ones and entries to the left are client-supplied
# (spoofable). Defaults to 1 (e.g. Render's load balancer). Set to 0 to ignore
# forwarding headers entirely when the service is directly exposed.
TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "1"))


class RateLimiter:
    """
    Simple in-memory rate limiter using token bucket algorithm.

    Note: This is a basic implementation suitable for single-instance deployments.
    For multi-instance deployments, use Redis-backed rate limiting.
    """

    def __init__(self):
        # Store: {ip: [(timestamp, count), ...]}
        self.requests: Dict[str, list] = defaultdict(list)

    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if the identifier has exceeded the rate limit.

        Args:
            identifier: IP address or user identifier
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        window_start = current_time - window_seconds

        # Clean old requests
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if ts > window_start
        ]

        # Check if limit exceeded
        request_count = len(self.requests[identifier])

        if request_count >= max_requests:
            # Calculate retry after time
            oldest_request = min(self.requests[identifier])
            retry_after = int(oldest_request + window_seconds - current_time) + 1
            return False, retry_after
        else:
            # Allow request and record it
            self.requests[identifier].append(current_time)
            return True, 0

    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """
        Cleanup entries older than max_age_seconds.
        Call this periodically to prevent memory bloat.
        """
        current_time = time.time()
        cutoff = current_time - max_age_seconds

        # Remove old identifiers
        identifiers_to_remove = []
        for identifier, timestamps in self.requests.items():
            # Remove old timestamps
            self.requests[identifier] = [
                ts for ts in timestamps if ts > cutoff
            ]
            # Mark identifier for removal if no recent requests
            if not self.requests[identifier]:
                identifiers_to_remove.append(identifier)

        for identifier in identifiers_to_remove:
            del self.requests[identifier]

        if identifiers_to_remove:
            logger.debug(f"Cleaned up {len(identifiers_to_remove)} old rate limit entries")

    def reset(self) -> None:
        """Clear all in-memory rate limit state."""
        self.requests.clear()


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, handling trusted reverse proxies.

    Only the proxy-appended (rightmost) entries of X-Forwarded-For are trusted,
    bounded by TRUSTED_PROXY_HOPS. Using the leftmost value would let a client
    spoof its IP and bypass rate limiting. When TRUSTED_PROXY_HOPS is 0,
    forwarding headers are ignored and the direct peer address is used.
    """
    if TRUSTED_PROXY_HOPS > 0:
        # Check for X-Forwarded-For header (set by reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                # Pick the address observed by the closest trusted proxy.
                idx = min(TRUSTED_PROXY_HOPS, len(parts))
                return parts[-idx]

        # Check for X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    # Fall back to direct client
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request, max_requests: int, window_seconds: int):
    """
    Dependency to check rate limit for an endpoint.

    Usage:
        @router.get("/endpoint")
        def endpoint(rate_limit: None = Depends(lambda r: check_rate_limit(r, 20, 60))):
            ...

    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds

    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = get_client_ip(request)

    is_allowed, retry_after = rate_limiter.check_rate_limit(
        client_ip,
        max_requests,
        window_seconds
    )

    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for {client_ip}. "
            f"Limit: {max_requests}/{window_seconds}s. "
            f"Retry after: {retry_after}s"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )
