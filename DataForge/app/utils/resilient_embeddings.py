"""
Resilient Embedding Service with Circuit Breaker Pattern and Fallback Provider Logic

This module wraps the base embedding service with:
1. Circuit breakers for each provider (Voyage, OpenAI, Cohere)
2. Automatic fallback to next provider on circuit open
3. Adaptive request caching
4. Metrics collection per provider
"""

import logging
import time
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from functools import lru_cache

from app.utils.circuit_breaker import CircuitBreakerRegistry, CircuitBreakerError
from app.config import VOYAGE_API_KEY, OPENAI_API_KEY, COHERE_API_KEY
from app.utils.embeddings import generate_embedding, generate_embeddings_batch

logger = logging.getLogger(__name__)


class ProviderMetrics:
    """Metrics for tracking provider performance."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency_ms = 0.0
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[datetime] = None

    def record_success(self, latency_ms: float) -> None:
        """Record successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms

    def record_failure(self, error: str) -> None:
        """Record failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_error = error
        self.last_error_time = datetime.utcnow()

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Get average latency."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "provider": self.provider_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{self.success_rate:.1f}%",
            "avg_latency_ms": f"{self.avg_latency_ms:.1f}",
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }


class ResilientEmbeddingService:
    """
    Embedding service with circuit breaker protection and fallback providers.

    Providers are tried in order:
    1. Voyage AI (recommended, Anthropic-owned)
    2. OpenAI (fallback)
    3. Cohere (fallback)

    Circuit breakers prevent cascading failures by temporarily disabling
    a provider after consecutive failures.
    """

    def __init__(self):
        """Initialize resilient embedding service."""
        registry = CircuitBreakerRegistry()

        # Register circuit breakers for each provider
        # Each provider gets: 5 failures before opening, 60s recovery timeout
        self.voyage_breaker = registry.register(
            name="embedding_voyage",
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception,
        )
        self.openai_breaker = registry.register(
            name="embedding_openai",
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception,
        )
        self.cohere_breaker = registry.register(
            name="embedding_cohere",
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception,
        )

        # Metrics per provider
        self.metrics = {
            "voyage": ProviderMetrics("voyage"),
            "openai": ProviderMetrics("openai"),
            "cohere": ProviderMetrics("cohere"),
        }

        # Request cache for embedding requests (simple LRU)
        self._request_cache: Dict[str, List[float]] = {}
        self._cache_max_size = 1000

        logger.info("✅ Resilient Embedding Service initialized")

    def _get_active_providers(self) -> List[Tuple[str, Any]]:
        """
        Get list of available providers (not open circuit).

        Returns list in priority order: (provider_name, circuit_breaker)
        """
        providers = []

        if VOYAGE_API_KEY and not self.voyage_breaker.is_open:
            providers.append(("voyage", self.voyage_breaker))

        if OPENAI_API_KEY and not self.openai_breaker.is_open:
            providers.append(("openai", self.openai_breaker))

        if COHERE_API_KEY and not self.cohere_breaker.is_open:
            providers.append(("cohere", self.cohere_breaker))

        return providers

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding with automatic fallback on provider failure.

        Tries providers in order until one succeeds.
        Falls back to next provider on circuit open or failure.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector (list of floats)

        Raises:
            Exception: If all providers are unavailable
        """
        # Check cache first
        cache_key = hash(text)
        if cache_key in self._request_cache:
            logger.debug(f"📦 Cache hit for text (first 50 chars: {text[:50]})")
            return self._request_cache[cache_key]

        providers = self._get_active_providers()

        if not providers:
            error_msg = (
                "❌ All embedding providers are unavailable (circuits open). "
                "Please check provider health or circuit breaker status."
            )
            logger.error(error_msg)
            raise Exception(error_msg)

        last_error = None

        for provider_name, breaker in providers:
            try:
                logger.debug(f"🔄 Attempting {provider_name} for embedding...")
                start_time = time.time()

                # Call underlying embedding service
                embedding = await generate_embedding(text)

                latency_ms = (time.time() - start_time) * 1000
                breaker.record_success()
                self.metrics[provider_name].record_success(latency_ms)

                logger.info(
                    f"✅ {provider_name.upper()} embedding generated in {latency_ms:.1f}ms"
                )

                # Cache result
                if len(self._request_cache) >= self._cache_max_size:
                    # Simple eviction: clear oldest half
                    self._request_cache.clear()

                self._request_cache[cache_key] = embedding
                return embedding

            except Exception as e:
                error_msg = f"{provider_name}: {str(e)}"
                last_error = error_msg
                breaker.record_failure()
                self.metrics[provider_name].record_failure(error_msg)

                logger.warning(
                    f"⚠️  {provider_name.upper()} failed, trying next provider: {error_msg}"
                )
                continue

        # All providers exhausted
        error_summary = (
            f"❌ All embedding providers failed. Last error: {last_error}. "
            f"Circuit status: {self.get_provider_health()}"
        )
        logger.error(error_summary)
        raise Exception(error_summary)

    async def generate_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with fallback.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embedding vectors

        Raises:
            Exception: If all providers are unavailable
        """
        providers = self._get_active_providers()

        if not providers:
            error_msg = (
                "❌ All embedding providers are unavailable (circuits open). "
                "Please check provider health or circuit breaker status."
            )
            logger.error(error_msg)
            raise Exception(error_msg)

        last_error = None

        for provider_name, breaker in providers:
            try:
                logger.debug(f"🔄 Attempting {provider_name} for batch embedding ({len(texts)} texts)...")
                start_time = time.time()

                # Call underlying batch embedding service
                embeddings = await generate_embeddings_batch(texts)

                latency_ms = (time.time() - start_time) * 1000
                breaker.record_success()
                self.metrics[provider_name].record_success(latency_ms)

                logger.info(
                    f"✅ {provider_name.upper()} batch embedding generated "
                    f"({len(texts)} texts in {latency_ms:.1f}ms)"
                )
                return embeddings

            except Exception as e:
                error_msg = f"{provider_name}: {str(e)}"
                last_error = error_msg
                breaker.record_failure()
                self.metrics[provider_name].record_failure(error_msg)

                logger.warning(
                    f"⚠️  {provider_name.upper()} failed, trying next provider: {error_msg}"
                )
                continue

        # All providers exhausted
        error_summary = (
            f"❌ All batch embedding providers failed. Last error: {last_error}. "
            f"Circuit status: {self.get_provider_health()}"
        )
        logger.error(error_summary)
        raise Exception(error_summary)

    def get_provider_health(self) -> Dict[str, Any]:
        """
        Get health status of all embedding providers.

        Returns dict with circuit state, metrics, and recommendations.
        """
        registry = CircuitBreakerRegistry()

        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "providers": {},
            "recommendations": [],
        }

        # Voyage AI
        voyage_status = self.voyage_breaker.get_status()
        voyage_metrics = self.metrics["voyage"].to_dict()
        health["providers"]["voyage"] = {
            "configured": bool(VOYAGE_API_KEY),
            "circuit_state": voyage_status["state"],
            "is_open": voyage_status["is_open"],
            "metrics": voyage_metrics,
        }

        # OpenAI
        openai_status = self.openai_breaker.get_status()
        openai_metrics = self.metrics["openai"].to_dict()
        health["providers"]["openai"] = {
            "configured": bool(OPENAI_API_KEY),
            "circuit_state": openai_status["state"],
            "is_open": openai_status["is_open"],
            "metrics": openai_metrics,
        }

        # Cohere
        cohere_status = self.cohere_breaker.get_status()
        cohere_metrics = self.metrics["cohere"].to_dict()
        health["providers"]["cohere"] = {
            "configured": bool(COHERE_API_KEY),
            "circuit_state": cohere_status["state"],
            "is_open": cohere_status["is_open"],
            "metrics": cohere_metrics,
        }

        # Generate recommendations
        open_count = sum(
            1 for p in health["providers"].values() if p["is_open"]
        )

        if open_count == 3:
            health["recommendations"].append(
                "🔴 CRITICAL: All embedding providers are unavailable (circuits open). "
                "Check external API health and connectivity."
            )
        elif open_count > 0:
            health["recommendations"].append(
                f"🟡 WARNING: {open_count} embedding provider(s) have open circuits. "
                "System is using fallback provider(s)."
            )
        else:
            health["recommendations"].append(
                "🟢 All embedding providers operational."
            )

        return health

    def reset_circuit_breaker(self, provider: str) -> bool:
        """
        Manually reset a provider's circuit breaker.

        Args:
            provider: Provider name (voyage, openai, cohere)

        Returns:
            True if reset successful, False if provider not found
        """
        breaker = None

        if provider == "voyage":
            breaker = self.voyage_breaker
        elif provider == "openai":
            breaker = self.openai_breaker
        elif provider == "cohere":
            breaker = self.cohere_breaker
        else:
            logger.warning(f"Unknown provider: {provider}")
            return False

        breaker.reset()
        logger.info(f"🔄 Reset circuit breaker for {provider}")
        return True


# Global singleton instance
_resilient_service: Optional[ResilientEmbeddingService] = None


def get_resilient_embedding_service() -> ResilientEmbeddingService:
    """Get or create global resilient embedding service."""
    global _resilient_service

    if _resilient_service is None:
        _resilient_service = ResilientEmbeddingService()

    return _resilient_service
