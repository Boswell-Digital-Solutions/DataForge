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
EMBEDDING_DIMENSION = 1536  # voyage-large-2 = 1536, voyage-2 = 1024
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dataforge")

# ============================================
# Security Configuration
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# ============================================
# API Keys
# ============================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # For future use (Claude API)
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")  # Recommended for embeddings (Anthropic-owned)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# ============================================
# Server Configuration
# ============================================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# ============================================
# CORS Configuration
# ============================================
CORS_ALLOW_METHODS = ["GET", "POST", "PATCH", "DELETE"]
CORS_ALLOW_HEADERS = ["*"]

# ============================================
# Logging Configuration
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config():
    """
    Validate that required configuration is present.
    Raises ValueError if critical config is missing.
    """
    errors = []

    if not SECRET_KEY or SECRET_KEY == "your-secret-key-here-change-this-in-production":
        errors.append("SECRET_KEY must be set to a secure value")

    if not VOYAGE_API_KEY and not OPENAI_API_KEY and not COHERE_API_KEY:
        errors.append(
            "At least one embedding provider API key must be set "
            "(VOYAGE_API_KEY, OPENAI_API_KEY, or COHERE_API_KEY)"
        )

    if not DATABASE_URL:
        errors.append("DATABASE_URL must be set")

    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))


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
