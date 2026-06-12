"""CSSA security ledger — append-only API (authority plan §22, §30).

Written by the ForgeAgents CSSA recorder; read back for integrity
verification. Law enforced here:

- Records are immutable: there are no update or delete endpoints.
- The server RECOMPUTES each record's hash from the payload (RFC 8785
  canonical form minus the record's own hash field) and rejects mismatches —
  a tampered record cannot enter the ledger.
- Idempotent retry: a duplicate write with an identical hash returns 200
  with the stored record; a conflicting write (same key, different hash)
  returns 409 and is logged as an integrity event.
- Cardinality: one decision and one authorization per attempt; at most one
  terminal outcome per attempt (unique indexes back these responses).
- cssa_counters are monotonic: a regression attempt returns 409.

Prefix: /api/v1/cloud-security
"""

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cloud_security_models import (
    CssaAuthorization,
    CssaCounter,
    CssaDecision,
    CssaOutcome,
)
from app.utils.cssa_canonical_json import canonicalize_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cloud-security", tags=["cloud-security"])

TERMINAL_EXECUTION_STATES = {"completed", "failed", "cancelled", "partially_delivered"}

#: record family -> (model, id field, hash field, expected schema_version)
_FAMILIES = {
    "decisions": (CssaDecision, "decision_id", "decision_hash", "cloud_security.decision.v1"),
    "authorizations": (
        CssaAuthorization,
        "authorization_id",
        "authorization_hash",
        "cloud_security.authorization.v1",
    ),
    "outcomes": (CssaOutcome, "outcome_id", "outcome_hash", "cloud_security.outcome.v1"),
}


def require_bearer(authorization: str | None = Header(None)) -> str:
    """Service-token posture consistent with bugcheck_router: extract the
    bearer token now; verification against the ForgeCommand token authority
    arrives with that integration."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    return authorization[7:]


class RecordEnvelope(BaseModel):
    payload: dict[str, Any] = Field(min_length=1)


class CounterAdvance(BaseModel):
    high_water: int = Field(ge=0)


def _recompute_hash(payload: dict[str, Any], hash_field: str) -> str:
    body = {k: v for k, v in payload.items() if k != hash_field}
    return "sha256:" + hashlib.sha256(canonicalize_json(body)).hexdigest()


def _validate_record(
    family: str, payload: dict[str, Any]
) -> tuple[type, str, str]:
    model, id_field, hash_field, schema_version = _FAMILIES[family]
    if payload.get("schema_version") != schema_version:
        raise HTTPException(
            status_code=422,
            detail=f"schema_version must be {schema_version!r}",
        )
    for required in (id_field, "attempt_id", "correlation_id", hash_field):
        if not payload.get(required):
            raise HTTPException(status_code=422, detail=f"{required} is required")
    recomputed = _recompute_hash(payload, hash_field)
    if recomputed != payload[hash_field]:
        logger.warning(
            "cssa_ledger_hash_mismatch family=%s id=%s", family, payload.get(id_field)
        )
        raise HTTPException(
            status_code=422,
            detail=f"{hash_field} does not match the canonical payload "
            "(record rejected; hash-covered fields are immutable)",
        )
    return model, id_field, hash_field


def _append_record(
    db: Session, family: str, payload: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    model, id_field, hash_field = _validate_record(family, payload)
    record_id = payload[id_field]

    columns: dict[str, Any] = {
        id_field: record_id,
        "attempt_id": payload["attempt_id"],
        "correlation_id": payload["correlation_id"],
        "record_hash": payload[hash_field],
        "payload": payload,
    }
    if family == "outcomes":
        columns["terminal"] = payload.get("execution_state") in TERMINAL_EXECUTION_STATES

    db.add(model(**columns))
    try:
        db.commit()
        return payload, 201
    except IntegrityError:
        db.rollback()
        existing = db.get(model, record_id)
        if existing is None:
            # cardinality collision on attempt_id rather than the primary key
            attempt_existing = (
                db.query(model).filter(model.attempt_id == payload["attempt_id"]).first()
            )
            if attempt_existing is not None and attempt_existing.record_hash == payload[hash_field]:
                return dict(attempt_existing.payload), 200
            logger.warning(
                "cssa_ledger_cardinality_conflict family=%s attempt_id=%s",
                family,
                payload["attempt_id"],
            )
            raise HTTPException(
                status_code=409,
                detail=f"attempt {payload['attempt_id']} already has a "
                f"{family[:-1]} record (cardinality law, plan §22.2)",
            ) from None
        if existing.record_hash == payload[hash_field]:
            return dict(existing.payload), 200  # idempotent retry
        logger.warning(
            "cssa_ledger_integrity_conflict family=%s id=%s", family, record_id
        )
        raise HTTPException(
            status_code=409,
            detail=f"{id_field} {record_id} exists with a different hash "
            "(immutable record conflict; logged as integrity event)",
        ) from None


def _make_record_routes(family: str) -> None:
    model, id_field, _, _ = _FAMILIES[family]

    @router.post(f"/{family}", status_code=201)
    def append(  # type: ignore[no-untyped-def]
        body: RecordEnvelope,
        db: Session = Depends(get_db),
        _token: str = Depends(require_bearer),
    ):
        from fastapi.responses import JSONResponse

        payload, status_code = _append_record(db, family, body.payload)
        return JSONResponse(status_code=status_code, content={"payload": payload})

    @router.get(f"/{family}/{{record_id}}")
    def read_back(  # type: ignore[no-untyped-def]
        record_id: str,
        db: Session = Depends(get_db),
        _token: str = Depends(require_bearer),
    ):
        record = db.get(model, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"{id_field} {record_id} not found")
        return {"payload": record.payload, "record_hash": record.record_hash}


for _family in _FAMILIES:
    _make_record_routes(_family)


@router.get("/counters/{counter}")
def get_counter(
    counter: str,
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    row = db.get(CssaCounter, counter)
    if row is None:
        return {"counter": counter, "high_water": None}
    return {"counter": counter, "high_water": row.high_water}


@router.put("/counters/{counter}")
def advance_counter(
    counter: str,
    body: CounterAdvance,
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    row = db.get(CssaCounter, counter)
    if row is None:
        db.add(CssaCounter(counter=counter, high_water=body.high_water))
        db.commit()
        return {"counter": counter, "high_water": body.high_water}
    if body.high_water < row.high_water:
        raise HTTPException(
            status_code=409,
            detail=f"counter {counter!r} is monotonic: {body.high_water} < {row.high_water}",
        )
    row.high_water = body.high_water
    db.commit()
    return {"counter": counter, "high_water": row.high_water}
