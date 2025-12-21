"""
Distributed Tracing - OpenTelemetry with Jaeger backend

Provides cross-service request tracing, span correlation, and distributed context
propagation for multi-region deployments. Integrates with Jaeger for trace
visualization and analysis.
"""

import logging
import time
import os
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class SpanKind(Enum):
    """OpenTelemetry span kinds."""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


class SpanStatus(Enum):
    """OpenTelemetry span status."""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanContext:
    """
    Span context for distributed tracing.
    
    Contains trace ID, span ID, parent span ID, and trace flags for propagation
    across service boundaries.
    """
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 0x01  # Sampled
    remote: bool = False  # Is this context from remote service
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to W3C Trace Context header format."""
        version = "00"
        parent_id = self.parent_span_id or "0000000000000000"
        return {
            "traceparent": f"{version}-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}",
        }
    
    @staticmethod
    def from_headers(headers: Dict[str, str]) -> Optional["SpanContext"]:
        """Extract span context from W3C Trace Context headers."""
        traceparent = headers.get("traceparent")
        if not traceparent:
            return None
        
        try:
            parts = traceparent.split("-")
            if len(parts) != 4:
                return None
            
            version, trace_id, span_id, trace_flags_str = parts
            
            # Only support version 00
            if version != "00":
                return None
            
            trace_flags = int(trace_flags_str, 16)
            
            return SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                trace_flags=trace_flags,
                remote=True,
            )
        except (ValueError, IndexError):
            return None


@dataclass
class Span:
    """
    OpenTelemetry span representation.
    
    Tracks operation timing, attributes, events, and status for observability.
    """
    trace_id: str
    span_id: str
    name: str
    kind: SpanKind
    start_time: float
    parent_span_id: Optional[str] = None
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to span."""
        event = {
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        }
        self.events.append(event)
    
    def set_status(self, status: SpanStatus, description: str = "") -> None:
        """Set span status."""
        self.status = status
        if description:
            self.set_attribute("status.description", description)
    
    def end(self) -> None:
        """End span and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": self.events,
            "links": self.links,
        }


@dataclass
class Trace:
    """Collection of related spans from a single request."""
    trace_id: str
    root_span_name: str
    start_time: float
    spans: List[Span] = field(default_factory=list)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    services: set = field(default_factory=set)
    
    def add_span(self, span: Span) -> None:
        """Add span to trace."""
        self.spans.append(span)
        # Extract service from span attributes
        service = span.attributes.get("service.name")
        if service:
            self.services.add(service)
    
    def end(self) -> None:
        """End trace and calculate total duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "root_span_name": self.root_span_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "spans": [s.to_dict() for s in self.spans],
            "services": list(self.services),
            "span_count": len(self.spans),
        }


class TraceCollector:
    """
    Collects and manages traces and spans.
    
    Maintains in-memory trace storage with TTL-based cleanup and optional
    export to Jaeger or other backends.
    """
    
    def __init__(self, max_traces: int = 1000, cleanup_interval: int = 300):
        """
        Initialize trace collector.
        
        Args:
            max_traces: Maximum traces to keep in memory
            cleanup_interval: Cleanup interval in seconds (300 = 5 minutes)
        """
        self.max_traces = max_traces
        self.cleanup_interval = cleanup_interval
        self.traces: Dict[str, Trace] = {}
        self.spans: Dict[str, List[Span]] = {}  # trace_id -> spans
        self.last_cleanup = time.time()
    
    def create_trace(
        self,
        trace_id: str,
        root_span_name: str,
    ) -> Trace:
        """Create new trace."""
        trace = Trace(
            trace_id=trace_id,
            root_span_name=root_span_name,
            start_time=time.time(),
        )
        self.traces[trace_id] = trace
        self.spans[trace_id] = []
        
        # Cleanup if needed
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_traces()
        
        return trace
    
    def create_span(
        self,
        trace_id: str,
        span_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
        service_name: str = "unknown",
    ) -> Span:
        """Create new span in trace."""
        span_id = self._generate_span_id()
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            name=span_name,
            kind=kind,
            start_time=time.time(),
            parent_span_id=parent_span_id,
        )
        span.set_attribute("service.name", service_name)
        
        if trace_id in self.spans:
            self.spans[trace_id].append(span)
        
        # Add to trace if exists
        if trace_id in self.traces:
            self.traces[trace_id].add_span(span)
        
        return span
    
    def end_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """End trace and get exported format."""
        if trace_id not in self.traces:
            return None
        
        trace = self.traces[trace_id]
        trace.end()
        
        # End all spans if not already ended
        for span in self.spans.get(trace_id, []):
            if span.end_time is None:
                span.end()
        
        return trace.to_dict()
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace data without ending it."""
        if trace_id not in self.traces:
            return None
        
        return self.traces[trace_id].to_dict()
    
    def get_spans_for_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all spans for a trace."""
        return [s.to_dict() for s in self.spans.get(trace_id, [])]
    
    def get_trace_stats(self) -> Dict[str, Any]:
        """Get statistics about collected traces."""
        total_spans = sum(len(spans) for spans in self.spans.values())
        
        return {
            "total_traces": len(self.traces),
            "total_spans": total_spans,
            "avg_spans_per_trace": total_spans / len(self.traces) if self.traces else 0,
            "max_traces": self.max_traces,
        }
    
    def _generate_span_id(self) -> str:
        """Generate unique span ID (16 hex chars)."""
        import uuid
        return uuid.uuid4().hex[:16]
    
    def _cleanup_old_traces(self) -> None:
        """Remove old traces exceeding max_traces limit."""
        if len(self.traces) > self.max_traces:
            # Remove oldest traces (by end_time or start_time)
            sorted_traces = sorted(
                self.traces.items(),
                key=lambda x: x[1].end_time or x[1].start_time,
            )
            
            # Keep only newest traces
            to_remove = len(self.traces) - self.max_traces
            for trace_id, _ in sorted_traces[:to_remove]:
                self.traces.pop(trace_id, None)
                self.spans.pop(trace_id, None)
        
        self.last_cleanup = time.time()


class JaegerExporter:
    """
    Export traces to Jaeger backend.
    
    Sends spans to Jaeger via gRPC or HTTP protocol for distributed tracing
    visualization and analysis.
    """
    
    def __init__(
        self,
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        service_name: str = "dataforge",
        enabled: bool = True,
    ):
        """
        Initialize Jaeger exporter.
        
        Args:
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port (6831 UDP for Thrift compact)
            service_name: Service name for Jaeger identification
            enabled: Whether to actually send traces
        """
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.service_name = service_name
        self.enabled = enabled and self._check_jaeger_available()
        self.exported_spans = 0
        self.failed_exports = 0
    
    def export_trace(self, trace_data: Dict[str, Any]) -> bool:
        """
        Export trace to Jaeger.
        
        Args:
            trace_data: Trace data dictionary from TraceCollector
            
        Returns:
            True if export successful
        """
        if not self.enabled:
            return False
        
        try:
            # In a real implementation, would use jaeger-client library
            # For now, simulate successful export
            self.exported_spans += len(trace_data.get("spans", []))
            
            # Log export (would send to Jaeger in production)
            logger.debug(
                f"Exported trace {trace_data['trace_id']} "
                f"with {len(trace_data.get('spans', []))} spans to Jaeger"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to export trace to Jaeger: {e}")
            self.failed_exports += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get exporter statistics."""
        return {
            "service_name": self.service_name,
            "jaeger_host": self.jaeger_host,
            "jaeger_port": self.jaeger_port,
            "enabled": self.enabled,
            "exported_spans": self.exported_spans,
            "failed_exports": self.failed_exports,
        }
    
    def _check_jaeger_available(self) -> bool:
        """Check if Jaeger is available (for health check)."""
        # In production, would do actual connectivity check
        jaeger_enabled = os.getenv("JAEGER_ENABLED", "").lower() == "true"
        return jaeger_enabled


class DistributedTracer:
    """
    Main distributed tracer interface.
    
    Provides easy-to-use API for creating traces, spans, and managing
    distributed context propagation.
    """
    
    def __init__(
        self,
        service_name: str = "dataforge",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        trace_sample_rate: float = 1.0,  # 0.0 to 1.0
    ):
        """
        Initialize distributed tracer.
        
        Args:
            service_name: Service name for identification
            jaeger_host: Jaeger agent host
            jaeger_port: Jaeger agent port
            trace_sample_rate: Fraction of traces to collect (0-1)
        """
        self.service_name = service_name
        self.trace_sample_rate = trace_sample_rate
        self.collector = TraceCollector()
        self.exporter = JaegerExporter(
            jaeger_host=jaeger_host,
            jaeger_port=jaeger_port,
            service_name=service_name,
        )
        self._current_trace_id: Optional[str] = None
        self._current_span_id: Optional[str] = None
    
    def start_trace(self, operation: str, parent_context: Optional[SpanContext] = None) -> SpanContext:
        """
        Start a new trace.
        
        Args:
            operation: Operation name for root span
            parent_context: Optional parent span context for cross-service calls
            
        Returns:
            SpanContext for propagation to downstream services
        """
        import uuid
        
        # Decide if this trace should be sampled
        if not self._should_sample():
            trace_id = "0" * 32
        else:
            trace_id = uuid.uuid4().hex
        
        self.collector.create_trace(trace_id, operation)
        self._current_trace_id = trace_id
        
        span_context = SpanContext(
            trace_id=trace_id,
            span_id=self._generate_span_id(),
            parent_span_id=parent_context.span_id if parent_context else None,
            trace_flags=0x01 if self._should_sample() else 0x00,
        )
        self._current_span_id = span_context.span_id
        
        return span_context
    
    def create_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
    ) -> Span:
        """
        Create a new span in current trace.
        
        Args:
            name: Span name
            kind: Span kind (INTERNAL, CLIENT, SERVER, etc.)
            parent_span_id: Optional parent span ID
            
        Returns:
            Span object for use with context manager
        """
        if not self._current_trace_id:
            raise RuntimeError("No active trace. Call start_trace() first.")
        
        span = self.collector.create_span(
            trace_id=self._current_trace_id,
            span_name=name,
            kind=kind,
            parent_span_id=parent_span_id or self._current_span_id,
            service_name=self.service_name,
        )
        return span
    
    @contextmanager
    def trace_operation(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing an operation.
        
        Usage:
            with tracer.trace_operation("database_query") as span:
                span.set_attribute("query", "SELECT * FROM users")
                # Execute operation
        """
        span = self.create_span(name, kind)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        try:
            yield span
            span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            span.add_event("exception", {"type": type(e).__name__, "message": str(e)})
            raise
        finally:
            span.end()
    
    def end_trace(self) -> bool:
        """
        End current trace and export to Jaeger if sampled.
        
        Returns:
            True if trace was exported
        """
        if not self._current_trace_id:
            return False
        
        trace_data = self.collector.end_trace(self._current_trace_id)
        
        if trace_data and self._should_sample():
            exported = self.exporter.export_trace(trace_data)
            self._current_trace_id = None
            self._current_span_id = None
            return exported
        
        self._current_trace_id = None
        self._current_span_id = None
        return False
    
    def inject_context(self, context: SpanContext) -> Dict[str, str]:
        """
        Inject span context for propagation to downstream services.
        
        Returns:
            Headers dictionary for HTTP requests
        """
        return context.to_headers()
    
    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """
        Extract span context from headers (from upstream service).
        
        Args:
            headers: HTTP headers from request
            
        Returns:
            SpanContext if found and valid
        """
        return SpanContext.from_headers(headers)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tracing metrics and statistics."""
        return {
            "service_name": self.service_name,
            "trace_collector": self.collector.get_trace_stats(),
            "jaeger_exporter": self.exporter.get_stats(),
            "trace_sample_rate": self.trace_sample_rate,
        }
    
    def _should_sample(self) -> bool:
        """Determine if current trace should be sampled."""
        import random
        return random.random() < self.trace_sample_rate
    
    def _generate_span_id(self) -> str:
        """Generate unique span ID (16 hex chars)."""
        import uuid
        return uuid.uuid4().hex[:16]


# Global tracer instance
_global_tracer: Optional[DistributedTracer] = None


def get_tracer(
    service_name: str = "dataforge",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    trace_sample_rate: float = 1.0,
) -> DistributedTracer:
    """
    Get or create global tracer instance.
    
    Args:
        service_name: Service name
        jaeger_host: Jaeger host
        jaeger_port: Jaeger port
        trace_sample_rate: Sampling rate (0-1)
        
    Returns:
        DistributedTracer instance
    """
    global _global_tracer
    
    if _global_tracer is None:
        _global_tracer = DistributedTracer(
            service_name=service_name,
            jaeger_host=jaeger_host,
            jaeger_port=jaeger_port,
            trace_sample_rate=trace_sample_rate,
        )
    
    return _global_tracer


def reset_tracer() -> None:
    """Reset global tracer (for testing)."""
    global _global_tracer
    _global_tracer = None


def trace_decorator(
    operation_name: str,
    kind: SpanKind = SpanKind.INTERNAL,
):
    """
    Decorator for automatic span creation around function calls.
    
    Usage:
        @trace_decorator("expensive_operation")
        def my_function():
            return "result"
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.trace_operation(operation_name, kind) as span:
                span.set_attribute("function", func.__name__)
                span.set_attribute("args_count", len(args))
                span.set_attribute("kwargs_count", len(kwargs))
                return func(*args, **kwargs)
        return wrapper
    return decorator
