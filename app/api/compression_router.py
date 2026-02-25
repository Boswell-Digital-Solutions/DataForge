"""Compression Dictionary API router for DataForge.

CRUD endpoints for Zstandard dictionary governance. Dictionaries are
registered by the training script, promoted through lifecycle states
(TRAINING -> CANDIDATE -> ACTIVE -> RETIRED), and fetched by services
via ForgeCommand's distribution layer.
"""

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.compression_models import CompressionDictionary
from app.models.compression_schemas import (
    ActiveDictionaryInfo,
    DictionaryCreate,
    DictionaryListResponse,
    DictionaryResponse,
    DictionaryStatusUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/compression/dictionaries",
    tags=["Compression Dictionaries"],
)

# Valid lifecycle transitions
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "TRAINING": {"CANDIDATE", "RETIRED"},
    "CANDIDATE": {"ACTIVE", "RETIRED"},
    "ACTIVE": {"RETIRED"},
    "RETIRED": set(),  # terminal
}


def _model_to_response(d: CompressionDictionary) -> DictionaryResponse:
    return DictionaryResponse.model_validate(d)


# --- POST: Register dictionary ---

@router.post(
    "",
    status_code=201,
    response_model=DictionaryResponse,
    summary="Register a new compression dictionary",
)
async def create_dictionary(
    body: DictionaryCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> DictionaryResponse:
    blob = base64.b64decode(body.dictionary_blob_b64)

    # Verify SHA-256
    computed = hashlib.sha256(blob).hexdigest()
    if computed != body.sha256_hash:
        raise HTTPException(
            status_code=400,
            detail=f"SHA-256 mismatch: computed {computed}, declared {body.sha256_hash}",
        )

    new_dict = CompressionDictionary(
        dictionary_id=uuid4(),
        name=body.name,
        version=1,
        service_pair=body.service_pair,
        payload_class=body.payload_class,
        schema_version_min=body.schema_version_min,
        schema_version_max=body.schema_version_max,
        algorithm=body.algorithm,
        dictionary_size_bytes=len(blob),
        dictionary_blob=blob,
        sha256_hash=body.sha256_hash,
        training_sample_n=body.training_sample_n,
        training_params=body.training_params,
        compression_ratio=body.compression_ratio,
        program=body.program,
        status=body.status,
    )

    db.add(new_dict)
    db.commit()
    db.refresh(new_dict)

    logger.info(
        "compression_dictionary_created",
        extra={
            "dictionary_id": str(new_dict.dictionary_id),
            "service_pair": new_dict.service_pair,
            "program": new_dict.program,
            "status": new_dict.status,
            "size_bytes": new_dict.dictionary_size_bytes,
        },
    )

    return _model_to_response(new_dict)


# --- GET: List dictionaries ---

@router.get(
    "",
    response_model=DictionaryListResponse,
    summary="List compression dictionaries",
)
async def list_dictionaries(
    service_pair: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    program: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DictionaryListResponse:
    query = db.query(CompressionDictionary)

    if service_pair:
        query = query.filter(CompressionDictionary.service_pair == service_pair)
    if status:
        query = query.filter(CompressionDictionary.status == status)
    if program:
        query = query.filter(CompressionDictionary.program == program)

    total = query.count()
    items = query.order_by(CompressionDictionary.created_at.desc()).offset(offset).limit(limit).all()

    return DictionaryListResponse(
        items=[_model_to_response(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# --- GET: Active dictionaries for a service pair ---

@router.get(
    "/active",
    response_model=list[ActiveDictionaryInfo],
    summary="Get active dictionaries for a service pair",
)
async def get_active_dictionaries(
    service_pair: str = Query(...),
    program: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[ActiveDictionaryInfo]:
    query = db.query(CompressionDictionary).filter(
        CompressionDictionary.service_pair == service_pair,
        CompressionDictionary.status == "ACTIVE",
    )
    if program:
        query = query.filter(CompressionDictionary.program == program)

    results = query.all()
    return [
        ActiveDictionaryInfo(
            dictionary_id=d.dictionary_id,
            service_pair=d.service_pair,
            payload_class=d.payload_class,
            sha256_hash=d.sha256_hash,
            dictionary_size_bytes=d.dictionary_size_bytes,
            version=d.version,
            program=d.program,
        )
        for d in results
    ]


# --- GET: Dictionary metadata ---

@router.get(
    "/{dictionary_id}",
    response_model=DictionaryResponse,
    summary="Get dictionary metadata",
)
async def get_dictionary(
    dictionary_id: UUID,
    db: Session = Depends(get_db),
) -> DictionaryResponse:
    d = db.query(CompressionDictionary).filter(
        CompressionDictionary.dictionary_id == dictionary_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    return _model_to_response(d)


# --- GET: Dictionary binary blob ---

@router.get(
    "/{dictionary_id}/blob",
    summary="Download dictionary binary",
    response_class=Response,
)
async def get_dictionary_blob(
    dictionary_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    d = db.query(CompressionDictionary).filter(
        CompressionDictionary.dictionary_id == dictionary_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dictionary not found")

    return Response(
        content=d.dictionary_blob,
        media_type="application/octet-stream",
        headers={
            "X-Dictionary-SHA256": d.sha256_hash,
            "X-Dictionary-ID": str(d.dictionary_id),
            "Content-Disposition": f'attachment; filename="{d.name}.zdict"',
        },
    )


# --- PUT: Lifecycle transition ---

@router.put(
    "/{dictionary_id}/status",
    response_model=DictionaryResponse,
    summary="Update dictionary lifecycle status",
)
async def update_dictionary_status(
    dictionary_id: UUID,
    body: DictionaryStatusUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> DictionaryResponse:
    d = db.query(CompressionDictionary).filter(
        CompressionDictionary.dictionary_id == dictionary_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dictionary not found")

    current = d.status
    target = body.status

    if target not in _VALID_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition: {current} -> {target}. "
                   f"Allowed: {_VALID_TRANSITIONS.get(current, set())}",
        )

    # When activating, retire any currently-active dictionary for the same slot
    if target == "ACTIVE":
        existing_active = db.query(CompressionDictionary).filter(
            CompressionDictionary.service_pair == d.service_pair,
            CompressionDictionary.payload_class == d.payload_class,
            CompressionDictionary.program == d.program,
            CompressionDictionary.status == "ACTIVE",
            CompressionDictionary.dictionary_id != dictionary_id,
        ).all()
        for old in existing_active:
            old.status = "RETIRED"
            old.retired_at = datetime.now(timezone.utc)
            logger.info(
                "compression_dictionary_auto_retired",
                extra={"dictionary_id": str(old.dictionary_id), "replaced_by": str(dictionary_id)},
            )

    d.status = target
    if target == "RETIRED":
        d.retired_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(d)

    logger.info(
        "compression_dictionary_status_updated",
        extra={
            "dictionary_id": str(d.dictionary_id),
            "from": current,
            "to": target,
        },
    )

    return _model_to_response(d)
