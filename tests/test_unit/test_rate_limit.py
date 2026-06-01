"""
Unit tests for rate limiting.
"""
import pytest
import time
from unittest.mock import Mock
from fastapi import Request, HTTPException

from app.utils.rate_limit import RateLimiter, check_rate_limit, get_client_ip


@pytest.mark.unit
class TestRateLimiter:
    """Test RateLimiter class."""

    def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter()
        client_id = "test_client"

        # Should allow first request
        is_allowed, retry_after = limiter.check_rate_limit(client_id, max_requests=5, window_seconds=60)
        assert is_allowed is True
        assert retry_after == 0

    def test_rate_limiter_blocks_excess_requests(self):
        """Test that rate limiter blocks requests over limit."""
        limiter = RateLimiter()
        client_id = "test_client"

        # Make max_requests
        for _ in range(5):
            is_allowed, _ = limiter.check_rate_limit(client_id, max_requests=5, window_seconds=60)
            assert is_allowed is True

        # Next request should be blocked
        is_allowed, retry_after = limiter.check_rate_limit(client_id, max_requests=5, window_seconds=60)
        assert is_allowed is False
        assert retry_after > 0

    def test_rate_limiter_different_clients(self):
        """Test that different clients have separate limits."""
        limiter = RateLimiter()

        # Client 1 uses up their limit
        for _ in range(5):
            limiter.check_rate_limit("client1", max_requests=5, window_seconds=60)

        # Client 2 should still be allowed
        is_allowed, _ = limiter.check_rate_limit("client2", max_requests=5, window_seconds=60)
        assert is_allowed is True

    def test_rate_limiter_window_reset(self):
        """Test that rate limit resets after window."""
        limiter = RateLimiter()
        client_id = "test_client"

        # Use up limit with very short window
        for _ in range(3):
            limiter.check_rate_limit(client_id, max_requests=3, window_seconds=1)

        # Should be blocked
        is_allowed, _ = limiter.check_rate_limit(client_id, max_requests=3, window_seconds=1)
        assert is_allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        is_allowed, _ = limiter.check_rate_limit(client_id, max_requests=3, window_seconds=1)
        assert is_allowed is True

    def test_cleanup_old_entries(self):
        """Test that cleanup removes old entries."""
        limiter = RateLimiter()

        # Add some entries
        limiter.check_rate_limit("client1", max_requests=5, window_seconds=1)
        limiter.check_rate_limit("client2", max_requests=5, window_seconds=1)

        # Wait for entries to expire
        time.sleep(1.1)

        # Cleanup
        limiter.cleanup_old_entries(max_age_seconds=1)

        # Requests dict should be empty or cleaned
        assert len(limiter.requests) == 0 or all(
            len(timestamps) == 0 for timestamps in limiter.requests.values()
        )


@pytest.mark.unit
class TestClientIPExtraction:
    """Test client IP extraction."""
    
    def test_get_client_ip_direct(self):
        """Test getting IP from direct connection."""
        request = Mock(spec=Request)
        request.client.host = "192.168.1.1"
        request.headers = {}
        
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_forwarded(self):
        """Test getting IP from X-Forwarded-For header.

        With one trusted proxy hop (the default), the trustworthy address is
        the rightmost (proxy-appended) entry; the leftmost is client-supplied
        and therefore spoofable.
        """
        request = Mock(spec=Request)
        request.client.host = "127.0.0.1"
        request.headers.get = Mock(side_effect=lambda key: {
            "X-Forwarded-For": "203.0.113.1, 198.51.100.1"
        }.get(key))

        ip = get_client_ip(request)
        assert ip == "198.51.100.1"

    def test_get_client_ip_real_ip(self):
        """Test getting IP from X-Real-IP header."""
        request = Mock(spec=Request)
        request.client.host = "127.0.0.1"
        request.headers.get = Mock(side_effect=lambda key: {
            "X-Real-IP": "203.0.113.1"
        }.get(key))

        ip = get_client_ip(request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_no_client(self):
        """Test fallback when no client info."""
        request = Mock(spec=Request)
        request.client = None
        request.headers = {}
        
        ip = get_client_ip(request)
        assert ip == "unknown"


@pytest.mark.unit
class TestCheckRateLimit:
    """Test check_rate_limit function."""
    
    def test_check_rate_limit_allows(self):
        """Test that check_rate_limit allows requests within limit."""
        request = Mock(spec=Request)
        request.client.host = "192.168.1.1"
        request.headers = {}
        
        # Should not raise exception
        result = check_rate_limit(request, max_requests=10, window_seconds=60)
        assert result is None
    
    def test_check_rate_limit_blocks(self):
        """Test that check_rate_limit blocks excess requests."""
        request = Mock(spec=Request)
        request.client.host = "192.168.1.2"
        request.headers = {}
        
        # Make max requests
        for _ in range(3):
            check_rate_limit(request, max_requests=3, window_seconds=60)
        
        # Next should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(request, max_requests=3, window_seconds=60)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail

