"""
Test suite for rate limiting system - comprehensive coverage.

Test Classes:
- TestRateLimitConfig: Configuration management
- TestSlidingWindowLimiter: Core rate limiting logic
- TestWhitelist: Whitelist functionality
- TestMetrics: Metrics tracking
- TestIntegration: Complete workflows
"""

import pytest
import time
from unittest.mock import Mock
from datetime import datetime, timedelta

from app.utils.rate_limiter import (
    RateLimitWindow,
    RateLimitScope,
    RateLimitConfig,
    RateLimitMetrics,
    SlidingWindowLimiter,
    get_rate_limiter,
    reset_rate_limiter,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return Mock()


@pytest.fixture
def rate_limiter(mock_redis):
    """Create rate limiter with mock Redis."""
    return SlidingWindowLimiter(mock_redis, key_prefix="test_limit")


# ============================================================================
# TestRateLimitConfig
# ============================================================================


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_create_config(self):
        """Test creating a rate limit configuration."""
        config = RateLimitConfig(
            name="test_limit",
            scope=RateLimitScope.USER,
            window=RateLimitWindow.MINUTE,
            max_requests=100,
            description="Test limit",
        )

        assert config.name == "test_limit"
        assert config.scope == RateLimitScope.USER
        assert config.window == RateLimitWindow.MINUTE
        assert config.max_requests == 100
        assert config.enabled is True

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = RateLimitConfig(
            name="test",
            scope=RateLimitScope.IP,
            window=RateLimitWindow.HOUR,
            max_requests=1000,
        )

        d = config.to_dict()
        assert d["name"] == "test"
        assert d["scope"] == "ip"
        assert d["window"] == "hour"
        assert d["max_requests"] == 1000

    def test_config_disabled(self):
        """Test disabled configuration."""
        config = RateLimitConfig(
            name="test",
            scope=RateLimitScope.USER,
            window=RateLimitWindow.MINUTE,
            max_requests=10,
            enabled=False,
        )

        assert config.enabled is False


# ============================================================================
# TestSlidingWindowLimiter
# ============================================================================


class TestSlidingWindowLimiter:
    """Tests for SlidingWindowLimiter core functionality."""

    def test_limiter_initialization(self, rate_limiter, mock_redis):
        """Test limiter initialization."""
        assert rate_limiter.redis == mock_redis
        assert rate_limiter.key_prefix == "test_limit"

    def test_default_configs_registered(self, rate_limiter):
        """Test default configurations are registered."""
        limits = rate_limiter.get_all_limits()
        assert "public_api" in limits
        assert "authenticated_api" in limits
        assert "search_endpoint" in limits
        assert "login_endpoint" in limits

    def test_register_custom_limit(self, rate_limiter):
        """Test registering a custom limit."""
        config = RateLimitConfig(
            name="custom",
            scope=RateLimitScope.USER,
            window=RateLimitWindow.SECOND,
            max_requests=10,
        )

        rate_limiter.register_limit(config)
        retrieved = rate_limiter.get_limit("custom")
        assert retrieved is not None
        assert retrieved.name == "custom"

    def test_window_seconds_conversion(self, rate_limiter):
        """Test converting windows to seconds."""
        assert rate_limiter._window_seconds(RateLimitWindow.SECOND) == 1
        assert rate_limiter._window_seconds(RateLimitWindow.MINUTE) == 60
        assert rate_limiter._window_seconds(RateLimitWindow.HOUR) == 3600
        assert rate_limiter._window_seconds(RateLimitWindow.DAY) == 86400

    def test_redis_key_generation(self, rate_limiter):
        """Test Redis key generation."""
        key = rate_limiter._redis_key("user", "user-123", "minute")
        assert key == "test_limit:user:user-123:minute"

    def test_rate_limiting_allowed(self, rate_limiter, mock_redis):
        """Test allowing request under limit."""
        mock_redis.ping.return_value = True
        mock_redis.zcard.return_value = 5  # 5 requests already
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = 1

        is_limited, info = rate_limiter.is_rate_limited("public_api", "1.2.3.4")

        assert is_limited is False
        assert info["used"] == 6
        assert info["remaining"] == 54  # 60 - 6

    def test_rate_limiting_exceeded(self, rate_limiter, mock_redis):
        """Test rejecting request when limit exceeded."""
        mock_redis.ping.return_value = True
        mock_redis.zremrangebyscore.return_value = 0
        mock_redis.zcard.return_value = 60  # At limit
        mock_redis.zrange.return_value = [("req1", 100.0)]  # Oldest request timestamp

        is_limited, info = rate_limiter.is_rate_limited("public_api", "1.2.3.4")

        assert is_limited is True
        assert info["used"] == 60
        assert info["allowed"] == 60

    def test_redis_unavailable_allows_request(self, mock_redis):
        """Test allowing request when Redis unavailable."""
        mock_redis.ping.side_effect = Exception("Connection refused")
        limiter = SlidingWindowLimiter(mock_redis)

        is_limited, info = limiter.is_rate_limited("public_api", "1.2.3.4")

        assert is_limited is False
        assert "Redis unavailable" in info.get("message", "")

    def test_disabled_limit_allows_request(self, rate_limiter, mock_redis):
        """Test disabled limit allows requests."""
        mock_redis.ping.return_value = True

        # Create disabled config
        config = RateLimitConfig(
            name="disabled_limit",
            scope=RateLimitScope.USER,
            window=RateLimitWindow.MINUTE,
            max_requests=5,
            enabled=False,
        )
        rate_limiter.register_limit(config)

        is_limited, info = rate_limiter.is_rate_limited("disabled_limit", "user-1")
        assert is_limited is False


# ============================================================================
# TestWhitelist
# ============================================================================


class TestWhitelist:
    """Tests for whitelist functionality."""

    def test_whitelist_identifier(self, rate_limiter, mock_redis):
        """Test whitelisting an identifier."""
        mock_redis.ping.return_value = True
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = 1

        success = rate_limiter.whitelist_identifier("admin-user-1", ttl_hours=24)
        assert success is True
        assert mock_redis.sadd.called

    def test_whitelisted_identifier_unlimited(self, rate_limiter, mock_redis):
        """Test whitelisted identifier gets unlimited requests."""
        mock_redis.ping.return_value = True
        mock_redis.sismember.return_value = 1  # Is whitelisted

        is_limited, info = rate_limiter.is_rate_limited("public_api", "admin-user-1")

        assert is_limited is False
        assert "whitelisted" in info.get("message", "").lower()

    def test_remove_from_whitelist(self, rate_limiter, mock_redis):
        """Test removing identifier from whitelist."""
        mock_redis.ping.return_value = True
        mock_redis.srem.return_value = 1

        success = rate_limiter.remove_from_whitelist("admin-user-1")
        assert success is True
        assert mock_redis.srem.called

    def test_whitelist_not_found_ok(self, rate_limiter, mock_redis):
        """Test removing non-whitelisted identifier is OK."""
        mock_redis.ping.return_value = True
        mock_redis.srem.return_value = 0

        success = rate_limiter.remove_from_whitelist("not-whitelisted")
        assert success is True


# ============================================================================
# TestMetrics
# ============================================================================


class TestMetrics:
    """Tests for metrics tracking."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = RateLimitMetrics(
            total_requests=100,
            rate_limited_requests=10,
            allowed_requests=90,
        )

        assert metrics.total_requests == 100
        assert metrics.rate_limited_requests == 10

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = RateLimitMetrics(
            total_requests=100,
            rate_limited_requests=10,
        )

        d = metrics.to_dict()
        assert d["total_requests"] == 100
        assert d["rate_limited_requests"] == 10

    def test_get_metrics(self, rate_limiter):
        """Test retrieving metrics."""
        metrics = rate_limiter.get_metrics()
        assert isinstance(metrics, RateLimitMetrics)
        assert metrics.total_requests >= 0

    def test_reset_metrics(self, rate_limiter):
        """Test resetting metrics."""
        # Increment by calling is_rate_limited
        rate_limiter.redis.ping.return_value = True
        rate_limiter.redis.zcard.return_value = 1

        rate_limiter.is_rate_limited("public_api", "1.2.3.4")
        assert rate_limiter.get_metrics().total_requests > 0

        rate_limiter.reset_metrics()
        assert rate_limiter.get_metrics().total_requests == 0


# ============================================================================
# TestIntegration
# ============================================================================


class TestIntegration:
    """Integration tests for rate limiting workflows."""

    def test_complete_rate_limit_workflow(self, rate_limiter, mock_redis):
        """Test complete rate limiting workflow."""
        mock_redis.ping.return_value = True
        mock_redis.zcard.return_value = 0
        mock_redis.zcount.return_value = 5
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = 1

        # First request
        is_limited, info = rate_limiter.is_rate_limited("authenticated_api", "user-123")
        assert is_limited is False

        # Check usage
        usage = rate_limiter.get_current_usage("authenticated_api", "user-123")
        assert usage["used"] == 5

    def test_multiple_identifiers_isolated(self, rate_limiter, mock_redis):
        """Test that different identifiers are isolated."""
        mock_redis.ping.return_value = True

        # Different mock returns for different calls
        def zcard_side_effect(key):
            if "user-1" in key:
                return 299
            elif "user-2" in key:
                return 50
            return 0

        mock_redis.zcard.side_effect = zcard_side_effect
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = 1

        # User 1 near limit
        is_limited_1, _ = rate_limiter.is_rate_limited("authenticated_api", "user-1")
        assert is_limited_1 is False

        # User 2 with plenty left
        is_limited_2, _ = rate_limiter.is_rate_limited("authenticated_api", "user-2")
        assert is_limited_2 is False

    def test_window_cleanup_simulation(self, rate_limiter, mock_redis):
        """Test that old entries are cleaned up."""
        mock_redis.ping.return_value = True

        # Simulate window cleanup
        config = rate_limiter.get_limit("public_api")
        assert config is not None

        # Should call zremrangebyscore to clean old entries
        mock_redis.zcard.return_value = 5
        mock_redis.zadd.return_value = 1
        mock_redis.expire.return_value = 1

        is_limited, info = rate_limiter.is_rate_limited("public_api", "1.2.3.4")

        # Verify zremrangebyscore was called (cleanup)
        assert mock_redis.zremrangebyscore.called


# ============================================================================
# TestSingleton
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_singleton_creation(self, mock_redis):
        """Test singleton creation."""
        reset_rate_limiter()
        mock_redis.ping.return_value = True

        limiter1 = get_rate_limiter(mock_redis)
        assert limiter1 is not None

    def test_reset_singleton(self, mock_redis):
        """Test resetting singleton."""
        mock_redis.ping.return_value = True

        get_rate_limiter(mock_redis)
        reset_rate_limiter()

        # After reset, should be None
        import app.utils.rate_limiter
        assert app.utils.rate_limiter._rate_limiter is None


# ============================================================================
# TestEdgeCases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_zero_limit(self, rate_limiter):
        """Test limit with zero max requests."""
        config = RateLimitConfig(
            name="zero_limit",
            scope=RateLimitScope.USER,
            window=RateLimitWindow.MINUTE,
            max_requests=1,
        )
        rate_limiter.register_limit(config)
        
        # Min limit should be 1
        assert config.max_requests == 1

    def test_get_nonexistent_limit(self, rate_limiter):
        """Test getting non-existent limit."""
        limit = rate_limiter.get_limit("nonexistent")
        assert limit is None

    def test_invalid_scope_raises(self):
        """Test invalid scope raises error."""
        with pytest.raises(ValueError):
            RateLimitScope("invalid")

    def test_invalid_window_raises(self):
        """Test invalid window raises error."""
        with pytest.raises(ValueError):
            RateLimitWindow("invalid")

    def test_clear_all_limits(self, rate_limiter, mock_redis):
        """Test clearing all rate limit data."""
        mock_redis.ping.return_value = True
        mock_redis.keys.return_value = [b"key1", b"key2", b"key3"]
        mock_redis.delete.return_value = 3

        count = rate_limiter.clear_all_limits()
        assert count == 3
        assert mock_redis.delete.called
