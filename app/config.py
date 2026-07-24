"""
DataForge Configuration

Central configuration for constants and settings.
"""

import os
from functools import lru_cache
from types import SimpleNamespace

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
# Local development default. Only used when neither DATAFORGE_DATABASE_URL nor
# the conventional DATABASE_URL is set — a Render/Heroku-style platform injects
# DATABASE_URL, and operators commonly set that name by habit, so honor it as a
# fallback to avoid a silent connection-refused against a non-existent localhost
# Postgres (the failure mode of the Supabase log-poll cron).
_LOCAL_DB_DEFAULT = "postgresql://postgres:postgres@localhost:5432/dataforge"
DATABASE_URL = (
    os.getenv("DATAFORGE_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or _LOCAL_DB_DEFAULT
)
# True when no DB URL was configured and we fell back to the localhost dev
# default. Callers (e.g. cron scripts) can use this to fail fast with a clear
# message instead of a cryptic "connection refused" traceback.
DATABASE_URL_IS_DEFAULT = not (
    os.getenv("DATAFORGE_DATABASE_URL") or os.getenv("DATABASE_URL")
)
DB_CONNECT_TIMEOUT_SECONDS = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5"))
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "10000"))
DB_LOCK_TIMEOUT_MS = int(os.getenv("DB_LOCK_TIMEOUT_MS", "5000"))
DB_IDLE_IN_TX_TIMEOUT_MS = int(os.getenv("DB_IDLE_IN_TX_TIMEOUT_MS", "15000"))
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT_SECONDS = int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "10"))
DB_POOL_RECYCLE_SECONDS = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800"))

# ============================================
# Redis Configuration (Caching)
# ============================================
REDIS_URL = (os.getenv("REDIS_URL") or "redis://localhost:6379/0").strip()
# Defensive against pasted env values: a stray trailing newline/space breaks the
# connection (already stripped above); restore a missing scheme to redis://.
if REDIS_URL and "://" not in REDIS_URL:
    REDIS_URL = "redis://" + REDIS_URL

# Cache TTLs (seconds)
DOC_FETCH_CACHE_TTL = int(os.getenv("DOC_FETCH_CACHE_TTL", "600"))
SEARCH_RESULTS_CACHE_TTL = int(os.getenv("SEARCH_RESULTS_CACHE_TTL", "300"))
EMBEDDING_RESULTS_CACHE_TTL = int(os.getenv("EMBEDDING_RESULTS_CACHE_TTL", "86400"))
SESSION_OAUTH_TOTP_CACHE_TTL = int(os.getenv("SESSION_OAUTH_TOTP_CACHE_TTL", "900"))
CORPUS_CURRENT_VERSION_CACHE_TTL = int(os.getenv("CORPUS_CURRENT_VERSION_CACHE_TTL", "60"))

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
NEUROFORGE_URL = os.getenv("NEUROFORGE_URL", "https://neuroforge-9lxc.onrender.com")

# Legacy API keys — kept for backward compatibility but NO LONGER USED
# for embeddings. NeuroForge handles all provider routing.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# ============================================
# Supabase Log Ingestion (scheduled pull → durable evidence)
# ============================================
# Pulled on a schedule by scripts/poll_supabase_logs.py. Secrets are only needed
# by that cron job, not the web service, so they default empty and the poller
# fails closed when they are missing (API mode). See app/utils/supabase_log_ingest.
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN", "")  # Management API token (secret)
SUPABASE_API_BASE = os.getenv("SUPABASE_API_BASE", "https://api.supabase.com")
SUPABASE_LOG_SOURCE_TABLE = os.getenv("SUPABASE_LOG_SOURCE_TABLE", "edge_logs")
# Salt for one-way hashing of auth_user; if empty, identities are dropped, not hashed.
SUPABASE_LOG_IDENTITY_SALT = os.getenv("SUPABASE_LOG_IDENTITY_SALT", "")


def _optional_int_env(name: str, default: int) -> int | None:
    """Leave malformed operational settings invalid for a sanitized caller check."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return None


SUPABASE_LOG_POLL_LOOKBACK_SECONDS = _optional_int_env(
    "SUPABASE_LOG_POLL_LOOKBACK_SECONDS", 900
)
SUPABASE_LOG_POLL_OVERLAP_SECONDS = _optional_int_env(
    "SUPABASE_LOG_POLL_OVERLAP_SECONDS", 120
)
SUPABASE_LOG_POLL_MAX_ROWS = _optional_int_env("SUPABASE_LOG_POLL_MAX_ROWS", 1000)

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
# Explicit allow-list instead of "*". Wildcard headers combined with
# allow_credentials=True is overly permissive; enumerate the headers the app
# actually needs. Override via CORS_ALLOW_HEADERS (comma-separated) if required.
CORS_ALLOW_HEADERS = [
    h.strip()
    for h in os.getenv(
        "CORS_ALLOW_HEADERS",
        "Authorization,Content-Type,X-Correlation-ID,X-Request-ID",
    ).split(",")
    if h.strip()
]

# ============================================
# Logging Configuration
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

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
    is_production = "production" in os.getenv("ENVIRONMENT", "development").lower()
    if not DATABASE_URL:
        errors.append("DATAFORGE_DATABASE_URL (or DATABASE_URL) must be set")
    elif DATABASE_URL_IS_DEFAULT and is_production:
        errors.append(
            "No database URL configured in production — falling back to the "
            "localhost dev default, which will fail with 'connection refused'. "
            "Set DATAFORGE_DATABASE_URL (or DATABASE_URL) to the Supabase "
            "connection string."
        )
    elif "localhost" in DATABASE_URL and is_production:
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


@lru_cache(maxsize=1)
def get_settings():
    """
    Backwards-compatible settings accessor for tests and older modules.
    """
    provider, _ = get_embedding_provider()
    normalized_provider = (provider or "voyage-ai").replace("-ai", "")
    return SimpleNamespace(
        DATABASE_URL=DATABASE_URL,
        DB_CONNECT_TIMEOUT_SECONDS=DB_CONNECT_TIMEOUT_SECONDS,
        DB_STATEMENT_TIMEOUT_MS=DB_STATEMENT_TIMEOUT_MS,
        DB_LOCK_TIMEOUT_MS=DB_LOCK_TIMEOUT_MS,
        DB_IDLE_IN_TX_TIMEOUT_MS=DB_IDLE_IN_TX_TIMEOUT_MS,
        DB_POOL_SIZE=DB_POOL_SIZE,
        DB_MAX_OVERFLOW=DB_MAX_OVERFLOW,
        DB_POOL_TIMEOUT_SECONDS=DB_POOL_TIMEOUT_SECONDS,
        DB_POOL_RECYCLE_SECONDS=DB_POOL_RECYCLE_SECONDS,
        REDIS_URL=REDIS_URL,
        SECRET_KEY=SECRET_KEY,
        ALGORITHM=ALGORITHM,
        ACCESS_TOKEN_EXPIRE_MINUTES=ACCESS_TOKEN_EXPIRE_MINUTES,
        EMBEDDING_MODEL=EMBEDDING_MODEL,
        EMBEDDING_PROVIDER=normalized_provider,
        NEUROFORGE_URL=NEUROFORGE_URL,
        HOST=HOST,
        PORT=PORT,
        LOG_LEVEL=LOG_LEVEL,
        REQUEST_TIMEOUT_SECONDS=REQUEST_TIMEOUT_SECONDS,
    )


def get_rate_limit_ttl(window_seconds: int) -> int:
    """
    Calculate a Redis TTL for rate-limit windows.
    """
    return window_seconds + 60


class _CompatConfig:
    """
    Backwards-compatible object interface for older modules.
    """

    redis_url = REDIS_URL


config = _CompatConfig()
