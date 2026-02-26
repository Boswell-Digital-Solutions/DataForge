"""
DataForge Integration Tests

Comprehensive test suite for NeuroForge ⇆ DataForge integration.

Test scenarios:
1. Happy path: Context fetch and caching
2. Circuit breaker: Failure threshold and recovery
3. Provenance logging: Fire-and-forget semantics
4. Retry logic: Transient error handling
5. Error cases: 4xx, network errors, timeouts
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.neuroforge.models import (
    InferenceRequest,
    BuiltContext,
    InferenceResult,
    ModelDecision,
)
from app.neuroforge.services.dataforge_client import (
    DataForgeContextRequest,
    DataForgeContextPack,
    DataForgeProvenancePayload,
    DataForgeSnippet,
    DataForgeContextMetadata,
    CircuitBreakerOpenError,
    CircuitBreakerState,
)
from app.neuroforge.services import (
    DataForgeClient,
    build_context_for_request,
    post_process_and_log_provenance,
    run_inference,
)
from app.neuroforge.cache import LRUContextCache, init_context_cache
from app.neuroforge.config import NeuroForgeSettings


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def settings():
    """Create test settings."""
    return NeuroForgeSettings(
        dataforge_base_url="http://localhost:8001",
        dataforge_api_key="test-key",
        dataforge_timeout=5,
        dataforge_cache_enabled=True,
        dataforge_cache_ttl=300,
        circuit_breaker_failure_threshold=3,
        circuit_breaker_recovery_seconds=5,
        environment="development",
    )


@pytest.fixture
def sample_context_pack():
    """Create sample DataForge context pack."""
    snippet1 = DataForgeSnippet(
        text="First context snippet about the topic.",
        source_id="doc-1",
        metadata={"page": 1}
    )
    snippet2 = DataForgeSnippet(
        text="Second context snippet with more details.",
        source_id="doc-2",
        metadata={"page": 2}
    )
    metadata = DataForgeContextMetadata(
        project_id="proj-1",
        retrieval_version="v1",
    )
    return DataForgeContextPack(
        id="pack-123",
        snippets=[snippet1, snippet2],
        metadata=metadata
    )


@pytest.fixture
def sample_inference_request():
    """Create sample inference request."""
    return InferenceRequest(
        request_id="req-123",
        domain="literary",
        task_type="analysis",
        user_query="Analyze the themes",
        max_tokens=2048,
        metadata={"project_id": "proj-1"},
    )


@pytest.fixture
def sample_inference_result():
    """Create sample inference result."""
    return InferenceResult(
        inference_id="inf-123",
        request_id="req-123",
        status="success",
        output="Analysis result text",
        model_id="gpt-4-mini",
        latency_ms=150,
        tokens_used=512,
        tokens_in=256,
        tokens_out=256,
        model_decision=ModelDecision(
            selected_model_id="gpt-4-mini",
            confidence=0.95,
        ),
        context_pack_id="pack-123",
    )


@pytest.fixture
def cache():
    """Create LRU cache instance."""
    return init_context_cache(max_size=100)


# ============================================================================
# DataForge Client Tests
# ============================================================================

@pytest.mark.asyncio
class TestDataForgeClient:
    """Tests for DataForgeClient."""
    
    async def test_fetch_context_success(self, settings, sample_context_pack):
        """Happy path: successful context fetch."""
        client = DataForgeClient(settings)
        
        # Mock the HTTP client (MagicMock, not AsyncMock: .json() and
        # .raise_for_status() are sync methods on httpx.Response)
        mock_response = MagicMock()
        mock_response.json.return_value = sample_context_pack.model_dump()
        
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)
        
        request = DataForgeContextRequest(
            project_id="proj-1",
            query="test query",
            domain="literary",
            max_tokens=2048,
        )
        
        result = await client.fetch_context_pack(request)
        
        assert result.id == "pack-123"
        assert len(result.snippets) == 2
        assert result.snippets[0].text == "First context snippet about the topic."
    
    async def test_fetch_context_circuit_breaker_open(self, settings, sample_context_pack):
        """Circuit breaker: open after threshold failures."""
        client = DataForgeClient(settings)
        client.circuit_breaker.metrics.failure_count = settings.circuit_breaker_failure_threshold
        client.circuit_breaker.metrics.state = CircuitBreakerState.OPEN
        client.circuit_breaker.metrics.opened_at = datetime.utcnow()
        
        request = DataForgeContextRequest(
            project_id="proj-1",
            query="test query",
            domain="literary",
        )
        
        with pytest.raises(CircuitBreakerOpenError):
            await client.fetch_context_pack(request)
    
    async def test_provenance_logging_non_fatal(self, settings):
        """Provenance logging: errors are non-fatal."""
        client = DataForgeClient(settings)
        
        # Mock client to raise error
        client._client = AsyncMock()
        client._client.post = AsyncMock(side_effect=Exception("Network error"))
        
        payload = DataForgeProvenancePayload(
            context_pack_id="pack-123",
            request_id="req-123",
            answer="test answer",
            model_name="gpt-4",
            latency_ms=100,
        )
        
        # Should not raise
        await client.log_provenance(payload)


# ============================================================================
# Context Builder Tests
# ============================================================================

@pytest.mark.asyncio
class TestContextBuilder:
    """Tests for context builder."""
    
    async def test_build_context_cache_hit(
        self,
        cache,
        sample_inference_request,
        sample_context_pack,
    ):
        """Happy path: context cache hit."""
        built_context = BuiltContext(
            context_pack_id=sample_context_pack.id,
            text_blocks=["snippet 1", "snippet 2"],
            source="dataforge",
            cached_at=datetime.utcnow(),
            ttl_seconds=300,
        )
        
        key = f"ctx:literary:analysis:test"
        await cache.put(key, built_context)
        
        # Get from cache
        retrieved = await cache.get(key)
        assert retrieved is not None
        assert retrieved.context_pack_id == "pack-123"
    
    async def test_cache_expiration(self, cache):
        """Cache: TTL expiration."""
        import datetime as dt
        
        past_time = datetime.utcnow() - dt.timedelta(seconds=400)
        
        expired_context = BuiltContext(
            context_pack_id="pack-old",
            text_blocks=["old"],
            source="dataforge",
            cached_at=past_time,
            ttl_seconds=300,  # Expired
        )
        
        key = "ctx:old:old:old"
        await cache.put(key, expired_context)
        
        # Should return None (expired)
        retrieved = await cache.get(key)
        assert retrieved is None
    
    async def test_cache_lru_eviction(self):
        """Cache: LRU eviction at max size."""
        small_cache = init_context_cache(max_size=3)
        
        # Fill cache
        for i in range(3):
            context = BuiltContext(
                context_pack_id=f"pack-{i}",
                text_blocks=[f"text-{i}"],
                source="dataforge",
            )
            await small_cache.put(f"key-{i}", context)
        
        assert await small_cache.size() == 3
        
        # Add one more - should evict oldest
        context = BuiltContext(
            context_pack_id="pack-new",
            text_blocks=["new"],
            source="dataforge",
        )
        await small_cache.put("key-new", context)
        
        assert await small_cache.size() == 3
        assert small_cache.evictions == 1
        
        # Oldest (key-0) should be gone
        assert await small_cache.get("key-0") is None


# ============================================================================
# Post Processor Tests
# ============================================================================

@pytest.mark.asyncio
class TestPostProcessor:
    """Tests for post processor."""
    
    async def test_post_process_logs_provenance(self, sample_inference_result):
        """Provenance logging: called with correct fields."""
        mock_client = AsyncMock()
        mock_client.log_provenance = AsyncMock()
        
        result = await post_process_and_log_provenance(
            sample_inference_result,
            context_pack_id="pack-123",
            dataforge_client=mock_client,
        )
        
        # Verify provenance was logged
        assert mock_client.log_provenance.called
        call_args = mock_client.log_provenance.call_args
        payload = call_args[0][0]  # First positional arg
        
        assert isinstance(payload, DataForgeProvenancePayload)
        assert payload.request_id == "req-123"
        assert payload.context_pack_id == "pack-123"
        assert payload.model_name == "gpt-4-mini"
        assert payload.latency_ms == 150
        assert payload.extra["tokens_in"] == 256


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestIntegration:
    """End-to-end integration tests."""
    
    async def test_full_inference_pipeline(self, settings, sample_context_pack, sample_inference_request):
        """Full pipeline: context fetch + inference + provenance logging."""
        mock_dataforge_client = AsyncMock()
        mock_dataforge_client.fetch_context_pack = AsyncMock(
            return_value=sample_context_pack
        )
        mock_dataforge_client.log_provenance = AsyncMock()
        
        # Run inference
        result = await run_inference(sample_inference_request, mock_dataforge_client)
        
        # Verify result
        assert result.status == "success"
        assert result.context_pack_id == "pack-123"
        assert result.model_id is not None
        
        # Verify DataForge calls
        assert mock_dataforge_client.fetch_context_pack.called
        assert mock_dataforge_client.log_provenance.called


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

@pytest.mark.asyncio
class TestCircuitBreaker:
    """Tests for circuit breaker."""
    
    async def test_circuit_breaker_opens_after_threshold(self, settings):
        """Circuit breaker: opens after failure threshold."""
        from app.neuroforge.services.dataforge_client import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3)
        
        async def failing_func():
            raise Exception("Test error")
        
        # Record failures
        for i in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)
        
        # Circuit should be OPEN
        assert cb.state == CircuitBreakerState.OPEN
        
        # Next call should fail immediately without calling func
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_func)
    
    async def test_circuit_breaker_half_open_recovery(self, settings):
        """Circuit breaker: recovers to HALF_OPEN after timeout."""
        from app.neuroforge.services.dataforge_client import CircuitBreaker
        from datetime import timedelta
        
        cb = CircuitBreaker(failure_threshold=1, recovery_seconds=1)
        
        # Trigger opening
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise Exception("First call fails")
            return "success"
        
        # First call fails
        with pytest.raises(Exception):
            await cb.call(flaky_func)
        
        assert cb.state == CircuitBreakerState.OPEN
        
        # Manually move time forward (simulated by setting opened_at)
        cb.metrics.opened_at = datetime.utcnow() - timedelta(seconds=2)
        
        # Next call should allow HALF_OPEN trial
        result = await cb.call(flaky_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED


# ============================================================================
# Cache Metrics Tests
# ============================================================================

@pytest.mark.asyncio
class TestCacheMetrics:
    """Tests for cache metrics."""
    
    async def test_cache_hit_rate_tracking(self):
        """Cache metrics: track hit rate."""
        cache = init_context_cache(max_size=10)
        
        context = BuiltContext(
            context_pack_id="pack-1",
            text_blocks=["text"],
            source="dataforge",
        )
        
        await cache.put("key-1", context)
        
        # Hit
        await cache.get("key-1")
        # Miss
        await cache.get("key-2")
        # Hit
        await cache.get("key-1")
        
        metrics = await cache.get_metrics()
        assert metrics["hits"] == 2
        assert metrics["misses"] == 1
        assert metrics["hit_rate_percent"] == pytest.approx(66.67, 0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
