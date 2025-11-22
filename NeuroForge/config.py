"""
NeuroForge Configuration

Simple configuration module for environment variables and settings.
"""

import os
from typing import Optional


class Config:
    """Configuration class for NeuroForge."""
    
    def __init__(self):
        # Server settings
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # CORS settings
        self.cors_origins: list[str] = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000"
        ).split(",")
        
        # Database settings
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "sqlite+aiosqlite:///./neuroforge.db"
        )
        
        # API keys
        self.admin_api_key: Optional[str] = os.getenv("ADMIN_API_KEY")
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        
        # Rate limiting
        self.rate_limit_enabled: bool = os.getenv(
            "RATE_LIMIT_ENABLED",
            "true"
        ).lower() == "true"
        self.rate_limit_per_minute: int = int(
            os.getenv("RATE_LIMIT_PER_MINUTE", "60")
        )
        
        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
    def get_cors_origins(self) -> list[str]:
        """Get list of allowed CORS origins."""
        return self.cors_origins
    
    def get_database_url(self) -> str:
        """Get database connection URL."""
        return self.database_url


# Global config instance
config = Config()
