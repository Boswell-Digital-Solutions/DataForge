"""
Security Configuration Module

Provides centralized security configuration, header middleware,
and security best practices for DataForge.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from app.config import CORS_ALLOW_HEADERS, CORS_ALLOW_METHODS

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Headers included:
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-Content-Type-Options: nosniff (prevent MIME type sniffing)
    - Strict-Transport-Security: enforce HTTPS
    - Content-Security-Policy: prevent XSS attacks
    - X-XSS-Protection: enable XSS filter in browsers
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enforce HTTPS for 1 year (31536000 seconds)
        # includeSubDomains ensures HSTS applies to subdomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Basic Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Enable XSS filter in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy for privacy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        
        return response


def configure_cors(app: FastAPI, allowed_origins: list = None):
    """
    Configure CORS with secure defaults.
    
    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origins (defaults to localhost only)
    """
    if allowed_origins is None:
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ]
    
    # Enumerate methods/headers instead of "*". A wildcard combined with
    # allow_credentials=True is both insecure and rejected by browsers, and
    # mirrors the live config in app/main.py (single source of truth in config.py).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
        max_age=600,  # 10 minutes
    )
    logger.info(f"CORS configured with allowed origins: {allowed_origins}")


def configure_security_headers(app: FastAPI):
    """
    Add security headers middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware configured")


def configure_security(app: FastAPI, allowed_origins: list = None):
    """
    Complete security configuration for the application.
    
    This is the main entry point for security setup.
    
    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed CORS origins
    """
    logger.info("Configuring application security...")
    
    # Add security headers
    configure_security_headers(app)
    
    # Configure CORS
    configure_cors(app, allowed_origins)
    
    logger.info("Security configuration complete")


# Security best practices checklist
SECURITY_CHECKLIST = {
    "authentication": {
        "oauth2_oidc": "✅ Implemented",
        "mfa_totp": "✅ Implemented",
        "mfa_backup_codes": "✅ Implemented",
        "device_tracking": "✅ Implemented",
        "session_management": "✅ Implemented",
    },
    "authorization": {
        "rbac": "✅ Implemented",
        "resource_level_checks": "✅ Implemented",
        "admin_operations": "✅ Implemented",
    },
    "encryption": {
        "at_rest_aes256": "✅ Implemented",
        "in_transit_tls13": "✅ Implemented",
        "key_rotation": "✅ Implemented",
        "certificate_pinning": "✅ Implemented",
    },
    "logging_audit": {
        "immutable_logs": "✅ Implemented",
        "hmac_signing": "✅ Implemented",
        "90_day_retention": "✅ Implemented",
        "real_time_alerting": "✅ Implemented",
    },
    "anomaly_detection": {
        "impossible_travel": "✅ Implemented",
        "brute_force": "✅ Implemented",
        "bulk_extraction": "✅ Implemented",
        "suspicious_patterns": "✅ Implemented",
        "after_hours_access": "✅ Implemented",
        "bulk_mutations": "✅ Implemented",
    },
    "infrastructure": {
        "fail2ban": "✅ Implemented",
        "rate_limiting": "✅ Implemented",
        "zero_trust_segmentation": "✅ Implemented",
        "security_headers": "✅ Added",
        "cors_configuration": "✅ Configured",
    },
    "backup_recovery": {
        "encrypted_snapshots": "✅ Implemented",
        "hourly_backups": "✅ Implemented",
        "daily_backups": "✅ Implemented",
        "weekly_backups": "✅ Implemented",
        "monthly_backups": "✅ Implemented",
        "pitr_capability": "✅ Implemented",
    },
    "supply_chain": {
        "pinned_dependencies": "✅ Configured",
        "no_saas_dependencies": "✅ Verified",
        "no_telemetry": "✅ Verified",
    },
}
