"""
Telemetry client for emitting events to the shared events table.
"""

import os
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from .models import TelemetryEvent, ServiceType, SeverityLevel


class TelemetryClient:
    """
    Client for emitting telemetry events to the shared Forge events table.

    Usage:
        telemetry = TelemetryClient(database_url)
        await telemetry.emit(... )

    Supports DATABASE_URL or DATABASE_BASE_URL + DATABASE_USER / DATABASE_PASSWORD / DATABASE_NAME
    and honors the TELEMETRY_REQUIRED flag.
    """

    def __init__(self, database_url: Optional[str] = None, *, telemetry_required: Optional[bool] = None):
        """
        Initialize telemetry client.

        Args:
            database_url: PostgreSQL connection URL. If not provided, reads DATABASE_URL env var.
        """
        self.telemetry_required = telemetry_required if telemetry_required is not None else os.getenv("TELEMETRY_REQUIRED", "false").lower() in {
            "1", "true", "yes"
        }
        self.db_url = self._resolve_database_url(database_url)
        self.database_url = self.db_url
        self.enabled = bool(self.db_url)
        self.engine: Optional[Any] = None
        self.SessionLocal: Optional[sessionmaker] = None

        if self.enabled:
            self.engine = create_engine(self.db_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        elif self.telemetry_required:
            raise ValueError(
                "Telemetry is required but no database configuration was found. "
                "Set DATABASE_URL or DATABASE_BASE_URL + DATABASE_USER/DATABASE_PASSWORD/DATABASE_NAME."
            )

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
        if not self.enabled or self.SessionLocal is None:
            return event.event_id

        import json
        db: Session = self.SessionLocal()
        try:
            is_sqlite = "sqlite" in self.database_url.lower()

            if is_sqlite:
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

    def _resolve_database_url(self, provided_url: Optional[str]) -> Optional[str]:
        if provided_url:
            return provided_url
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        return self._build_url_from_components()

    def _build_url_from_components(self) -> Optional[str]:
        base_url = os.getenv("DATABASE_BASE_URL")
        user = os.getenv("DATABASE_USER")
        password = os.getenv("DATABASE_PASSWORD")
        name = os.getenv("DATABASE_NAME")
        if not (base_url and user and password and name):
            return None
        sslmode = os.getenv("DATABASE_SSLMODE", "require")
        return self._compose_url(base_url, user, password, name, sslmode)

    def _compose_url(
        self,
        base_url: str,
        user: str,
        password: str,
        name: str,
        sslmode: str,
    ) -> str:
        parsed = urlparse(base_url)
        scheme = parsed.scheme or "postgresql"
        hostname = parsed.hostname or parsed.path or ""
        port = f":{parsed.port}" if parsed.port else ""
        netloc = f"{user}:{password}@{hostname}{port}"
        path = f"/{name}"
        query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_params.setdefault("sslmode", sslmode)
        query = urlencode(query_params)
        return urlunparse((scheme, netloc, path, parsed.params, query, parsed.fragment))


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
