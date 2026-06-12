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


# ── Atomic quota (authority plan §13; OPEN-3) ───────────────────────

from datetime import UTC, datetime  # noqa: E402

from sqlalchemy import func, text as sa_text  # noqa: E402

from app.models.cloud_security_models import (  # noqa: E402
    CssaAuthorizationConsumption,
    CssaQuotaReservation,
)

ACTIVE_RESERVATION_STATUSES = ("reserved", "committed")


class QuotaReserveRequest(BaseModel):
    payload: dict[str, Any] = Field(min_length=1)
    bucket_limit: int = Field(ge=0)


class QuotaCommitRequest(BaseModel):
    actual_units: int = Field(ge=0)


def _bucket_lock(db: Session, bucket: str) -> None:
    """Serialize per-bucket reserves on PostgreSQL; SQLite serializes natively."""
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(sa_text("SELECT pg_advisory_xact_lock(hashtext(:bucket))"), {"bucket": bucket})


def _active_bucket_units(db: Session, bucket: str, now: datetime) -> int:
    used = (
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(
                        CssaQuotaReservation.committed_units,
                        CssaQuotaReservation.reserved_units,
                    )
                ),
                0,
            )
        )
        .filter(
            CssaQuotaReservation.quota_bucket == bucket,
            CssaQuotaReservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            (CssaQuotaReservation.status == "committed")
            | (CssaQuotaReservation.expires_at > now),
        )
        .scalar()
    )
    return int(used or 0)


@router.post("/quota/reserve", status_code=201)
def reserve_quota(
    body: QuotaReserveRequest,
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    """Atomic reserve: active bucket usage + request must fit bucket_limit.

    DataForge enforces the arithmetic; the LIMIT is policy and comes from the
    caller's entitlement/quota_class resolution (gate-side).
    """
    payload = body.payload
    if payload.get("schema_version") != "cloud_security.quota_reservation.v1":
        raise HTTPException(status_code=422, detail="schema_version must be cloud_security.quota_reservation.v1")
    for required in ("quota_reservation_id", "principal_id", "service", "quota_bucket", "unit_type", "expires_at"):
        if not payload.get(required):
            raise HTTPException(status_code=422, detail=f"{required} is required")
    units = payload.get("reserved_units")
    if not isinstance(units, int) or units < 0:
        raise HTTPException(status_code=422, detail="reserved_units must be a non-negative integer")
    if payload.get("status") not in (None, "reserved"):
        raise HTTPException(status_code=422, detail="a new reservation must have status 'reserved'")

    bucket = str(payload["quota_bucket"])
    now = datetime.now(UTC).replace(tzinfo=None)
    _bucket_lock(db, bucket)

    existing = db.get(CssaQuotaReservation, payload["quota_reservation_id"])
    if existing is not None:
        if existing.reserved_units == units and existing.quota_bucket == bucket:
            return {"reservation": _reservation_dict(existing), "idempotent_retry": True}
        raise HTTPException(status_code=409, detail="reservation id exists with different content")

    used = _active_bucket_units(db, bucket, now)
    if used + units > body.bucket_limit:
        db.rollback()
        logger.info(
            "cssa_quota_exceeded bucket=%s used=%s requested=%s limit=%s",
            bucket, used, units, body.bucket_limit,
        )
        raise HTTPException(
            status_code=409,
            detail=f"QUOTA_EXCEEDED: bucket {bucket} has {used}/{body.bucket_limit} used; "
            f"{units} more does not fit",
        )

    row = CssaQuotaReservation(
        quota_reservation_id=payload["quota_reservation_id"],
        tenant_id=payload.get("tenant_id"),
        principal_id=payload["principal_id"],
        service=payload["service"],
        quota_bucket=bucket,
        reserved_units=units,
        committed_units=None,
        unit_type=payload["unit_type"],
        status="reserved",
        expires_at=datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00")).replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    return {"reservation": _reservation_dict(row), "idempotent_retry": False}


def _reservation_dict(row: CssaQuotaReservation) -> dict[str, Any]:
    return {
        "quota_reservation_id": row.quota_reservation_id,
        "quota_bucket": row.quota_bucket,
        "reserved_units": row.reserved_units,
        "committed_units": row.committed_units,
        "unit_type": row.unit_type,
        "status": row.status,
    }


def _get_reservation(db: Session, reservation_id: str) -> CssaQuotaReservation:
    row = db.get(CssaQuotaReservation, reservation_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"reservation {reservation_id} not found")
    return row


@router.post("/quota/{reservation_id}/commit")
def commit_quota(
    reservation_id: str,
    body: QuotaCommitRequest,
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    """Commit actual usage; the unused remainder is implicitly released."""
    row = _get_reservation(db, reservation_id)
    if row.status == "committed" and row.committed_units == body.actual_units:
        return {"reservation": _reservation_dict(row), "idempotent_retry": True}
    if row.status != "reserved":
        raise HTTPException(status_code=409, detail=f"reservation is {row.status}, not reserved")
    if body.actual_units > row.reserved_units:
        raise HTTPException(
            status_code=409,
            detail=f"actual {body.actual_units} exceeds reserved {row.reserved_units}",
        )
    row.status = "committed"
    row.committed_units = body.actual_units
    db.commit()
    return {"reservation": _reservation_dict(row), "idempotent_retry": False}


@router.post("/quota/{reservation_id}/release")
def release_quota(
    reservation_id: str,
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    row = _get_reservation(db, reservation_id)
    if row.status == "released":
        return {"reservation": _reservation_dict(row), "idempotent_retry": True}
    if row.status != "reserved":
        raise HTTPException(status_code=409, detail=f"reservation is {row.status}, not reserved")
    row.status = "released"
    db.commit()
    return {"reservation": _reservation_dict(row), "idempotent_retry": False}


@router.post("/quota/reconcile")
def reconcile_quota(
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    """Expire abandoned reservations (§13.3 leaked-reservation reconciliation)."""
    now = datetime.now(UTC).replace(tzinfo=None)
    leaked = (
        db.query(CssaQuotaReservation)
        .filter(
            CssaQuotaReservation.status == "reserved",
            CssaQuotaReservation.expires_at <= now,
        )
        .all()
    )
    for row in leaked:
        row.status = "expired"
    db.commit()
    if leaked:
        logger.warning("cssa_quota_reconcile expired=%s", len(leaked))
    return {"expired": len(leaked)}


@router.get("/quota/buckets/{bucket}/usage")
def bucket_usage(
    bucket: str,
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    """Read-only usage view (SHADOW quota simulation, §10.3)."""
    now = datetime.now(UTC).replace(tzinfo=None)
    return {"quota_bucket": bucket, "active_units": _active_bucket_units(db, bucket, now)}


# ── Durable single-use consumption ledger (plan §15.4) ──────────────


@router.post("/authorizations/{authorization_id}/consume", status_code=201)
def consume_authorization(
    authorization_id: str,
    db: Session = Depends(get_db),
    _token: str = Depends(require_bearer),
) -> dict[str, Any]:
    """Consume a single-use authorization; a second consume is 409 forever."""
    db.add(CssaAuthorizationConsumption(authorization_id=authorization_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("cssa_authorization_replay authorization_id=%s", authorization_id)
        raise HTTPException(
            status_code=409,
            detail=f"authorization {authorization_id} already consumed (single-use law)",
        ) from None
    return {"authorization_id": authorization_id, "consumed": True}
