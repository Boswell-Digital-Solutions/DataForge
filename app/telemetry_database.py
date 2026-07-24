"""Least-privilege, bounded database boundary for canonical telemetry ingest."""

from __future__ import annotations

import math
import os
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_URL
from app.database import _normalize_pg_dsn


TELEMETRY_INGEST_ROLE = "dataforge_telemetry_ingest"


class TelemetryDatabaseConfigurationError(RuntimeError):
    """Value-free configuration failure for the isolated telemetry pool."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class TelemetryDatabaseLimits:
    """Explicit CP2 pool, timeout, and rate-budget bounds."""

    pool_size: int
    max_overflow: int
    pool_timeout_s: int
    pool_recycle_s: int
    connect_timeout_s: int
    statement_timeout_ms: int
    lock_timeout_ms: int
    idle_in_transaction_timeout_ms: int
    rate_per_second: float
    rate_burst: int

    def __post_init__(self) -> None:
        _bounded_int("pool_size", self.pool_size, 1, 4)
        _bounded_int("max_overflow", self.max_overflow, 0, 2)
        if self.pool_size + self.max_overflow > 4:
            raise TelemetryDatabaseConfigurationError(
                "telemetry_database_pool_capacity_invalid"
            )
        _bounded_int("pool_timeout_s", self.pool_timeout_s, 1, 10)
        _bounded_int("pool_recycle_s", self.pool_recycle_s, 30, 1800)
        _bounded_int("connect_timeout_s", self.connect_timeout_s, 1, 10)
        _bounded_int(
            "statement_timeout_ms",
            self.statement_timeout_ms,
            100,
            10000,
        )
        _bounded_int("lock_timeout_ms", self.lock_timeout_ms, 50, 5000)
        _bounded_int(
            "idle_in_transaction_timeout_ms",
            self.idle_in_transaction_timeout_ms,
            1000,
            30000,
        )
        _bounded_float(
            "rate_per_second",
            self.rate_per_second,
            0.1,
            100.0,
        )
        _bounded_int("rate_burst", self.rate_burst, 1, 200)


def _bounded_int(name: str, value: int, lower: int, upper: int) -> None:
    if type(value) is not int or not lower <= value <= upper:
        raise TelemetryDatabaseConfigurationError(f"telemetry_database_{name}_invalid")


def _bounded_float(
    name: str,
    value: float,
    lower: float,
    upper: float,
) -> None:
    if (
        type(value) not in {int, float}
        or not math.isfinite(value)
        or not lower <= float(value) <= upper
    ):
        raise TelemetryDatabaseConfigurationError(f"telemetry_database_{name}_invalid")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        raise TelemetryDatabaseConfigurationError(
            f"telemetry_database_{name.lower()}_invalid"
        ) from None


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        raise TelemetryDatabaseConfigurationError(
            f"telemetry_database_{name.lower()}_invalid"
        ) from None


def telemetry_database_limits() -> TelemetryDatabaseLimits:
    """Read and validate the finite per-process telemetry resource budget."""

    return TelemetryDatabaseLimits(
        pool_size=_env_int("DATAFORGE_TELEMETRY_DB_POOL_SIZE", 2),
        max_overflow=_env_int("DATAFORGE_TELEMETRY_DB_MAX_OVERFLOW", 0),
        pool_timeout_s=_env_int(
            "DATAFORGE_TELEMETRY_DB_POOL_TIMEOUT_SECONDS",
            2,
        ),
        pool_recycle_s=_env_int(
            "DATAFORGE_TELEMETRY_DB_POOL_RECYCLE_SECONDS",
            300,
        ),
        connect_timeout_s=_env_int(
            "DATAFORGE_TELEMETRY_DB_CONNECT_TIMEOUT_SECONDS",
            3,
        ),
        statement_timeout_ms=_env_int(
            "DATAFORGE_TELEMETRY_DB_STATEMENT_TIMEOUT_MS",
            2000,
        ),
        lock_timeout_ms=_env_int(
            "DATAFORGE_TELEMETRY_DB_LOCK_TIMEOUT_MS",
            500,
        ),
        idle_in_transaction_timeout_ms=_env_int(
            "DATAFORGE_TELEMETRY_DB_IDLE_IN_TX_TIMEOUT_MS",
            5000,
        ),
        rate_per_second=_env_float(
            "DATAFORGE_TELEMETRY_INGEST_RATE_PER_SECOND",
            20.0,
        ),
        rate_burst=_env_int("DATAFORGE_TELEMETRY_INGEST_RATE_BURST", 40),
    )


def _writer_enabled() -> bool:
    return os.getenv(
        "DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED",
        "false",
    ).strip().lower() in {"1", "true", "yes", "on"}


def _configured_database_url() -> str:
    database_url = os.getenv("DATAFORGE_TELEMETRY_DATABASE_URL", "").strip()
    if not database_url:
        raise TelemetryDatabaseConfigurationError("telemetry_database_url_missing")
    return _normalize_pg_dsn(database_url)


def _validate_dedicated_role_url(database_url: str) -> None:
    try:
        telemetry_url = make_url(database_url)
        business_url = make_url(_normalize_pg_dsn(DATABASE_URL))
    except Exception:
        raise TelemetryDatabaseConfigurationError(
            "telemetry_database_url_invalid"
        ) from None
    if telemetry_url.get_backend_name() not in {"postgresql", "postgres"}:
        raise TelemetryDatabaseConfigurationError(
            "telemetry_database_postgresql_required"
        )
    if not telemetry_url.username:
        raise TelemetryDatabaseConfigurationError("telemetry_database_role_missing")
    if (
        business_url.get_backend_name() in {"postgresql", "postgres"}
        and telemetry_url.username == business_url.username
    ):
        raise TelemetryDatabaseConfigurationError(
            "telemetry_database_role_not_dedicated"
        )


def _engine_kwargs(
    database_url: str,
    limits: TelemetryDatabaseLimits,
) -> dict[str, Any]:
    url = make_url(database_url)
    options = " ".join(
        (
            f"-c statement_timeout={limits.statement_timeout_ms}",
            f"-c lock_timeout={limits.lock_timeout_ms}",
            (
                "-c idle_in_transaction_session_timeout="
                f"{limits.idle_in_transaction_timeout_ms}"
            ),
            "-c application_name=dataforge-telemetry",
        )
    )
    connect_args: dict[str, Any] = {
        "connect_timeout": limits.connect_timeout_s,
        "options": options,
    }
    if "sslmode" not in url.query:
        host = (url.host or "").lower()
        connect_args["sslmode"] = (
            "prefer" if host in {"localhost", "127.0.0.1", "::1", ""} else "require"
        )
    return {
        "pool_pre_ping": True,
        "pool_size": limits.pool_size,
        "max_overflow": limits.max_overflow,
        "pool_timeout": limits.pool_timeout_s,
        "pool_recycle": limits.pool_recycle_s,
        "connect_args": connect_args,
    }


_engine_lock = threading.Lock()
_preflight_lock = threading.Lock()
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_engine_identity: tuple[str, TelemetryDatabaseLimits] | None = None
_role_preflight_complete = False


def _get_session_factory() -> sessionmaker[Session]:
    global _engine
    global _engine_identity
    global _session_factory

    database_url = _configured_database_url()
    _validate_dedicated_role_url(database_url)
    limits = telemetry_database_limits()
    identity = (database_url, limits)
    with _engine_lock:
        if _session_factory is not None:
            if _engine_identity != identity:
                raise TelemetryDatabaseConfigurationError(
                    "telemetry_database_reconfiguration_requires_restart"
                )
            return _session_factory
        _engine = create_engine(
            database_url,
            **_engine_kwargs(database_url, limits),
        )
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
        )
        _engine_identity = identity
        return _session_factory


def _verify_runtime_role(session: Session) -> None:
    global _role_preflight_complete

    if _role_preflight_complete:
        return
    with _preflight_lock:
        if _role_preflight_complete:
            return
        row = (
            session.execute(
                text(
                    """
                SELECT
                    pg_has_role(
                        current_user,
                        'dataforge_telemetry_ingest',
                        'member'
                    ) AS has_ingest_role,
                    current_setting('application_name')
                        = 'dataforge-telemetry' AS application_name_ok,
                    role_state.rolsuper AS is_superuser,
                    role_state.rolbypassrls AS bypasses_rls
                FROM pg_roles AS role_state
                WHERE role_state.rolname = current_user
                """
                )
            )
            .mappings()
            .one()
        )
        if (
            row["has_ingest_role"] is not True
            or row["application_name_ok"] is not True
            or row["is_superuser"] is True
            or row["bypasses_rls"] is True
        ):
            raise TelemetryDatabaseConfigurationError(
                "telemetry_database_role_preflight_failed"
            )
        _role_preflight_complete = True


def get_telemetry_db() -> Generator[Session | None, None, None]:
    """Yield from only the bounded telemetry pool when the writer is enabled."""

    if not _writer_enabled():
        yield None
        return
    session: Session | None = None
    try:
        session = _get_session_factory()()
        _verify_runtime_role(session)
    except TelemetryDatabaseConfigurationError as exc:
        if session is not None:
            session.close()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code},
        ) from exc
    except (SQLAlchemyError, OSError) as exc:
        if session is not None:
            session.close()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_unavailable"},
        ) from exc
    assert session is not None
    try:
        yield session
    finally:
        session.close()


class _TelemetryRateBudget:
    def __init__(self, rate_per_second: float, burst: int) -> None:
        self.rate_per_second = rate_per_second
        self.burst = burst
        self._tokens = float(burst)
        self._updated_at = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = max(0.0, now - self._updated_at)
            self._tokens = min(
                float(self.burst),
                self._tokens + elapsed * self.rate_per_second,
            )
            self._updated_at = now
            if self._tokens < 1.0:
                return False
            self._tokens -= 1.0
            return True

    def status(self) -> dict[str, float | int]:
        with self._lock:
            return {
                "rate_per_second": self.rate_per_second,
                "burst": self.burst,
                "available_tokens": max(0.0, self._tokens),
            }


_rate_budget_lock = threading.Lock()
_rate_budget: _TelemetryRateBudget | None = None
_rate_budget_identity: tuple[float, int] | None = None


def _get_rate_budget() -> _TelemetryRateBudget:
    global _rate_budget
    global _rate_budget_identity

    limits = telemetry_database_limits()
    identity = (limits.rate_per_second, limits.rate_burst)
    with _rate_budget_lock:
        if _rate_budget is None or _rate_budget_identity != identity:
            _rate_budget = _TelemetryRateBudget(*identity)
            _rate_budget_identity = identity
        return _rate_budget


def require_telemetry_rate_budget() -> None:
    """Reject excess telemetry before it checks out a telemetry connection."""

    if not _writer_enabled():
        return
    try:
        admitted = _get_rate_budget().acquire()
    except TelemetryDatabaseConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code},
        ) from exc
    if not admitted:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "telemetry_ingest_rate_budget_exceeded"},
        )


def telemetry_storage_status() -> dict[str, Any]:
    """Return only non-secret pool, timeout, role, and rate-budget state."""

    try:
        limits = telemetry_database_limits()
        configured = bool(os.getenv("DATAFORGE_TELEMETRY_DATABASE_URL", "").strip())
        if configured:
            _validate_dedicated_role_url(_configured_database_url())
        with _engine_lock:
            engine = _engine
        pool_state: dict[str, Any] = {
            "initialized": engine is not None,
            "checked_out": 0,
            "overflow": 0,
        }
        if engine is not None:
            checked_out = getattr(engine.pool, "checkedout", None)
            overflow = getattr(engine.pool, "overflow", None)
            pool_state["checked_out"] = checked_out() if callable(checked_out) else None
            pool_state["overflow"] = max(0, overflow()) if callable(overflow) else None
        budget = _get_rate_budget().status()
        return {
            "configured": configured,
            "role_preflight_complete": _role_preflight_complete,
            "pool": {
                **pool_state,
                "size": limits.pool_size,
                "max_overflow": limits.max_overflow,
                "timeout_s": limits.pool_timeout_s,
                "recycle_s": limits.pool_recycle_s,
            },
            "timeouts": {
                "connect_s": limits.connect_timeout_s,
                "statement_ms": limits.statement_timeout_ms,
                "lock_ms": limits.lock_timeout_ms,
                "idle_in_transaction_ms": (limits.idle_in_transaction_timeout_ms),
            },
            "rate_budget": budget,
        }
    except TelemetryDatabaseConfigurationError as exc:
        return {
            "configured": False,
            "error_code": exc.code,
        }


def close_telemetry_database() -> None:
    """Dispose idle isolated-pool connections without touching business state."""

    global _engine
    global _engine_identity
    global _role_preflight_complete
    global _session_factory

    with _engine_lock:
        engine = _engine
        _engine = None
        _session_factory = None
        _engine_identity = None
        _role_preflight_complete = False
    if engine is not None:
        engine.dispose(close=True)


def reset_telemetry_database_state_for_tests() -> None:
    """Reset process-local pool and rate state for isolated tests."""

    global _rate_budget
    global _rate_budget_identity

    close_telemetry_database()
    with _rate_budget_lock:
        _rate_budget = None
        _rate_budget_identity = None
