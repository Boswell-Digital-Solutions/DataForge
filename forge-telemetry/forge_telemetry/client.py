"""
Telemetry client for emitting events to the shared events table.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from .models import TelemetryEvent, ServiceType, SeverityLevel


class TelemetryClient:
    """
    Client for emitting telemetry events to the shared Forge events table.

    Usage:
        telemetry = TelemetryClient(database_url)
        await telemetry.emit({
            "service": "dataforge",
            "event_type": "query",
            "correlation_id": correlation_id,
            "metadata": {"query": "search term"},
            "metrics": {"duration_ms": 123}
        })
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize telemetry client.

        Args:
            database_url: PostgreSQL connection URL. If not provided, uses DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL must be provided or set in environment")

        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def emit(
        self,
        service: str,
        event_type: str,
        severity: str = "info",
        correlation_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Emit a telemetry event (synchronous).

        Args:
            service: Service name ('dataforge', 'neuroforge', 'rake')
            event_type: Type of event ('query', 'model_request', 'job_completed', etc.)
            severity: Event severity ('info', 'warning', 'error', 'critical')
            correlation_id: UUID for distributed tracing
            metadata: Additional context as JSON
            metrics: Numerical metrics as JSON

        Returns:
            UUID: The event_id of the created event
        """
        event = TelemetryEvent(
            service=ServiceType(service),
            event_type=event_type,
            severity=SeverityLevel(severity),
            correlation_id=correlation_id,
            metadata=metadata,
            metrics=metrics,
        )

        return self._write_event(event)

    async def emit_async(
        self,
        service: str,
        event_type: str,
        severity: str = "info",
        correlation_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Emit a telemetry event (asynchronous).

        For async code, use this method. For sync code, use emit().

        Args:
            service: Service name ('dataforge', 'neuroforge', 'rake')
            event_type: Type of event ('query', 'model_request', 'job_completed', etc.)
            severity: Event severity ('info', 'warning', 'error', 'critical')
            correlation_id: UUID for distributed tracing
            metadata: Additional context as JSON
            metrics: Numerical metrics as JSON

        Returns:
            UUID: The event_id of the created event
        """
        # For now, using sync implementation
        # TODO: Implement true async with asyncpg
        return self.emit(
            service=service,
            event_type=event_type,
            severity=severity,
            correlation_id=correlation_id,
            metadata=metadata,
            metrics=metrics,
        )

    def _write_event(self, event: TelemetryEvent) -> UUID:
        """Write event to database."""
        import json
        from datetime import datetime

        db: Session = self.SessionLocal()
        try:
            # Detect if we're using SQLite or PostgreSQL
            is_sqlite = "sqlite" in self.database_url.lower()

            if is_sqlite:
                # SQLite: use TEXT for UUIDs and JSON, use CURRENT_TIMESTAMP
                query = text("""
                    INSERT INTO events (
                        event_id, timestamp, service, event_type, severity,
                        correlation_id, metadata, metrics, created_at
                    )
                    VALUES (
                        :event_id, :timestamp, :service, :event_type, :severity,
                        :correlation_id, :metadata, :metrics, CURRENT_TIMESTAMP
                    )
                """)

                db.execute(query, {
                    "event_id": str(event.event_id),
                    "timestamp": event.timestamp.isoformat(),
                    "service": event.service,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                    "metadata": json.dumps(event.metadata) if event.metadata else None,
                    "metrics": json.dumps(event.metrics) if event.metrics else None,
                })
            else:
                # PostgreSQL: use UUID and JSONB types, use NOW()
                query = text("""
                    INSERT INTO events (
                        event_id, timestamp, service, event_type, severity,
                        correlation_id, metadata, metrics, created_at
                    )
                    VALUES (
                        :event_id, :timestamp, :service, :event_type, :severity,
                        :correlation_id, :metadata, :metrics, NOW()
                    )
                """)

                db.execute(query, {
                    "event_id": str(event.event_id),
                    "timestamp": event.timestamp,
                    "service": event.service,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                    "metadata": event.metadata,
                    "metrics": event.metrics,
                })

            db.commit()
            return event.event_id
        except Exception as e:
            db.rollback()
            # Don't fail the application if telemetry fails
            print(f"Telemetry emission failed: {e}")
            return event.event_id
        finally:
            db.close()


# Convenience function for quick event emission
def emit_event(
    service: str,
    event_type: str,
    severity: str = "info",
    correlation_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    database_url: Optional[str] = None,
) -> UUID:
    """
    Quick function to emit a telemetry event without creating a client instance.

    Usage:
        from forge_telemetry import emit_event

        emit_event(
            service="dataforge",
            event_type="query",
            correlation_id=correlation_id,
            metrics={"duration_ms": 123}
        )
    """
    client = TelemetryClient(database_url)
    return client.emit(
        service=service,
        event_type=event_type,
        severity=severity,
        correlation_id=correlation_id,
        metadata=metadata,
        metrics=metrics,
    )
