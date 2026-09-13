"""Focused transactional tests for the NeuroForge cloud-image state boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.api.admin_keys_router import AuthContext
from app.api.cloud_image_state_router import (
    _require_neuroforge_scope,
    create_cloud_image_job_state,
    read_cloud_image_job_state,
)
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
    CloudImageCreateRequestV1,
    CloudImageTransitionRequestV1,
)
from app.services.cloud_image_state import (
    CloudImageStateConflict,
    append_event,
    create_or_replay_job,
    get_job,
    get_retry_source,
    list_events,
    transition_job,
)


BASE = "/api/v1/internal/cloud-image-state"
FINGERPRINT = "hmac-sha256:" + "a" * 64
TRANSITION_FINGERPRINT = "hmac-sha256:" + "b" * 64


def _auth(*scopes: str, service_name: str = "neuroforge") -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=SimpleNamespace(
            metadata={"service_name": service_name, "scopes": list(scopes)}
        ),
    )


def _create_payload(*, fingerprint: str = FINGERPRINT) -> dict[str, object]:
    now = datetime.now(UTC).replace(microsecond=0)
    job = {
        "schema_version": "cloud_image_job_record.v1",
        "job_id": "nfimg_slice01",
        "request_id": "nfreq_slice01",
        "correlation_id": "corr_slice01",
        "idempotency_key": "idem_slice01",
        "source_service": "authorforge",
        "caller_identity": "service:authorforge",
        "app_id": "authorforge",
        "use_case": "book_cover_concept",
        "provider_override": None,
        "policy_block_code": None,
        "status": "queued",
        "requested_count": 2,
        "accepted_final_count": 0,
        "candidate_count": 0,
        "replacement_round": 0,
        "max_replacement_rounds": 3,
        "max_total_candidates": 6,
        "max_cost_usd": "5.0000",
        "fulfillment_limits_exhausted": False,
        "deadline_at": (now + timedelta(hours=1)).isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "terminal_at": None,
    }
    event = {
        "schema_version": "cloud_image_audit_event.v1",
        "event_id": "nfevt_requested_slice01",
        "event_type": "cloud_image.job_requested",
        "caller_identity": "service:authorforge",
        "app_id": "authorforge",
        "correlation_id": "corr_slice01",
        "job_id": "nfimg_slice01",
        "details": {},
        "created_at": now.isoformat(),
    }
    return {
        "schema_version": "cloud_image_state_create.v1",
        "operation_id": "nfop_create_slice01",
        "operation_fingerprint": fingerprint,
        "job": job,
        "protected_request": {
            "schema_version": "cloud_image_protected_request.v1",
            "algorithm": "A256GCM",
            "key_ref": "kms://neuroforge/cloud-image/test",
            "nonce_b64": "MTIzNDU2Nzg5MDEy",
            "aad_b64": "bmZpbWdfc2xpY2UwMQ==",
            "ciphertext": "Y2lwaGVydGV4dC13aXRoLWFlcy1nY20tdGFn",
            "ciphertext_sha256": "sha256:" + "c" * 64,
            "semantic_request_fingerprint": fingerprint,
            "created_at": now.isoformat(),
            "retention_until": (now + timedelta(days=30)).isoformat(),
        },
        "events": [event],
        "retry_source_job_id": None,
    }


def _transition_payload(created: dict[str, object]) -> dict[str, object]:
    job = dict(created["job"])
    job["status"] = "planning"
    job["updated_at"] = datetime.now(UTC).isoformat()
    return {
        "schema_version": "cloud_image_state_transition.v1",
        "operation_id": "nfop_transition_slice01",
        "operation_fingerprint": TRANSITION_FINGERPRINT,
        "expected_row_version": 1,
        "expected_status": "queued",
        "updated_job": job,
        "event": {
            "schema_version": "cloud_image_audit_event.v1",
            "event_id": "nfevt_planning_slice01",
            "event_type": "cloud_image.job_transitioned",
            "caller_identity": "service:neuroforge",
            "app_id": "authorforge",
            "correlation_id": "corr_slice01",
            "job_id": "nfimg_slice01",
            "details": {"from_status": "queued", "to_status": "planning"},
            "created_at": datetime.now(UTC).isoformat(),
        },
    }


def test_create_replay_survives_a_new_session_and_stores_only_ciphertext(
    db: Session,
) -> None:
    payload = _create_payload()
    first = create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(payload))
    assert first.created is True

    NewSession = sessionmaker(bind=db.get_bind())
    with NewSession() as restarted:
        replay = create_or_replay_job(
            restarted, CloudImageCreateRequestV1.model_validate(payload)
        )
        assert replay.replayed is True
        assert replay.job.job_id == "nfimg_slice01"
        assert restarted.query(CloudImageJob).count() == 1
        assert restarted.query(CloudImageIdempotencyBinding).count() == 1
        assert restarted.query(CloudImageEvent).count() == 1
        assert restarted.query(CloudImageOutbox).count() == 1
        protected = restarted.query(CloudImageProtectedRequest).one()
        assert protected.algorithm == "A256GCM"
        assert "lighthouse" not in protected.ciphertext.lower()


def test_create_rejects_semantic_idempotency_reuse(
    db: Session,
) -> None:
    create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(_create_payload()))
    conflicting = _create_payload(fingerprint="hmac-sha256:" + "d" * 64)
    conflicting["operation_id"] = "nfop_create_conflicting_slice01"
    with pytest.raises(CloudImageStateConflict) as exc_info:
        create_or_replay_job(
            db,
            CloudImageCreateRequestV1.model_validate(conflicting),
        )
    assert exc_info.value.code == "idempotency_key_reuse"
    assert exc_info.value.existing_job_id == "nfimg_slice01"


def test_create_rejects_operation_identity_reuse(db: Session) -> None:
    create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(_create_payload()))
    with pytest.raises(CloudImageStateConflict) as exc_info:
        create_or_replay_job(
            db,
            CloudImageCreateRequestV1.model_validate(
                _create_payload(fingerprint="hmac-sha256:" + "d" * 64)
            ),
        )
    assert exc_info.value.code == "operation_identity_reuse"


def test_transition_commits_state_event_receipt_and_outbox_together(
    db: Session,
) -> None:
    created = _create_payload()
    create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(created))
    transitioned = transition_job(
        db,
        "nfimg_slice01",
        CloudImageTransitionRequestV1.model_validate(_transition_payload(created)),
    )
    assert transitioned.job.status == "planning"
    assert transitioned.row_version == 2
    assert db.query(CloudImageEvent).count() == 2
    assert db.query(CloudImageOutbox).count() == 2
    assert db.query(CloudImageOperationReceipt).count() == 2

    with pytest.raises(CloudImageStateConflict) as exc_info:
        transition_job(
            db,
            "nfimg_slice01",
            CloudImageTransitionRequestV1.model_validate({
            **_transition_payload(created),
            "operation_id": "nfop_stale_slice01",
            "operation_fingerprint": "hmac-sha256:" + "e" * 64,
            "event": {
                **_transition_payload(created)["event"],
                "event_id": "nfevt_stale_slice01",
            },
        }),
        )
    assert exc_info.value.code == "compare_and_set_conflict"
    assert db.query(CloudImageEvent).count() == 2
    assert db.query(CloudImageOutbox).count() == 2


@pytest.mark.parametrize(
    "failure_stage",
    [
        "after_create_job",
        "after_create_protected_request",
        "after_create_idempotency",
        "after_create_events_and_outbox",
        "after_create_receipt",
        "before_create_commit",
    ],
)
def test_failure_injection_rolls_back_every_create_record(
    db: Session, failure_stage: str
) -> None:
    request = CloudImageCreateRequestV1.model_validate(_create_payload())

    def fail(stage: str) -> None:
        if stage == failure_stage:
            raise RuntimeError("injected transaction failure")

    with pytest.raises(RuntimeError, match="injected transaction failure"):
        create_or_replay_job(db, request, failure_injector=fail)

    assert db.query(CloudImageJob).count() == 0
    assert db.query(CloudImageProtectedRequest).count() == 0
    assert db.query(CloudImageIdempotencyBinding).count() == 0
    assert db.query(CloudImageEvent).count() == 0
    assert db.query(CloudImageOutbox).count() == 0


@pytest.mark.parametrize(
    "failure_stage",
    [
        "after_transition_state",
        "after_transition_event_and_outbox",
        "after_transition_receipt",
        "before_transition_commit",
    ],
)
def test_transition_failure_injection_preserves_prior_state(
    db: Session, failure_stage: str
) -> None:
    created = _create_payload()
    create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(created))

    def fail(stage: str) -> None:
        if stage == failure_stage:
            raise RuntimeError("injected transition failure")

    with pytest.raises(RuntimeError, match="injected transition failure"):
        transition_job(
            db,
            "nfimg_slice01",
            CloudImageTransitionRequestV1.model_validate(_transition_payload(created)),
            failure_injector=fail,
        )
    db.expire_all()
    job = db.query(CloudImageJob).one()
    assert job.status == "queued"
    assert job.row_version == 1
    assert db.query(CloudImageEvent).count() == 1
    assert db.query(CloudImageOutbox).count() == 1
    assert db.query(CloudImageOperationReceipt).count() == 1


def test_reads_are_caller_scoped_and_retry_source_is_protected(
    db: Session,
) -> None:
    create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(_create_payload()))
    from app.services.cloud_image_state import CloudImageStateNotFound

    with pytest.raises(CloudImageStateNotFound):
        get_job(db, "nfimg_slice01", caller_identity="service:pressforge")
    visible = get_job(db, "nfimg_slice01", caller_identity="service:authorforge")
    assert visible.job.job_id == "nfimg_slice01"
    retry_source = get_retry_source(db, "nfimg_slice01")
    assert "prompt" not in retry_source.model_dump_json().lower()
    assert retry_source.protected_request.algorithm == "A256GCM"


def test_event_append_and_read_are_idempotent(db: Session) -> None:
    create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(_create_payload()))
    event_request = {
        "schema_version": "cloud_image_state_append_event.v1",
        "operation_id": "nfop_event_slice01",
        "operation_fingerprint": "hmac-sha256:" + "f" * 64,
        "expected_row_version": 1,
        "event": {
            "schema_version": "cloud_image_audit_event.v1",
            "event_id": "nfevt_control_slice01",
            "event_type": "cloud_image.control_checked",
            "caller_identity": "service:neuroforge",
            "app_id": "authorforge",
            "correlation_id": "corr_slice01",
            "job_id": "nfimg_slice01",
            "details": {"operation_id": "nfop_event_slice01"},
            "created_at": datetime.now(UTC).isoformat(),
        },
    }
    request = CloudImageAppendEventRequestV1.model_validate(event_request)
    appended = append_event(db, "nfimg_slice01", request)
    assert appended.row_version == 2
    replay = append_event(db, "nfimg_slice01", request)
    assert replay.replayed is True
    assert replay.row_version == 2
    events = list_events(db, "nfimg_slice01")
    assert len(events.events) == 2

    stale_payload = dict(event_request)
    stale_payload["operation_id"] = "nfop_event_stale_slice01"
    stale_payload["operation_fingerprint"] = "hmac-sha256:" + "1" * 64
    stale_payload["event"] = {
        **event_request["event"],
        "event_id": "nfevt_control_stale_slice01",
    }
    with pytest.raises(CloudImageStateConflict) as exc_info:
        append_event(
            db,
            "nfimg_slice01",
            CloudImageAppendEventRequestV1.model_validate(stale_payload),
        )
    assert exc_info.value.code == "compare_and_set_conflict"


@pytest.mark.parametrize(
    "failure_stage",
    [
        "after_append_event_and_outbox",
        "after_append_receipt",
        "before_event_commit",
    ],
)
def test_event_append_failure_rolls_back_version_and_evidence(
    db: Session, failure_stage: str
) -> None:
    create_or_replay_job(db, CloudImageCreateRequestV1.model_validate(_create_payload()))
    payload = {
        "schema_version": "cloud_image_state_append_event.v1",
        "operation_id": "nfop_event_rollback_slice01",
        "operation_fingerprint": "hmac-sha256:" + "2" * 64,
        "expected_row_version": 1,
        "event": {
            "schema_version": "cloud_image_audit_event.v1",
            "event_id": "nfevt_control_rollback_slice01",
            "event_type": "cloud_image.control_checked",
            "caller_identity": "service:neuroforge",
            "app_id": "authorforge",
            "correlation_id": "corr_slice01",
            "job_id": "nfimg_slice01",
            "details": {"operation_id": "nfop_event_rollback_slice01"},
            "created_at": datetime.now(UTC).isoformat(),
        },
    }

    def fail(stage: str) -> None:
        if stage == failure_stage:
            raise RuntimeError("injected event append failure")

    with pytest.raises(RuntimeError, match="injected event append failure"):
        append_event(
            db,
            "nfimg_slice01",
            CloudImageAppendEventRequestV1.model_validate(payload),
            failure_injector=fail,
        )

    db.expire_all()
    assert db.query(CloudImageJob).one().row_version == 1
    assert db.query(CloudImageEvent).count() == 1
    assert db.query(CloudImageOutbox).count() == 1
    assert db.query(CloudImageOperationReceipt).count() == 1


def test_routes_require_exact_neuroforge_service_and_scopes() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as wrong_subject:
        _require_neuroforge_scope(
            _auth("cloud-image:state:write", service_name="forge_command"),
            "cloud-image:state:write",
        )
    assert wrong_subject.value.detail["code"] == "neuroforge_subject_binding_mismatch"

    with pytest.raises(HTTPException) as wrong_scope:
        _require_neuroforge_scope(
            _auth("cloud-image:state:read"), "cloud-image:state:write"
        )
    assert wrong_scope.value.detail["code"] == "cloud_image_state_scope_required"


def test_route_functions_create_and_enforce_caller_scoped_read(db: Session) -> None:
    request = CloudImageCreateRequestV1.model_validate(_create_payload())
    created = create_cloud_image_job_state(
        request=request,
        _auth=_auth("cloud-image:state:write"),
        db=db,
    )
    assert created.created is True

    visible = read_cloud_image_job_state(
        job_id="nfimg_slice01",
        _auth=_auth("cloud-image:state:read"),
        db=db,
        caller_identity="service:authorforge",
    )
    assert visible.job.job_id == "nfimg_slice01"

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as hidden:
        read_cloud_image_job_state(
            job_id="nfimg_slice01",
            _auth=_auth("cloud-image:state:read"),
            db=db,
            caller_identity="service:pressforge",
        )
    assert hidden.value.status_code == 404
    assert hidden.value.detail["code"] == "cloud_image_job_not_found"


def test_plaintext_fields_are_rejected_at_the_contract_boundary() -> None:
    payload = _create_payload()
    payload["protected_request"]["prompt"] = "must never cross this boundary"
    with pytest.raises(ValidationError):
        CloudImageCreateRequestV1.model_validate(payload)
