"""
Security Authentication API Router (PHASE 4.1)

Provides REST endpoints for OAuth2/OIDC authentication, MFA setup and
verification, and email verification.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.utils.oauth2_oidc import (
    get_oauth2_manager,
    OAuth2Manager,
)
from app.utils.mfa_handler import (
    get_mfa_manager,
    MFAManager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth-secure", tags=["Security Authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AuthorizationRequest(BaseModel):
    """OAuth2 authorization request."""
    client_id: str = Field(..., description="OAuth2 client ID")
    redirect_uri: str = Field(..., description="Redirect URI")
    scope: str = Field(default="openid profile email", description="Requested scopes")
    state: str = Field(..., description="CSRF protection state")
    code_challenge: Optional[str] = Field(None, description="PKCE code challenge")


class AuthorizationResponse(BaseModel):
    """OAuth2 authorization response."""
    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State from request")


class TokenRequest(BaseModel):
    """OAuth2 token request."""
    grant_type: str = Field(..., description="Grant type (authorization_code or refresh_token)")
    code: Optional[str] = Field(None, description="Authorization code")
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    code_verifier: Optional[str] = Field(None, description="PKCE code verifier")


class TokenResponse(BaseModel):
    """OAuth2 token response."""
    access_token: str = Field(..., description="Access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(default=3600, description="Seconds until expiration")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    scope: Optional[str] = Field(None, description="Granted scopes")


class OIDCCallbackRequest(BaseModel):
    """OIDC provider callback."""
    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="State from original request")
    provider: str = Field(..., description="OIDC provider name")


class UserInfoResponse(BaseModel):
    """User information response."""
    user_id: str = Field(..., description="Local user ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    provider: str = Field(..., description="Authentication provider")
    email_verified: bool = Field(..., description="Email verification status")


class TOTPSetupRequest(BaseModel):
    """TOTP setup request."""
    user_id: str = Field(..., description="User ID")


class TOTPSetupResponse(BaseModel):
    """TOTP setup response."""
    secret: str = Field(..., description="Base32 encoded secret")
    qr_code_uri: str = Field(..., description="otpauth:// URI for QR code")
    backup_codes: list = Field(..., description="10 backup codes")


class TOTPVerifyRequest(BaseModel):
    """TOTP verification request."""
    user_id: str = Field(..., description="User ID")
    code: str = Field(..., description="6-digit TOTP code")


class TOTPVerifyResponse(BaseModel):
    """TOTP verification response."""
    verified: bool = Field(..., description="Whether TOTP was verified")


class EmailVerificationRequest(BaseModel):
    """Email verification request."""
    email: str = Field(..., description="Email address to verify")
    user_id: Optional[str] = Field(None, description="Optional user ID")


class EmailVerificationResponse(BaseModel):
    """Email verification response."""
    code: str = Field(..., description="6-digit verification code")
    expires_in: int = Field(default=600, description="Code expiration in seconds")


class EmailVerifyRequest(BaseModel):
    """Email verification confirmation."""
    code: str = Field(..., description="Verification code")
    email: str = Field(..., description="Email address")


class EmailVerifyResponse(BaseModel):
    """Email verification response."""
    verified: bool = Field(..., description="Whether email was verified")
    user_id: Optional[str] = Field(None, description="User ID if created")


class MFAStatusResponse(BaseModel):
    """MFA status response."""
    totp_enabled: bool = Field(..., description="Whether TOTP is enabled")
    totp_verified: bool = Field(..., description="Whether TOTP is verified")
    backup_codes_remaining: int = Field(..., description="Number of backup codes left")
    email_verified: bool = Field(..., description="Whether email is verified")


class BackupCodeVerifyRequest(BaseModel):
    """Backup code verification request."""
    user_id: str = Field(..., description="User ID")
    code: str = Field(..., description="Backup code (XXXX-XXXX)")


class BackupCodeVerifyResponse(BaseModel):
    """Backup code verification response."""
    verified: bool = Field(..., description="Whether backup code was valid")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_oauth2_manager_instance() -> OAuth2Manager:
    """Get OAuth2 manager instance."""
    return get_oauth2_manager()


def get_mfa_manager_instance() -> MFAManager:
    """Get MFA manager instance."""
    return get_mfa_manager()


# ============================================================================
# OAuth2 Authorization Endpoints
# ============================================================================

@router.post("/authorize", response_model=AuthorizationResponse)
async def authorize(
    request: AuthorizationRequest,
    manager: OAuth2Manager = Depends(get_oauth2_manager_instance),
) -> AuthorizationResponse:
    """
    OAuth2 authorization endpoint.
    
    Generates authorization code for OAuth2 authorization code flow.
    """
    # Validate client_id and redirect_uri
    # In production, would check against registered clients
    
    # Generate authorization code
    code = manager.generate_authorization_code(
        client_id=request.client_id,
        redirect_uri=request.redirect_uri,
        scope=request.scope,
    )
    
    logger.info(f"Generated authorization code for client {request.client_id}")
    
    return AuthorizationResponse(code=code, state=request.state)


@router.post("/token", response_model=TokenResponse)
async def token(
    request: TokenRequest,
    manager: OAuth2Manager = Depends(get_oauth2_manager_instance),
) -> TokenResponse:
    """
    OAuth2 token endpoint.
    
    Exchanges authorization code for access token.
    """
    if request.grant_type == "authorization_code":
        if not request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code required",
            )
        
        # Exchange code for token
        token_dict = manager.exchange_authorization_code(
            code=request.code,
            client_id=request.client_id,
            client_secret=request.client_secret,
        )
        
        if not token_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired authorization code",
            )
        
        logger.info(f"Issued access token for client {request.client_id}")
        
        return TokenResponse(
            access_token=token_dict["access_token"],
            token_type=token_dict["token_type"],
            expires_in=int(token_dict["expires_in"]),
            scope=token_dict.get("scope"),
        )
    
    elif request.grant_type == "refresh_token":
        if not request.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required",
            )
        
        # Refresh access token
        token_dict = manager.refresh_access_token(
            refresh_token=request.refresh_token,
            client_id=request.client_id,
        )
        
        if not token_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token",
            )
        
        logger.info(f"Refreshed access token for client {request.client_id}")
        
        return TokenResponse(
            access_token=token_dict["access_token"],
            token_type=token_dict["token_type"],
            expires_in=int(token_dict["expires_in"]),
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported grant type: {request.grant_type}",
        )


# ============================================================================
# OIDC Integration Endpoints
# ============================================================================

@router.post("/oidc/callback", response_model=UserInfoResponse)
async def oidc_callback(
    request: OIDCCallbackRequest,
    manager: OAuth2Manager = Depends(get_oauth2_manager_instance),
) -> UserInfoResponse:
    """
    OIDC provider callback.
    
    Handles OAuth2 callback from OIDC provider (Google, GitHub, etc.).
    """
    # Get provider config
    if request.provider not in manager.providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown OIDC provider: {request.provider}",
        )
    
    provider_config = manager.providers[request.provider]
    
    # In production, would:
    # 1. Exchange code for token from provider
    # 2. Get user info from provider userinfo endpoint
    # 3. Verify ID token signature
    # 4. Create/update local user
    
    # Simulated user info
    from app.utils.oauth2_oidc import OIDCUserInfo
    user_info = OIDCUserInfo(
        sub=f"provider_{request.provider}_user",
        email=f"user@{request.provider}.com",
        email_verified=True,
        name="Test User",
        provider=request.provider,
    )
    
    logger.info(f"OIDC callback from {request.provider}")
    
    return UserInfoResponse(
        user_id="user_123",
        email=user_info.email,
        name=user_info.name,
        picture=user_info.picture,
        provider=user_info.provider,
        email_verified=user_info.email_verified,
    )


# ============================================================================
# TOTP MFA Endpoints
# ============================================================================

@router.post("/mfa/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(
    request: TOTPSetupRequest,
    mfa: MFAManager = Depends(get_mfa_manager_instance),
) -> TOTPSetupResponse:
    """
    Setup TOTP for user.
    
    Generates TOTP secret and backup codes.
    """
    secret, qr_uri, backup_codes = mfa.setup_totp(user_id=request.user_id)
    
    logger.info(f"Started TOTP setup for user {request.user_id}")
    
    return TOTPSetupResponse(
        secret=secret,
        qr_code_uri=qr_uri,
        backup_codes=backup_codes,
    )


@router.post("/mfa/totp/verify-setup", response_model=TOTPVerifyResponse)
async def totp_verify_setup(
    request: TOTPVerifyRequest,
    mfa: MFAManager = Depends(get_mfa_manager_instance),
) -> TOTPVerifyResponse:
    """
    Verify TOTP setup.
    
    User confirms possession of authenticator app.
    """
    verified = mfa.verify_totp_setup(
        user_id=request.user_id,
        code=request.code,
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )
    
    logger.info(f"Verified TOTP setup for user {request.user_id}")
    
    return TOTPVerifyResponse(verified=True)


@router.post("/mfa/totp/verify-login", response_model=TOTPVerifyResponse)
async def totp_verify_login(
    request: TOTPVerifyRequest,
    mfa: MFAManager = Depends(get_mfa_manager_instance),
) -> TOTPVerifyResponse:
    """
    Verify TOTP during login.
    """
    verified = mfa.verify_totp_login(
        user_id=request.user_id,
        code=request.code,
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )
    
    logger.info(f"Verified TOTP login for user {request.user_id}")
    
    return TOTPVerifyResponse(verified=True)


@router.post("/mfa/backup-code/verify", response_model=BackupCodeVerifyResponse)
async def verify_backup_code(
    request: BackupCodeVerifyRequest,
    mfa: MFAManager = Depends(get_mfa_manager_instance),
) -> BackupCodeVerifyResponse:
    """
    Verify backup code.
    
    Can be used if authenticator device is lost.
    """
    verified = mfa.verify_backup_code(
        user_id=request.user_id,
        code=request.code,
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backup code",
        )
    
    logger.info(f"Verified backup code for user {request.user_id}")
    
    return BackupCodeVerifyResponse(verified=True)


# ============================================================================
# Email Verification Endpoints
# ============================================================================

@router.post("/email/send-verification", response_model=EmailVerificationResponse)
async def send_email_verification(
    request: EmailVerificationRequest,
    mfa: MFAManager = Depends(get_mfa_manager_instance),
) -> EmailVerificationResponse:
    """
    Send email verification code.
    
    Generates and sends 6-digit code to user's email.
    In production, would actually send email.
    """
    code = mfa.generate_email_verification(
        email=request.email,
        user_id=request.user_id,
    )
    
    logger.info(f"Generated email verification code for {request.email}")
    
    return EmailVerificationResponse(code=code)


@router.post("/email/verify", response_model=EmailVerifyResponse)
async def verify_email(
    request: EmailVerifyRequest,
    mfa: MFAManager = Depends(get_mfa_manager_instance),
) -> EmailVerifyResponse:
    """
    Verify email address.
    
    User confirms ownership of email by providing code.
    """
    is_valid, user_id = mfa.verify_email(
        code=request.code,
        email=request.email,
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )
    
    logger.info(f"Verified email {request.email}")
    
    return EmailVerifyResponse(verified=True, user_id=user_id)


# ============================================================================
# MFA Status Endpoint
# ============================================================================

@router.get("/mfa/status/{user_id}", response_model=MFAStatusResponse)
async def get_mfa_status(
    user_id: str,
    mfa: MFAManager = Depends(get_mfa_manager_instance),
) -> MFAStatusResponse:
    """Get MFA status for user."""
    totp_status = mfa.get_totp_status(user_id)
    
    return MFAStatusResponse(
        totp_enabled=totp_status["enabled"],
        totp_verified=totp_status["verified"],
        backup_codes_remaining=totp_status["backup_codes"],
        email_verified=mfa.is_email_verified(user_id),
    )
