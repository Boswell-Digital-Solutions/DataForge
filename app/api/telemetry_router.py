"""Authenticated generic Forge Telemetry ingest boundary."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.admin_keys_router import AuthContext, require_api_key
from app.database import get_db
from app.logging_config import get_logger
from app.models.telemetry_models import TelemetryEventRecord
from app.models.telemetry_schemas import (
    TelemetryIngestBatch,
    TelemetryIngestResponse,
)


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


def _authorize_event_services(auth: AuthContext, batch: TelemetryIngestBatch) -> None:
    """Honor optional service/scope restrictions on issued service keys.

    Existing unscoped service keys remain valid.  Newly issued keys can bind
    callers to one service and the ``telemetry:write`` scope through metadata.
    """

    # AuthorForge has a stricter, content-free contract and must never enter
    # through this generic metadata-bearing surface, regardless of key type.
    if any(event.service == "authorforge" for event in batch.events):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AuthorForge must use the dedicated analytics endpoint",
        )

    if auth.key_info is None:
        return

    metadata = auth.key_info.metadata or {}
    bound_service = metadata.get("service")
    if isinstance(bound_service, str):
        normalized = bound_service.strip().lower()[:50]
        if any(event.service != normalized for event in batch.events):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key is not authorized for the submitted telemetry service",
            )

    scopes = metadata.get("scopes")
    if scopes is not None:
        if not isinstance(scopes, list) or "telemetry:write" not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key lacks telemetry:write scope",
            )


def _insert_idempotently(db: Session, values: list[dict]) -> int:
    table = TelemetryEventRecord.__table__
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = postgresql_insert(table).values(values).on_conflict_do_nothing(
            index_elements=[table.c.event_id]
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(table).values(values).on_conflict_do_nothing(
            index_elements=[table.c.event_id]
        )
    else:
        statement = insert(table).values(values)

    result = db.execute(statement)
    rowcount = result.rowcount
    return len(values) if rowcount is None or rowcount < 0 else rowcount


@router.post(
    "/events:batch",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_telemetry_events(
    batch: TelemetryIngestBatch,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_api_key),
) -> TelemetryIngestResponse:
    """Persist a bounded generic telemetry batch in the shared events table."""

    _authorize_event_services(auth, batch)
    values = [
        {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "service": event.service,
            "event_type": event.event_type,
            "severity": event.severity,
            "correlation_id": event.correlation_id,
            "metadata": event.metadata,
            "metrics": event.metrics,
        }
        for event in batch.events
    ]

    try:
        accepted = _insert_idempotently(db, values)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Telemetry batch conflicted during persistence")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="telemetry batch conflicted during persistence",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Telemetry batch persistence failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="telemetry persistence unavailable",
        ) from exc

    duplicates = len(values) - accepted
    logger.info(
        "Forge telemetry batch persisted",
        extra={
            "accepted": accepted,
            "duplicates": duplicates,
            "key_id": auth.key_id,
        },
    )
    return TelemetryIngestResponse(
        accepted=accepted,
        duplicates=duplicates,
        event_ids=[event.event_id for event in batch.events],
    )
