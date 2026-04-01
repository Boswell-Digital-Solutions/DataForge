"""
Resilient Embedding Service with Circuit Breaker for NeuroForge.

Law 2 Compliance: All embedding operations route through NeuroForge.
This module wraps the base embedding service with circuit breaker
protection and metrics collection for the single NeuroForge provider.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC

from app.utils.circuit_breaker import CircuitBreakerRegistry, CircuitBreakerError
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
        self.last_error_time = datetime.now(UTC)

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
    Embedding service with circuit breaker protection for NeuroForge.

    All embedding requests route through NeuroForge (Law 2).
    Circuit breaker prevents cascading failures if NeuroForge is down.
    """

    def __init__(self):
        """Initialize resilient embedding service."""
        registry = CircuitBreakerRegistry()

        # Circuit breaker for NeuroForge: 5 failures before opening, 60s recovery
        self.neuroforge_breaker = registry.register(
            name="embedding_neuroforge",
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception,
        )

        # Metrics for NeuroForge
        self.metrics = {
            "neuroforge": ProviderMetrics("neuroforge"),
        }

        # Request cache for embedding requests (simple LRU)
        self._request_cache: Dict[str, List[float]] = {}
        self._cache_max_size = 1000

        logger.info("Resilient Embedding Service initialized (NeuroForge provider)")

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding with circuit breaker protection.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector (list of floats)

        Raises:
            Exception: If NeuroForge is unavailable
        """
        # Check cache first
        cache_key = hash(text)
        if cache_key in self._request_cache:
            logger.debug(f"Cache hit for text (first 50 chars: {text[:50]})")
            return self._request_cache[cache_key]

        if self.neuroforge_breaker.is_open:
            raise Exception(
                "NeuroForge embedding circuit breaker is OPEN. "
                "Check NeuroForge health at http://127.0.0.1:8000/health"
            )

        try:
            start_time = time.time()
            embedding = await generate_embedding(text)
            latency_ms = (time.time() - start_time) * 1000

            self.neuroforge_breaker.record_success()
            self.metrics["neuroforge"].record_success(latency_ms)

            # Cache result
            if len(self._request_cache) >= self._cache_max_size:
                self._request_cache.clear()
            self._request_cache[cache_key] = embedding

            return embedding

        except Exception as e:
            self.neuroforge_breaker.record_failure()
            self.metrics["neuroforge"].record_failure(str(e))
            logger.warning(f"NeuroForge embedding failed: {e}")
            raise

    async def generate_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with circuit breaker.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embedding vectors

        Raises:
            Exception: If NeuroForge is unavailable
        """
        if self.neuroforge_breaker.is_open:
            raise Exception(
                "NeuroForge embedding circuit breaker is OPEN. "
                "Check NeuroForge health at http://127.0.0.1:8000/health"
            )

        try:
            start_time = time.time()
            embeddings = await generate_embeddings_batch(texts)
            latency_ms = (time.time() - start_time) * 1000

            self.neuroforge_breaker.record_success()
            self.metrics["neuroforge"].record_success(latency_ms)

            return embeddings

        except Exception as e:
            self.neuroforge_breaker.record_failure()
            self.metrics["neuroforge"].record_failure(str(e))
            logger.warning(f"NeuroForge batch embedding failed: {e}")
            raise

    def get_provider_health(self) -> Dict[str, Any]:
        """
        Get health status of the NeuroForge embedding provider.

        Returns dict with circuit state, metrics, and recommendations.
        """
        neuroforge_status = self.neuroforge_breaker.get_status()
        neuroforge_metrics = self.metrics["neuroforge"].to_dict()

        health = {
            "timestamp": datetime.now(UTC).isoformat(),
            "providers": {
                "neuroforge": {
                    "configured": True,
                    "circuit_state": neuroforge_status["state"],
                    "is_open": neuroforge_status["is_open"],
                    "metrics": neuroforge_metrics,
                },
            },
            "recommendations": [],
        }

        if neuroforge_status["is_open"]:
            health["recommendations"].append(
                "CRITICAL: NeuroForge embedding provider circuit is OPEN. "
                "Check NeuroForge service health at http://127.0.0.1:8000/health"
            )
        else:
            health["recommendations"].append(
                "NeuroForge embedding provider operational."
            )

        return health

    def reset_circuit_breaker(self, provider: str = "neuroforge") -> bool:
        """
        Manually reset the NeuroForge circuit breaker.

        Args:
            provider: Provider name (only "neuroforge" supported)

        Returns:
            True if reset successful
        """
        if provider != "neuroforge":
            logger.warning(f"Unknown provider: {provider}. Only 'neuroforge' is supported.")
            return False

        self.neuroforge_breaker.reset()
        logger.info("Reset circuit breaker for NeuroForge embeddings")
        return True


# Global singleton instance
_resilient_service: Optional[ResilientEmbeddingService] = None


def get_resilient_embedding_service() -> ResilientEmbeddingService:
    """Get or create global resilient embedding service."""
    global _resilient_service

    if _resilient_service is None:
        _resilient_service = ResilientEmbeddingService()

    return _resilient_service
