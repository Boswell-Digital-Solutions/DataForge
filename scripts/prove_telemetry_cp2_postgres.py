"""Disposable PostgreSQL proof for CP2 role, pool, timeout, and rate bounds."""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, TimeoutError


def _event():
    from app.models.telemetry_schemas import ForgeEventV1Submission

    return ForgeEventV1Submission.model_validate(
        {
            "schema_version": "ForgeEvent.v1",
            "event_id": str(uuid4()),
            "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "service_name": "dataforge",
            "service_instance_id": "cp2-proof",
            "environment": "test",
            "tenant_ref": None,
            "event_type": "cp2.database.proved",
            "severity": "info",
            "outcome": "ok",
            "evidence_class": "operational",
            "correlation_id": None,
            "trace_id": None,
            "span_id": None,
            "parent_span_id": None,
            "attributes": {"proof": "bounded_pool"},
            "metrics": {"events": 1},
            "privacy_class": "internal",
            "retention_class": "short",
            "sampled": True,
            "sample_rate": None,
            "sampling_reason": "always_on",
        }
    )


def prove() -> dict[str, object]:
    admin_url = os.environ["DATAFORGE_DATABASE_URL"]
    admin_engine = create_engine(admin_url)
    runtime_role = "dataforge_telemetry_runtime_proof"
    disposable_password = "cp2-disposable-proof-only"
    with admin_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE ROLE dataforge_telemetry_runtime_proof
                    LOGIN
                    NOSUPERUSER
                    NOCREATEDB
                    NOCREATEROLE
                    NOREPLICATION
                    NOBYPASSRLS
                    PASSWORD 'cp2-disposable-proof-only'
                    CONNECTION LIMIT 4
                """
            )
        )
        connection.execute(
            text(
                """
                GRANT dataforge_telemetry_ingest
                TO dataforge_telemetry_runtime_proof
                """
            )
        )

    runtime_url = make_url(admin_url).set(
        username=runtime_role,
        password=disposable_password,
    )
    os.environ["DATAFORGE_TELEMETRY_DATABASE_URL"] = runtime_url.render_as_string(
        hide_password=False
    )
    os.environ["DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED"] = "true"

    from app.api.telemetry_router import _persist_event
    from app.database import engine as business_engine
    import app.telemetry_database as telemetry_database
    from app.models.telemetry_schemas import event_digest

    telemetry_database.reset_telemetry_database_state_for_tests()

    admitted = 0
    rejected = 0
    for _ in range(41):
        try:
            telemetry_database.require_telemetry_rate_budget()
            admitted += 1
        except HTTPException as exc:
            if exc.status_code != 429:
                raise
            rejected += 1
    if (admitted, rejected) != (40, 1):
        raise AssertionError("telemetry rate budget did not enforce 40-event burst")

    dependency = telemetry_database.get_telemetry_db()
    session = next(dependency)
    assert session is not None
    event = _event()
    digest = event_digest(event)
    if _persist_event(session, event, digest) != "inserted":
        raise AssertionError("least-privilege insert did not persist")
    session.commit()
    if _persist_event(session, event, digest) != "exact_replay":
        raise AssertionError("least-privilege replay was not idempotent")
    session.commit()

    denied_business_read = False
    try:
        session.execute(text("SELECT count(*) FROM events")).scalar_one()
    except DBAPIError:
        session.rollback()
        denied_business_read = True
    if not denied_business_read:
        raise AssertionError("telemetry role could read a business table")

    denied_delete = False
    try:
        session.execute(
            text("DELETE FROM forge_events_v1 WHERE event_id = :event_id"),
            {"event_id": str(event.event_id)},
        )
    except DBAPIError:
        session.rollback()
        denied_delete = True
    if not denied_delete:
        raise AssertionError("telemetry role could delete canonical evidence")
    dependency.close()

    telemetry_engine = telemetry_database._engine
    assert telemetry_engine is not None
    business_checked_out_before = business_engine.pool.checkedout()
    first = telemetry_engine.connect()
    second = telemetry_engine.connect()
    timeout_started = time.monotonic()
    pool_timed_out = False
    try:
        telemetry_engine.connect()
    except TimeoutError:
        pool_timed_out = True
    pool_timeout_elapsed_s = time.monotonic() - timeout_started
    finally_connections = (first, second)
    for connection in finally_connections:
        connection.close()
    if not pool_timed_out or not 1.8 <= pool_timeout_elapsed_s <= 4.0:
        raise AssertionError("telemetry pool timeout/capacity was not bounded")
    if business_engine.pool.checkedout() != business_checked_out_before:
        raise AssertionError("telemetry used the business database pool")

    status = telemetry_database.telemetry_storage_status()
    if (
        status["pool"]["size"] != 2
        or status["pool"]["max_overflow"] != 0
        or not status["role_preflight_complete"]
    ):
        raise AssertionError("telemetry storage status did not prove isolation")

    telemetry_database.close_telemetry_database()
    with admin_engine.begin() as connection:
        connection.execute(
            text(
                """
                REVOKE dataforge_telemetry_ingest
                FROM dataforge_telemetry_runtime_proof
                """
            )
        )
        connection.execute(text("DROP ROLE dataforge_telemetry_runtime_proof"))
    admin_engine.dispose()

    return {
        "schema_version": "dataforge.telemetry.cp2_postgres_proof.v1",
        "result": "passed",
        "role": {
            "group": "dataforge_telemetry_ingest",
            "runtime_distinct": True,
            "preflight": True,
            "business_read_denied": denied_business_read,
            "canonical_delete_denied": denied_delete,
        },
        "pool": {
            "size": 2,
            "max_overflow": 0,
            "timeout_s": 2,
            "exhaustion_timed_out": pool_timed_out,
            "business_pool_unchanged": True,
        },
        "rate_budget": {
            "admitted": admitted,
            "rejected": rejected,
        },
        "identity": {
            "insert": "inserted",
            "replay": "exact_replay",
        },
    }


if __name__ == "__main__":
    print(json.dumps(prove(), sort_keys=True))
    print("CP2_TELEMETRY_POSTGRES_PROOF_OK")
