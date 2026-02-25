"""
DataForge Configuration

Central configuration for constants and settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# Chunking Configuration
# ============================================
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# ============================================
# Embedding Configuration
# ============================================
# Note: Anthropic (Claude) doesn't provide embeddings API
# Use Voyage AI (owned by Anthropic) for embeddings
EMBEDDING_MODEL = "voyage-large-2"  # Default to Voyage AI
EMBEDDING_DIMENSION = int(os.getenv("FORGE_EMBED_DIM", "1536"))  # Ecosystem-wide; voyage-large-2 = 1536
MAX_EMBEDDING_INPUT_LENGTH = 8000  # Max chars for embedding API

# ============================================
# Search Configuration
# ============================================
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.7
MAX_SEARCH_LIMIT = 100

# ============================================
# Input Validation
# ============================================
MAX_DOCUMENT_LENGTH = 1000000  # 1MB of text
MAX_TITLE_LENGTH = 500
MAX_QUERY_LENGTH = 2000

# ============================================
# Rate Limiting
# ============================================
RATE_LIMIT_SEARCH = "20/minute"  # 20 searches per minute
RATE_LIMIT_ADMIN = "100/minute"  # 100 admin operations per minute

# ============================================
# Database Configuration
# ============================================
DATABASE_URL = os.getenv("DATAFORGE_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dataforge")

# ============================================
# Redis Configuration (Caching)
# ============================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ============================================
# Security Configuration
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET_KEY"))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# ============================================
# NeuroForge Integration (Law 2)
# ============================================
# All AI operations (embeddings, inference) route through NeuroForge.
# API keys are managed by NeuroForge, not by DataForge.
NEUROFORGE_URL = os.getenv("NEUROFORGE_URL", "http://127.0.0.1:8000")

# Legacy API keys — kept for backward compatibility but NO LONGER USED
# for embeddings. NeuroForge handles all provider routing.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# ============================================
# Server Configuration
# ============================================
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8788"))  # Default port for DataForge
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:8021,http://127.0.0.1:8022").split(",")

# ============================================
# CORS Configuration
# ============================================
CORS_ALLOW_METHODS = ["GET", "POST", "PATCH", "DELETE"]
CORS_ALLOW_HEADERS = ["*"]

# ============================================
# Logging Configuration
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================
# Compression Configuration (Phase 3)
# ============================================
COMPRESSION_ENABLED = os.getenv("COMPRESSION_ENABLED", "false").lower() == "true"
FORGECOMMAND_COMPRESSION_URL = os.getenv("FORGECOMMAND_COMPRESSION_URL", "http://127.0.0.1:8003")
COMPRESSION_MIN_SIZE = int(os.getenv("COMPRESSION_MIN_SIZE", "1024"))
COMPRESSION_POLL_INTERVAL = int(os.getenv("COMPRESSION_POLL_INTERVAL", "300"))


def validate_config():
    """
    Validate that required configuration is present.
    Raises ValueError if critical config is missing.
    
    SECURITY: Validates that sensitive configuration is properly set
    for the deployment environment (development vs production).
    """
    errors = []
    warnings = []

    # Check Redis configuration (optional but recommended)
    if not REDIS_URL:
        warnings.append(
            "WARNING: REDIS_URL not configured. Caching disabled. "
            "Set REDIS_URL for better performance."
        )

    # Check SECRET_KEY
    if not SECRET_KEY:
        errors.append(
            "SECRET_KEY is not set. Required for JWT token signing. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    elif SECRET_KEY in ("your-secret-key-here-change-this-in-production", "your-secret-key-here-change-in-production", ""):
        errors.append(
            "SECRET_KEY is set to the default placeholder value. "
            "MUST use a strong, random secret key in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # Check embedding provider (legacy — NeuroForge handles all embeddings per Law 2)
    if not VOYAGE_API_KEY and not OPENAI_API_KEY and not COHERE_API_KEY:
        warnings.append(
            "WARNING: No legacy embedding provider API key configured. "
            "Embeddings route through NeuroForge (Law 2). "
            "Set VOYAGE_API_KEY only if direct embedding fallback is needed."
        )

    # Check database URL
    if not DATABASE_URL:
        errors.append("DATAFORGE_DATABASE_URL must be set")
    elif "localhost" in DATABASE_URL and "production" in os.getenv("ENVIRONMENT", "development").lower():
        warnings.append("WARNING: Using localhost database URL in production environment")

    # Warn about default database credentials (if using Docker default)
    if "postgres:postgres" in DATABASE_URL:
        warnings.append(
            "WARNING: Using default PostgreSQL credentials (postgres:postgres). "
            "Change POSTGRES_PASSWORD in production."
        )

    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(f"  ❌ {e}" for e in errors)
        if warnings:
            error_message += "\n\n" + "\n".join(f"  ⚠️  {w}" for w in warnings)
        raise ValueError(error_message)

    if warnings:
        import logging
        logger = logging.getLogger(__name__)
        for warning in warnings:
            logger.warning(warning)


def get_redis_enabled() -> bool:
    """
    Check if Redis is configured and should be used.
    Returns False if REDIS_URL is not set.
    """
    return bool(REDIS_URL)


def get_embedding_provider():
    """
    Determine which embedding provider to use based on available API keys.
    Priority: Voyage AI (Anthropic-owned) > OpenAI > Cohere
    Returns: tuple of (provider_name, api_key)
    """
    if VOYAGE_API_KEY:
        return ("voyage-ai", VOYAGE_API_KEY)
    elif OPENAI_API_KEY:
        return ("openai", OPENAI_API_KEY)
    elif COHERE_API_KEY:
        return ("cohere", COHERE_API_KEY)
    else:
        return (None, None)
