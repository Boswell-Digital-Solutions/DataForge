"""CP2 blast-radius tests for the isolated telemetry database boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

import app.telemetry_database as telemetry_database
from app.telemetry_database import (
    TelemetryDatabaseConfigurationError,
    TelemetryDatabaseLimits,
    get_telemetry_db,
    require_telemetry_rate_budget,
    reset_telemetry_database_state_for_tests,
    telemetry_database_limits,
    telemetry_storage_status,
)


def test_pool_timeout_and_rate_limits_are_explicit_and_bounded(monkeypatch) -> None:
    limits = telemetry_database_limits()

    assert limits == TelemetryDatabaseLimits(
        pool_size=2,
        max_overflow=0,
        pool_timeout_s=2,
        pool_recycle_s=300,
        connect_timeout_s=3,
        statement_timeout_ms=2000,
        lock_timeout_ms=500,
        idle_in_transaction_timeout_ms=5000,
        rate_per_second=20.0,
        rate_burst=40,
    )

    monkeypatch.setenv("DATAFORGE_TELEMETRY_DB_POOL_SIZE", "4")
    monkeypatch.setenv("DATAFORGE_TELEMETRY_DB_MAX_OVERFLOW", "1")
    with pytest.raises(TelemetryDatabaseConfigurationError) as error:
        telemetry_database_limits()
    assert error.value.code == "telemetry_database_pool_capacity_invalid"


def test_dedicated_role_rejects_business_user_and_non_postgres(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        telemetry_database,
        "DATABASE_URL",
        "postgresql://business:secret@db.example.test/dataforge",
    )

    with pytest.raises(TelemetryDatabaseConfigurationError) as same_role:
        telemetry_database._validate_dedicated_role_url(
            "postgresql://business:other@db.example.test/dataforge"
        )
    assert same_role.value.code == "telemetry_database_role_not_dedicated"

    with pytest.raises(TelemetryDatabaseConfigurationError) as sqlite:
        telemetry_database._validate_dedicated_role_url("sqlite:///telemetry.db")
    assert sqlite.value.code == "telemetry_database_postgresql_required"


def test_engine_budget_sets_database_side_timeouts_without_url_values() -> None:
    database_url = (
        "postgresql://telemetry_runtime:CANARY_SECRET@db.example.test/dataforge"
    )
    limits = telemetry_database_limits()

    kwargs = telemetry_database._engine_kwargs(database_url, limits)
    rendered = json.dumps(kwargs, default=str)

    assert kwargs["pool_size"] == 2
    assert kwargs["max_overflow"] == 0
    assert kwargs["pool_timeout"] == 2
    assert kwargs["connect_args"]["connect_timeout"] == 3
    assert "statement_timeout=2000" in kwargs["connect_args"]["options"]
    assert "lock_timeout=500" in kwargs["connect_args"]["options"]
    assert "application_name=dataforge-telemetry" in (kwargs["connect_args"]["options"])
    assert "CANARY_SECRET" not in rendered


def test_disabled_writer_never_requires_or_opens_telemetry_database(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED", "false")
    monkeypatch.delenv("DATAFORGE_TELEMETRY_DATABASE_URL", raising=False)
    dependency = get_telemetry_db()

    assert next(dependency) is None
    with pytest.raises(StopIteration):
        next(dependency)
    assert telemetry_database._engine is None


def test_enabled_writer_fails_closed_without_dedicated_url(monkeypatch) -> None:
    monkeypatch.setenv("DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED", "true")
    monkeypatch.delenv("DATAFORGE_TELEMETRY_DATABASE_URL", raising=False)

    with pytest.raises(HTTPException) as error:
        next(get_telemetry_db())

    assert error.value.status_code == 503
    assert error.value.detail == {"code": "telemetry_database_url_missing"}


def test_rate_budget_rejects_before_unbounded_admission(monkeypatch) -> None:
    monkeypatch.setenv("DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED", "true")
    monkeypatch.setenv("DATAFORGE_TELEMETRY_INGEST_RATE_PER_SECOND", "0.1")
    monkeypatch.setenv("DATAFORGE_TELEMETRY_INGEST_RATE_BURST", "1")
    reset_telemetry_database_state_for_tests()

    require_telemetry_rate_budget()
    with pytest.raises(HTTPException) as error:
        require_telemetry_rate_budget()

    assert error.value.status_code == 429
    assert error.value.detail == {"code": "telemetry_ingest_rate_budget_exceeded"}


def test_storage_health_never_exposes_database_url(monkeypatch) -> None:
    secret = "CANARY_DATABASE_PASSWORD"
    monkeypatch.setenv(
        "DATAFORGE_TELEMETRY_DATABASE_URL",
        f"postgresql://telemetry:{secret}@db.example.test/dataforge",
    )

    status = telemetry_storage_status()
    rendered = json.dumps(status)

    assert status["configured"] is True
    assert status["pool"]["size"] == 2
    assert status["pool"]["max_overflow"] == 0
    assert status["rate_budget"]["burst"] == 40
    assert secret not in rendered


def test_canonical_ingest_has_no_business_pool_fallback() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "telemetry_router.py"
    ).read_text(encoding="utf-8")

    assert "Depends(get_telemetry_db)" in source
    assert "Depends(get_db)" not in source
