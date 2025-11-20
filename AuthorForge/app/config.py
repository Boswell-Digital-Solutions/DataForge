"""Configuration management for AuthorForge"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATAFORGE_URL = os.getenv("DATAFORGE_URL", "http://localhost:8001")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# CORS configuration
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8080"
).split(",")

CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["*"]


def validate_config():
    """Validate required configuration"""
    errors = []

    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY environment variable is required")

    if errors:
        raise ValueError("\n".join(errors))


def get_config_info() -> dict:
    """Get configuration information for health checks"""
    return {
        "dataforge_url": DATAFORGE_URL,
        "debug": DEBUG,
        "log_level": LOG_LEVEL,
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
    }
