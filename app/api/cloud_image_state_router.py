"""Authenticated internal persistence API for NeuroForge cloud-image jobs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.admin_keys_router import AuthContext, require_api_key
from app.database import get_db
from app.models.cloud_image_state_schemas import (
    CloudImageAppendEventRequestV1,
    CloudImageCreateRequestV1,
    CloudImageEventListResponseV1,
    CloudImageJobStateResponseV1,
    CloudImageLeaseClaimRequestV1,
    CloudImageLeaseExpireRequestV1,
    CloudImageLeaseReleaseRequestV1,
    CloudImageLeaseRenewRequestV1,
    CloudImageLeaseResponseV1,
    CloudImageOutboxClaimRequestV1,
    CloudImageOutboxClaimResponseV1,
    CloudImageOutboxItemV1,
    CloudImageOutboxSettleRequestV1,
    CloudImageRetrySourceResponseV1,
    CloudImageStageAttemptCompleteRequestV1,
    CloudImageStageAttemptListV1,
    CloudImageStageAttemptStartRequestV1,
    CloudImageStageAttemptV1,
    CloudImageTransitionRequestV1,
    CloudImageWorkerTransitionRequestV1,
)
from app.services.cloud_image_state import (
    CloudImageStateConflict,
    CloudImageStateNotFound,
    append_event,
    claim_lease,
    claim_outbox,
    complete_stage_attempt,
    create_or_replay_job,
    expire_lease,
    get_job,
    get_retry_source,
    list_events,
    list_stage_attempts,
    release_lease,
    renew_lease,
    settle_outbox,
    start_stage_attempt,
    transition_job,
    transition_job_with_lease,
)


router = APIRouter(
    prefix="/api/v1/internal/cloud-image-state",
    tags=["internal-cloud-image-state"],
)


def _require_neuroforge_scope(auth: AuthContext, scope: str) -> AuthContext:
    if auth.auth_mode != "api_key" or auth.key_info is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "neuroforge_service_key_required"},
        )
    metadata = auth.key_info.metadata or {}
    scopes = metadata.get("scopes")
    if metadata.get("service_name") != "neuroforge":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "neuroforge_subject_binding_mismatch"},
        )
    if not isinstance(scopes, list) or scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "cloud_image_state_scope_required", "scope": scope},
        )
    return auth


async def require_cloud_image_read(
    auth: Annotated[AuthContext, Depends(require_api_key)],
) -> AuthContext:
    return _require_neuroforge_scope(auth, "cloud-image:state:read")


async def require_cloud_image_write(
    auth: Annotated[AuthContext, Depends(require_api_key)],
) -> AuthContext:
    return _require_neuroforge_scope(auth, "cloud-image:state:write")


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CloudImageStateNotFound):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "cloud_image_job_not_found"},
        )
    if isinstance(exc, CloudImageStateConflict):
        detail: dict[str, str] = {"code": exc.code, "message": str(exc)}
        if exc.existing_job_id is not None:
            detail["existing_job_id"] = exc.existing_job_id
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise exc


@router.post(
    "/jobs",
    response_model=CloudImageJobStateResponseV1,
    status_code=status.HTTP_201_CREATED,
)
def create_cloud_image_job_state(
    request: CloudImageCreateRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageJobStateResponseV1:
    try:
        return create_or_replay_job(db, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.get("/jobs/{job_id}", response_model=CloudImageJobStateResponseV1)
def read_cloud_image_job_state(
    job_id: str,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_read)],
    db: Annotated[Session, Depends(get_db)],
    caller_identity: Annotated[str | None, Query(min_length=1, max_length=256)] = None,
) -> CloudImageJobStateResponseV1:
    try:
        return get_job(db, job_id, caller_identity=caller_identity)
    except CloudImageStateNotFound as exc:
        raise _translate_error(exc) from exc


@router.get(
    "/jobs/{job_id}/retry-source",
    response_model=CloudImageRetrySourceResponseV1,
)
def read_cloud_image_retry_source(
    job_id: str,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_read)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageRetrySourceResponseV1:
    try:
        return get_retry_source(db, job_id)
    except CloudImageStateNotFound as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/leases/claim",
    response_model=CloudImageLeaseResponseV1,
)
def claim_cloud_image_job_lease(
    job_id: str,
    request: CloudImageLeaseClaimRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageLeaseResponseV1:
    try:
        return claim_lease(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/leases/renew",
    response_model=CloudImageLeaseResponseV1,
)
def renew_cloud_image_job_lease(
    job_id: str,
    request: CloudImageLeaseRenewRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageLeaseResponseV1:
    try:
        return renew_lease(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/leases/release",
    response_model=CloudImageLeaseResponseV1,
)
def release_cloud_image_job_lease(
    job_id: str,
    request: CloudImageLeaseReleaseRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageLeaseResponseV1:
    try:
        return release_lease(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/leases/expire",
    response_model=CloudImageLeaseResponseV1,
)
def expire_cloud_image_job_lease(
    job_id: str,
    request: CloudImageLeaseExpireRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageLeaseResponseV1:
    try:
        return expire_lease(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/transitions",
    response_model=CloudImageJobStateResponseV1,
)
def transition_cloud_image_job_state(
    job_id: str,
    request: CloudImageTransitionRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageJobStateResponseV1:
    try:
        return transition_job(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/worker-transitions",
    response_model=CloudImageJobStateResponseV1,
)
def transition_cloud_image_job_state_with_lease(
    job_id: str,
    request: CloudImageWorkerTransitionRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageJobStateResponseV1:
    try:
        return transition_job_with_lease(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/attempts",
    response_model=CloudImageStageAttemptV1,
    status_code=status.HTTP_201_CREATED,
)
def start_cloud_image_stage_attempt(
    job_id: str,
    request: CloudImageStageAttemptStartRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageStageAttemptV1:
    try:
        return start_stage_attempt(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/attempts/{attempt_id}/complete",
    response_model=CloudImageStageAttemptV1,
)
def complete_cloud_image_stage_attempt(
    job_id: str,
    attempt_id: str,
    request: CloudImageStageAttemptCompleteRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageStageAttemptV1:
    try:
        return complete_stage_attempt(db, job_id, attempt_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.get(
    "/jobs/{job_id}/attempts",
    response_model=CloudImageStageAttemptListV1,
)
def read_cloud_image_stage_attempts(
    job_id: str,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_read)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageStageAttemptListV1:
    try:
        return list_stage_attempts(db, job_id)
    except CloudImageStateNotFound as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/jobs/{job_id}/events",
    response_model=CloudImageJobStateResponseV1,
)
def append_cloud_image_job_event(
    job_id: str,
    request: CloudImageAppendEventRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageJobStateResponseV1:
    try:
        return append_event(db, job_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.get(
    "/jobs/{job_id}/events",
    response_model=CloudImageEventListResponseV1,
)
def read_cloud_image_job_events(
    job_id: str,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_read)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageEventListResponseV1:
    try:
        return list_events(db, job_id)
    except CloudImageStateNotFound as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/outbox/claims",
    response_model=CloudImageOutboxClaimResponseV1,
)
def claim_cloud_image_outbox(
    request: CloudImageOutboxClaimRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageOutboxClaimResponseV1:
    try:
        return claim_outbox(db, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/outbox/{outbox_id}/settlements",
    response_model=CloudImageOutboxItemV1,
)
def settle_cloud_image_outbox(
    outbox_id: str,
    request: CloudImageOutboxSettleRequestV1,
    _auth: Annotated[AuthContext, Depends(require_cloud_image_write)],
    db: Annotated[Session, Depends(get_db)],
) -> CloudImageOutboxItemV1:
    try:
        return settle_outbox(db, outbox_id, request)
    except (CloudImageStateConflict, CloudImageStateNotFound) as exc:
        raise _translate_error(exc) from exc
