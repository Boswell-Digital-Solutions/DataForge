"""
NeuroForge Settings

Configuration management for NeuroForge integration within DataForge.
Uses Pydantic BaseModel for type-safe settings with sensible defaults.
"""
from typing import Optional

from pydantic import BaseModel, Field


class NeuroForgeSettings(BaseModel):
    """Configuration for NeuroForge ⇆ DataForge integration."""

    # DataForge connection
    dataforge_base_url: str = Field(
        default="http://127.0.0.1:8001",
        description="DataForge API base URL",
    )
    dataforge_api_key: Optional[str] = Field(
        default=None,
        description="DataForge API key for authentication",
    )
    dataforge_timeout: int = Field(
        default=10,
        description="HTTP timeout in seconds for DataForge calls",
    )

    # Caching
    dataforge_cache_enabled: bool = Field(
        default=True,
        description="Enable local context cache",
    )
    dataforge_cache_ttl: int = Field(
        default=300,
        description="Cache TTL in seconds",
    )

    # Circuit breaker
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Number of failures before circuit opens",
    )
    circuit_breaker_recovery_seconds: int = Field(
        default=30,
        description="Seconds before half-open recovery attempt",
    )
    circuit_breaker_half_open_max_calls: int = Field(
        default=1,
        description="Max trial calls allowed in half-open state",
    )

    # Retry
    retry_max_attempts: int = Field(
        default=3,
        description="Max retry attempts for transient failures",
    )
    retry_initial_delay: float = Field(
        default=0.5,
        description="Initial retry delay in seconds",
    )
    retry_backoff_base: float = Field(
        default=2.0,
        description="Exponential backoff base multiplier",
    )

    # Environment
    environment: str = Field(
        default="development",
        description="Runtime environment (development, staging, production)",
    )


# Module-level singleton
_settings: Optional[NeuroForgeSettings] = None


def init_settings(environment: str = "development", **overrides) -> NeuroForgeSettings:
    """Initialize settings singleton with optional overrides."""
    global _settings
    _settings = NeuroForgeSettings(environment=environment, **overrides)
    return _settings


def get_settings() -> NeuroForgeSettings:
    """Get the current settings singleton. Creates default if not initialized."""
    global _settings
    if _settings is None:
        _settings = NeuroForgeSettings()
    return _settings
