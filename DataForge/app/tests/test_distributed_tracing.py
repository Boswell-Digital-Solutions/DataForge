"""
Tests for Distributed Tracing - PHASE 3.4

Comprehensive test suite covering:
    - OpenTelemetry tracing with span lifecycle
    - Distributed context propagation (W3C Trace Context)
    - Cross-region trace coordination
    - Region health monitoring
    - Trace sampling and filtering
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from app.utils.distributed_tracing import (
    DistributedTracer,
    TraceCollector,
    JaegerExporter,
    Span,
    SpanKind,
    SpanStatus,
    SpanContext,
    get_tracer,
    reset_tracer,
    trace_decorator,
)
from app.utils.cross_region_tracing import (
    CrossRegionTraceCoordinator,
    RegionHealthMonitor,
    RegionInfo,
    RegionStatus,
    get_cross_region_coordinator,
    reset_cross_region_coordinator,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tracer() -> DistributedTracer:
    """Create tracer for testing."""
    reset_tracer()
    return get_tracer(service_name="test-service", trace_sample_rate=1.0)


@pytest.fixture
def coordinator() -> CrossRegionTraceCoordinator:
    """Create cross-region coordinator for testing."""
    reset_cross_region_coordinator()
    return get_cross_region_coordinator()


# ============================================================================
# Span Context Tests
# ============================================================================

class TestSpanContext:
    """Test W3C Trace Context format."""
    
    def test_span_context_to_headers(self):
        """Test converting span context to headers."""
        context = SpanContext(
            trace_id="12345678901234567890123456789012",
            span_id="1234567890123456",
        )
        
        headers = context.to_headers()
        assert "traceparent" in headers
        assert headers["traceparent"].startswith("00-")
    
    def test_span_context_from_headers(self):
        """Test extracting span context from headers."""
        traceparent = "00-12345678901234567890123456789012-1234567890123456-01"
        headers = {"traceparent": traceparent}
        
        context = SpanContext.from_headers(headers)
        assert context is not None
        assert context.trace_id == "12345678901234567890123456789012"
        assert context.span_id == "1234567890123456"
        assert context.remote is True
    
    def test_invalid_traceparent_format(self):
        """Test handling invalid traceparent format."""
        headers = {"traceparent": "invalid"}
        context = SpanContext.from_headers(headers)
        assert context is None


# ============================================================================
# Span Tests
# ============================================================================

class TestSpan:
    """Test span creation and lifecycle."""
    
    def test_create_span(self):
        """Test creating span."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            name="test-operation",
            kind=SpanKind.INTERNAL,
            start_time=time.time(),
        )
        
        assert span.name == "test-operation"
        assert span.status == SpanStatus.UNSET
    
    def test_set_span_attribute(self):
        """Test setting span attributes."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            name="test",
            kind=SpanKind.INTERNAL,
            start_time=time.time(),
        )
        
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"
    
    def test_add_span_event(self):
        """Test adding events to span."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            name="test",
            kind=SpanKind.INTERNAL,
            start_time=time.time(),
        )
        
        span.add_event("error", {"message": "Something went wrong"})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "error"
    
    def test_set_span_status(self):
        """Test setting span status."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            name="test",
            kind=SpanKind.INTERNAL,
            start_time=time.time(),
        )
        
        span.set_status(SpanStatus.OK)
        assert span.status == SpanStatus.OK
    
    def test_span_duration_calculation(self):
        """Test span duration calculation."""
        start = time.time()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            name="test",
            kind=SpanKind.INTERNAL,
            start_time=start,
        )
        
        time.sleep(0.1)
        span.end()
        
        assert span.duration_ms >= 100
        assert span.end_time is not None


# ============================================================================
# Trace Collector Tests
# ============================================================================

class TestTraceCollector:
    """Test trace collection."""
    
    def test_create_trace(self):
        """Test creating trace."""
        collector = TraceCollector()
        
        trace = collector.create_trace("trace-1", "operation")
        assert trace.trace_id == "trace-1"
        assert len(collector.traces) == 1
    
    def test_create_span_in_trace(self):
        """Test creating span in trace."""
        collector = TraceCollector()
        
        trace = collector.create_trace("trace-1", "operation")
        span = collector.create_span("trace-1", "span-1")
        
        assert span.trace_id == "trace-1"
        assert "trace-1" in collector.spans
    
    def test_end_trace(self):
        """Test ending trace."""
        collector = TraceCollector()
        
        trace = collector.create_trace("trace-1", "operation")
        trace_data = collector.end_trace("trace-1")
        
        assert trace_data is not None
        assert trace_data["trace_id"] == "trace-1"
        assert trace_data["duration_ms"] > 0


# ============================================================================
# Tracer Tests
# ============================================================================

class TestDistributedTracer:
    """Test distributed tracer."""
    
    def test_start_trace(self, tracer: DistributedTracer):
        """Test starting trace."""
        context = tracer.start_trace("test-operation")
        
        assert context.trace_id is not None
        assert context.span_id is not None
        assert context.trace_flags == 0x01  # Sampled
    
    def test_create_span(self, tracer: DistributedTracer):
        """Test creating span."""
        tracer.start_trace("operation")
        span = tracer.create_span("child-span")
        
        assert span.name == "child-span"
        assert span.trace_id is not None
    
    def test_trace_operation_context_manager(self, tracer: DistributedTracer):
        """Test trace_operation context manager."""
        tracer.start_trace("operation")
        
        with tracer.trace_operation("db-query") as span:
            span.set_attribute("query", "SELECT *")
            assert span.status == SpanStatus.UNSET
        
        assert span.status == SpanStatus.OK
        assert span.end_time is not None
    
    def test_trace_operation_with_exception(self, tracer: DistributedTracer):
        """Test trace_operation handles exceptions."""
        tracer.start_trace("operation")
        
        with pytest.raises(ValueError):
            with tracer.trace_operation("failing-op") as span:
                raise ValueError("Test error")
        
        assert span.status == SpanStatus.ERROR
    
    def test_context_injection(self, tracer: DistributedTracer):
        """Test context injection for downstream services."""
        context = tracer.start_trace("operation")
        headers = tracer.inject_context(context)
        
        assert "traceparent" in headers
        assert headers["traceparent"].startswith("00-")
    
    def test_context_extraction(self, tracer: DistributedTracer):
        """Test context extraction from headers."""
        traceparent = "00-12345678901234567890123456789012-1234567890123456-01"
        headers = {"traceparent": traceparent}
        
        extracted = tracer.extract_context(headers)
        assert extracted is not None
        assert extracted.trace_id == "12345678901234567890123456789012"


# ============================================================================
# Trace Sampling Tests
# ============================================================================

class TestTraceSampling:
    """Test trace sampling."""
    
    def test_full_sampling_rate(self):
        """Test 100% sampling rate."""
        tracer = DistributedTracer(trace_sample_rate=1.0)
        context = tracer.start_trace("operation")
        
        assert context.trace_flags == 0x01  # Sampled
    
    def test_zero_sampling_rate(self):
        """Test 0% sampling rate."""
        tracer = DistributedTracer(trace_sample_rate=0.0)
        context = tracer.start_trace("operation")
        
        assert context.trace_flags == 0x00  # Not sampled


# ============================================================================
# Region Health Monitor Tests
# ============================================================================

class TestRegionHealthMonitor:
    """Test region health monitoring."""
    
    def test_register_region(self):
        """Test registering region."""
        monitor = RegionHealthMonitor()
        
        monitor.register_region(
            name="US East",
            code="us-east-1",
            jaeger_host="jaeger-us-east",
        )
        
        assert "us-east-1" in monitor.regions
    
    def test_record_latency(self):
        """Test recording latency."""
        monitor = RegionHealthMonitor(latency_threshold_ms=100.0)
        monitor.register_region("US East", "us-east-1", "jaeger-host")
        
        monitor.record_latency("us-east-1", 45.0)
        assert "us-east-1" in monitor.latency_measurements
        assert len(monitor.latency_measurements["us-east-1"]) == 1
    
    def test_latency_exceeds_threshold(self):
        """Test status change when latency exceeds threshold."""
        monitor = RegionHealthMonitor(latency_threshold_ms=100.0)
        monitor.register_region("US East", "us-east-1", "jaeger-host")
        
        # Record high latency measurements
        for _ in range(5):
            monitor.record_latency("us-east-1", 150.0)
        
        region = monitor.regions["us-east-1"]
        assert region.status == RegionStatus.DEGRADED
    
    def test_failure_tracking(self):
        """Test failure tracking."""
        monitor = RegionHealthMonitor()
        monitor.register_region("US East", "us-east-1", "jaeger-host")
        
        # Record failures
        for _ in range(5):
            monitor.record_failure("us-east-1")
        
        region = monitor.regions["us-east-1"]
        assert region.status == RegionStatus.UNHEALTHY
    
    def test_get_healthy_regions(self):
        """Test getting healthy regions."""
        monitor = RegionHealthMonitor()
        monitor.register_region("US East", "us-east-1", "jaeger-host")
        monitor.register_region("EU West", "eu-west-1", "jaeger-host")
        
        healthy = monitor.get_healthy_regions()
        assert "us-east-1" in healthy
        assert "eu-west-1" in healthy


# ============================================================================
# Cross-Region Trace Coordinator Tests
# ============================================================================

class TestCrossRegionTraceCoordinator:
    """Test cross-region tracing."""
    
    def test_register_region(self, coordinator: CrossRegionTraceCoordinator):
        """Test registering region."""
        coordinator.register_region("US East", "us-east-1", "jaeger-host")
        
        assert "us-east-1" in coordinator.region_exporters
    
    def test_create_cross_region_trace(self, coordinator: CrossRegionTraceCoordinator):
        """Test creating cross-region trace."""
        trace = coordinator.create_cross_region_trace("trace-1", "us-east-1")
        
        assert trace.trace_id == "trace-1"
        assert "us-east-1" in trace.regions_involved
    
    def test_add_region_span(self, coordinator: CrossRegionTraceCoordinator):
        """Test adding span from region."""
        coordinator.create_cross_region_trace("trace-1", "us-east-1")
        
        coordinator.add_region_span(
            trace_id="trace-1",
            region_code="us-east-1",
            span_id="span-1",
            span_name="api-call",
            start_time=time.time(),
            duration_ms=45.5,
            service_name="api-service",
        )
        
        trace = coordinator.traces["trace-1"]
        assert len(trace.region_spans["us-east-1"]) == 1
    
    def test_multi_region_trace(self, coordinator: CrossRegionTraceCoordinator):
        """Test trace spanning multiple regions."""
        coordinator.register_region("US East", "us-east-1", "host")
        coordinator.register_region("EU West", "eu-west-1", "host")
        
        trace = coordinator.create_cross_region_trace("trace-1", "us-east-1")
        
        # Add spans from both regions
        coordinator.add_region_span("trace-1", "us-east-1", "span-1", "call-1", time.time(), 45.0, "api")
        coordinator.add_region_span("trace-1", "eu-west-1", "span-2", "call-2", time.time(), 50.0, "api")
        
        assert len(trace.regions_involved) == 2
        assert trace.total_span_count() == 2
    
    def test_finalize_trace(self, coordinator: CrossRegionTraceCoordinator):
        """Test finalizing cross-region trace."""
        coordinator.create_cross_region_trace("trace-1", "us-east-1")
        coordinator.add_region_span("trace-1", "us-east-1", "span-1", "op", time.time(), 45.5, "svc")
        
        result = coordinator.finalize_trace("trace-1")
        assert result is not None
        assert result["span_count"] == 1


# ============================================================================
# Trace Decorator Tests
# ============================================================================

class TestTraceDecorator:
    """Test @trace_decorator."""
    
    def test_trace_decorated_function(self):
        """Test tracing decorated function."""
        reset_tracer()
        tracer = get_tracer(trace_sample_rate=1.0)
        tracer.start_trace("operation")
        
        @trace_decorator("decorated_op")
        def my_function():
            return "result"
        
        result = my_function()
        assert result == "result"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_trace_lifecycle(self, tracer: DistributedTracer):
        """Test complete trace lifecycle."""
        # Start trace
        context = tracer.start_trace("user-request")
        
        # Create child spans
        with tracer.trace_operation("database-query") as db_span:
            db_span.set_attribute("table", "users")
            db_span.add_event("query_start")
        
        with tracer.trace_operation("external-api") as api_span:
            api_span.set_attribute("endpoint", "/api/users")
        
        # End trace
        tracer.end_trace()
        
        metrics = tracer.get_metrics()
        assert metrics["trace_collector"]["total_traces"] > 0
    
    def test_cross_region_workflow(self, coordinator: CrossRegionTraceCoordinator):
        """Test cross-region tracing workflow."""
        # Register regions
        coordinator.register_region("US East", "us-east-1", "jaeger-us")
        coordinator.register_region("EU West", "eu-west-1", "jaeger-eu")
        
        # Create multi-region trace
        trace = coordinator.create_cross_region_trace("trace-1", "us-east-1")
        
        # Simulate regional service calls
        coordinator.add_region_span("trace-1", "us-east-1", "span-1", "api-request", time.time(), 45.0, "api")
        coordinator.add_region_span("trace-1", "eu-west-1", "span-2", "cache-lookup", time.time(), 10.0, "cache")
        coordinator.add_region_span("trace-1", "us-east-1", "span-3", "response", time.time(), 5.0, "api")
        
        # Get stats
        stats = coordinator.get_cross_region_stats()
        assert stats["total_traces"] == 1
        assert stats["multi_region_traces"] == 1
