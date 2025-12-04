"""
Telemetry data models and types.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """Forge service types."""
    DATAFORGE = "dataforge"
    NEUROFORGE = "neuroforge"
    RAKE = "rake"


class SeverityLevel(str, Enum):
    """Event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TelemetryEvent(BaseModel):
    """
    Telemetry event model matching the events table schema.

    All telemetry events across the Forge ecosystem use this model.
    """
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: ServiceType
    event_type: str
    severity: SeverityLevel = SeverityLevel.INFO
    correlation_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True
