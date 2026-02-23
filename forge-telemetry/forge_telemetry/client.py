"""
Telemetry client for emitting events to the shared events table.
"""

import logging
import os
import socket
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session

from .models import TelemetryEvent, ServiceType, SeverityLevel

logger = logging.getLogger(__name__)


class TelemetryClient:
    """
    Client for emitting telemetry events to the shared Forge events table.

    Usage:
        telemetry = TelemetryClient(database_url)
        await telemetry.emit(... )

    Supports DATAFORGE_DATABASE_URL or DATABASE_BASE_URL + DATABASE_USER / DATABASE_PASSWORD / DATABASE_NAME
    and honors the TELEMETRY_REQUIRED flag.
    """

    def __init__(self, database_url: Optional[str] = None, *, telemetry_required: Optional[bool] = None):
        """
        Initialize telemetry client.

        Args:
            database_url: PostgreSQL connection URL. If not provided, reads DATAFORGE_DATABASE_URL env var.
        """
        self.telemetry_required = telemetry_required if telemetry_required is not None else os.getenv("TELEMETRY_REQUIRED", "false").lower() in {
            "1", "true", "yes"
        }
        self.db_url, host, port = self._resolve_database_url(database_url)
        self.database_url = self.db_url
        self.enabled = bool(self.db_url)
        self.engine: Optional[Any] = None
        self.SessionLocal: Optional[sessionmaker] = None

        if host:
            logger.info("Telemetry DB target host=%s port=%s", host, port or 5432)

        if self.enabled:
            try:
                self.engine = create_engine(self.db_url)
                with self.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
            except (socket.gaierror, OperationalError, TimeoutError, OSError) as exc:
                self._handle_connection_error(exc)
                return
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        elif self.telemetry_required:
            raise ValueError(
                "Telemetry is required but no database configuration was found. "
                "Set DATAFORGE_DATABASE_URL or DATABASE_BASE_URL + DATABASE_USER/DATABASE_PASSWORD/DATABASE_NAME."
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

    def _resolve_database_url(
        self, provided_url: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        if provided_url:
            return provided_url, *self._extract_host_port(provided_url)
        env_url = os.getenv("DATAFORGE_DATABASE_URL")
        if env_url:
            return env_url, *self._extract_host_port(env_url)
        return self._build_url_from_components()

    def _handle_connection_error(self, exc: Exception) -> None:
        if self.telemetry_required:
            raise ValueError(
                "Telemetry is required but the database connection could not be established."
            ) from exc

        logger.warning("Telemetry disabled because the database connection failed: %s", exc)
        self.enabled = False
        self.db_url = None
        self.engine = None
        self.SessionLocal = None

    def _build_url_from_components(
        self,
    ) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        base_url = os.getenv("DATABASE_BASE_URL")
        user = os.getenv("DATABASE_USER")
        password = os.getenv("DATABASE_PASSWORD")
        name = os.getenv("DATABASE_NAME")
        if not (base_url and user and password and name):
            return None, None, None
        sslmode = os.getenv("DATABASE_SSLMODE", "require")
        host, port = self._extract_host_port(base_url)
        if not host:
            return None, None, None
        return (
            self._compose_url(host, port, user, password, name, sslmode),
            host,
            port,
        )

    def _compose_url(
        self,
        host: str,
        port: Optional[int],
        user: str,
        password: str,
        name: str,
        sslmode: str,
    ) -> str:
        scheme = "postgresql"
        port_value = port or 5432
        port_fragment = f":{port_value}"
        netloc = f"{user}:{password}@{host}{port_fragment}"
        path = f"/{name}"
        query_params = {"sslmode": sslmode}
        query = urlencode(query_params)
        return urlunparse((scheme, netloc, path, "", query, ""))

    def _extract_host_port(self, raw_url: str) -> Tuple[Optional[str], Optional[int]]:
        parsed = urlparse(raw_url)
        host = parsed.hostname
        port = parsed.port
        if not host:
            candidate = parsed.path or parsed.netloc or raw_url
            candidate = candidate.split("/", 1)[0]
            if "@" in candidate:
                candidate = candidate.split("@")[-1]
            if ":" in candidate:
                host_part, port_part = candidate.split(":", 1)
                host = host_part
                try:
                    port = int(port_part)
                except ValueError:
                    port = None
            else:
                host = candidate
        if host:
            host = host.strip()
        return host or None, port


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
