"""Authenticated canonical ForgeEvent.v1 capability and ingest boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.admin_keys_router import AuthContext, require_api_key
from app.database import get_db
from app.logging_config import get_logger
from app.models.telemetry_models import ForgeEventV1Record
from app.models.telemetry_schemas import (
    ForgeEventV1IngestResponse,
    ForgeEventV1Submission,
    ForgeTelemetrySinkCapabilityV1,
    event_digest,
    forge_event_v1_write_enabled,
    forge_telemetry_sink_capability,
)


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


class EventIdentityConflict(ValueError):
    """The event ID is already bound to different canonical content."""


def _authorize_event(auth: AuthContext, event: ForgeEventV1Submission) -> None:
    """Require an explicitly scoped and identity-bound canonical service key."""

    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )

    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if not isinstance(scopes, list) or "telemetry:write" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_write_scope_required"},
        )

    expected_binding = {
        "service_name": event.service_name,
        "environment": event.environment,
        "tenant_ref": event.tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )


def _storage_values(
    event: ForgeEventV1Submission,
    digest: str,
    *,
    received_at: datetime | None = None,
) -> dict[str, Any]:
    values = event.model_dump(mode="python")
    values["event_digest"] = digest
    if received_at is not None:
        values["received_at"] = received_at
    return values


def _binding_matches(
    record: ForgeEventV1Record,
    event: ForgeEventV1Submission,
    digest: str,
) -> bool:
    return (
        record.event_digest == digest
        and record.schema_version == event.schema_version
        and record.service_name == event.service_name
        and record.service_instance_id == event.service_instance_id
        and record.environment == event.environment
        and record.tenant_ref == event.tenant_ref
    )


def _persist_sqlite(
    db: Session,
    event: ForgeEventV1Submission,
    digest: str,
) -> str:
    """Exercise equivalent identity behavior in the unit-test database."""

    values = _storage_values(event, digest, received_at=datetime.now(UTC))
    statement = (
        sqlite_insert(ForgeEventV1Record.__table__)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = db.execute(statement)
    if result.rowcount == 1:
        return "inserted"

    record = db.execute(
        select(ForgeEventV1Record).where(ForgeEventV1Record.event_id == event.event_id)
    ).scalar_one()
    if _binding_matches(record, event, digest):
        return "exact_replay"
    raise EventIdentityConflict("event_identity_conflict")


def _persist_postgresql(
    db: Session,
    event: ForgeEventV1Submission,
    digest: str,
) -> str:
    """Invoke the migration-owned atomic identity transaction."""

    candidate = json.dumps(
        event.model_dump(mode="json"),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    outcome = db.execute(
        text(
            """
            SELECT ingest_forge_event_v1(
                CAST(:candidate AS jsonb),
                CAST(:event_digest AS char(64))
            )
            """
        ),
        {"candidate": candidate, "event_digest": digest},
    ).scalar_one()
    if outcome == "event_identity_conflict":
        raise EventIdentityConflict(outcome)
    if outcome not in {"inserted", "exact_replay"}:
        raise RuntimeError("canonical telemetry ingest returned an unknown outcome")
    return outcome


def _persist_event(
    db: Session,
    event: ForgeEventV1Submission,
    digest: str,
) -> str:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return _persist_postgresql(db, event, digest)
    if dialect == "sqlite":
        return _persist_sqlite(db, event, digest)
    raise RuntimeError("canonical telemetry ingest requires PostgreSQL")


@router.get(
    "/capabilities/forge-event-v1",
    response_model=ForgeTelemetrySinkCapabilityV1,
)
def get_forge_event_v1_capability(
    _auth: AuthContext = Depends(require_api_key),
) -> ForgeTelemetrySinkCapabilityV1:
    """Return the exact active canonical sink capability."""

    return forge_telemetry_sink_capability()


@router.post(
    "/events",
    response_model=ForgeEventV1IngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_forge_event_v1(
    event: ForgeEventV1Submission,
    response: Response,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_api_key),
) -> ForgeEventV1IngestResponse:
    """Persist one canonical event without aliases, fallback, or dual-write."""

    if not forge_event_v1_write_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_disabled"},
        )
    _authorize_event(auth, event)
    digest = event_digest(event)

    try:
        identity_outcome = _persist_event(db, event, digest)
        record = db.execute(
            select(ForgeEventV1Record).where(
                ForgeEventV1Record.event_id == event.event_id
            )
        ).scalar_one()
        db.commit()
    except EventIdentityConflict as exc:
        db.rollback()
        logger.warning(
            "Canonical Forge telemetry event identity conflict",
            extra={"event_id": str(event.event_id), "key_id": auth.key_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "event_identity_conflict",
                "event_id": str(event.event_id),
            },
        ) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        db.rollback()
        logger.error(
            "Canonical Forge telemetry persistence failed",
            extra={"event_id": str(event.event_id), "key_id": auth.key_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    if identity_outcome == "exact_replay":
        response.status_code = status.HTTP_200_OK
    logger.info(
        "Canonical Forge telemetry event persisted",
        extra={
            "event_id": str(event.event_id),
            "identity_outcome": identity_outcome,
            "key_id": auth.key_id,
        },
    )
    return ForgeEventV1IngestResponse(
        event_id=event.event_id,
        event_digest=digest,
        received_at=record.received_at,
        identity_outcome=identity_outcome,
    )
