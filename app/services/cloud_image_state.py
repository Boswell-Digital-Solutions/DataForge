"""Transactional cloud-image state service.

NeuroForge decides whether a domain transition is valid. DataForge enforces
durability, compare-and-set ordering, idempotency, and atomic evidence writes.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import NoReturn, cast
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cloud_image_state_models import (
    CloudImageControlReceipt,
    CloudImageEvent,
    CloudImageIdempotencyBinding,
    CloudImageJob,
    CloudImageLease,
    CloudImageOperationReceipt,
    CloudImageOutbox,
    CloudImageProtectedRequest,
    CloudImageStageAttempt,
)
from app.models.cloud_image_state_schemas import (
    CloudImageAppendEventRequestV1,
    CloudImageAuditEventV1,
    CloudImageCreateRequestV1,
    CloudImageEventListResponseV1,
    CloudImageJobRecordV1,
    CloudImageJobStateResponseV1,
    CloudImageLeaseClaimRequestV1,
    CloudImageLeaseExpireRequestV1,
    CloudImageLeaseGuardV1,
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
    ProtectedRequestEnvelopeV1,
)


FailureInjector = Callable[[str], None]


class CloudImageStateNotFound(LookupError):
    pass


class CloudImageStateConflict(ValueError):
    def __init__(self, code: str, message: str, *, existing_job_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.existing_job_id = existing_job_id


def _inject(injector: FailureInjector | None, stage: str) -> None:
    if injector is not None:
        injector(stage)


def _raise_integrity_conflict(exc: IntegrityError) -> NoReturn:
    raise CloudImageStateConflict(
        "cloud_image_identity_conflict",
        "A cloud-image identity is already bound to another record",
    ) from exc


def _job_model(record: CloudImageJob) -> CloudImageJobRecordV1:
    return cast(
        CloudImageJobRecordV1,
        CloudImageJobRecordV1.model_validate(record.record_payload),
    )


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's timezone-naive reloads without weakening API contracts."""

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _job_response(
    record: CloudImageJob,
    *,
    created: bool = False,
    replayed: bool = False,
) -> CloudImageJobStateResponseV1:
    return CloudImageJobStateResponseV1(
        job=_job_model(record),
        row_version=record.row_version,
        created=created,
        replayed=replayed,
    )


def _protected_model(record: CloudImageProtectedRequest) -> ProtectedRequestEnvelopeV1:
    return ProtectedRequestEnvelopeV1(
        schema_version=record.schema_version,
        algorithm=record.algorithm,
        key_ref=record.key_ref,
        nonce_b64=record.nonce_b64,
        aad_b64=record.aad_b64,
        ciphertext=record.ciphertext,
        ciphertext_sha256=record.ciphertext_sha256,
        semantic_request_fingerprint=record.semantic_request_fingerprint,
        created_at=_as_utc(record.created_at),
        retention_until=_as_utc(record.retention_until),
    )


def _find_create_replay(
    db: Session,
    request: CloudImageCreateRequestV1,
) -> CloudImageJobStateResponseV1 | None:
    binding = (
        db.query(CloudImageIdempotencyBinding)
        .filter(
            CloudImageIdempotencyBinding.caller_identity == request.job.caller_identity,
            CloudImageIdempotencyBinding.idempotency_key == request.job.idempotency_key,
        )
        .one_or_none()
    )
    if binding is None:
        return None
    if binding.semantic_request_fingerprint != request.operation_fingerprint:
        raise CloudImageStateConflict(
            "idempotency_key_reuse",
            "Idempotency key is bound to a different semantic request",
            existing_job_id=binding.job_id,
        )
    job = db.query(CloudImageJob).filter(CloudImageJob.job_id == binding.job_id).one()
    return _job_response(job, replayed=True)


def _operation_replay(
    db: Session,
    *,
    operation_id: str,
    operation_fingerprint: str,
    expected_job_id: str | None = None,
) -> CloudImageJobStateResponseV1 | None:
    receipt = (
        db.query(CloudImageOperationReceipt)
        .filter(CloudImageOperationReceipt.operation_id == operation_id)
        .one_or_none()
    )
    if receipt is None:
        return None
    if receipt.operation_fingerprint != operation_fingerprint:
        raise CloudImageStateConflict(
            "operation_identity_reuse",
            "Operation ID is bound to different content",
            existing_job_id=receipt.job_id,
        )
    if expected_job_id is not None and receipt.job_id != expected_job_id:
        raise CloudImageStateConflict(
            "operation_job_mismatch",
            "Operation ID is bound to a different cloud-image job",
            existing_job_id=receipt.job_id,
        )
    return CloudImageJobStateResponseV1(
        job=CloudImageJobRecordV1.model_validate(receipt.resulting_record_payload),
        row_version=receipt.resulting_row_version,
        replayed=True,
    )


def _new_job(record: CloudImageJobRecordV1) -> CloudImageJob:
    return CloudImageJob(
        job_id=record.job_id,
        request_id=record.request_id,
        caller_identity=record.caller_identity,
        idempotency_key=record.idempotency_key,
        correlation_id=record.correlation_id,
        source_service=record.source_service,
        app_id=record.app_id,
        use_case=record.use_case,
        status=record.status,
        provider_override=record.provider_override,
        policy_block_code=record.policy_block_code,
        requested_count=record.requested_count,
        accepted_final_count=record.accepted_final_count,
        candidate_count=record.candidate_count,
        replacement_round=record.replacement_round,
        max_replacement_rounds=record.max_replacement_rounds,
        max_total_candidates=record.max_total_candidates,
        max_cost_usd=record.max_cost_usd,
        fulfillment_limits_exhausted=record.fulfillment_limits_exhausted,
        deadline_at=record.deadline_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        terminal_at=record.terminal_at,
        row_version=1,
        record_payload=record.model_dump(mode="json"),
    )


def _new_protected(
    job_id: str,
    envelope: ProtectedRequestEnvelopeV1,
) -> CloudImageProtectedRequest:
    return CloudImageProtectedRequest(
        job_id=job_id,
        schema_version=envelope.schema_version,
        algorithm=envelope.algorithm,
        key_ref=envelope.key_ref,
        nonce_b64=envelope.nonce_b64,
        aad_b64=envelope.aad_b64,
        ciphertext=envelope.ciphertext,
        ciphertext_sha256=envelope.ciphertext_sha256,
        semantic_request_fingerprint=envelope.semantic_request_fingerprint,
        created_at=envelope.created_at,
        retention_until=envelope.retention_until,
    )


def _append_event_rows(db: Session, event: CloudImageAuditEventV1) -> None:
    payload = event.model_dump(mode="json")
    event_record = CloudImageEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        caller_identity=event.caller_identity,
        app_id=event.app_id,
        correlation_id=event.correlation_id,
        job_id=event.job_id,
        details=event.details,
        created_at=event.created_at,
    )
    db.add(event_record)
    # Relationships are deliberately absent from these append-only mappings;
    # establish FK order explicitly while remaining inside the same transaction.
    db.flush()
    db.add(
        CloudImageOutbox(
            outbox_id=f"dfout_{uuid4().hex}",
            event_id=event.event_id,
            aggregate_id=event.job_id,
            event_type=event.event_type,
            payload=payload,
            created_at=event.created_at,
            published_at=None,
            delivery_attempts=0,
            next_attempt_at=event.created_at,
            claim_owner=None,
            claim_token=0,
            claim_expires_at=None,
            last_error_code=None,
            dead_lettered_at=None,
        )
    )


def _add_receipt(
    db: Session,
    *,
    operation_id: str,
    operation_kind: str,
    operation_fingerprint: str,
    job: CloudImageJob,
) -> None:
    db.add(
        CloudImageOperationReceipt(
            operation_id=operation_id,
            operation_kind=operation_kind,
            operation_fingerprint=operation_fingerprint,
            job_id=job.job_id,
            resulting_row_version=job.row_version,
            resulting_status=job.status,
            resulting_record_payload=job.record_payload,
            created_at=job.updated_at,
        )
    )


def create_or_replay_job(
    db: Session,
    request: CloudImageCreateRequestV1,
    *,
    failure_injector: FailureInjector | None = None,
) -> CloudImageJobStateResponseV1:
    operation_replay = _operation_replay(
        db,
        operation_id=request.operation_id,
        operation_fingerprint=request.operation_fingerprint,
    )
    if operation_replay is not None:
        return operation_replay
    replay = _find_create_replay(db, request)
    if replay is not None:
        return replay

    try:
        job = _new_job(request.job)
        db.add(job)
        db.flush()
        _inject(failure_injector, "after_create_job")
        db.add(_new_protected(job.job_id, request.protected_request))
        db.flush()
        _inject(failure_injector, "after_create_protected_request")
        db.add(
            CloudImageIdempotencyBinding(
                binding_id=f"dfidem_{uuid4().hex}",
                caller_identity=request.job.caller_identity,
                idempotency_key=request.job.idempotency_key,
                semantic_request_fingerprint=request.operation_fingerprint,
                job_id=job.job_id,
                created_at=request.job.created_at,
            )
        )
        db.flush()
        _inject(failure_injector, "after_create_idempotency")
        for event in request.events:
            _append_event_rows(db, event)
        db.flush()
        _inject(failure_injector, "after_create_events_and_outbox")
        _add_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="create",
            operation_fingerprint=request.operation_fingerprint,
            job=job,
        )
        db.flush()
        _inject(failure_injector, "after_create_receipt")
        _inject(failure_injector, "before_create_commit")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        replay = _find_create_replay(db, request)
        if replay is not None:
            return replay
        _raise_integrity_conflict(exc)
    except Exception:
        db.rollback()
        raise
    db.refresh(job)
    return _job_response(job, created=True)


def get_job(
    db: Session,
    job_id: str,
    *,
    caller_identity: str | None = None,
) -> CloudImageJobStateResponseV1:
    query = db.query(CloudImageJob).filter(CloudImageJob.job_id == job_id)
    if caller_identity is not None:
        query = query.filter(CloudImageJob.caller_identity == caller_identity)
    record = query.one_or_none()
    if record is None:
        raise CloudImageStateNotFound(job_id)
    return _job_response(record)


def get_retry_source(db: Session, job_id: str) -> CloudImageRetrySourceResponseV1:
    job = db.query(CloudImageJob).filter(CloudImageJob.job_id == job_id).one_or_none()
    protected = (
        db.query(CloudImageProtectedRequest)
        .filter(CloudImageProtectedRequest.job_id == job_id)
        .one_or_none()
    )
    if job is None or protected is None:
        raise CloudImageStateNotFound(job_id)
    return CloudImageRetrySourceResponseV1(
        job=_job_model(job),
        row_version=job.row_version,
        protected_request=_protected_model(protected),
    )


_IMMUTABLE_JOB_FIELDS = (
    "job_id",
    "request_id",
    "correlation_id",
    "idempotency_key",
    "source_service",
    "caller_identity",
    "app_id",
    "use_case",
    "provider_override",
    "policy_block_code",
    "requested_count",
    "max_replacement_rounds",
    "max_total_candidates",
    "max_cost_usd",
    "deadline_at",
    "created_at",
)


def transition_job(
    db: Session,
    job_id: str,
    request: CloudImageTransitionRequestV1 | CloudImageWorkerTransitionRequestV1,
    *,
    lease_guard: CloudImageLeaseGuardV1 | None = None,
    evaluated_at: datetime | None = None,
    failure_injector: FailureInjector | None = None,
) -> CloudImageJobStateResponseV1:
    replay = _operation_replay(
        db,
        operation_id=request.operation_id,
        operation_fingerprint=request.operation_fingerprint,
        expected_job_id=job_id,
    )
    if replay is not None:
        return replay

    try:
        current = (
            db.query(CloudImageJob)
            .filter(CloudImageJob.job_id == job_id)
            .with_for_update()
            .one_or_none()
        )
        if current is None:
            raise CloudImageStateNotFound(job_id)
        if lease_guard is not None:
            _require_active_lease(
                db,
                job_id,
                lease_guard,
                evaluated_at=evaluated_at,
            )
        if (
            current.row_version != request.expected_row_version
            or current.status != request.expected_status
        ):
            raise CloudImageStateConflict(
                "compare_and_set_conflict",
                "Cloud-image job changed before this transition was committed",
                existing_job_id=job_id,
            )
        old_job = _job_model(current)
        new_job = request.updated_job
        if any(
            getattr(old_job, field) != getattr(new_job, field)
            for field in _IMMUTABLE_JOB_FIELDS
        ):
            raise CloudImageStateConflict(
                "immutable_job_field_changed",
                "Transition attempted to change immutable job identity or limits",
                existing_job_id=job_id,
            )
        if new_job.job_id != job_id or request.event.job_id != job_id:
            raise CloudImageStateConflict(
                "job_identity_mismatch",
                "Transition payload identities do not match the route job",
            )
        if (
            request.event.app_id != new_job.app_id
            or request.event.correlation_id != new_job.correlation_id
        ):
            raise CloudImageStateConflict(
                "event_identity_mismatch",
                "Transition event does not match the job application or correlation",
            )

        current.status = new_job.status
        current.accepted_final_count = new_job.accepted_final_count
        current.candidate_count = new_job.candidate_count
        current.replacement_round = new_job.replacement_round
        current.fulfillment_limits_exhausted = new_job.fulfillment_limits_exhausted
        current.updated_at = new_job.updated_at
        current.terminal_at = new_job.terminal_at
        current.row_version += 1
        current.record_payload = new_job.model_dump(mode="json")
        _inject(failure_injector, "after_transition_state")
        _append_event_rows(db, request.event)
        db.flush()
        _inject(failure_injector, "after_transition_event_and_outbox")
        _add_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind=(
                "worker_transition" if lease_guard is not None else "transition"
            ),
            operation_fingerprint=request.operation_fingerprint,
            job=current,
        )
        if lease_guard is not None:
            attempt_id = cast(CloudImageWorkerTransitionRequestV1, request).attempt_id
            attempt = (
                db.query(CloudImageStageAttempt)
                .filter(
                    CloudImageStageAttempt.attempt_id == attempt_id,
                    CloudImageStageAttempt.job_id == job_id,
                )
                .with_for_update()
                .one_or_none()
            )
            if attempt is None:
                raise CloudImageStateNotFound(attempt_id)
            if attempt.stage != lease_guard.stage:
                raise CloudImageStateConflict(
                    "attempt_stage_mismatch",
                    "Transition attempt does not match its active worker stage",
                    existing_job_id=job_id,
                )
            if attempt.fencing_token > lease_guard.fencing_token:
                raise CloudImageStateConflict(
                    "attempt_fence_conflict",
                    "Transition attempt was recorded by a newer worker lease",
                    existing_job_id=job_id,
                )
            latest_attempt_number = (
                db.query(CloudImageStageAttempt.attempt_number)
                .filter(
                    CloudImageStageAttempt.job_id == job_id,
                    CloudImageStageAttempt.stage == attempt.stage,
                )
                .order_by(CloudImageStageAttempt.attempt_number.desc())
                .limit(1)
                .scalar()
            )
            if latest_attempt_number != attempt.attempt_number:
                raise CloudImageStateConflict(
                    "attempt_superseded",
                    "A newer attempt exists for this worker stage",
                    existing_job_id=job_id,
                )
            if attempt.status not in {"succeeded", "permanent_failure"}:
                raise CloudImageStateConflict(
                    "attempt_not_transitionable",
                    "Worker transition requires a final stage attempt outcome",
                    existing_job_id=job_id,
                )
            if attempt.transitioned_to_status is not None:
                raise CloudImageStateConflict(
                    "attempt_already_transitioned",
                    "Stage attempt is already linked to a committed transition",
                    existing_job_id=job_id,
                )
            attempt.transitioned_to_status = current.status
            attempt.transitioned_row_version = current.row_version
            attempt.transitioned_at = current.updated_at
            _inject(failure_injector, "after_worker_attempt_link")
        db.flush()
        _inject(failure_injector, "after_transition_receipt")
        _inject(failure_injector, "before_transition_commit")
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = _operation_replay(
            db,
            operation_id=request.operation_id,
            operation_fingerprint=request.operation_fingerprint,
            expected_job_id=job_id,
        )
        if replay is not None:
            return replay
        _raise_integrity_conflict(exc)
    except Exception:
        db.rollback()
        raise
    db.refresh(current)
    return _job_response(current)


def append_event(
    db: Session,
    job_id: str,
    request: CloudImageAppendEventRequestV1,
    *,
    failure_injector: FailureInjector | None = None,
) -> CloudImageJobStateResponseV1:
    replay = _operation_replay(
        db,
        operation_id=request.operation_id,
        operation_fingerprint=request.operation_fingerprint,
        expected_job_id=job_id,
    )
    if replay is not None:
        return replay
    try:
        job = (
            db.query(CloudImageJob)
            .filter(CloudImageJob.job_id == job_id)
            .with_for_update()
            .one_or_none()
        )
        if job is None:
            raise CloudImageStateNotFound(job_id)
        if job.row_version != request.expected_row_version:
            raise CloudImageStateConflict(
                "compare_and_set_conflict",
                "Cloud-image job changed before this event was appended",
                existing_job_id=job_id,
            )
        if request.event.job_id != job_id:
            raise CloudImageStateConflict(
                "job_identity_mismatch", "Event job ID mismatch"
            )
        current_job = _job_model(job)
        if (
            request.event.app_id != current_job.app_id
            or request.event.correlation_id != current_job.correlation_id
        ):
            raise CloudImageStateConflict(
                "event_identity_mismatch",
                "Event does not match the job application or correlation",
            )
        job.row_version += 1
        _append_event_rows(db, request.event)
        db.flush()
        _inject(failure_injector, "after_append_event_and_outbox")
        _add_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="event",
            operation_fingerprint=request.operation_fingerprint,
            job=job,
        )
        db.flush()
        _inject(failure_injector, "after_append_receipt")
        _inject(failure_injector, "before_event_commit")
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = _operation_replay(
            db,
            operation_id=request.operation_id,
            operation_fingerprint=request.operation_fingerprint,
            expected_job_id=job_id,
        )
        if replay is not None:
            return replay
        _raise_integrity_conflict(exc)
    except Exception:
        db.rollback()
        raise
    return _job_response(job)


def list_events(db: Session, job_id: str) -> CloudImageEventListResponseV1:
    if (
        db.query(CloudImageJob.job_id)
        .filter(CloudImageJob.job_id == job_id)
        .one_or_none()
        is None
    ):
        raise CloudImageStateNotFound(job_id)
    records = (
        db.query(CloudImageEvent)
        .filter(CloudImageEvent.job_id == job_id)
        .order_by(CloudImageEvent.created_at.asc(), CloudImageEvent.event_id.asc())
        .all()
    )
    return CloudImageEventListResponseV1(
        job_id=job_id,
        events=[
            CloudImageAuditEventV1(
                event_id=record.event_id,
                event_type=record.event_type,
                caller_identity=record.caller_identity,
                app_id=record.app_id,
                correlation_id=record.correlation_id,
                job_id=record.job_id,
                details=record.details or {},
                created_at=_as_utc(record.created_at),
            )
            for record in records
        ],
    )


_TERMINAL_STATUSES = frozenset(
    {"fulfilled", "partial", "failed", "blocked", "expired", "cancelled"}
)


def _now(value: datetime | None = None) -> datetime:
    return datetime.now(UTC) if value is None else _as_utc(value)


def _control_replay(
    db: Session,
    *,
    operation_id: str,
    operation_kind: str,
    operation_fingerprint: str,
    response_model: type[BaseModel],
    expected_job_id: str | None = None,
) -> BaseModel | None:
    receipt = (
        db.query(CloudImageControlReceipt)
        .filter(CloudImageControlReceipt.operation_id == operation_id)
        .one_or_none()
    )
    if receipt is None:
        return None
    if (
        receipt.operation_kind != operation_kind
        or receipt.operation_fingerprint != operation_fingerprint
        or (expected_job_id is not None and receipt.job_id != expected_job_id)
    ):
        raise CloudImageStateConflict(
            "operation_identity_reuse",
            "Control operation ID is bound to different content",
            existing_job_id=receipt.job_id,
        )
    payload = dict(receipt.response_payload)
    if "replayed" in response_model.model_fields:
        payload["replayed"] = True
    return response_model.model_validate(payload)


def _save_control_receipt(
    db: Session,
    *,
    operation_id: str,
    operation_kind: str,
    operation_fingerprint: str,
    job_id: str | None,
    response: BaseModel,
    created_at: datetime,
) -> None:
    db.add(
        CloudImageControlReceipt(
            operation_id=operation_id,
            operation_kind=operation_kind,
            operation_fingerprint=operation_fingerprint,
            job_id=job_id,
            response_payload=response.model_dump(mode="json"),
            created_at=created_at,
        )
    )


def _lease_response(
    lease: CloudImageLease, *, replayed: bool = False
) -> CloudImageLeaseResponseV1:
    return CloudImageLeaseResponseV1(
        job_id=lease.job_id,
        worker_id=lease.worker_id,
        stage=lease.stage,
        fencing_token=lease.fencing_token,
        acquired_at=_as_utc(lease.acquired_at),
        renewed_at=_as_utc(lease.renewed_at),
        expires_at=_as_utc(lease.expires_at),
        released_at=(None if lease.released_at is None else _as_utc(lease.released_at)),
        release_reason=lease.release_reason,
        replayed=replayed,
    )


def _require_active_lease(
    db: Session,
    job_id: str,
    guard: CloudImageLeaseGuardV1,
    *,
    evaluated_at: datetime | None = None,
) -> CloudImageLease:
    lease = (
        db.query(CloudImageLease)
        .filter(CloudImageLease.job_id == job_id)
        .with_for_update()
        .one_or_none()
    )
    if lease is None:
        raise CloudImageStateConflict(
            "lease_fence_conflict", "Cloud-image job has no worker lease"
        )
    if (
        lease.worker_id != guard.worker_id
        or lease.stage != guard.stage
        or lease.fencing_token != guard.fencing_token
        or lease.released_at is not None
    ):
        raise CloudImageStateConflict(
            "lease_fence_conflict",
            "Worker lease identity or fencing token is stale",
            existing_job_id=job_id,
        )
    if _as_utc(lease.expires_at) <= _now(evaluated_at):
        raise CloudImageStateConflict(
            "lease_expired",
            "Worker lease expired before the operation committed",
            existing_job_id=job_id,
        )
    return cast(CloudImageLease, lease)


def claim_lease(
    db: Session,
    job_id: str,
    request: CloudImageLeaseClaimRequestV1,
    *,
    evaluated_at: datetime | None = None,
    failure_injector: FailureInjector | None = None,
) -> CloudImageLeaseResponseV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="lease_claim",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageLeaseResponseV1,
        expected_job_id=job_id,
    )
    if replay is not None:
        return cast(CloudImageLeaseResponseV1, replay)
    now = _now(evaluated_at)
    try:
        job = (
            db.query(CloudImageJob)
            .filter(CloudImageJob.job_id == job_id)
            .with_for_update()
            .one_or_none()
        )
        if job is None:
            raise CloudImageStateNotFound(job_id)
        if job.status in _TERMINAL_STATUSES:
            raise CloudImageStateConflict(
                "terminal_job_not_claimable",
                "Terminal cloud-image jobs cannot be claimed",
                existing_job_id=job_id,
            )
        lease = (
            db.query(CloudImageLease)
            .filter(CloudImageLease.job_id == job_id)
            .with_for_update()
            .one_or_none()
        )
        if (
            lease is not None
            and lease.released_at is None
            and _as_utc(lease.expires_at) > now
        ):
            raise CloudImageStateConflict(
                "lease_held",
                "Cloud-image job already has an active worker lease",
                existing_job_id=job_id,
            )
        if lease is None:
            lease = CloudImageLease(
                job_id=job_id,
                stage=request.stage,
                worker_id=request.worker_id,
                fencing_token=1,
                acquired_at=now,
                renewed_at=now,
                expires_at=now + timedelta(seconds=request.lease_seconds),
                released_at=None,
                release_reason=None,
            )
            db.add(lease)
        else:
            lease.stage = request.stage
            lease.worker_id = request.worker_id
            lease.fencing_token += 1
            lease.acquired_at = now
            lease.renewed_at = now
            lease.expires_at = now + timedelta(seconds=request.lease_seconds)
            lease.released_at = None
            lease.release_reason = None
        db.flush()
        _inject(failure_injector, "after_lease_claim")
        response = _lease_response(lease)
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="lease_claim",
            operation_fingerprint=request.operation_fingerprint,
            job_id=job_id,
            response=response,
            created_at=now,
        )
        _inject(failure_injector, "before_lease_claim_commit")
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = _control_replay(
            db,
            operation_id=request.operation_id,
            operation_kind="lease_claim",
            operation_fingerprint=request.operation_fingerprint,
            response_model=CloudImageLeaseResponseV1,
            expected_job_id=job_id,
        )
        if replay is not None:
            return cast(CloudImageLeaseResponseV1, replay)
        _raise_integrity_conflict(exc)
    except Exception:
        db.rollback()
        raise
    return response


def renew_lease(
    db: Session,
    job_id: str,
    request: CloudImageLeaseRenewRequestV1,
    *,
    evaluated_at: datetime | None = None,
) -> CloudImageLeaseResponseV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="lease_renew",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageLeaseResponseV1,
        expected_job_id=job_id,
    )
    if replay is not None:
        return cast(CloudImageLeaseResponseV1, replay)
    now = _now(evaluated_at)
    try:
        lease = _require_active_lease(db, job_id, request.lease, evaluated_at=now)
        lease.renewed_at = now
        lease.expires_at = now + timedelta(seconds=request.lease_seconds)
        response = _lease_response(lease)
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="lease_renew",
            operation_fingerprint=request.operation_fingerprint,
            job_id=job_id,
            response=response,
            created_at=now,
        )
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return response


def release_lease(
    db: Session,
    job_id: str,
    request: CloudImageLeaseReleaseRequestV1,
    *,
    evaluated_at: datetime | None = None,
) -> CloudImageLeaseResponseV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="lease_release",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageLeaseResponseV1,
        expected_job_id=job_id,
    )
    if replay is not None:
        return cast(CloudImageLeaseResponseV1, replay)
    now = _now(evaluated_at)
    try:
        lease = _require_active_lease(db, job_id, request.lease, evaluated_at=now)
        lease.released_at = now
        lease.release_reason = request.reason_code
        response = _lease_response(lease)
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="lease_release",
            operation_fingerprint=request.operation_fingerprint,
            job_id=job_id,
            response=response,
            created_at=now,
        )
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return response


def expire_lease(
    db: Session,
    job_id: str,
    request: CloudImageLeaseExpireRequestV1,
    *,
    evaluated_at: datetime | None = None,
) -> CloudImageLeaseResponseV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="lease_expire",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageLeaseResponseV1,
        expected_job_id=job_id,
    )
    if replay is not None:
        return cast(CloudImageLeaseResponseV1, replay)
    now = _now(evaluated_at)
    try:
        lease = (
            db.query(CloudImageLease)
            .filter(CloudImageLease.job_id == job_id)
            .with_for_update()
            .one_or_none()
        )
        if lease is None:
            raise CloudImageStateNotFound(job_id)
        if (
            lease.worker_id != request.lease.worker_id
            or lease.stage != request.lease.stage
            or lease.fencing_token != request.lease.fencing_token
            or lease.released_at is not None
        ):
            raise CloudImageStateConflict(
                "lease_fence_conflict",
                "Worker lease identity or fencing token is stale",
                existing_job_id=job_id,
            )
        if _as_utc(lease.expires_at) > now:
            raise CloudImageStateConflict(
                "lease_not_expired",
                "Active worker lease cannot be expired early",
                existing_job_id=job_id,
            )
        lease.released_at = now
        lease.release_reason = request.reason_code
        response = _lease_response(lease)
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="lease_expire",
            operation_fingerprint=request.operation_fingerprint,
            job_id=job_id,
            response=response,
            created_at=now,
        )
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return response


def transition_job_with_lease(
    db: Session,
    job_id: str,
    request: CloudImageWorkerTransitionRequestV1,
    *,
    evaluated_at: datetime | None = None,
    failure_injector: FailureInjector | None = None,
) -> CloudImageJobStateResponseV1:
    return transition_job(
        db,
        job_id,
        request,
        lease_guard=request.lease,
        evaluated_at=evaluated_at,
        failure_injector=failure_injector,
    )


def _attempt_response(
    attempt: CloudImageStageAttempt, *, replayed: bool = False
) -> CloudImageStageAttemptV1:
    return CloudImageStageAttemptV1(
        attempt_id=attempt.attempt_id,
        operation_id=attempt.operation_id,
        operation_fingerprint=attempt.operation_fingerprint,
        job_id=attempt.job_id,
        stage=attempt.stage,
        attempt_number=attempt.attempt_number,
        fencing_token=attempt.fencing_token,
        status=attempt.status,
        retry_class=attempt.retry_class,
        failure_code=attempt.failure_code,
        result_digest=attempt.result_digest,
        next_attempt_at=(
            None
            if attempt.next_attempt_at is None
            else _as_utc(attempt.next_attempt_at)
        ),
        started_at=_as_utc(attempt.started_at),
        completed_at=(
            None if attempt.completed_at is None else _as_utc(attempt.completed_at)
        ),
        transitioned_to_status=attempt.transitioned_to_status,
        transitioned_row_version=attempt.transitioned_row_version,
        transitioned_at=(
            None
            if attempt.transitioned_at is None
            else _as_utc(attempt.transitioned_at)
        ),
        replayed=replayed,
    )


def start_stage_attempt(
    db: Session,
    job_id: str,
    request: CloudImageStageAttemptStartRequestV1,
    *,
    evaluated_at: datetime | None = None,
    failure_injector: FailureInjector | None = None,
) -> CloudImageStageAttemptV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="attempt_start",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageStageAttemptV1,
        expected_job_id=job_id,
    )
    if replay is not None:
        return cast(CloudImageStageAttemptV1, replay)
    now = _now(evaluated_at)
    try:
        _require_active_lease(db, job_id, request.lease, evaluated_at=now)
        if request.stage != request.lease.stage:
            raise CloudImageStateConflict(
                "attempt_stage_mismatch", "Attempt stage does not match its lease"
            )
        latest = (
            db.query(CloudImageStageAttempt)
            .filter(
                CloudImageStageAttempt.job_id == job_id,
                CloudImageStageAttempt.stage == request.stage,
            )
            .order_by(CloudImageStageAttempt.attempt_number.desc())
            .limit(1)
            .one_or_none()
        )
        expected_attempt_number = 1 if latest is None else latest.attempt_number + 1
        if request.attempt_number != expected_attempt_number:
            raise CloudImageStateConflict(
                "attempt_out_of_order",
                "Stage attempt number is not the next durable sequence",
                existing_job_id=job_id,
            )
        if latest is not None and latest.status in {
            "started",
            "reconciliation_required",
        }:
            raise CloudImageStateConflict(
                "attempt_in_progress",
                "Previous stage attempt still requires reconciliation",
                existing_job_id=job_id,
            )
        if (
            latest is not None
            and latest.status == "retryable_failure"
            and latest.next_attempt_at is not None
            and _as_utc(latest.next_attempt_at) > now
        ):
            raise CloudImageStateConflict(
                "attempt_retry_not_due",
                "Stage attempt retry backoff has not elapsed",
                existing_job_id=job_id,
            )
        if (
            latest is not None
            and latest.status in {"succeeded", "permanent_failure"}
            and latest.transitioned_to_status is None
        ):
            raise CloudImageStateConflict(
                "attempt_result_uncommitted",
                "Previous final attempt has not been linked to job state",
                existing_job_id=job_id,
            )
        attempt = CloudImageStageAttempt(
            attempt_id=request.attempt_id,
            operation_id=request.operation_id,
            operation_fingerprint=request.operation_fingerprint,
            job_id=job_id,
            stage=request.stage,
            attempt_number=request.attempt_number,
            fencing_token=request.lease.fencing_token,
            status="started",
            retry_class="none",
            failure_code=None,
            result_digest=None,
            next_attempt_at=None,
            started_at=now,
            completed_at=None,
            transitioned_to_status=None,
            transitioned_row_version=None,
            transitioned_at=None,
        )
        db.add(attempt)
        db.flush()
        _inject(failure_injector, "after_attempt_start")
        response = _attempt_response(attempt)
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="attempt_start",
            operation_fingerprint=request.operation_fingerprint,
            job_id=job_id,
            response=response,
            created_at=now,
        )
        _inject(failure_injector, "before_attempt_start_commit")
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = _control_replay(
            db,
            operation_id=request.operation_id,
            operation_kind="attempt_start",
            operation_fingerprint=request.operation_fingerprint,
            response_model=CloudImageStageAttemptV1,
            expected_job_id=job_id,
        )
        if replay is not None:
            return cast(CloudImageStageAttemptV1, replay)
        _raise_integrity_conflict(exc)
    except Exception:
        db.rollback()
        raise
    return response


def complete_stage_attempt(
    db: Session,
    job_id: str,
    attempt_id: str,
    request: CloudImageStageAttemptCompleteRequestV1,
    *,
    evaluated_at: datetime | None = None,
    failure_injector: FailureInjector | None = None,
) -> CloudImageStageAttemptV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="attempt_complete",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageStageAttemptV1,
        expected_job_id=job_id,
    )
    if replay is not None:
        return cast(CloudImageStageAttemptV1, replay)
    now = _now(evaluated_at)
    try:
        lease = _require_active_lease(db, job_id, request.lease, evaluated_at=now)
        attempt = (
            db.query(CloudImageStageAttempt)
            .filter(
                CloudImageStageAttempt.attempt_id == attempt_id,
                CloudImageStageAttempt.job_id == job_id,
            )
            .with_for_update()
            .one_or_none()
        )
        if attempt is None:
            raise CloudImageStateNotFound(attempt_id)
        if attempt.stage != request.lease.stage:
            raise CloudImageStateConflict(
                "attempt_stage_mismatch", "Attempt stage does not match its lease"
            )
        if attempt.fencing_token > lease.fencing_token:
            raise CloudImageStateConflict(
                "attempt_fence_conflict",
                "Stage attempt was recorded by a newer worker lease",
                existing_job_id=job_id,
            )
        latest_attempt_number = (
            db.query(CloudImageStageAttempt.attempt_number)
            .filter(
                CloudImageStageAttempt.job_id == job_id,
                CloudImageStageAttempt.stage == attempt.stage,
            )
            .order_by(CloudImageStageAttempt.attempt_number.desc())
            .limit(1)
            .scalar()
        )
        if latest_attempt_number != attempt.attempt_number:
            raise CloudImageStateConflict(
                "attempt_superseded",
                "A newer attempt exists for this worker stage",
                existing_job_id=job_id,
            )
        if attempt.status not in {"started", "reconciliation_required"}:
            raise CloudImageStateConflict(
                "attempt_already_completed", "Stage attempt already has an outcome"
            )
        if request.status == "started":
            raise CloudImageStateConflict(
                "invalid_attempt_outcome", "Completion cannot return started status"
            )
        attempt.status = request.status
        attempt.retry_class = request.retry_class
        attempt.failure_code = request.failure_code
        attempt.result_digest = request.result_digest
        attempt.next_attempt_at = request.next_attempt_at
        attempt.completed_at = now
        db.flush()
        _inject(failure_injector, "after_attempt_complete")
        response = _attempt_response(attempt)
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="attempt_complete",
            operation_fingerprint=request.operation_fingerprint,
            job_id=job_id,
            response=response,
            created_at=now,
        )
        _inject(failure_injector, "before_attempt_complete_commit")
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        replay = _control_replay(
            db,
            operation_id=request.operation_id,
            operation_kind="attempt_complete",
            operation_fingerprint=request.operation_fingerprint,
            response_model=CloudImageStageAttemptV1,
            expected_job_id=job_id,
        )
        if replay is not None:
            return cast(CloudImageStageAttemptV1, replay)
        _raise_integrity_conflict(exc)
    except Exception:
        db.rollback()
        raise
    return response


def list_stage_attempts(db: Session, job_id: str) -> CloudImageStageAttemptListV1:
    if (
        db.query(CloudImageJob.job_id)
        .filter(CloudImageJob.job_id == job_id)
        .one_or_none()
        is None
    ):
        raise CloudImageStateNotFound(job_id)
    attempts = (
        db.query(CloudImageStageAttempt)
        .filter(CloudImageStageAttempt.job_id == job_id)
        .order_by(
            CloudImageStageAttempt.started_at.asc(),
            CloudImageStageAttempt.attempt_id.asc(),
        )
        .all()
    )
    return CloudImageStageAttemptListV1(
        job_id=job_id,
        attempts=[_attempt_response(attempt) for attempt in attempts],
    )


def _outbox_response(
    item: CloudImageOutbox, *, replayed: bool = False
) -> CloudImageOutboxItemV1:
    next_attempt_at = item.next_attempt_at or item.created_at
    return CloudImageOutboxItemV1(
        outbox_id=item.outbox_id,
        event_id=item.event_id,
        aggregate_id=item.aggregate_id,
        event_type=item.event_type,
        payload=item.payload,
        created_at=_as_utc(item.created_at),
        published_at=(
            None if item.published_at is None else _as_utc(item.published_at)
        ),
        delivery_attempts=item.delivery_attempts,
        next_attempt_at=_as_utc(next_attempt_at),
        claim_owner=item.claim_owner,
        claim_token=item.claim_token,
        claim_expires_at=(
            None if item.claim_expires_at is None else _as_utc(item.claim_expires_at)
        ),
        last_error_code=item.last_error_code,
        dead_lettered_at=(
            None if item.dead_lettered_at is None else _as_utc(item.dead_lettered_at)
        ),
        replayed=replayed,
    )


def claim_outbox(
    db: Session,
    request: CloudImageOutboxClaimRequestV1,
    *,
    evaluated_at: datetime | None = None,
    failure_injector: FailureInjector | None = None,
) -> CloudImageOutboxClaimResponseV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="outbox_claim",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageOutboxClaimResponseV1,
    )
    if replay is not None:
        return cast(CloudImageOutboxClaimResponseV1, replay)
    now = _now(evaluated_at)
    try:
        items = (
            db.query(CloudImageOutbox)
            .filter(
                CloudImageOutbox.published_at.is_(None),
                CloudImageOutbox.dead_lettered_at.is_(None),
                CloudImageOutbox.next_attempt_at <= now,
                or_(
                    CloudImageOutbox.claim_expires_at.is_(None),
                    CloudImageOutbox.claim_expires_at <= now,
                ),
            )
            .order_by(
                CloudImageOutbox.next_attempt_at.asc(),
                CloudImageOutbox.created_at.asc(),
                CloudImageOutbox.outbox_id.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(request.max_items)
            .all()
        )
        for item in items:
            item.claim_owner = request.dispatcher_id
            item.claim_token += 1
            item.claim_expires_at = now + timedelta(seconds=request.lease_seconds)
            item.delivery_attempts += 1
        db.flush()
        _inject(failure_injector, "after_outbox_claim")
        response = CloudImageOutboxClaimResponseV1(
            dispatcher_id=request.dispatcher_id,
            items=[_outbox_response(item) for item in items],
        )
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="outbox_claim",
            operation_fingerprint=request.operation_fingerprint,
            job_id=None,
            response=response,
            created_at=now,
        )
        _inject(failure_injector, "before_outbox_claim_commit")
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return response


def settle_outbox(
    db: Session,
    outbox_id: str,
    request: CloudImageOutboxSettleRequestV1,
    *,
    evaluated_at: datetime | None = None,
) -> CloudImageOutboxItemV1:
    replay = _control_replay(
        db,
        operation_id=request.operation_id,
        operation_kind="outbox_settle",
        operation_fingerprint=request.operation_fingerprint,
        response_model=CloudImageOutboxItemV1,
    )
    if replay is not None:
        result = cast(CloudImageOutboxItemV1, replay)
        if result.outbox_id != outbox_id:
            raise CloudImageStateConflict(
                "operation_identity_reuse",
                "Outbox settlement operation is bound to another item",
            )
        return result
    now = _now(evaluated_at)
    try:
        item = (
            db.query(CloudImageOutbox)
            .filter(CloudImageOutbox.outbox_id == outbox_id)
            .with_for_update()
            .one_or_none()
        )
        if item is None:
            raise CloudImageStateNotFound(outbox_id)
        if (
            item.claim_owner != request.dispatcher_id
            or item.claim_token != request.claim_token
            or item.claim_expires_at is None
            or _as_utc(item.claim_expires_at) <= now
        ):
            raise CloudImageStateConflict(
                "outbox_claim_conflict", "Outbox claim is stale or owned elsewhere"
            )
        if request.outcome == "published":
            item.published_at = now
            item.last_error_code = None
        elif request.outcome == "retry":
            item.next_attempt_at = now + timedelta(
                seconds=request.retry_after_seconds or 1
            )
            item.last_error_code = request.error_code
        else:
            item.dead_lettered_at = now
            item.last_error_code = request.error_code
        item.claim_owner = None
        item.claim_expires_at = None
        response = _outbox_response(item)
        _save_control_receipt(
            db,
            operation_id=request.operation_id,
            operation_kind="outbox_settle",
            operation_fingerprint=request.operation_fingerprint,
            job_id=item.aggregate_id,
            response=response,
            created_at=now,
        )
        db.commit()
    except (CloudImageStateConflict, CloudImageStateNotFound):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return response
