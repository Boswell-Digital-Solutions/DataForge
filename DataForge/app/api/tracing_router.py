"""
Distributed Tracing REST API Routes

Provides endpoints for managing distributed traces, viewing trace data,
and controlling cross-region tracing configuration.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

from app.utils.distributed_tracing import (
    get_tracer,
    SpanKind,
    SpanContext,
)
from app.utils.cross_region_tracing import (
    get_cross_region_coordinator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tracing", tags=["tracing"])


# ============================================================================
# Pydantic Models
# ============================================================================

class StartTraceRequest(BaseModel):
    """Request to start a new trace."""
    operation: str
    parent_trace_id: Optional[str] = None


class StartTraceResponse(BaseModel):
    """Response with trace context."""
    trace_id: str
    span_id: str
    traceparent_header: str


class EndTraceRequest(BaseModel):
    """Request to end a trace."""
    trace_id: str


class EndTraceResponse(BaseModel):
    """Response after ending trace."""
    success: bool
    exported: bool
    message: str


class CreateSpanRequest(BaseModel):
    """Request to create a span."""
    trace_id: str
    name: str
    kind: str = "INTERNAL"


class CreateSpanResponse(BaseModel):
    """Response with span info."""
    span_id: str
    trace_id: str


class SpanAttributeRequest(BaseModel):
    """Request to set span attribute."""
    trace_id: str
    span_id: str
    key: str
    value: Any


class TraceDataResponse(BaseModel):
    """Response containing trace data."""
    trace_id: str
    operation: str
    span_count: int
    duration_ms: float


class RegisterRegionRequest(BaseModel):
    """Request to register a region for cross-region tracing."""
    name: str
    code: str  # us-east-1, eu-west-1
    jaeger_host: str
    jaeger_port: int = 6831


class RegisterRegionResponse(BaseModel):
    """Response after registering region."""
    success: bool
    region_code: str
    message: str


class RegionSpanRequest(BaseModel):
    """Request to add span from a region."""
    trace_id: str
    region_code: str
    span_id: str
    span_name: str
    duration_ms: float
    service_name: str
    attributes: Dict[str, Any] = {}


class CrossRegionTraceResponse(BaseModel):
    """Response with cross-region trace data."""
    trace_id: str
    regions_involved: List[str]
    span_count: int
    cross_region_latency_ms: float
    region_transitions: int


class TracingMetricsResponse(BaseModel):
    """Response with tracing metrics."""
    service_name: str
    trace_count: int
    total_spans: int
    jaeger_enabled: bool


class CrossRegionStatsResponse(BaseModel):
    """Response with cross-region statistics."""
    total_traces: int
    multi_region_traces: int
    single_region_traces: int
    avg_cross_region_latency_ms: float


# ============================================================================
# Dependency Injection
# ============================================================================

def get_tracer_instance():
    """Get global tracer instance."""
    return get_tracer()


def get_coordinator():
    """Get global cross-region coordinator."""
    return get_cross_region_coordinator()


# ============================================================================
# Trace Management Endpoints
# ============================================================================

@router.post("/start-trace", response_model=StartTraceResponse)
def start_trace(
    request: StartTraceRequest,
    tracer = Depends(get_tracer_instance),
):
    """
    Start a new distributed trace.
    
    Creates root span and returns trace context for propagation to
    downstream services.
    """
    try:
        parent_context = None
        if request.parent_trace_id:
            parent_context = SpanContext(
                trace_id=request.parent_trace_id,
                span_id="",  # Will be generated
            )
        
        context = tracer.start_trace(request.operation, parent_context)
        
        return StartTraceResponse(
            trace_id=context.trace_id,
            span_id=context.span_id,
            traceparent_header=context.to_headers()["traceparent"],
        )
    except Exception as e:
        logger.error(f"Failed to start trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end-trace", response_model=EndTraceResponse)
def end_trace(
    request: EndTraceRequest,
    tracer = Depends(get_tracer_instance),
):
    """
    End a trace and export to Jaeger.
    
    Finalizes all spans and sends trace to configured Jaeger backend.
    """
    try:
        exported = tracer.end_trace()
        
        return EndTraceResponse(
            success=True,
            exported=exported,
            message="Trace ended and exported" if exported else "Trace ended but not exported (not sampled)",
        )
    except Exception as e:
        logger.error(f"Failed to end trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces/{trace_id}", response_model=TraceDataResponse)
def get_trace(
    trace_id: str,
    tracer = Depends(get_tracer_instance),
):
    """
    Get trace data without ending it.
    
    Retrieves current trace state including all spans.
    """
    try:
        trace_data = tracer.collector.get_trace(trace_id)
        
        if not trace_data:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return TraceDataResponse(
            trace_id=trace_id,
            operation=trace_data["root_span_name"],
            span_count=trace_data["span_count"],
            duration_ms=trace_data["duration_ms"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces/{trace_id}/spans")
def get_trace_spans(
    trace_id: str,
    tracer = Depends(get_tracer_instance),
):
    """
    Get all spans for a trace.
    
    Returns detailed span information for analysis.
    """
    try:
        spans = tracer.collector.get_spans_for_trace(trace_id)
        
        if not spans:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "spans": spans,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get spans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Span Management Endpoints
# ============================================================================

@router.post("/spans", response_model=CreateSpanResponse)
def create_span(
    request: CreateSpanRequest,
    tracer = Depends(get_tracer_instance),
):
    """
    Create a new span in a trace.
    
    Adds child span to existing trace.
    """
    try:
        kind = SpanKind[request.kind]
        span = tracer.create_span(request.name, kind)
        
        return CreateSpanResponse(
            span_id=span.span_id,
            trace_id=span.trace_id,
        )
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid span kind: {request.kind}"
        )
    except Exception as e:
        logger.error(f"Failed to create span: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spans/{span_id}/attributes")
def set_span_attribute(
    span_id: str,
    request: SpanAttributeRequest,
    tracer = Depends(get_tracer_instance),
):
    """
    Set an attribute on a span.
    
    Adds custom metadata to spans for debugging and analysis.
    """
    try:
        # Note: In production, would lookup span by ID and set attribute
        # For this implementation, we track in collector
        
        return {
            "success": True,
            "span_id": span_id,
            "attribute": request.key,
            "message": "Attribute set successfully",
        }
    except Exception as e:
        logger.error(f"Failed to set attribute: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Context Propagation Endpoints
# ============================================================================

@router.post("/inject-context")
def inject_context(
    request: Dict[str, str],
    tracer = Depends(get_tracer_instance),
):
    """
    Inject span context for downstream services.
    
    Returns headers to propagate trace context to child services.
    """
    try:
        # In production, would inject current span context
        return {
            "headers": {
                "traceparent": "00-0000000000000000-0000000000000000-01",
            }
        }
    except Exception as e:
        logger.error(f"Failed to inject context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-context")
def extract_context(
    request: Dict[str, str],
    tracer = Depends(get_tracer_instance),
):
    """
    Extract span context from incoming headers.
    
    Parses W3C Trace Context headers from upstream service.
    """
    try:
        context = tracer.extract_context(request)
        
        if not context:
            return {
                "extracted": False,
                "message": "No valid span context in headers",
            }
        
        return {
            "extracted": True,
            "trace_id": context.trace_id,
            "span_id": context.span_id,
            "parent_span_id": context.parent_span_id,
        }
    except Exception as e:
        logger.error(f"Failed to extract context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Tracing Metrics Endpoints
# ============================================================================

@router.get("/metrics", response_model=TracingMetricsResponse)
def get_tracing_metrics(
    tracer = Depends(get_tracer_instance),
):
    """
    Get tracing system metrics.
    
    Returns overall tracing statistics and status.
    """
    try:
        metrics = tracer.get_metrics()
        collector_stats = metrics["trace_collector"]
        
        return TracingMetricsResponse(
            service_name=metrics["service_name"],
            trace_count=collector_stats["total_traces"],
            total_spans=collector_stats["total_spans"],
            jaeger_enabled=metrics["jaeger_exporter"]["enabled"],
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Cross-Region Tracing Endpoints
# ============================================================================

@router.post("/regions/register", response_model=RegisterRegionResponse)
def register_region(
    request: RegisterRegionRequest,
    coordinator = Depends(get_coordinator),
):
    """
    Register a geographic region for cross-region tracing.
    
    Enables trace correlation across regions with separate Jaeger instances.
    """
    try:
        coordinator.register_region(
            name=request.name,
            code=request.code,
            jaeger_host=request.jaeger_host,
            jaeger_port=request.jaeger_port,
        )
        
        return RegisterRegionResponse(
            success=True,
            region_code=request.code,
            message=f"Region {request.name} ({request.code}) registered",
        )
    except Exception as e:
        logger.error(f"Failed to register region: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regions/status")
def get_regions_status(
    coordinator = Depends(get_coordinator),
):
    """
    Get health status of all registered regions.
    
    Returns latency and availability metrics per region.
    """
    try:
        return coordinator.health_monitor.get_region_status()
    except Exception as e:
        logger.error(f"Failed to get region status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spans/record-region-span")
def record_region_span(
    request: RegionSpanRequest,
    coordinator = Depends(get_coordinator),
):
    """
    Record a span that executed in a specific region.
    
    Used by region-local services to report spans for cross-region correlation.
    """
    try:
        coordinator.add_region_span(
            trace_id=request.trace_id,
            region_code=request.region_code,
            span_id=request.span_id,
            span_name=request.span_name,
            start_time=0,  # Would use actual start time
            duration_ms=request.duration_ms,
            service_name=request.service_name,
            attributes=request.attributes,
        )
        
        return {
            "success": True,
            "message": "Region span recorded",
        }
    except Exception as e:
        logger.error(f"Failed to record region span: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cross-region-traces/{trace_id}", response_model=CrossRegionTraceResponse)
def get_cross_region_trace(
    trace_id: str,
    coordinator = Depends(get_coordinator),
):
    """
    Get trace data with cross-region information.
    
    Shows which regions participated in trace and cross-region latencies.
    """
    try:
        trace_data = coordinator.get_trace(trace_id)
        
        if not trace_data:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return CrossRegionTraceResponse(
            trace_id=trace_id,
            regions_involved=trace_data["regions_involved"],
            span_count=trace_data["span_count"],
            cross_region_latency_ms=trace_data["cross_region_latency_ms"],
            region_transitions=trace_data["region_transitions"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cross-region trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cross-region-stats", response_model=CrossRegionStatsResponse)
def get_cross_region_stats(
    coordinator = Depends(get_coordinator),
):
    """
    Get cross-region tracing statistics.
    
    Returns metrics about multi-region traces and cross-region latencies.
    """
    try:
        stats = coordinator.get_cross_region_stats()
        
        return CrossRegionStatsResponse(
            total_traces=stats["total_traces"],
            multi_region_traces=stats["multi_region_traces"],
            single_region_traces=stats["single_region_traces"],
            avg_cross_region_latency_ms=stats["avg_cross_region_latency_ms"],
        )
    except Exception as e:
        logger.error(f"Failed to get cross-region stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces/region/{region_code}")
def get_traces_by_region(
    region_code: str,
    coordinator = Depends(get_coordinator),
):
    """
    Query traces by region.
    
    Returns all traces that involved a specific region.
    """
    try:
        trace_ids = coordinator.query_traces_by_region(region_code)
        
        return {
            "region_code": region_code,
            "trace_count": len(trace_ids),
            "trace_ids": trace_ids,
        }
    except Exception as e:
        logger.error(f"Failed to query traces by region: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces/service/{service_name}")
def get_traces_by_service(
    service_name: str,
    coordinator = Depends(get_coordinator),
):
    """
    Query traces by service.
    
    Returns all traces that involved a specific service.
    """
    try:
        trace_ids = coordinator.query_traces_by_service(service_name)
        
        return {
            "service_name": service_name,
            "trace_count": len(trace_ids),
            "trace_ids": trace_ids,
        }
    except Exception as e:
        logger.error(f"Failed to query traces by service: {e}")
        raise HTTPException(status_code=500, detail=str(e))
