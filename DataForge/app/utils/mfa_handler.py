"""
Multi-Factor Authentication (MFA) Handler

Implements TOTP-based MFA with backup codes, QR code generation,
and email verification for secure account access.
"""

import logging
import secrets
import hashlib
import time
import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class MFAMethod(Enum):
    """Supported MFA methods."""
    TOTP = "totp"  # Time-based One-Time Password
    EMAIL = "email"  # Email verification codes


class VerificationStatus(Enum):
    """Email verification status."""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"


@dataclass
class TOTPSecret:
    """TOTP secret configuration."""
    secret: str  # Base32 encoded secret
    user_id: str
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    verified: bool = False
    backup_codes: List[str] = field(default_factory=list)
    last_used_counter: int = 0


@dataclass
class VerificationCode:
    """Email verification code."""
    code: str
    email: str
    user_id: Optional[str] = None
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    expires_in: int = 600  # 10 minutes
    used: bool = False
    verification_type: str = "email_verification"  # or "mfa_setup", "password_reset"
    
    def is_valid(self) -> bool:
        """Check if code is still valid."""
        if self.used:
            return False
        elapsed = datetime.utcnow().timestamp() - self.created_at
        return elapsed < self.expires_in


class TOTP:
    """
    Time-based One-Time Password (TOTP) implementation.
    
    Implements RFC 6238 for generating and verifying time-based OTP codes.
    """
    
    DIGITS = 6  # Standard TOTP digits
    TIME_STEP = 30  # Time window in seconds
    
    @staticmethod
    def generate_secret() -> str:
        """
        Generate a new TOTP secret.
        
        Returns:
            Base32 encoded secret (32 bytes)
        """
        random_bytes = secrets.token_bytes(20)
        # Simple base32 encoding without padding
        import base64
        return base64.b32encode(random_bytes).decode().rstrip("=")
    
    @staticmethod
    def get_totp(secret: str, timestamp: Optional[float] = None) -> str:
        """
        Generate TOTP code for current time.
        
        Args:
            secret: Base32 encoded secret
            timestamp: Optional Unix timestamp (defaults to current time)
            
        Returns:
            6-digit TOTP code
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Decode base32 secret
        import base64
        try:
            # Add padding if needed
            padded_secret = secret + ("=" * (8 - len(secret) % 8)) if len(secret) % 8 else secret
            secret_bytes = base64.b32decode(padded_secret, casefold=True)
        except Exception as e:
            logger.error(f"Failed to decode TOTP secret: {e}")
            return "000000"
        
        # Calculate time counter
        counter = int(timestamp) // TOTP.TIME_STEP
        
        # HMAC-SHA1
        counter_bytes = counter.to_bytes(8, byteorder='big')
        import hmac
        hmac_result = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
        
        # Extract 4 bytes
        offset = hmac_result[-1] & 0x0f
        code_int = (
            (hmac_result[offset] & 0x7f) << 24 |
            (hmac_result[offset + 1] & 0xff) << 16 |
            (hmac_result[offset + 2] & 0xff) << 8 |
            (hmac_result[offset + 3] & 0xff)
        )
        
        # Extract last 6 digits
        code = code_int % (10 ** TOTP.DIGITS)
        return str(code).zfill(TOTP.DIGITS)
    
    @staticmethod
    def verify_totp(
        secret: str,
        code: str,
        window: int = 1,
    ) -> bool:
        """
        Verify TOTP code.
        
        Args:
            secret: Base32 encoded secret
            code: 6-digit code to verify
            window: Number of time steps to check before/after current
            
        Returns:
            True if code is valid
        """
        current_time = time.time()
        
        # Check current and neighboring time windows
        for i in range(-window, window + 1):
            timestamp = current_time + (i * TOTP.TIME_STEP)
            if TOTP.get_totp(secret, timestamp) == code:
                return True
        
        return False
    
    @staticmethod
    def get_provisioning_uri(secret: str, user: str, issuer: str) -> str:
        """
        Get otpauth:// URI for QR code generation.
        
        Args:
            secret: Base32 encoded secret
            user: User identifier (email)
            issuer: Service name
            
        Returns:
            otpauth:// URI
        """
        import urllib.parse
        
        # Escape user and issuer
        user_escaped = urllib.parse.quote(user, safe='')
        issuer_escaped = urllib.parse.quote(issuer, safe='')
        
        return (
            f"otpauth://totp/{issuer_escaped}:{user_escaped}?"
            f"secret={secret}&issuer={issuer_escaped}"
        )


class BackupCodeGenerator:
    """Generate and manage backup codes for MFA."""
    
    NUM_CODES = 10
    CODE_LENGTH = 8
    
    @staticmethod
    def generate_backup_codes() -> List[str]:
        """
        Generate backup codes.
        
        Returns:
            List of 10 backup codes
        """
        codes = []
        for _ in range(BackupCodeGenerator.NUM_CODES):
            code = secrets.token_hex(BackupCodeGenerator.CODE_LENGTH // 2).upper()
            # Format as XXXX-XXXX
            code = f"{code[:4]}-{code[4:]}"
            codes.append(code)
        return codes
    
    @staticmethod
    def hash_backup_code(code: str) -> str:
        """Hash backup code for storage."""
        return hashlib.sha256(code.encode()).hexdigest()
    
    @staticmethod
    def verify_backup_code(code: str, hashed: str) -> bool:
        """Verify backup code against hash."""
        return BackupCodeGenerator.hash_backup_code(code) == hashed


class EmailVerificationManager:
    """Manages email verification codes."""
    
    def __init__(self, max_codes: int = 5000):
        """Initialize email verification manager."""
        self.max_codes = max_codes
        self.codes: Dict[str, VerificationCode] = {}
    
    def generate_verification_code(
        self,
        email: str,
        user_id: Optional[str] = None,
        verification_type: str = "email_verification",
    ) -> str:
        """
        Generate email verification code.
        
        Args:
            email: Email address to verify
            user_id: Optional user ID
            verification_type: Type of verification (email_verification, mfa_setup, password_reset)
            
        Returns:
            6-digit verification code
        """
        code = str(secrets.randbelow(999999)).zfill(6)
        
        verification_code = VerificationCode(
            code=code,
            email=email,
            user_id=user_id,
            verification_type=verification_type,
        )
        
        self.codes[code] = verification_code
        
        # Cleanup if too many codes
        if len(self.codes) > self.max_codes:
            self._cleanup_expired_codes()
        
        return code
    
    def verify_code(
        self,
        code: str,
        email: str,
        verification_type: str = "email_verification",
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify email code.
        
        Args:
            code: Code to verify
            email: Email address that code was sent to
            verification_type: Expected verification type
            
        Returns:
            Tuple of (is_valid, user_id)
        """
        if code not in self.codes:
            logger.warning(f"Invalid verification code: {code}")
            return False, None
        
        verification_code = self.codes[code]
        
        # Validate code
        if not verification_code.is_valid():
            logger.warning(f"Expired verification code: {code}")
            return False, None
        
        if verification_code.email != email:
            logger.warning(f"Email mismatch for verification code: {code}")
            return False, None
        
        if verification_code.verification_type != verification_type:
            logger.warning(f"Verification type mismatch for code: {code}")
            return False, None
        
        # Mark code as used
        verification_code.used = True
        
        return True, verification_code.user_id
    
    def _cleanup_expired_codes(self) -> None:
        """Remove expired verification codes."""
        expired = [
            code for code, verification_code in self.codes.items()
            if not verification_code.is_valid()
        ]
        
        for code in expired:
            self.codes.pop(code, None)
        
        logger.info(f"Cleaned up {len(expired)} expired verification codes")


class MFAManager:
    """
    Manages multi-factor authentication for users.
    
    Handles TOTP setup, backup code management, and email verification.
    """
    
    def __init__(self):
        """Initialize MFA manager."""
        self.totp_secrets: Dict[str, TOTPSecret] = {}  # user_id -> secret
        self.verified_emails: Dict[str, str] = {}  # user_id -> email
        self.email_manager = EmailVerificationManager()
        self.failed_attempts: Dict[str, int] = {}  # user_id -> attempt count
    
    def setup_totp(self, user_id: str) -> Tuple[str, str, List[str]]:
        """
        Setup TOTP for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (secret, provisioning_uri, backup_codes)
        """
        secret = TOTP.generate_secret()
        backup_codes = BackupCodeGenerator.generate_backup_codes()
        
        # Hash backup codes for storage
        hashed_codes = [
            BackupCodeGenerator.hash_backup_code(code)
            for code in backup_codes
        ]
        
        totp_secret = TOTPSecret(
            secret=secret,
            user_id=user_id,
            backup_codes=hashed_codes,
        )
        
        self.totp_secrets[user_id] = totp_secret
        
        provisioning_uri = TOTP.get_provisioning_uri(
            secret=secret,
            user=user_id,
            issuer="DataForge",
        )
        
        return secret, provisioning_uri, backup_codes
    
    def verify_totp_setup(self, user_id: str, code: str) -> bool:
        """
        Verify TOTP code during setup.
        
        Args:
            user_id: User ID
            code: 6-digit code from authenticator app
            
        Returns:
            True if setup verified
        """
        if user_id not in self.totp_secrets:
            logger.warning(f"User {user_id} has no TOTP secret")
            return False
        
        totp_secret = self.totp_secrets[user_id]
        
        if not TOTP.verify_totp(totp_secret.secret, code):
            logger.warning(f"Invalid TOTP code for user {user_id}")
            return False
        
        # Mark as verified
        totp_secret.verified = True
        logger.info(f"TOTP verified for user {user_id}")
        
        return True
    
    def verify_totp_login(self, user_id: str, code: str) -> bool:
        """
        Verify TOTP during login.
        
        Args:
            user_id: User ID
            code: 6-digit code from authenticator app
            
        Returns:
            True if code is valid
        """
        if user_id not in self.totp_secrets:
            logger.warning(f"User {user_id} has no TOTP secret")
            return False
        
        totp_secret = self.totp_secrets[user_id]
        
        if not totp_secret.verified:
            logger.warning(f"TOTP not verified for user {user_id}")
            return False
        
        if not TOTP.verify_totp(totp_secret.secret, code):
            logger.warning(f"Invalid TOTP code for user {user_id}")
            self.failed_attempts[user_id] = self.failed_attempts.get(user_id, 0) + 1
            return False
        
        # Reset failed attempts on successful verification
        self.failed_attempts[user_id] = 0
        
        return True
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """
        Verify backup code (e.g., when authenticator is lost).
        
        Args:
            user_id: User ID
            code: Backup code (XXXX-XXXX format)
            
        Returns:
            True if code is valid and marks it as used
        """
        if user_id not in self.totp_secrets:
            logger.warning(f"User {user_id} has no backup codes")
            return False
        
        totp_secret = self.totp_secrets[user_id]
        
        # Check all backup codes
        for i, hashed_code in enumerate(totp_secret.backup_codes):
            if BackupCodeGenerator.verify_backup_code(code, hashed_code):
                # Remove used code
                totp_secret.backup_codes.pop(i)
                logger.info(f"Backup code used for user {user_id}")
                return True
        
        logger.warning(f"Invalid backup code for user {user_id}")
        return False
    
    def generate_email_verification(
        self,
        email: str,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Generate email verification code.
        
        Args:
            email: Email to verify
            user_id: Optional user ID
            
        Returns:
            Verification code
        """
        code = self.email_manager.generate_verification_code(
            email=email,
            user_id=user_id,
            verification_type="email_verification",
        )
        return code
    
    def verify_email(self, code: str, email: str) -> Tuple[bool, Optional[str]]:
        """
        Verify email address.
        
        Args:
            code: Verification code sent to email
            email: Email address being verified
            
        Returns:
            Tuple of (is_valid, user_id)
        """
        is_valid, user_id = self.email_manager.verify_code(
            code=code,
            email=email,
            verification_type="email_verification",
        )
        
        if is_valid and user_id:
            self.verified_emails[user_id] = email
        
        return is_valid, user_id
    
    def is_email_verified(self, user_id: str) -> bool:
        """Check if user's email is verified."""
        return user_id in self.verified_emails
    
    def get_verified_email(self, user_id: str) -> Optional[str]:
        """Get user's verified email."""
        return self.verified_emails.get(user_id)
    
    def get_totp_status(self, user_id: str) -> Dict[str, any]:
        """
        Get TOTP status for user.
        
        Returns:
            Dict with TOTP status and backup codes remaining
        """
        if user_id not in self.totp_secrets:
            return {
                "enabled": False,
                "verified": False,
                "backup_codes": 0,
            }
        
        totp_secret = self.totp_secrets[user_id]
        return {
            "enabled": True,
            "verified": totp_secret.verified,
            "backup_codes": len(totp_secret.backup_codes),
        }


# Global MFA manager instance
_global_mfa_manager: Optional[MFAManager] = None


def get_mfa_manager() -> MFAManager:
    """Get or create global MFA manager."""
    global _global_mfa_manager
    
    if _global_mfa_manager is None:
        _global_mfa_manager = MFAManager()
    
    return _global_mfa_manager


def reset_mfa_manager() -> None:
    """Reset global manager (for testing)."""
    global _global_mfa_manager
    _global_mfa_manager = None
