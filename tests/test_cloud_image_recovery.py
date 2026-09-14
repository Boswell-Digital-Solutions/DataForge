"""Focused lease, fencing, attempt, and rebuildable-outbox tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.cloud_image_state_models import (
    CloudImageControlReceipt,
    CloudImageLease,
    CloudImageOutbox,
    CloudImageStageAttempt,
)
from app.models.cloud_image_state_schemas import (
    CloudImageCreateRequestV1,
    CloudImageLeaseClaimRequestV1,
    CloudImageLeaseExpireRequestV1,
    CloudImageLeaseGuardV1,
    CloudImageLeaseReleaseRequestV1,
    CloudImageLeaseRenewRequestV1,
    CloudImageOutboxClaimRequestV1,
    CloudImageOutboxSettleRequestV1,
    CloudImageStageAttemptCompleteRequestV1,
    CloudImageStageAttemptStartRequestV1,
    CloudImageWorkerTransitionRequestV1,
)
from app.services.cloud_image_state import (
    CloudImageStateConflict,
    claim_lease,
    claim_outbox,
    complete_stage_attempt,
    create_or_replay_job,
    expire_lease,
    get_job,
    list_stage_attempts,
    release_lease,
    renew_lease,
    settle_outbox,
    start_stage_attempt,
    transition_job_with_lease,
)


NOW = datetime(2026, 9, 13, 18, 0, tzinfo=UTC)


def _fingerprint(char: str) -> str:
    return "hmac-sha256:" + char * 64


def _create_request() -> CloudImageCreateRequestV1:
    job = {
        "schema_version": "cloud_image_job_record.v1",
        "job_id": "nfimg_slice02",
        "request_id": "nfreq_slice02",
        "correlation_id": "corr_slice02",
        "idempotency_key": "idem_slice02",
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
        "deadline_at": (NOW + timedelta(hours=1)).isoformat(),
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        "terminal_at": None,
    }
    return CloudImageCreateRequestV1.model_validate(
        {
            "schema_version": "cloud_image_state_create.v1",
            "operation_id": "nfop_create_slice02",
            "operation_fingerprint": _fingerprint("a"),
            "job": job,
            "protected_request": {
                "schema_version": "cloud_image_protected_request.v1",
                "algorithm": "A256GCM",
                "key_ref": "kms://neuroforge/cloud-image/test",
                "nonce_b64": "MTIzNDU2Nzg5MDEy",
                "aad_b64": "bmZpbWdfc2xpY2UwMg==",
                "ciphertext": "Y2lwaGVydGV4dC13aXRoLWFlcy1nY20tdGFn",
                "ciphertext_sha256": "sha256:" + "b" * 64,
                "semantic_request_fingerprint": _fingerprint("a"),
                "created_at": NOW.isoformat(),
                "retention_until": (NOW + timedelta(days=30)).isoformat(),
            },
            "events": [
                {
                    "schema_version": "cloud_image_audit_event.v1",
                    "event_id": "nfevt_requested_slice02",
                    "event_type": "cloud_image.job_requested",
                    "caller_identity": "service:authorforge",
                    "app_id": "authorforge",
                    "correlation_id": "corr_slice02",
                    "job_id": "nfimg_slice02",
                    "details": {},
                    "created_at": NOW.isoformat(),
                }
            ],
            "retry_source_job_id": None,
        }
    )


def _claim(
    db: Session,
    *,
    worker_id: str,
    operation_id: str,
    char: str,
    at: datetime,
    stage: str = "planning",
    lease_seconds: int = 10,
):
    request = CloudImageLeaseClaimRequestV1.model_validate(
        {
            "schema_version": "cloud_image_lease_claim.v1",
            "operation_id": operation_id,
            "operation_fingerprint": _fingerprint(char),
            "worker_id": worker_id,
            "stage": stage,
            "lease_seconds": lease_seconds,
        }
    )
    return claim_lease(db, "nfimg_slice02", request, evaluated_at=at), request


def _guard(lease) -> CloudImageLeaseGuardV1:
    return CloudImageLeaseGuardV1(
        worker_id=lease.worker_id,
        stage=lease.stage,
        fencing_token=lease.fencing_token,
    )


def test_lease_replay_renew_release_and_monotonic_takeover(db: Session) -> None:
    create_or_replay_job(db, _create_request())
    first, request = _claim(
        db,
        worker_id="worker-a",
        operation_id="nfop_claim_a",
        char="c",
        at=NOW,
    )
    replay = claim_lease(db, "nfimg_slice02", request, evaluated_at=NOW)
    assert first.fencing_token == 1
    assert replay.fencing_token == 1
    assert replay.replayed is True

    renewed = renew_lease(
        db,
        "nfimg_slice02",
        CloudImageLeaseRenewRequestV1(
            schema_version="cloud_image_lease_renew.v1",
            operation_id="nfop_renew_a",
            operation_fingerprint=_fingerprint("d"),
            lease=_guard(first),
            lease_seconds=20,
        ),
        evaluated_at=NOW + timedelta(seconds=1),
    )
    assert renewed.expires_at == NOW + timedelta(seconds=21)

    released = release_lease(
        db,
        "nfimg_slice02",
        CloudImageLeaseReleaseRequestV1(
            schema_version="cloud_image_lease_release.v1",
            operation_id="nfop_release_a",
            operation_fingerprint=_fingerprint("e"),
            lease=_guard(first),
            reason_code="stage_complete",
        ),
        evaluated_at=NOW + timedelta(seconds=2),
    )
    assert released.release_reason == "stage_complete"

    second, _ = _claim(
        db,
        worker_id="worker-b",
        operation_id="nfop_claim_b",
        char="f",
        at=NOW + timedelta(seconds=3),
    )
    assert second.fencing_token == 2
    assert second.worker_id == "worker-b"


def test_expired_worker_is_fenced_from_transition_and_takeover(db: Session) -> None:
    created = create_or_replay_job(db, _create_request())
    first, _ = _claim(
        db,
        worker_id="worker-a",
        operation_id="nfop_claim_expiring",
        char="1",
        at=NOW,
        lease_seconds=5,
    )
    expired = expire_lease(
        db,
        "nfimg_slice02",
        CloudImageLeaseExpireRequestV1(
            schema_version="cloud_image_lease_expire.v1",
            operation_id="nfop_expire_a",
            operation_fingerprint=_fingerprint("2"),
            lease=_guard(first),
            reason_code="lease_timeout",
        ),
        evaluated_at=NOW + timedelta(seconds=6),
    )
    assert expired.release_reason == "lease_timeout"
    second, _ = _claim(
        db,
        worker_id="worker-b",
        operation_id="nfop_claim_takeover",
        char="3",
        at=NOW + timedelta(seconds=7),
    )
    assert second.fencing_token == 2

    updated = created.job.model_copy(
        update={"status": "planning", "updated_at": NOW + timedelta(seconds=7)}
    )
    stale = CloudImageWorkerTransitionRequestV1.model_validate(
        {
            "schema_version": "cloud_image_worker_transition.v1",
            "operation_id": "nfop_stale_transition",
            "operation_fingerprint": _fingerprint("4"),
            "expected_row_version": created.row_version,
            "expected_status": "queued",
            "lease": _guard(first).model_dump(mode="json"),
            "attempt_id": "nfattempt_stale",
            "updated_job": updated.model_dump(mode="json"),
            "event": {
                "schema_version": "cloud_image_audit_event.v1",
                "event_id": "nfevt_stale_transition",
                "event_type": "cloud_image.job_transitioned",
                "caller_identity": "service:neuroforge",
                "app_id": "authorforge",
                "correlation_id": "corr_slice02",
                "job_id": "nfimg_slice02",
                "details": {"from_status": "queued", "to_status": "planning"},
                "created_at": (NOW + timedelta(seconds=7)).isoformat(),
            },
        }
    )
    with pytest.raises(CloudImageStateConflict) as exc_info:
        transition_job_with_lease(
            db,
            "nfimg_slice02",
            stale,
            evaluated_at=NOW + timedelta(seconds=7),
        )
    assert exc_info.value.code == "lease_fence_conflict"


def test_stage_attempt_requires_lease_and_reconciles_unknown_outcome(
    db: Session,
) -> None:
    create_or_replay_job(db, _create_request())
    lease, _ = _claim(
        db,
        worker_id="worker-a",
        operation_id="nfop_claim_attempt",
        char="5",
        at=NOW,
    )
    with pytest.raises(CloudImageStateConflict) as out_of_order:
        start_stage_attempt(
            db,
            "nfimg_slice02",
            CloudImageStageAttemptStartRequestV1(
                schema_version="cloud_image_stage_attempt_start.v1",
                operation_id="nfop_attempt_out_of_order",
                operation_fingerprint=_fingerprint("0"),
                attempt_id="nfattempt_planning_2_early",
                stage="planning",
                attempt_number=2,
                lease=_guard(lease),
            ),
            evaluated_at=NOW,
        )
    assert out_of_order.value.code == "attempt_out_of_order"

    start_request = CloudImageStageAttemptStartRequestV1(
        schema_version="cloud_image_stage_attempt_start.v1",
        operation_id="nfop_attempt_1_start",
        operation_fingerprint=_fingerprint("6"),
        attempt_id="nfattempt_planning_1",
        stage="planning",
        attempt_number=1,
        lease=_guard(lease),
    )
    started = start_stage_attempt(db, "nfimg_slice02", start_request, evaluated_at=NOW)
    replay = start_stage_attempt(db, "nfimg_slice02", start_request, evaluated_at=NOW)
    assert started.status == "started"
    assert replay.replayed is True

    unknown = complete_stage_attempt(
        db,
        "nfimg_slice02",
        started.attempt_id,
        CloudImageStageAttemptCompleteRequestV1(
            schema_version="cloud_image_stage_attempt_complete.v1",
            operation_id="nfop_attempt_1_unknown",
            operation_fingerprint=_fingerprint("7"),
            lease=_guard(lease),
            status="reconciliation_required",
            retry_class="unknown_outcome",
            failure_code="provider_outcome_unknown",
        ),
        evaluated_at=NOW + timedelta(seconds=1),
    )
    assert unknown.status == "reconciliation_required"

    reconciled = complete_stage_attempt(
        db,
        "nfimg_slice02",
        started.attempt_id,
        CloudImageStageAttemptCompleteRequestV1(
            schema_version="cloud_image_stage_attempt_complete.v1",
            operation_id="nfop_attempt_1_reconciled",
            operation_fingerprint=_fingerprint("8"),
            lease=_guard(lease),
            status="succeeded",
            retry_class="none",
            result_digest="sha256:" + "9" * 64,
        ),
        evaluated_at=NOW + timedelta(seconds=2),
    )
    assert reconciled.status == "succeeded"
    assert list_stage_attempts(db, "nfimg_slice02").attempts == [reconciled]
    with pytest.raises(CloudImageStateConflict) as uncommitted:
        start_stage_attempt(
            db,
            "nfimg_slice02",
            CloudImageStageAttemptStartRequestV1(
                schema_version="cloud_image_stage_attempt_start.v1",
                operation_id="nfop_attempt_before_transition",
                operation_fingerprint=_fingerprint("f"),
                attempt_id="nfattempt_planning_2",
                stage="planning",
                attempt_number=2,
                lease=_guard(lease),
            ),
            evaluated_at=NOW + timedelta(seconds=3),
        )
    assert uncommitted.value.code == "attempt_result_uncommitted"


def test_worker_transition_atomically_links_final_attempt(db: Session) -> None:
    created = create_or_replay_job(db, _create_request())
    lease, _ = _claim(
        db,
        worker_id="worker-a",
        operation_id="nfop_claim_link",
        char="a",
        at=NOW,
    )
    started = start_stage_attempt(
        db,
        "nfimg_slice02",
        CloudImageStageAttemptStartRequestV1(
            schema_version="cloud_image_stage_attempt_start.v1",
            operation_id="nfop_link_start",
            operation_fingerprint=_fingerprint("b"),
            attempt_id="nfattempt_link",
            stage="planning",
            attempt_number=1,
            lease=_guard(lease),
        ),
        evaluated_at=NOW,
    )
    complete_stage_attempt(
        db,
        "nfimg_slice02",
        started.attempt_id,
        CloudImageStageAttemptCompleteRequestV1(
            schema_version="cloud_image_stage_attempt_complete.v1",
            operation_id="nfop_link_complete",
            operation_fingerprint=_fingerprint("c"),
            lease=_guard(lease),
            status="succeeded",
            retry_class="none",
            result_digest="sha256:" + "d" * 64,
        ),
        evaluated_at=NOW + timedelta(seconds=1),
    )
    updated = created.job.model_copy(
        update={"status": "planning", "updated_at": NOW + timedelta(seconds=2)}
    )
    transition = CloudImageWorkerTransitionRequestV1.model_validate(
        {
            "schema_version": "cloud_image_worker_transition.v1",
            "operation_id": "nfop_link_transition",
            "operation_fingerprint": _fingerprint("e"),
            "expected_row_version": created.row_version,
            "expected_status": "queued",
            "lease": _guard(lease).model_dump(mode="json"),
            "attempt_id": started.attempt_id,
            "updated_job": updated.model_dump(mode="json"),
            "event": {
                "schema_version": "cloud_image_audit_event.v1",
                "event_id": "nfevt_link_transition",
                "event_type": "cloud_image.job_transitioned",
                "caller_identity": "service:neuroforge",
                "app_id": "authorforge",
                "correlation_id": "corr_slice02",
                "job_id": "nfimg_slice02",
                "details": {
                    "attempt_id": started.attempt_id,
                    "fencing_token": str(lease.fencing_token),
                    "from_status": "queued",
                    "stage": "planning",
                    "to_status": "planning",
                },
                "created_at": (NOW + timedelta(seconds=2)).isoformat(),
            },
        }
    )

    def fail_after_link(stage: str) -> None:
        if stage == "after_worker_attempt_link":
            raise RuntimeError("injected attempt link failure")

    with pytest.raises(RuntimeError, match="injected attempt link failure"):
        transition_job_with_lease(
            db,
            "nfimg_slice02",
            transition,
            evaluated_at=NOW + timedelta(seconds=2),
            failure_injector=fail_after_link,
        )
    assert get_job(db, "nfimg_slice02").job.status == "queued"
    after_rollback = list_stage_attempts(db, "nfimg_slice02").attempts[0]
    assert after_rollback.transitioned_to_status is None
    assert db.query(CloudImageOutbox).count() == 1

    committed = transition_job_with_lease(
        db,
        "nfimg_slice02",
        transition,
        evaluated_at=NOW + timedelta(seconds=2),
    )
    assert committed.job.status == "planning"
    linked = list_stage_attempts(db, "nfimg_slice02").attempts[0]
    assert linked.transitioned_to_status == "planning"
    assert linked.transitioned_row_version == committed.row_version
    assert linked.transitioned_at == NOW + timedelta(seconds=2)


def test_outbox_is_reclaimable_after_retry_and_ack_is_fenced(db: Session) -> None:
    create_or_replay_job(db, _create_request())
    claim_request = CloudImageOutboxClaimRequestV1(
        schema_version="cloud_image_outbox_claim.v1",
        operation_id="nfop_outbox_claim_a",
        operation_fingerprint=_fingerprint("a"),
        dispatcher_id="dispatcher-a",
        max_items=10,
        lease_seconds=10,
    )
    first = claim_outbox(db, claim_request, evaluated_at=NOW)
    replay = claim_outbox(db, claim_request, evaluated_at=NOW)
    assert len(first.items) == 1
    assert replay.replayed is True
    item = first.items[0]

    retried = settle_outbox(
        db,
        item.outbox_id,
        CloudImageOutboxSettleRequestV1(
            schema_version="cloud_image_outbox_settle.v1",
            operation_id="nfop_outbox_retry",
            operation_fingerprint=_fingerprint("b"),
            dispatcher_id="dispatcher-a",
            claim_token=item.claim_token,
            outcome="retry",
            error_code="broker_unavailable",
            retry_after_seconds=5,
        ),
        evaluated_at=NOW + timedelta(seconds=1),
    )
    assert retried.next_attempt_at == NOW + timedelta(seconds=6)
    assert (
        claim_outbox(
            db,
            CloudImageOutboxClaimRequestV1(
                schema_version="cloud_image_outbox_claim.v1",
                operation_id="nfop_outbox_claim_early",
                operation_fingerprint=_fingerprint("c"),
                dispatcher_id="dispatcher-b",
                max_items=10,
                lease_seconds=10,
            ),
            evaluated_at=NOW + timedelta(seconds=5),
        ).items
        == []
    )

    second = claim_outbox(
        db,
        CloudImageOutboxClaimRequestV1(
            schema_version="cloud_image_outbox_claim.v1",
            operation_id="nfop_outbox_claim_b",
            operation_fingerprint=_fingerprint("d"),
            dispatcher_id="dispatcher-b",
            max_items=10,
            lease_seconds=10,
        ),
        evaluated_at=NOW + timedelta(seconds=6),
    ).items[0]
    assert second.claim_token == item.claim_token + 1

    with pytest.raises(CloudImageStateConflict) as exc_info:
        settle_outbox(
            db,
            item.outbox_id,
            CloudImageOutboxSettleRequestV1(
                schema_version="cloud_image_outbox_settle.v1",
                operation_id="nfop_outbox_stale_ack",
                operation_fingerprint=_fingerprint("e"),
                dispatcher_id="dispatcher-a",
                claim_token=item.claim_token,
                outcome="published",
            ),
            evaluated_at=NOW + timedelta(seconds=7),
        )
    assert exc_info.value.code == "outbox_claim_conflict"

    published = settle_outbox(
        db,
        item.outbox_id,
        CloudImageOutboxSettleRequestV1(
            schema_version="cloud_image_outbox_settle.v1",
            operation_id="nfop_outbox_ack_b",
            operation_fingerprint=_fingerprint("f"),
            dispatcher_id="dispatcher-b",
            claim_token=second.claim_token,
            outcome="published",
        ),
        evaluated_at=NOW + timedelta(seconds=8),
    )
    assert published.published_at == NOW + timedelta(seconds=8)


@pytest.mark.parametrize(
    ("operation", "failure_stage", "model"),
    [
        ("claim", "after_lease_claim", CloudImageLease),
        ("attempt", "after_attempt_start", CloudImageStageAttempt),
        ("outbox", "after_outbox_claim", CloudImageControlReceipt),
    ],
)
def test_recovery_mutations_roll_back_atomically(
    db: Session, operation: str, failure_stage: str, model: type
) -> None:
    create_or_replay_job(db, _create_request())

    def fail(stage: str) -> None:
        if stage == failure_stage:
            raise RuntimeError("injected recovery failure")

    if operation == "claim":
        request = CloudImageLeaseClaimRequestV1(
            schema_version="cloud_image_lease_claim.v1",
            operation_id="nfop_claim_rollback",
            operation_fingerprint=_fingerprint("1"),
            worker_id="worker-a",
            stage="planning",
            lease_seconds=10,
        )
        with pytest.raises(RuntimeError, match="injected recovery failure"):
            claim_lease(db, "nfimg_slice02", request, failure_injector=fail)
        assert db.query(model).count() == 0
        return

    lease, _ = _claim(
        db,
        worker_id="worker-a",
        operation_id="nfop_claim_for_rollback",
        char="2",
        at=NOW,
    )
    if operation == "attempt":
        request = CloudImageStageAttemptStartRequestV1(
            schema_version="cloud_image_stage_attempt_start.v1",
            operation_id="nfop_attempt_rollback",
            operation_fingerprint=_fingerprint("3"),
            attempt_id="nfattempt_rollback",
            stage="planning",
            attempt_number=1,
            lease=_guard(lease),
        )
        with pytest.raises(RuntimeError, match="injected recovery failure"):
            start_stage_attempt(
                db,
                "nfimg_slice02",
                request,
                evaluated_at=NOW,
                failure_injector=fail,
            )
        assert db.query(model).count() == 0
        return

    before = db.query(CloudImageOutbox).one()
    with pytest.raises(RuntimeError, match="injected recovery failure"):
        claim_outbox(
            db,
            CloudImageOutboxClaimRequestV1(
                schema_version="cloud_image_outbox_claim.v1",
                operation_id="nfop_outbox_rollback",
                operation_fingerprint=_fingerprint("4"),
                dispatcher_id="dispatcher-a",
                max_items=10,
                lease_seconds=10,
            ),
            evaluated_at=NOW,
            failure_injector=fail,
        )
    db.refresh(before)
    assert before.claim_owner is None
    assert before.delivery_attempts == 0
