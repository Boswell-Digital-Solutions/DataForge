"""Transactional cloud-image state service.

NeuroForge decides whether a domain transition is valid. DataForge enforces
durability, compare-and-set ordering, idempotency, and atomic evidence writes.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import NoReturn
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cloud_image_state_models import (
    CloudImageEvent,
    CloudImageIdempotencyBinding,
    CloudImageJob,
    CloudImageOperationReceipt,
    CloudImageOutbox,
    CloudImageProtectedRequest,
)
from app.models.cloud_image_state_schemas import (
    CloudImageAppendEventRequestV1,
    CloudImageAuditEventV1,
    CloudImageCreateRequestV1,
    CloudImageEventListResponseV1,
    CloudImageJobRecordV1,
    CloudImageJobStateResponseV1,
    CloudImageRetrySourceResponseV1,
    CloudImageTransitionRequestV1,
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
    return CloudImageJobRecordV1.model_validate(record.record_payload)


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
    request: CloudImageTransitionRequestV1,
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
        current = (
            db.query(CloudImageJob)
            .filter(CloudImageJob.job_id == job_id)
            .with_for_update()
            .one_or_none()
        )
        if current is None:
            raise CloudImageStateNotFound(job_id)
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
            operation_kind="transition",
            operation_fingerprint=request.operation_fingerprint,
            job=current,
        )
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
            raise CloudImageStateConflict("job_identity_mismatch", "Event job ID mismatch")
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
    if db.query(CloudImageJob.job_id).filter(CloudImageJob.job_id == job_id).one_or_none() is None:
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
