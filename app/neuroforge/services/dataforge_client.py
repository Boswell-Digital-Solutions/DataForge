"""
DataForge HTTP Client

Provides async HTTP client wrapper for DataForge integration with:
- Circuit breaker pattern for resilience
- Exponential backoff retries
- Non-fatal provenance logging
- Request/response models based on DataForge contract
"""
import asyncio
import logging
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Optional, Any, Dict
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, Field, ConfigDict

from app.neuroforge.config import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# DataForge Request/Response Models (Pydantic v2)
# ============================================================================

class DataForgeContextRequest(BaseModel):
    """Request model for DataForge context fetch."""
    project_id: str
    query: str
    domain: str
    max_tokens: int = 2048
    filters: Optional[Dict[str, Any]] = None


class DataForgeSnippet(BaseModel):
    """Individual snippet from context pack."""
    text: str
    source_id: str
    metadata: Optional[Dict[str, Any]] = None


class DataForgeContextMetadata(BaseModel):
    """Metadata for context pack."""
    project_id: str
    retrieval_version: str = "v1"
    created_at: Optional[str] = None


class DataForgeContextPack(BaseModel):
    """Response model for DataForge context fetch."""
    id: str = Field(..., alias="context_pack_id")
    snippets: list[DataForgeSnippet]
    metadata: DataForgeContextMetadata

    model_config = ConfigDict(populate_by_name=True)
  # Allow both 'id' and 'context_pack_id'


class DataForgeRouterDecision(BaseModel):
    """Router decision metadata."""
    ensemble: Optional[list[str]] = None
    winner: Optional[str] = None


class DataForgeProvenancePayload(BaseModel):
    """Request model for DataForge provenance logging."""
    context_pack_id: str
    request_id: str
    answer: str
    model_name: str
    latency_ms: int
    extra: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(json_schema_extra={'example': {'context_pack_id': 'context-pack-id', 'request_id': 'nf-req-id', 'answer': 'final model answer', 'model_name': 'gpt-4.1-mini', 'latency_ms': 95, 'extra': {'tokens_in': 1024, 'tokens_out': 256, 'router_decision': {'ensemble': ['model_a', 'model_b'], 'winner': 'model_b'}}}})



# ============================================================================
# Circuit Breaker Pattern
# ============================================================================

class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by circuit breaker."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    opened_at: Optional[datetime] = None
    half_open_attempt_count: int = 0


class CircuitBreaker:
    """
    Simple circuit breaker implementation for DataForge client.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Failures threshold reached, calls fail immediately
    - HALF_OPEN: Recovery window passed, allowing trial calls
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_seconds: int = 60,
        half_open_max_calls: int = 1,
        name: str = "DataForgeCircuitBreaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.half_open_max_calls = half_open_max_calls
        self.name = name
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit state."""
        return self.metrics.state
    
    async def call(self, func, *args, **kwargs):
        """
        Execute function through circuit breaker.
        
        Args:
            func: Async callable to execute
            *args, **kwargs: Arguments to pass to func
        
        Returns:
            Result of func()
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Propagates exceptions from func if not retriable
        """
        async with self._lock:
            self._check_and_update_state()
            
            if self.metrics.state == CircuitBreakerState.OPEN:
                raise CircuitBreakerOpenError(
                    f"{self.name} is OPEN. Failing fast. "
                    f"Will retry at {self.metrics.opened_at + timedelta(seconds=self.recovery_seconds)}"
                )
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise
    
    def _check_and_update_state(self) -> None:
        """Check if we should transition states."""
        if self.metrics.state == CircuitBreakerState.OPEN:
            # Check if recovery window has passed
            if (self.metrics.opened_at and 
                datetime.now(UTC) >= self.metrics.opened_at + timedelta(seconds=self.recovery_seconds)):
                logger.info(f"{self.name}: Transitioning OPEN → HALF_OPEN")
                self.metrics.state = CircuitBreakerState.HALF_OPEN
                self.metrics.half_open_attempt_count = 0
    
    async def _record_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self.metrics.success_count += 1
            
            if self.metrics.state == CircuitBreakerState.HALF_OPEN:
                logger.info(f"{self.name}: Success in HALF_OPEN, transitioning to CLOSED")
                self.metrics.state = CircuitBreakerState.CLOSED
                self.metrics.failure_count = 0
                self.metrics.half_open_attempt_count = 0
    
    async def _record_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self.metrics.failure_count += 1
            self.metrics.last_failure_time = datetime.now(UTC)
            
            if self.metrics.state == CircuitBreakerState.HALF_OPEN:
                logger.warning(f"{self.name}: Failure in HALF_OPEN, transitioning back to OPEN")
                self.metrics.state = CircuitBreakerState.OPEN
                self.metrics.opened_at = datetime.now(UTC)
                self.metrics.half_open_attempt_count = 0
            elif self.metrics.failure_count >= self.failure_threshold:
                logger.error(f"{self.name}: Failure threshold {self.failure_threshold} reached, opening circuit")
                self.metrics.state = CircuitBreakerState.OPEN
                self.metrics.opened_at = datetime.now(UTC)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# ============================================================================
# DataForge Client
# ============================================================================

class DataForgeClient:
    """
    Async HTTP client for DataForge integration.
    
    Features:
    - Circuit breaker for resilience
    - Exponential backoff retries (only for transient errors)
    - Non-fatal provenance logging
    - Request correlation via X-Request-ID header
    """
    
    def __init__(self, settings=None):
        """
        Initialize DataForge client.
        
        Args:
            settings: NeuroForgeSettings instance (uses get_settings() if None)
        """
        self.settings = settings or get_settings()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.settings.circuit_breaker_failure_threshold,
            recovery_seconds=self.settings.circuit_breaker_recovery_seconds,
            half_open_max_calls=self.settings.circuit_breaker_half_open_max_calls,
            name="DataForgeCircuitBreaker"
        )
        self._client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP client (call during FastAPI startup)."""
        self._client = httpx.AsyncClient(
            base_url=str(self.settings.dataforge_base_url),
            timeout=self.settings.dataforge_timeout,
            headers={
                "Authorization": f"Bearer {self.settings.dataforge_api_key}",
                "Content-Type": "application/json",
            } if self.settings.dataforge_api_key else {}
        )
        logger.info(f"DataForgeClient initialized with base_url={self.settings.dataforge_base_url}")
    
    async def shutdown(self) -> None:
        """Shutdown HTTP client (call during FastAPI shutdown)."""
        if self._client:
            await self._client.aclose()
            logger.info("DataForgeClient shutdown complete")
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if not self._client:
            raise RuntimeError("DataForgeClient not initialized. Call await client.initialize() first.")
        return self._client
    
    async def fetch_context_pack(
        self,
        payload: DataForgeContextRequest,
        retries: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> DataForgeContextPack:
        """
        Fetch context pack from DataForge.
        
        Args:
            payload: Context request
            retries: Number of retries (uses settings default if None)
            request_id: Optional request ID for tracing
        
        Returns:
            DataForgeContextPack
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            httpx.HTTPError: If request fails after retries
        """
        if retries is None:
            retries = self.settings.retry_max_attempts - 1
        
        async def _fetch() -> DataForgeContextPack:
            client = await self._ensure_client()
            headers = {"X-Request-ID": request_id} if request_id else {}
            
            response = await client.post(
                "/api/v1/context/fetch",
                json=payload.model_dump(),
                headers=headers
            )
            response.raise_for_status()
            
            return DataForgeContextPack.model_validate(response.json())
        
        # Execute through circuit breaker with retries
        return await self._retry_with_backoff(_fetch, retries)
    
    async def log_provenance(
        self,
        payload: DataForgeProvenancePayload,
        request_id: Optional[str] = None
    ) -> None:
        """
        Log provenance to DataForge (fire-and-forget, errors are non-fatal).
        
        Args:
            payload: Provenance record
            request_id: Optional request ID for tracing
        """
        try:
            async def _log() -> None:
                client = await self._ensure_client()
                headers = {"X-Request-ID": request_id} if request_id else {}
                
                response = await client.post(
                    "/api/v1/provenance/write",
                    json=payload.model_dump(),
                    headers=headers,
                    timeout=5.0  # Shorter timeout for fire-and-forget
                )
                response.raise_for_status()
                logger.debug(f"Provenance logged: {payload.request_id}")
            
            # Don't use circuit breaker for provenance (it's best-effort)
            # But still retry transient errors
            await self._retry_with_backoff(_log, retries=1)
        
        except Exception as e:
            # Log error but don't raise - provenance is non-fatal
            logger.warning(
                f"Failed to log provenance {payload.request_id}: {type(e).__name__}: {e}",
                exc_info=False
            )
    
    async def _retry_with_backoff(
        self,
        func,
        retries: int = 2,
        initial_delay: Optional[float] = None,
        backoff_base: Optional[float] = None
    ):
        """
        Execute function with exponential backoff retries.
        
        Only retries on transient errors:
        - Timeouts
        - 5xx responses
        - Network errors
        
        Does NOT retry on:
        - 4xx responses (client errors, auth errors)
        
        Args:
            func: Async callable
            retries: Number of retries
            initial_delay: Initial delay in seconds (uses settings if None)
            backoff_base: Backoff multiplier (uses settings if None)
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            httpx.HTTPError: If final attempt fails
        """
        if initial_delay is None:
            initial_delay = self.settings.retry_initial_delay
        if backoff_base is None:
            backoff_base = self.settings.retry_backoff_base
        
        async def _execute():
            return await self.circuit_breaker.call(func)
        
        for attempt in range(retries + 1):
            try:
                return await _execute()
            except CircuitBreakerOpenError:
                raise  # Don't retry circuit breaker errors
            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors
                if 400 <= e.response.status_code < 500:
                    raise
                
                if attempt < retries:
                    delay = initial_delay * (backoff_base ** attempt)
                    logger.warning(
                        f"DataForge request failed (attempt {attempt + 1}/{retries + 1}): "
                        f"{e.response.status_code}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < retries:
                    delay = initial_delay * (backoff_base ** attempt)
                    logger.warning(
                        f"DataForge request timeout/network error (attempt {attempt + 1}/{retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    raise


# Global singleton instance
_dataforge_client: Optional[DataForgeClient] = None


def get_dataforge_client() -> DataForgeClient:
    """Get or create the global DataForge client singleton."""
    global _dataforge_client
    if _dataforge_client is None:
        _dataforge_client = DataForgeClient()
    return _dataforge_client


async def initialize_dataforge_client() -> DataForgeClient:
    """Initialize the global DataForge client (call during app startup)."""
    global _dataforge_client
    _dataforge_client = DataForgeClient()
    await _dataforge_client.initialize()
    return _dataforge_client


async def shutdown_dataforge_client() -> None:
    """Shutdown the global DataForge client (call during app shutdown)."""
    global _dataforge_client
    if _dataforge_client:
        await _dataforge_client.shutdown()
        _dataforge_client = None
