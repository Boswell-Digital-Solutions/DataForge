"""
Forge Telemetry - Unified telemetry client for the Forge ecosystem.

This package provides telemetry emission for DataForge, NeuroForge, and Rake.
All events are written to a shared PostgreSQL events table.
"""

from .client import TelemetryClient, emit_event
from .models import TelemetryEvent, ServiceType, SeverityLevel

__version__ = "0.1.0"

__all__ = [
    "TelemetryClient",
    "emit_event",
    "TelemetryEvent",
    "ServiceType",
    "SeverityLevel",
]
