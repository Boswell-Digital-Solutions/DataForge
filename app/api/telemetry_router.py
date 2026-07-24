"""Authenticated canonical ForgeEvent.v1 capability and ingest boundary."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.admin_keys_router import AuthContext, require_api_key
from app.logging_config import get_logger
from app.models.telemetry_models import ForgeEventV1Record
from app.models.telemetry_schemas import (
    ForgeEventCorrelationReadV1,
    ForgeEventCorrelationSummaryV1,
    ForgeEventV1IngestResponse,
    ForgeEventV1Submission,
    ForgeTelemetrySinkCapabilityV1,
    event_digest,
    forge_event_v1_write_enabled,
    forge_telemetry_sink_capability,
)
from app.telemetry_database import (
    get_telemetry_db,
    require_telemetry_rate_budget,
)


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])
MAX_CORRELATION_EVENTS = 200
MAX_CORRELATION_RESPONSE_BYTES = 256 * 1024


class EventIdentityConflict(ValueError):
    """The event ID is already bound to different canonical content."""


def forge_event_correlation_read_enabled() -> bool:
    """Require an explicit rollout switch for the CP3 read boundary."""

    return (
        os.getenv("DATAFORGE_TELEMETRY_CORRELATION_READ_ENABLED", "false")
        .strip()
        .lower()
        == "true"
    )


def _authorize_correlation_read(
    auth: AuthContext,
    *,
    environment: str,
    tenant_ref: str | None,
) -> set[str]:
    """Require Forge_Command's exact read identity and requested scope."""

    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if not isinstance(scopes, list) or "telemetry:read" not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_read_scope_required"},
        )
    expected_binding = {
        "service_name": "forge_command",
        "environment": environment,
        "tenant_ref": tenant_ref,
    }
    if any(metadata.get(field) != value for field, value in expected_binding.items()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_subject_binding_mismatch"},
        )
    return {scope for scope in scopes if isinstance(scope, str)}


def _admit_telemetry_rate_budget(
    _auth: AuthContext = Depends(require_api_key),
) -> None:
    """Charge only authenticated requests before database checkout."""

    require_telemetry_rate_budget()


def _authorize_event(auth: AuthContext, event: ForgeEventV1Submission) -> None:
    """Require an explicitly scoped and identity-bound canonical service key."""

    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "telemetry_service_key_required"},
        )

    # AuthorForge has a stricter content-free analytics contract. Even a
    # correctly bound telemetry key cannot use this attributes-bearing route.
    if event.service_name == "authorforge":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "authorforge_canonical_telemetry_forbidden"},
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


@router.get(
    "/correlations/{correlation_id}",
    response_model=ForgeEventCorrelationReadV1,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def read_forge_event_correlation(
    correlation_id: UUID,
    environment: str = Query(pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    tenant_ref: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9._:-]*$"),
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> ForgeEventCorrelationReadV1:
    """Return a payload-free correlation projection under exact scope binding."""

    if not forge_event_correlation_read_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_correlation_disabled"},
        )
    scopes = _authorize_correlation_read(
        auth,
        environment=environment,
        tenant_ref=tenant_ref,
    )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
        )
    try:
        observed_scopes = {
            (row.environment, row.tenant_ref)
            for row in db.execute(
                select(
                    ForgeEventV1Record.environment,
                    ForgeEventV1Record.tenant_ref,
                )
                .where(ForgeEventV1Record.correlation_id == correlation_id)
                .distinct()
                .limit(2)
            ).all()
        }
        records = list(
            db.execute(
                select(ForgeEventV1Record)
                .where(ForgeEventV1Record.correlation_id == correlation_id)
                .order_by(ForgeEventV1Record.occurred_at, ForgeEventV1Record.event_id)
                .limit(MAX_CORRELATION_EVENTS + 1)
            ).scalars()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_persistence_unavailable"},
        ) from exc

    requested_scope = (environment, tenant_ref)
    if any(scope != requested_scope for scope in observed_scopes):
        logger.warning(
            "Canonical Forge telemetry correlation scope conflict",
            extra={"correlation_id": str(correlation_id), "key_id": auth.key_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "correlation_scope_conflict"},
        )

    partial = len(records) > MAX_CORRELATION_EVENTS
    records = records[:MAX_CORRELATION_EVENTS]
    can_read_restricted = "telemetry:read:restricted" in scopes
    summaries: list[ForgeEventCorrelationSummaryV1] = []
    observed_at = datetime.now(UTC)
    for record in records:
        restricted = (
            record.privacy_class in {"restricted", "confidential"}
            and not can_read_restricted
        )
        if restricted:
            detail_state = "restricted"
        elif not record.sampled:
            detail_state = "sampled"
        elif record.trace_id is None:
            detail_state = "missing"
        else:
            detail_state = "available"
        summaries.append(
            ForgeEventCorrelationSummaryV1(
                event_id=record.event_id,
                occurred_at=record.occurred_at,
                received_at=record.received_at,
                service_name=record.service_name,
                event_type=None if restricted else record.event_type,
                severity=record.severity,
                outcome=record.outcome,
                trace_id=None if restricted else record.trace_id,
                span_id=None if restricted else record.span_id,
                parent_span_id=None if restricted else record.parent_span_id,
                privacy_class=record.privacy_class,
                retention_class=record.retention_class,
                detail_state=detail_state,
            )
        )
        size_probe = ForgeEventCorrelationReadV1(
            correlation_id=correlation_id,
            environment=environment,
            tenant_ref=tenant_ref,
            shared_state="partial",
            events=summaries,
            observed_at=observed_at,
        )
        if len(size_probe.model_dump_json().encode("utf-8")) > (
            MAX_CORRELATION_RESPONSE_BYTES
        ):
            summaries.pop()
            partial = True
            break

    return ForgeEventCorrelationReadV1(
        correlation_id=correlation_id,
        environment=environment,
        tenant_ref=tenant_ref,
        shared_state="partial" if partial else ("available" if summaries else "missing"),
        events=summaries,
        observed_at=observed_at,
    )


@router.post(
    "/events",
    response_model=ForgeEventV1IngestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_admit_telemetry_rate_budget)],
)
def ingest_forge_event_v1(
    event: ForgeEventV1Submission,
    response: Response,
    db: Session | None = Depends(get_telemetry_db),
    auth: AuthContext = Depends(require_api_key),
) -> ForgeEventV1IngestResponse:
    """Persist one canonical event without aliases, fallback, or dual-write."""

    if not forge_event_v1_write_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_disabled"},
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "telemetry_database_configuration_invalid"},
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
