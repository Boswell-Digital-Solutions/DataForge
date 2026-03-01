"""
Token Revocation Manager - Redis-backed token blacklist for immediate token revocation.

This module provides a secure token revocation system that allows immediate invalidation
of JWT tokens without waiting for their natural expiration. Uses Redis for fast lookups
and automatic expiration of revocation records.

Features:
- Redis-backed blacklist with automatic TTL expiration
- Revoke tokens by JTI (JWT ID claim)
- Bulk revocation by user ID or token patterns
- Metrics tracking for revocation events
- Graceful fallback when Redis unavailable
- Token revocation reasons and timestamps
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Set, Any
import json
import logging
from functools import lru_cache

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, SESSION_OAUTH_TOTP_CACHE_TTL
from app.utils.cache_governance import redis_set_with_ttl_sync


logger = logging.getLogger(__name__)


class RevocationReason(str, Enum):
    """Reasons for token revocation."""
    USER_LOGOUT = "user_logout"
    PASSWORD_CHANGED = "password_changed"
    ACCOUNT_COMPROMISED = "account_compromised"
    ADMIN_REVOCATION = "admin_revocation"
    SESSION_TIMEOUT = "session_timeout"
    MFA_DISABLED = "mfa_disabled"
    PERMISSION_CHANGE = "permission_change"
    DEVICE_REMOVAL = "device_removal"
    SECURITY_EVENT = "security_event"


@dataclass
class RevocationRecord:
    """Record of a revoked token."""
    jti: str  # JWT ID claim
    user_id: str
    revoked_at: str  # ISO timestamp
    reason: RevocationReason = RevocationReason.USER_LOGOUT
    expires_at: Optional[str] = None  # ISO timestamp (when to auto-delete)
    metadata: Dict = field(default_factory=dict)  # Extra context

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "jti": self.jti,
            "user_id": self.user_id,
            "revoked_at": self.revoked_at,
            "reason": self.reason.value if isinstance(self.reason, RevocationReason) else self.reason,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }


@dataclass
class RevocationMetrics:
    """Metrics for token revocation system."""
    total_revoked: int = 0  # Total tokens revoked
    active_revocations: int = 0  # Currently blacklisted tokens
    revoked_by_reason: Dict[str, int] = field(default_factory=dict)  # Breakdown by reason
    bulk_revocations: int = 0  # Number of bulk revocation operations
    failed_revocations: int = 0  # Revocations that failed

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return asdict(self)


class TokenRevocationManager:
    """
    Manages JWT token revocation using Redis as the blacklist backend.

    Redis Key Structure:
    - `token:{jti}`: Revocation record (JSON) with TTL = token_exp_time - now
    - `user_revocations:{user_id}`: Set of revoked JTIs for user (for bulk operations)
    - `metrics`: Hash with revocation metrics
    """

    def __init__(self, redis_client: Any, key_prefix: str = "revoke"):
        """
        Initialize token revocation manager.

        Args:
            redis_client: Redis client instance (duck-typed, no redis dependency)
            key_prefix: Prefix for all Redis keys (default: 'revoke')
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self._metrics = RevocationMetrics()
        self._redis_available = self._check_redis_connection()

    def _check_redis_connection(self) -> bool:
        """Check if Redis is available."""
        try:
            self.redis.ping()
            logger.info("Token revocation manager connected to Redis")
            return True
        except Exception as e:
            logger.warning(f"Redis unavailable for token revocation: {e}")
            return False

    def _redis_key(self, key_type: str, identifier: str = "") -> str:
        """Generate Redis key with prefix."""
        if identifier:
            return f"{self.key_prefix}:{key_type}:{identifier}"
        return f"{self.key_prefix}:{key_type}"

    def _default_revocation_ttl(self) -> int:
        return max(ACCESS_TOKEN_EXPIRE_MINUTES * 60, SESSION_OAUTH_TOTP_CACHE_TTL)

    def _load_user_revocations(self, user_id: str) -> List[str]:
        try:
            raw = self.redis.get(self._redis_key("user_revocations", user_id))
            if not raw:
                return []
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except Exception as e:
            logger.error(f"Failed to load user revocations for {user_id}: {e}")
            return []

    def _store_user_revocations(self, user_id: str, jtis: List[str], ttl: int) -> None:
        redis_set_with_ttl_sync(
            self.redis,
            self._redis_key("user_revocations", user_id),
            json.dumps(sorted(set(jtis))),
            max(ttl, SESSION_OAUTH_TOTP_CACHE_TTL),
        )

    def revoke_token(
        self,
        jti: str,
        user_id: str,
        reason: RevocationReason = RevocationReason.USER_LOGOUT,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Revoke a single token by JTI.

        Args:
            jti: JWT ID claim (unique token identifier)
            user_id: User who owns the token
            reason: Why the token is being revoked
            expires_at: When to auto-delete revocation record (defaults to token expiration)
            metadata: Optional extra context (device info, IP, etc.)

        Returns:
            True if revocation successful, False if Redis unavailable
        """
        if not self._redis_available:
            logger.warning(f"Token revocation skipped (Redis unavailable): {jti}")
            return False

        try:
            record = RevocationRecord(
                jti=jti,
                user_id=user_id,
                revoked_at=datetime.utcnow().isoformat(),
                reason=reason,
                expires_at=expires_at.isoformat() if expires_at else None,
                metadata=metadata or {},
            )

            # Calculate TTL: expire revocation record when token would naturally expire
            ttl = self._default_revocation_ttl()
            if expires_at:
                ttl = max(int((expires_at - datetime.utcnow()).total_seconds()), 1)

            # Store revocation record
            token_key = self._redis_key("token", jti)
            record_json = json.dumps(record.to_dict())
            redis_set_with_ttl_sync(self.redis, token_key, record_json, ttl)

            # Track user's revoked tokens (for bulk operations)
            user_revocations = self._load_user_revocations(user_id)
            user_revocations.append(jti)
            self._store_user_revocations(user_id, user_revocations, ttl)

            # Update metrics
            self._metrics.total_revoked += 1
            self._metrics.active_revocations += 1
            reason_str = reason.value if isinstance(reason, RevocationReason) else reason
            self._metrics.revoked_by_reason[reason_str] = self._metrics.revoked_by_reason.get(reason_str, 0) + 1

            logger.info(f"Token revoked: {jti} ({reason.value})")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke token {jti}: {e}")
            self._metrics.failed_revocations += 1
            return False

    def is_revoked(self, jti: str) -> bool:
        """
        Check if a token is revoked.

        Args:
            jti: JWT ID claim to check

        Returns:
            True if token is revoked, False otherwise
        """
        if not self._redis_available:
            logger.warning(f"Redis unavailable for revocation check: {jti}")
            return True

        try:
            token_key = self._redis_key("token", jti)
            return self.redis.exists(token_key) > 0
        except Exception as e:
            logger.error(f"Failed to check revocation status for {jti}: {e}")
            return True

    def get_revocation(self, jti: str) -> Optional[RevocationRecord]:
        """
        Get revocation details for a token.

        Args:
            jti: JWT ID claim

        Returns:
            RevocationRecord if revoked, None otherwise
        """
        if not self._redis_available:
            return None

        try:
            token_key = self._redis_key("token", jti)
            record_json = self.redis.get(token_key)
            if not record_json:
                return None

            record_dict = json.loads(record_json)
            return RevocationRecord(**record_dict)

        except (Exception, json.JSONDecodeError) as e:
            logger.error(f"Failed to retrieve revocation record for {jti}: {e}")
            return None

    def revoke_user_tokens(
        self,
        user_id: str,
        reason: RevocationReason = RevocationReason.USER_LOGOUT,
        metadata: Optional[Dict] = None,
    ) -> int:
        """
        Revoke all tokens for a user.

        Args:
            user_id: User ID to revoke all tokens for
            reason: Why tokens are being revoked
            metadata: Optional extra context

        Returns:
            Number of tokens revoked
        """
        if not self._redis_available:
            logger.warning(f"User token revocation skipped (Redis unavailable): {user_id}")
            return 0

        try:
            jtis = self._load_user_revocations(user_id)
            count = 0

            for jti in jtis:
                if self.revoke_token(jti, user_id, reason, metadata=metadata):
                    count += 1

            self._metrics.bulk_revocations += 1
            logger.info(f"Revoked {count} tokens for user {user_id} ({reason.value})")
            return count

        except Exception as e:
            logger.error(f"Failed to revoke user tokens for {user_id}: {e}")
            self._metrics.failed_revocations += 1
            return 0

    def revoke_tokens_except(
        self,
        user_id: str,
        keep_jti: str,
        reason: RevocationReason = RevocationReason.SESSION_TIMEOUT,
    ) -> int:
        """
        Revoke all tokens for a user except one (useful for logout-everywhere-except-this).

        Args:
            user_id: User ID
            keep_jti: JTI to keep active
            reason: Why other tokens are being revoked

        Returns:
            Number of tokens revoked
        """
        if not self._redis_available:
            return 0

        try:
            jtis = self._load_user_revocations(user_id)
            count = 0

            for jti in jtis:
                if jti != keep_jti:
                    if self.revoke_token(jti, user_id, reason):
                        count += 1

            logger.info(f"Revoked {count} tokens for user {user_id} (kept {keep_jti})")
            return count

        except Exception as e:
            logger.error(f"Failed to revoke tokens for {user_id}: {e}")
            return 0

    def unrevoke_token(self, jti: str) -> bool:
        """
        Remove a token from the blacklist (restore it).

        Args:
            jti: JWT ID claim to restore

        Returns:
            True if successfully restored, False if not found or error
        """
        if not self._redis_available:
            return False

        try:
            token_key = self._redis_key("token", jti)
            revocation = self.get_revocation(jti)
            if not revocation:
                return False

            # Remove from blacklist
            deleted = self.redis.delete(token_key) > 0

            if deleted:
                remaining = [
                    item for item in self._load_user_revocations(revocation.user_id) if item != jti
                ]
                if remaining:
                    self._store_user_revocations(
                        revocation.user_id,
                        remaining,
                        self._default_revocation_ttl(),
                    )
                else:
                    self.redis.delete(self._redis_key("user_revocations", revocation.user_id))
                self._metrics.active_revocations = max(0, self._metrics.active_revocations - 1)
                logger.info(f"Token revocation removed: {jti}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to unrevoke token {jti}: {e}")
            return False

    def cleanup_expired(self) -> int:
        """
        Clean up expired revocation records (Redis handles this with TTL, but can be called manually).

        Redis automatically deletes expired keys, so this is mainly for logging/metrics.

        Returns:
            Number of keys cleaned (approximate)
        """
        if not self._redis_available:
            return 0

        # Redis handles expiration automatically with TTL, so we just return 0
        # This method exists for API completeness and potential future enhancements
        return 0

    def get_revocations_for_user(self, user_id: str) -> List[RevocationRecord]:
        """
        Get all revocation records for a user.

        Args:
            user_id: User ID

        Returns:
            List of revocation records
        """
        if not self._redis_available:
            return []

        try:
            jtis = self._load_user_revocations(user_id)
            records = []

            for jti in jtis:
                record = self.get_revocation(jti)
                if record:
                    records.append(record)

            return records

        except Exception as e:
            logger.error(f"Failed to get revocations for user {user_id}: {e}")
            return []

    def get_metrics(self) -> RevocationMetrics:
        """Get revocation metrics."""
        if self._redis_available:
            try:
                # Update active count from Redis
                self._metrics.active_revocations = self.redis.dbsize() or 0
            except Exception:
                pass  # Use cached value

        return self._metrics

    def reset_metrics(self) -> None:
        """Reset metrics to zero."""
        self._metrics = RevocationMetrics()

    def is_redis_available(self) -> bool:
        """Check if Redis is available."""
        return self._redis_available


# Global singleton instance
_revocation_manager: Optional[TokenRevocationManager] = None


def get_token_revocation_manager(redis_client: Any) -> TokenRevocationManager:
    """
    Get or create token revocation manager singleton.

    Args:
        redis_client: Redis client instance (duck-typed)

    Returns:
        TokenRevocationManager instance
    """
    global _revocation_manager
    if _revocation_manager is None:
        _revocation_manager = TokenRevocationManager(redis_client)
    return _revocation_manager


def reset_token_revocation_manager() -> None:
    """Reset the singleton (for testing)."""
    global _revocation_manager
    _revocation_manager = None
