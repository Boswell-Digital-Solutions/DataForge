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


def describe_target(dsn: Optional[str]) -> Dict[str, Optional[str]]:
    """Non-secret identity of a Postgres DSN: host + port + db + Supabase project
    ref. NEVER returns the password. Lets /health/telemetry show *which* DB
    telemetry is bound to (compare project_ref against the DB the reader uses)
    without leaking credentials."""
    if not dsn:
        return {"host": None, "port": None, "database": None, "project_ref": None}
    try:
        parts = urlparse(dsn)
        user = parts.username or ""
        ref = user.split(".", 1)[1] if "." in user else None  # supabase: postgres.<ref>
        return {
            "host": parts.hostname,
            "port": str(parts.port) if parts.port else None,
            "database": (parts.path or "/").lstrip("/") or None,
            "project_ref": ref,
        }
    except Exception:
        return {"host": None, "port": None, "database": None, "project_ref": None}


def _normalize_pg_dsn(url: Optional[str]) -> Optional[str]:
    """Make a Postgres DSN safe to parse even if the password contains an
    unescaped special char (most often '@').

    urlsplit rpartitions the netloc, so it extracts host/user/password correctly;
    SQLAlchemy's string parser (and libpq) split on the FIRST '@' and fold the
    password tail into the host -> a misleading "Name or service not known" DNS
    error. If the two disagree, rebuild from the parsed components (URL.create
    re-encodes the raw password ONCE). A correctly percent-encoded password parses
    identically and is left untouched (no double-encoding).
    """
    if not url:
        return url
    from sqlalchemy.engine.url import URL, make_url

    url = url.strip()
    parts = urlparse(url)
    if not parts.hostname:
        return url
    try:
        if make_url(url).host == parts.hostname:
            return url
    except Exception:
        pass
    try:
        return URL.create(
            drivername=parts.scheme or "postgresql",
            username=parts.username,
            password=parts.password,
            host=parts.hostname,
            port=parts.port,
            database=(parts.path or "/").lstrip("/") or None,
            query=dict(parse_qsl(parts.query)),
        ).render_as_string(hide_password=False)
    except Exception:
        return url


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
        # Observability fields, surfaced via status() / a service's /health/telemetry.
        self.source_var: Optional[str] = None
        self.emit_attempts = 0
        self.emit_succeeded = 0
        self.emit_failed = 0
        self.last_error: Optional[str] = None
        self.disabled_reason: Optional[str] = None
        self.init_error: Optional[str] = None
        self.target: Dict[str, Optional[str]] = describe_target(None)

        self.db_url, host, port = self._resolve_database_url(database_url)
        # Auto-encode an unescaped special char (e.g. '@') in the password.
        self.db_url = _normalize_pg_dsn(self.db_url)
        self.database_url = self.db_url
        self.enabled = bool(self.db_url)
        self.engine: Optional[Any] = None
        self.SessionLocal: Optional[sessionmaker] = None

        if host:
            logger.info("Telemetry DB target host=%s port=%s", host, port or 5432)

        if self.enabled:
            self.target = describe_target(self.db_url)
            try:
                self.engine = create_engine(self.db_url)
                with self.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
            except (socket.gaierror, OperationalError, TimeoutError, OSError) as exc:
                self._handle_connection_error(exc)
                return
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        elif self.telemetry_required:
            self.disabled_reason = "no DSN — DATAFORGE_DATABASE_URL / DATABASE_BASE_URL+components unset"
            raise ValueError(
                "Telemetry is required but no database configuration was found. "
                "Set DATAFORGE_DATABASE_URL or DATABASE_BASE_URL + DATABASE_USER/DATABASE_PASSWORD/DATABASE_NAME."
            )
        else:
            self.disabled_reason = "no DSN — DATAFORGE_DATABASE_URL / DATABASE_BASE_URL+components unset"

    def status(self) -> Dict[str, Any]:
        """Non-secret runtime snapshot for a service's /health/telemetry endpoint —
        never the password. Confirms telemetry is armed AND bound to the expected
        DB (compare target.project_ref), and whether emits land or silently fail."""
        return {
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
            "init_error": self.init_error,
            "source_var": self.source_var,
            "target": self.target,
            "emit_attempts": self.emit_attempts,
            "emit_succeeded": self.emit_succeeded,
            "emit_failed": self.emit_failed,
            "last_error": self.last_error,
            "telemetry_required": self.telemetry_required,
        }

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
        self.emit_attempts += 1
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
                        :correlation_id, CAST(:metadata AS jsonb), CAST(:metrics AS jsonb), NOW()
                    )
                """)

                db.execute(query, {
                    "event_id": str(event.event_id),
                    "timestamp": event.timestamp,
                    "service": event.service,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                    # psycopg2 cannot adapt a raw dict to JSONB; serialize to a JSON
                    # string and cast (::jsonb) in the query, mirroring the SQLite path.
                    "metadata": json.dumps(event.metadata) if event.metadata is not None else None,
                    "metrics": json.dumps(event.metrics) if event.metrics is not None else None,
                })

            db.commit()
            self.emit_succeeded += 1
            return event.event_id
        except Exception as e:
            db.rollback()
            # Don't fail the application if telemetry fails
            self.emit_failed += 1
            self.last_error = f"{type(e).__name__}: {e}"
            print(f"Telemetry emission failed: {e}")
            return event.event_id
        finally:
            db.close()

    def _resolve_database_url(
        self, provided_url: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        if provided_url:
            self.source_var = "explicit"
            return provided_url, *self._extract_host_port(provided_url)
        env_url = os.getenv("DATAFORGE_DATABASE_URL")
        if env_url:
            self.source_var = "DATAFORGE_DATABASE_URL"
            return env_url, *self._extract_host_port(env_url)
        built = self._build_url_from_components()
        if built[0]:
            self.source_var = "DATABASE_BASE_URL+components"
        return built

    def _handle_connection_error(self, exc: Exception) -> None:
        self.init_error = f"{type(exc).__name__}: {exc}"
        self.disabled_reason = f"connect failed: {self.init_error}"
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
