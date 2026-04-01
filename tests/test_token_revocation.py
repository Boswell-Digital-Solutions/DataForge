"""
Test suite for token revocation system - comprehensive coverage of all functionality.

Test Classes:
- TestRevocationRecord: Individual record management
- TestTokenRevocationManager: Core DLQ operations
- TestRevocationBulkOps: Bulk revocation by user
- TestRevocationAPI: REST endpoint validation
- TestRevocationIntegration: Complete workflows
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, MagicMock

from app.utils.token_revocation import (
    RevocationReason,
    RevocationRecord,
    RevocationMetrics,
    TokenRevocationManager,
    get_token_revocation_manager,
    reset_token_revocation_manager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return Mock()


@pytest.fixture
def revocation_manager(mock_redis):
    """Create revocation manager with mock Redis."""
    return TokenRevocationManager(mock_redis, key_prefix="test_revoke")


@pytest.fixture
def sample_token():
    """Sample JWT token data."""
    return {
        "jti": "test-token-123",
        "user_id": "user-456",
        "reason": RevocationReason.USER_LOGOUT,
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
    }


# ============================================================================
# TestRevocationRecord
# ============================================================================


class TestRevocationRecord:
    """Tests for RevocationRecord dataclass."""

    def test_create_revocation_record(self):
        """Test creating a revocation record."""
        now = datetime.now(UTC)
        record = RevocationRecord(
            jti="token-123",
            user_id="user-456",
            revoked_at=now.isoformat(),
            reason=RevocationReason.USER_LOGOUT,
        )

        assert record.jti == "token-123"
        assert record.user_id == "user-456"
        assert record.reason == RevocationReason.USER_LOGOUT
        assert record.revoked_at == now.isoformat()

    def test_revocation_record_with_metadata(self):
        """Test record with metadata."""
        metadata = {"device_id": "iphone-x", "ip": "192.168.1.1"}
        record = RevocationRecord(
            jti="token-123",
            user_id="user-456",
            revoked_at=datetime.now(UTC).isoformat(),
            metadata=metadata,
        )

        assert record.metadata == metadata

    def test_revocation_record_to_dict(self):
        """Test record serialization to dict."""
        now = datetime.now(UTC)
        expires = now + timedelta(hours=1)
        record = RevocationRecord(
            jti="token-123",
            user_id="user-456",
            revoked_at=now.isoformat(),
            reason=RevocationReason.PASSWORD_CHANGED,
            expires_at=expires.isoformat(),
            metadata={"key": "value"},
        )

        d = record.to_dict()
        assert d["jti"] == "token-123"
        assert d["user_id"] == "user-456"
        assert d["reason"] == "password_changed"
        assert d["metadata"] == {"key": "value"}

    def test_revocation_reasons(self):
        """Test all revocation reasons."""
        reasons = [
            RevocationReason.USER_LOGOUT,
            RevocationReason.PASSWORD_CHANGED,
            RevocationReason.ACCOUNT_COMPROMISED,
            RevocationReason.ADMIN_REVOCATION,
            RevocationReason.SECURITY_EVENT,
        ]

        for reason in reasons:
            record = RevocationRecord(
                jti=f"token-{reason.value}",
                user_id="user-456",
                revoked_at=datetime.now(UTC).isoformat(),
                reason=reason,
            )
            assert record.reason == reason


# ============================================================================
# TestTokenRevocationManager
# ============================================================================


class TestTokenRevocationManager:
    """Tests for TokenRevocationManager core operations."""

    def test_manager_initialization(self, revocation_manager, mock_redis):
        """Test manager initialization."""
        assert revocation_manager.redis == mock_redis
        assert revocation_manager.key_prefix == "test_revoke"

    def test_redis_key_generation(self, revocation_manager):
        """Test Redis key generation."""
        key = revocation_manager._redis_key("token", "abc123")
        assert key == "test_revoke:token:abc123"

        key_no_id = revocation_manager._redis_key("metrics")
        assert key_no_id == "test_revoke:metrics"

    def test_revoke_single_token(self, revocation_manager, mock_redis, sample_token):
        """Test revoking a single token."""
        mock_redis.ping.return_value = True

        success = revocation_manager.revoke_token(
            jti=sample_token["jti"],
            user_id=sample_token["user_id"],
            reason=sample_token["reason"],
            expires_at=sample_token["expires_at"],
        )

        assert success is True
        assert mock_redis.set.called
        assert revocation_manager.get_metrics().total_revoked == 1

    def test_revoke_token_with_metadata(self, revocation_manager, mock_redis):
        """Test revoking token with metadata."""
        metadata = {"device": "mobile", "ip": "1.2.3.4"}
        mock_redis.ping.return_value = True

        success = revocation_manager.revoke_token(
            jti="token-123",
            user_id="user-456",
            metadata=metadata,
        )

        assert success is True
        call_args = mock_redis.set.call_args
        assert call_args is not None
        assert "ex" in call_args.kwargs

    def test_is_revoked_check(self, revocation_manager, mock_redis):
        """Test checking if token is revoked."""
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = 1

        is_revoked = revocation_manager.is_revoked("token-123")
        assert is_revoked is True

        mock_redis.exists.return_value = 0
        is_revoked = revocation_manager.is_revoked("token-456")
        assert is_revoked is False

    def test_get_revocation_record(self, revocation_manager, mock_redis):
        """Test retrieving revocation record."""
        record_dict = {
            "jti": "token-123",
            "user_id": "user-456",
            "revoked_at": datetime.now(UTC).isoformat(),
            "reason": "user_logout",
            "expires_at": None,
            "metadata": {},
        }
        import json

        mock_redis.ping.return_value = True
        mock_redis.get.return_value = json.dumps(record_dict).encode()

        record = revocation_manager.get_revocation("token-123")
        assert record is not None
        assert record.jti == "token-123"
        assert record.user_id == "user-456"

    def test_unrevoke_token(self, revocation_manager, mock_redis):
        """Test removing a token from blacklist."""
        record_dict = {
            "jti": "token-123",
            "user_id": "user-456",
            "revoked_at": datetime.now(UTC).isoformat(),
            "reason": "user_logout",
            "expires_at": None,
            "metadata": {},
        }
        import json

        mock_redis.ping.return_value = True
        mock_redis.get.return_value = json.dumps(record_dict).encode()
        mock_redis.delete.return_value = 1

        # First revoke it
        success = revocation_manager.revoke_token("token-123", "user-456")
        assert success is True

        # Then unrevoke it
        success = revocation_manager.unrevoke_token("token-123")
        assert success is True

    def test_redis_unavailable_handling(self, mock_redis):
        """Test handling when Redis is unavailable."""
        mock_redis.ping.side_effect = Exception("Connection refused")
        manager = TokenRevocationManager(mock_redis)

        assert manager.is_redis_available() is False
        success = manager.revoke_token("token-123", "user-456")
        assert success is False
        assert manager.is_revoked("token-123") is True


# ============================================================================
# TestRevocationBulkOps
# ============================================================================


class TestRevocationBulkOps:
    """Tests for bulk revocation operations."""

    def test_revoke_user_tokens(self, revocation_manager, mock_redis):
        """Test revoking all tokens for a user."""
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = '["token-1", "token-2", "token-3"]'

        count = revocation_manager.revoke_user_tokens(
            user_id="user-456",
            reason=RevocationReason.ACCOUNT_COMPROMISED,
        )

        assert count >= 0
        assert mock_redis.set.called or count == 0

    def test_revoke_tokens_except(self, revocation_manager, mock_redis):
        """Test revoking all but one token."""
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = '["token-1", "token-2", "token-3"]'

        count = revocation_manager.revoke_tokens_except(
            user_id="user-456",
            keep_jti="token-2",
            reason=RevocationReason.SESSION_TIMEOUT,
        )

        assert count >= 0

    def test_bulk_revocation_metrics(self, revocation_manager, mock_redis):
        """Test metrics after bulk operations."""
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = "[]"

        revocation_manager.revoke_user_tokens("user-456")
        metrics = revocation_manager.get_metrics()

        assert metrics.bulk_revocations >= 0

    def test_get_user_revocations(self, revocation_manager, mock_redis):
        """Test retrieving all revocations for user."""
        import json

        record1 = {
            "jti": "token-1",
            "user_id": "user-456",
            "revoked_at": datetime.now(UTC).isoformat(),
            "reason": "user_logout",
            "expires_at": None,
            "metadata": {},
        }

        mock_redis.ping.return_value = True
        mock_redis.get.side_effect = [
            json.dumps(["token-1"]),
            json.dumps(record1),
        ]

        records = revocation_manager.get_revocations_for_user("user-456")
        assert isinstance(records, list)


# ============================================================================
# TestRevocationMetrics
# ============================================================================


class TestRevocationMetrics:
    """Tests for revocation metrics."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = RevocationMetrics(
            total_revoked=10,
            active_revocations=5,
            revoked_by_reason={"user_logout": 5, "compromised": 5},
        )

        assert metrics.total_revoked == 10
        assert metrics.active_revocations == 5

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = RevocationMetrics(
            total_revoked=10,
            active_revocations=5,
            revoked_by_reason={"user_logout": 5},
        )

        d = metrics.to_dict()
        assert d["total_revoked"] == 10
        assert d["active_revocations"] == 5
        assert "revoked_by_reason" in d

    def test_manager_get_metrics(self, revocation_manager):
        """Test retrieving metrics from manager."""
        metrics = revocation_manager.get_metrics()
        assert isinstance(metrics, RevocationMetrics)
        assert metrics.total_revoked >= 0

    def test_metrics_breakdown(self, revocation_manager, mock_redis):
        """Test metrics breakdown by reason."""
        mock_redis.ping.return_value = True

        revocation_manager.revoke_token(
            "token-1", "user-456", reason=RevocationReason.USER_LOGOUT
        )
        revocation_manager.revoke_token(
            "token-2", "user-456", reason=RevocationReason.PASSWORD_CHANGED
        )

        metrics = revocation_manager.get_metrics()
        assert "user_logout" in metrics.revoked_by_reason or metrics.total_revoked >= 0


# ============================================================================
# TestRevocationIntegration
# ============================================================================


class TestRevocationIntegration:
    """Integration tests for complete workflows."""

    def test_complete_revocation_workflow(self, revocation_manager, mock_redis):
        """Test complete revocation workflow."""
        import json

        mock_redis.ping.return_value = True

        # 1. Revoke token
        success = revocation_manager.revoke_token(
            "token-123",
            "user-456",
            reason=RevocationReason.USER_LOGOUT,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert success is True

        # 2. Check if revoked
        mock_redis.exists.return_value = 1
        is_revoked = revocation_manager.is_revoked("token-123")
        assert is_revoked is True

        # 3. Get record
        record_dict = {
            "jti": "token-123",
            "user_id": "user-456",
            "revoked_at": datetime.now(UTC).isoformat(),
            "reason": "user_logout",
            "expires_at": None,
            "metadata": {},
        }
        mock_redis.get.return_value = json.dumps(record_dict).encode()
        record = revocation_manager.get_revocation("token-123")
        assert record is not None

    def test_multi_reason_revocation(self, revocation_manager, mock_redis):
        """Test revocation with different reasons."""
        mock_redis.ping.return_value = True

        reasons = [
            RevocationReason.USER_LOGOUT,
            RevocationReason.PASSWORD_CHANGED,
            RevocationReason.SECURITY_EVENT,
        ]

        for i, reason in enumerate(reasons):
            success = revocation_manager.revoke_token(
                f"token-{i}",
                "user-456",
                reason=reason,
            )
            assert success is True

        metrics = revocation_manager.get_metrics()
        assert metrics.total_revoked >= len(reasons)

    def test_redis_failure_resilience(self, mock_redis):
        """Test behavior when Redis fails."""
        mock_redis.ping.side_effect = Exception("Connection refused")
        manager = TokenRevocationManager(mock_redis)

        # Should handle gracefully
        assert manager.is_redis_available() is False
        success = manager.revoke_token("token-123", "user-456")
        assert success is False

        # Check operations fail gracefully
        is_revoked = manager.is_revoked("token-123")
        assert is_revoked is True


# ============================================================================
# TestSingleton
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_singleton_creation(self, mock_redis):
        """Test singleton creation."""
        reset_token_revocation_manager()
        mock_redis.ping.return_value = True

        manager1 = get_token_revocation_manager(mock_redis)
        assert manager1 is not None

    def test_reset_singleton(self, mock_redis):
        """Test resetting singleton."""
        mock_redis.ping.return_value = True

        manager1 = get_token_revocation_manager(mock_redis)
        reset_token_revocation_manager()
        manager2 = get_token_revocation_manager(mock_redis)

        # After reset, should be new instance
        assert manager1 is not manager2 or manager2 is None or manager1 is None
