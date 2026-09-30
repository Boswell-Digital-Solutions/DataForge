"""Narrow ForgeAgents service API for finalized BDS sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import validate_api_key
from app.database import get_db
from app.models.bds_session_models import BdsSession

router = APIRouter(prefix="/api/v1/bds/sessions", tags=["BDS sessions"])
bearer = HTTPBearer(auto_error=False)
SessionKind = Literal["planning", "execution", "evaluation", "workflow"]
FinalStatus = Literal["COMPLETED", "FAILED", "CANCELLED"]


class FinalizedSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_kind: SessionKind
    session_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    final_status: FinalStatus
    completed_at: datetime | None = None
    session_data: dict[str, Any]


class SessionRecord(BaseModel):
    session_kind: SessionKind
    session_id: str
    final_status: FinalStatus
    completed_at: datetime | None
    session_data: dict[str, Any]


def _require_scope(scope: str):
    def check(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> None:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Service key required")
        key = validate_api_key(credentials.credentials)
        if key is None:
            raise HTTPException(status_code=401, detail="Service key required")
        metadata = key.metadata or {}
        scopes = metadata.get("scopes")
        if (
            metadata.get("service_name") != "forge-agents"
            or not isinstance(scopes, list)
            or scope not in scopes
        ):
            raise HTTPException(status_code=403, detail="BDS session scope required")

    return check


write_scope = _require_scope("bds:sessions:write")
read_scope = _require_scope("bds:sessions:read")


def _record(row: BdsSession) -> SessionRecord:
    return SessionRecord(
        session_kind=row.session_kind,
        session_id=row.session_id,
        final_status=row.final_status,
        completed_at=row.completed_at,
        session_data=row.session_data,
    )


@router.post(
    "",
    response_model=SessionRecord,
    status_code=201,
    dependencies=[Depends(write_scope)],
)
def persist_session(
    body: FinalizedSessionIn, response: Response, db: Session = Depends(get_db)
) -> SessionRecord:
    if (
        body.session_data.get("id") != body.session_id
        or body.session_data.get("status") != body.final_status
    ):
        raise HTTPException(
            status_code=422, detail="Session identity or status mismatch"
        )
    existing = db.get(BdsSession, (body.session_kind, body.session_id))
    if existing is not None:
        if (
            existing.final_status != body.final_status
            or existing.session_data != body.session_data
        ):
            raise HTTPException(status_code=409, detail="Finalized session conflict")
        response.status_code = 200
        return _record(existing)
    row = BdsSession(
        session_kind=body.session_kind,
        session_id=body.session_id,
        final_status=body.final_status,
        completed_at=body.completed_at,
        session_data=body.session_data,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # A concurrent identical terminal write is idempotent; a different one conflicts.
        winner = db.get(BdsSession, (body.session_kind, body.session_id))
        if (
            winner is None
            or winner.final_status != body.final_status
            or winner.session_data != body.session_data
        ):
            raise HTTPException(
                status_code=409, detail="Finalized session conflict"
            ) from None
        response.status_code = 200
        return _record(winner)
    db.refresh(row)
    response.status_code = 201
    return _record(row)


@router.get(
    "/{session_kind}/{session_id}",
    response_model=SessionRecord,
    dependencies=[Depends(read_scope)],
)
def get_session(
    session_kind: SessionKind, session_id: str, db: Session = Depends(get_db)
) -> SessionRecord:
    row = db.get(BdsSession, (session_kind, session_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _record(row)


@router.get(
    "/{session_kind}",
    response_model=list[SessionRecord],
    dependencies=[Depends(read_scope)],
)
def list_sessions(
    session_kind: SessionKind,
    limit: int = Query(default=200, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[SessionRecord]:
    rows = (
        db.query(BdsSession)
        .filter(BdsSession.session_kind == session_kind)
        .order_by(
            BdsSession.completed_at.desc().nullslast(), BdsSession.session_id.desc()
        )
        .limit(limit)
        .all()
    )
    return [_record(row) for row in rows]
