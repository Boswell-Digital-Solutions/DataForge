"""
OAuth2 and OIDC Authentication

Implements OAuth2 authorization code flow with OIDC provider support
(Google, GitHub, Microsoft). Handles token management, user provisioning,
and secure session creation.
"""

import logging
import secrets
import hashlib
import json
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re

logger = logging.getLogger(__name__)


class OIDCProvider(Enum):
    """Supported OIDC providers."""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    CUSTOM = "custom"


class TokenType(Enum):
    """OAuth2 token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    ID = "id"


class GrantType(Enum):
    """OAuth2 grant types."""
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"


@dataclass
class OIDCProviderConfig:
    """Configuration for OIDC provider."""
    provider: OIDCProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    scopes: List[str] = field(default_factory=lambda: ["openid", "profile", "email"])


@dataclass
class AuthorizationCode:
    """Authorization code for OAuth2 flow."""
    code: str
    client_id: str
    redirect_uri: str
    scope: str
    user_id: Optional[str] = None
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    expires_in: int = 600  # 10 minutes
    used: bool = False
    
    def is_valid(self) -> bool:
        """Check if code is still valid."""
        if self.used:
            return False
        elapsed = datetime.utcnow().timestamp() - self.created_at
        return elapsed < self.expires_in


@dataclass
class AccessToken:
    """OAuth2 access token."""
    token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour
    scope: str = ""
    issued_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        elapsed = datetime.utcnow().timestamp() - self.issued_at
        return elapsed >= self.expires_in
    
    def remaining_seconds(self) -> int:
        """Get seconds until expiration."""
        elapsed = datetime.utcnow().timestamp() - self.issued_at
        return max(0, self.expires_in - int(elapsed))


@dataclass
class OIDCUserInfo:
    """User information from OIDC provider."""
    sub: str  # Subject (unique ID from provider)
    email: str
    email_verified: bool = False
    name: str = ""
    picture: str = ""
    provider: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sub": self.sub,
            "email": self.email,
            "email_verified": self.email_verified,
            "name": self.name,
            "picture": self.picture,
            "provider": self.provider,
        }


class OAuth2Manager:
    """
    Manages OAuth2 authorization code flow.
    
    Handles authorization code generation, token exchange, and token
    refresh for OIDC providers.
    """
    
    def __init__(self, max_auth_codes: int = 10000):
        """
        Initialize OAuth2 manager.
        
        Args:
            max_auth_codes: Maximum authorization codes to keep in memory
        """
        self.max_auth_codes = max_auth_codes
        self.auth_codes: Dict[str, AuthorizationCode] = {}
        self.providers: Dict[str, OIDCProviderConfig] = {}
    
    def register_provider(self, config: OIDCProviderConfig) -> None:
        """Register OIDC provider."""
        self.providers[config.provider.value] = config
        logger.info(f"Registered OIDC provider: {config.provider.value}")
    
    def generate_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Generate authorization code for OAuth2 flow.
        
        Args:
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI for authorization code
            scope: Requested scopes
            user_id: Optional user ID (if user authenticated at provider)
            
        Returns:
            Authorization code string
        """
        code = secrets.token_urlsafe(32)
        
        auth_code = AuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            user_id=user_id,
        )
        
        self.auth_codes[code] = auth_code
        
        # Cleanup if too many codes
        if len(self.auth_codes) > self.max_auth_codes:
            self._cleanup_expired_codes()
        
        return code
    
    def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        client_secret: str,
    ) -> Optional[Dict[str, str]]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            
        Returns:
            Token dict or None if code invalid
        """
        if code not in self.auth_codes:
            logger.warning(f"Invalid authorization code: {code}")
            return None
        
        auth_code = self.auth_codes[code]
        
        # Validate code
        if not auth_code.is_valid():
            logger.warning(f"Expired authorization code: {code}")
            return None
        
        if auth_code.client_id != client_id:
            logger.warning(f"Client ID mismatch for code: {code}")
            return None
        
        # Mark code as used
        auth_code.used = True
        
        # Generate access token
        access_token = self._generate_token(32)
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": "3600",
            "scope": auth_code.scope,
        }
    
    def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
    ) -> Optional[Dict[str, str]]:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token from previous token exchange
            client_id: OAuth2 client ID
            
        Returns:
            New token dict or None if refresh token invalid
        """
        # In production, would validate refresh token against database
        # For now, simulate successful refresh
        
        access_token = self._generate_token(32)
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": "3600",
        }
    
    def _generate_token(self, length: int = 32) -> str:
        """Generate secure random token."""
        return secrets.token_urlsafe(length)
    
    def _cleanup_expired_codes(self) -> None:
        """Remove expired authorization codes."""
        expired = [
            code for code, auth_code in self.auth_codes.items()
            if not auth_code.is_valid()
        ]
        
        for code in expired:
            self.auth_codes.pop(code, None)
        
        logger.info(f"Cleaned up {len(expired)} expired authorization codes")


class OIDCUserProvisioner:
    """
    Provisions and manages users from OIDC providers.
    
    Creates local user accounts on first login, updates user info on
    subsequent logins, and maps provider identities to local users.
    """
    
    def __init__(self):
        """Initialize user provisioner."""
        self.users: Dict[str, OIDCUserInfo] = {}  # user_id -> user_info
        self.provider_mappings: Dict[str, str] = {}  # provider:sub -> user_id
    
    def provision_user(
        self,
        user_info: OIDCUserInfo,
        local_user_id: Optional[str] = None,
    ) -> str:
        """
        Provision or update user from OIDC provider.
        
        Args:
            user_info: User information from provider
            local_user_id: Optional existing local user ID
            
        Returns:
            Local user ID
        """
        # Check if user already exists
        mapping_key = f"{user_info.provider}:{user_info.sub}"
        
        if mapping_key in self.provider_mappings:
            user_id = self.provider_mappings[mapping_key]
            # Update existing user
            self.users[user_id] = user_info
            logger.info(f"Updated user {user_id} from {user_info.provider}")
            return user_id
        
        # Create new user
        if local_user_id is None:
            # Generate user ID from email
            local_user_id = self._generate_user_id(user_info.email)
        
        self.users[local_user_id] = user_info
        self.provider_mappings[mapping_key] = local_user_id
        
        logger.info(f"Provisioned new user {local_user_id} from {user_info.provider}")
        return local_user_id
    
    def get_user(self, user_id: str) -> Optional[OIDCUserInfo]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_provider(self, provider: str, sub: str) -> Optional[str]:
        """Get local user ID by provider and subject."""
        mapping_key = f"{provider}:{sub}"
        return self.provider_mappings.get(mapping_key)
    
    def _generate_user_id(self, email: str) -> str:
        """Generate user ID from email."""
        # Use email hash as base
        hash_obj = hashlib.sha256(email.encode())
        return f"user_{hash_obj.hexdigest()[:16]}"


class PKCE:
    """
    PKCE (Proof Key for Public Clients) support.
    
    Implements RFC 7636 for enhanced security in OAuth2 flows for public
    clients (SPAs, mobile apps).
    """
    
    @staticmethod
    def generate_code_verifier() -> str:
        """
        Generate PKCE code verifier.
        
        Returns:
            Code verifier (43-128 unreserved characters)
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """
        Generate PKCE code challenge from verifier.
        
        Args:
            code_verifier: Code verifier from generate_code_verifier()
            
        Returns:
            Code challenge (base64url(SHA256(verifier)))
        """
        code_sha = hashlib.sha256(code_verifier.encode()).digest()
        # Base64url encode without padding
        import base64
        return base64.urlsafe_b64encode(code_sha).decode().rstrip("=")
    
    @staticmethod
    def verify_code_verifier(
        code_verifier: str,
        code_challenge: str,
    ) -> bool:
        """
        Verify PKCE code verifier matches challenge.
        
        Args:
            code_verifier: Original code verifier
            code_challenge: Challenge from authorization request
            
        Returns:
            True if valid
        """
        generated_challenge = PKCE.generate_code_challenge(code_verifier)
        return generated_challenge == code_challenge


# Global OAuth2 manager instance
_global_oauth2_manager: Optional[OAuth2Manager] = None


def get_oauth2_manager() -> OAuth2Manager:
    """Get or create global OAuth2 manager."""
    global _global_oauth2_manager
    
    if _global_oauth2_manager is None:
        _global_oauth2_manager = OAuth2Manager()
    
    return _global_oauth2_manager


def reset_oauth2_manager() -> None:
    """Reset global manager (for testing)."""
    global _global_oauth2_manager
    _global_oauth2_manager = None
