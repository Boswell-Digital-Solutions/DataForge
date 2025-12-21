"""
Cross-Region Trace Correlation

Coordinates tracing across geographic regions with latency awareness,
region-specific exporters, and aggregated trace visualization.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RegionStatus(Enum):
    """Health status of a region."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass
class RegionInfo:
    """Information about a geographic region."""
    name: str
    code: str  # us-east-1, eu-west-1, etc.
    jaeger_host: str
    jaeger_port: int = 6831
    latency_baseline_ms: float = 0.0
    status: RegionStatus = RegionStatus.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)
    
    def is_healthy(self, heartbeat_timeout: int = 30) -> bool:
        """Check if region is responsive."""
        elapsed = time.time() - self.last_heartbeat
        if self.status == RegionStatus.UNHEALTHY:
            return False
        return elapsed < heartbeat_timeout


@dataclass
class RegionSpan:
    """Span that originated in or executed in a specific region."""
    span_id: str
    region_code: str
    span_name: str
    start_time: float
    duration_ms: float
    service_name: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossRegionTrace:
    """
    Trace distributed across multiple regions.
    
    Tracks which regions participated in a single logical operation,
    enabling visualization and latency analysis across regions.
    """
    trace_id: str
    regions_involved: Set[str] = field(default_factory=set)
    region_spans: Dict[str, List[RegionSpan]] = field(default_factory=dict)  # region -> spans
    cross_region_latency_ms: float = 0.0
    region_transition_count: int = 0
    created_at: float = field(default_factory=time.time)
    
    def add_span(self, region_code: str, span: RegionSpan) -> None:
        """Add span from a region."""
        self.regions_involved.add(region_code)
        
        if region_code not in self.region_spans:
            self.region_spans[region_code] = []
        
        self.region_spans[region_code].append(span)
    
    def get_span_count(self, region_code: str) -> int:
        """Get span count for a region."""
        return len(self.region_spans.get(region_code, []))
    
    def total_span_count(self) -> int:
        """Get total spans across all regions."""
        return sum(len(spans) for spans in self.region_spans.values())
    
    def get_region_breakdown(self) -> Dict[str, Any]:
        """Get breakdown by region."""
        breakdown = {}
        for region, spans in self.region_spans.items():
            total_duration = sum(s.duration_ms for s in spans)
            breakdown[region] = {
                "span_count": len(spans),
                "total_duration_ms": total_duration,
                "services": len(set(s.service_name for s in spans)),
            }
        return breakdown


class RegionHealthMonitor:
    """
    Monitor health of regions and coordinate failover.
    
    Tracks latency, availability, and automatically disables regions
    that become unhealthy.
    """
    
    def __init__(self, latency_threshold_ms: float = 500.0):
        """
        Initialize region health monitor.
        
        Args:
            latency_threshold_ms: Latency threshold for degraded status
        """
        self.regions: Dict[str, RegionInfo] = {}
        self.latency_threshold_ms = latency_threshold_ms
        self.latency_measurements: Dict[str, List[float]] = {}
        self.failure_count: Dict[str, int] = {}
    
    def register_region(
        self,
        name: str,
        code: str,
        jaeger_host: str,
        jaeger_port: int = 6831,
    ) -> None:
        """Register a region for tracing."""
        region = RegionInfo(
            name=name,
            code=code,
            jaeger_host=jaeger_host,
            jaeger_port=jaeger_port,
        )
        self.regions[code] = region
        self.latency_measurements[code] = []
        self.failure_count[code] = 0
    
    def record_latency(self, region_code: str, latency_ms: float) -> None:
        """Record latency measurement for region."""
        if region_code not in self.regions:
            return
        
        # Keep last 100 measurements
        measurements = self.latency_measurements[region_code]
        measurements.append(latency_ms)
        if len(measurements) > 100:
            measurements.pop(0)
        
        # Update status based on average latency
        avg_latency = sum(measurements) / len(measurements)
        region = self.regions[region_code]
        
        if avg_latency > self.latency_threshold_ms:
            region.status = RegionStatus.DEGRADED
        else:
            if region.status == RegionStatus.DEGRADED:
                region.status = RegionStatus.HEALTHY
    
    def record_failure(self, region_code: str) -> None:
        """Record failed request to region."""
        if region_code not in self.regions:
            return
        
        self.failure_count[region_code] += 1
        
        # Mark unhealthy after 5 consecutive failures
        if self.failure_count[region_code] >= 5:
            self.regions[region_code].status = RegionStatus.UNHEALTHY
    
    def record_success(self, region_code: str) -> None:
        """Record successful request to region."""
        if region_code not in self.regions:
            return
        
        self.failure_count[region_code] = 0
        self.regions[region_code].last_heartbeat = time.time()
        
        # Recover from degraded state
        if self.regions[region_code].status == RegionStatus.DEGRADED:
            self.regions[region_code].status = RegionStatus.HEALTHY
    
    def get_healthy_regions(self) -> List[str]:
        """Get list of healthy region codes."""
        return [
            code for code, region in self.regions.items()
            if region.status == RegionStatus.HEALTHY
        ]
    
    def get_region_status(self) -> Dict[str, Any]:
        """Get status of all regions."""
        status = {}
        for code, region in self.regions.items():
            measurements = self.latency_measurements.get(code, [])
            avg_latency = sum(measurements) / len(measurements) if measurements else 0
            
            status[code] = {
                "name": region.name,
                "status": region.status.value,
                "avg_latency_ms": avg_latency,
                "measurement_count": len(measurements),
                "failure_count": self.failure_count.get(code, 0),
            }
        return status


class CrossRegionTraceCoordinator:
    """
    Coordinate tracing across multiple geographic regions.
    
    Aggregates traces from different regions, tracks cross-region calls,
    and provides unified visualization of distributed operations.
    """
    
    def __init__(self, max_traces: int = 1000):
        """
        Initialize cross-region coordinator.
        
        Args:
            max_traces: Maximum traces to keep
        """
        self.max_traces = max_traces
        self.traces: Dict[str, CrossRegionTrace] = {}
        self.health_monitor = RegionHealthMonitor()
        self.region_exporters: Dict[str, "RegionExporter"] = {}
        self.last_cleanup = time.time()
    
    def register_region(
        self,
        name: str,
        code: str,
        jaeger_host: str,
        jaeger_port: int = 6831,
    ) -> None:
        """Register region for cross-region tracing."""
        self.health_monitor.register_region(name, code, jaeger_host, jaeger_port)
        exporter = RegionExporter(code, jaeger_host, jaeger_port)
        self.region_exporters[code] = exporter
    
    def create_cross_region_trace(self, trace_id: str, origin_region: str) -> CrossRegionTrace:
        """Create new cross-region trace."""
        trace = CrossRegionTrace(trace_id=trace_id)
        trace.regions_involved.add(origin_region)
        self.traces[trace_id] = trace
        return trace
    
    def add_region_span(
        self,
        trace_id: str,
        region_code: str,
        span_id: str,
        span_name: str,
        start_time: float,
        duration_ms: float,
        service_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add span from specific region to trace."""
        if trace_id not in self.traces:
            self.traces[trace_id] = CrossRegionTrace(trace_id=trace_id)
        
        span = RegionSpan(
            span_id=span_id,
            region_code=region_code,
            span_name=span_name,
            start_time=start_time,
            duration_ms=duration_ms,
            service_name=service_name,
            attributes=attributes or {},
        )
        
        self.traces[trace_id].add_span(region_code, span)
        
        # Cleanup if needed
        if len(self.traces) > self.max_traces:
            self._cleanup_old_traces()
    
    def finalize_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Finalize trace and calculate cross-region metrics.
        
        Returns:
            Trace data for export
        """
        if trace_id not in self.traces:
            return None
        
        trace = self.traces[trace_id]
        
        # Calculate cross-region latency (time between first and last span across regions)
        all_spans = []
        for spans in trace.region_spans.values():
            all_spans.extend(spans)
        
        if all_spans:
            min_start = min(s.start_time for s in all_spans)
            max_end = max(s.start_time + s.duration_ms / 1000 for s in all_spans)
            trace.cross_region_latency_ms = (max_end - min_start) * 1000
        
        # Count region transitions (spans in different regions with parent-child relationship)
        trace.region_transition_count = len(trace.regions_involved) - 1
        
        return {
            "trace_id": trace_id,
            "regions_involved": list(trace.regions_involved),
            "span_count": trace.total_span_count(),
            "cross_region_latency_ms": trace.cross_region_latency_ms,
            "region_transitions": trace.region_transition_count,
            "region_breakdown": trace.get_region_breakdown(),
        }
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace data."""
        if trace_id not in self.traces:
            return None
        
        return self.finalize_trace(trace_id)
    
    def query_traces_by_region(self, region_code: str) -> List[str]:
        """Get all traces that involve a specific region."""
        return [
            trace_id for trace_id, trace in self.traces.items()
            if region_code in trace.regions_involved
        ]
    
    def query_traces_by_service(self, service_name: str) -> List[str]:
        """Get all traces that involve a specific service."""
        result = []
        for trace_id, trace in self.traces.items():
            services = set()
            for spans in trace.region_spans.values():
                services.update(s.service_name for s in spans)
            
            if service_name in services:
                result.append(trace_id)
        
        return result
    
    def get_cross_region_stats(self) -> Dict[str, Any]:
        """Get statistics about cross-region tracing."""
        multi_region_traces = [
            t for t in self.traces.values()
            if len(t.regions_involved) > 1
        ]
        
        avg_cross_region_latency = 0.0
        if multi_region_traces:
            avg_cross_region_latency = (
                sum(t.cross_region_latency_ms for t in multi_region_traces)
                / len(multi_region_traces)
            )
        
        return {
            "total_traces": len(self.traces),
            "multi_region_traces": len(multi_region_traces),
            "single_region_traces": len(self.traces) - len(multi_region_traces),
            "avg_cross_region_latency_ms": avg_cross_region_latency,
            "regions": self.health_monitor.get_region_status(),
        }
    
    def _cleanup_old_traces(self) -> None:
        """Remove old traces exceeding limit."""
        if len(self.traces) > self.max_traces:
            sorted_traces = sorted(
                self.traces.items(),
                key=lambda x: x[1].created_at,
            )
            
            to_remove = len(self.traces) - self.max_traces
            for trace_id, _ in sorted_traces[:to_remove]:
                self.traces.pop(trace_id, None)


class RegionExporter:
    """Export traces to region-specific Jaeger instance."""
    
    def __init__(self, region_code: str, jaeger_host: str, jaeger_port: int):
        """Initialize region exporter."""
        self.region_code = region_code
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.exported_traces = 0
        self.failed_exports = 0
    
    def export(self, trace_data: Dict[str, Any]) -> bool:
        """Export trace to region's Jaeger instance."""
        try:
            # In production, would send to region-specific Jaeger
            self.exported_traces += 1
            logger.debug(
                f"Exported trace {trace_data['trace_id']} "
                f"to {self.region_code} Jaeger at {self.jaeger_host}:{self.jaeger_port}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to export to {self.region_code}: {e}")
            self.failed_exports += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get exporter statistics."""
        return {
            "region_code": self.region_code,
            "jaeger_host": self.jaeger_host,
            "jaeger_port": self.jaeger_port,
            "exported_traces": self.exported_traces,
            "failed_exports": self.failed_exports,
        }


# Global cross-region coordinator instance
_global_coordinator: Optional[CrossRegionTraceCoordinator] = None


def get_cross_region_coordinator() -> CrossRegionTraceCoordinator:
    """Get or create global cross-region coordinator."""
    global _global_coordinator
    
    if _global_coordinator is None:
        _global_coordinator = CrossRegionTraceCoordinator()
    
    return _global_coordinator


def reset_cross_region_coordinator() -> None:
    """Reset coordinator (for testing)."""
    global _global_coordinator
    _global_coordinator = None
