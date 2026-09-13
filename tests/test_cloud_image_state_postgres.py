"""PostgreSQL-only concurrency proof for cloud-image compare-and-set writes."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
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
    CloudImageCreateRequestV1,
    CloudImageLeaseClaimRequestV1,
    CloudImageLeaseExpireRequestV1,
    CloudImageLeaseGuardV1,
    CloudImageOutboxClaimRequestV1,
    CloudImageTransitionRequestV1,
)
from app.services.cloud_image_state import (
    CloudImageStateConflict,
    claim_lease,
    claim_outbox,
    create_or_replay_job,
    expire_lease,
    transition_job,
)


POSTGRES_URL = os.getenv("CLOUD_IMAGE_TEST_POSTGRES_URL", "")
TABLES = [
    CloudImageJob.__table__,
    CloudImageProtectedRequest.__table__,
    CloudImageIdempotencyBinding.__table__,
    CloudImageOperationReceipt.__table__,
    CloudImageEvent.__table__,
    CloudImageOutbox.__table__,
    CloudImageLease.__table__,
    CloudImageStageAttempt.__table__,
    CloudImageControlReceipt.__table__,
]


def _drop_test_tables(engine) -> None:
    """Drop only this suite's tables without firing global metadata enum hooks."""

    with engine.begin() as connection:
        for table in reversed(TABLES):
            connection.exec_driver_sql(f'DROP TABLE IF EXISTS "{table.name}" CASCADE')


def _create_request() -> CloudImageCreateRequestV1:
    now = datetime.now(UTC).replace(microsecond=0)
    fingerprint = "hmac-sha256:" + "a" * 64
    return CloudImageCreateRequestV1.model_validate(
        {
            "schema_version": "cloud_image_state_create.v1",
            "operation_id": "nfop_pg_create",
            "operation_fingerprint": fingerprint,
            "job": {
                "schema_version": "cloud_image_job_record.v1",
                "job_id": "nfimg_pg_concurrency",
                "request_id": "nfreq_pg_concurrency",
                "correlation_id": "corr_pg_concurrency",
                "idempotency_key": "idem_pg_concurrency",
                "source_service": "authorforge",
                "caller_identity": "service:authorforge",
                "app_id": "authorforge",
                "use_case": "book_cover_concept",
                "provider_override": None,
                "policy_block_code": None,
                "status": "queued",
                "requested_count": 1,
                "accepted_final_count": 0,
                "candidate_count": 0,
                "replacement_round": 0,
                "max_replacement_rounds": 3,
                "max_total_candidates": 3,
                "max_cost_usd": "5.00",
                "fulfillment_limits_exhausted": False,
                "deadline_at": (now + timedelta(hours=1)).isoformat(),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "terminal_at": None,
            },
            "protected_request": {
                "schema_version": "cloud_image_protected_request.v1",
                "algorithm": "A256GCM",
                "key_ref": "kms://neuroforge/cloud-image/test",
                "nonce_b64": "MTIzNDU2Nzg5MDEy",
                "aad_b64": "bmZpbWdfcGdfY29uY3VycmVuY3k=",
                "ciphertext": "Y2lwaGVydGV4dC13aXRoLWFlcy1nY20tdGFn",
                "ciphertext_sha256": "sha256:" + "c" * 64,
                "semantic_request_fingerprint": fingerprint,
                "created_at": now.isoformat(),
                "retention_until": (now + timedelta(days=30)).isoformat(),
            },
            "events": [
                {
                    "schema_version": "cloud_image_audit_event.v1",
                    "event_id": "nfevt_pg_created",
                    "event_type": "cloud_image.job_requested",
                    "caller_identity": "service:authorforge",
                    "app_id": "authorforge",
                    "correlation_id": "corr_pg_concurrency",
                    "job_id": "nfimg_pg_concurrency",
                    "details": {},
                    "created_at": now.isoformat(),
                }
            ],
            "retry_source_job_id": None,
        }
    )


@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="set CLOUD_IMAGE_TEST_POSTGRES_URL for the PostgreSQL concurrency gate",
)
def test_competing_transitions_have_one_winner_and_one_explicit_conflict() -> None:
    engine = create_engine(POSTGRES_URL)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine, tables=TABLES)
    create_request = _create_request()
    try:
        with Session() as db:
            create_or_replay_job(db, create_request)

        start = Barrier(2)

        def compete(target: str, suffix: str) -> tuple[str, str]:
            payload = create_request.job.model_copy(
                update={
                    "status": target,
                    "updated_at": datetime.now(UTC),
                    "terminal_at": (
                        datetime.now(UTC) if target == "cancelled" else None
                    ),
                }
            )
            request = CloudImageTransitionRequestV1.model_validate(
                {
                    "schema_version": "cloud_image_state_transition.v1",
                    "operation_id": f"nfop_pg_{suffix}",
                    "operation_fingerprint": "hmac-sha256:" + suffix * 64,
                    "expected_row_version": 1,
                    "expected_status": "queued",
                    "updated_job": payload,
                    "event": {
                        "schema_version": "cloud_image_audit_event.v1",
                        "event_id": f"nfevt_pg_{suffix}",
                        "event_type": "cloud_image.job_transitioned",
                        "caller_identity": "service:neuroforge",
                        "app_id": "authorforge",
                        "correlation_id": "corr_pg_concurrency",
                        "job_id": "nfimg_pg_concurrency",
                        "details": {"from_status": "queued", "to_status": target},
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                }
            )
            start.wait()
            with Session() as db:
                try:
                    result = transition_job(db, "nfimg_pg_concurrency", request)
                    return ("winner", result.job.status)
                except CloudImageStateConflict as exc:
                    return ("conflict", exc.code)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda args: compete(*args),
                    [("planning", "b"), ("cancelled", "c")],
                )
            )

        assert sorted(result[0] for result in results) == ["conflict", "winner"]
        assert [result[1] for result in results if result[0] == "conflict"] == [
            "compare_and_set_conflict"
        ]
        with Session() as db:
            assert db.query(CloudImageEvent).count() == 2
            assert db.query(CloudImageOutbox).count() == 2
            assert db.query(CloudImageOperationReceipt).count() == 2
    finally:
        _drop_test_tables(engine)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="set CLOUD_IMAGE_TEST_POSTGRES_URL for the PostgreSQL concurrency gate",
)
def test_competing_lease_and_outbox_claims_have_single_winners() -> None:
    engine = create_engine(POSTGRES_URL)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine, tables=TABLES)
    create_request = _create_request()
    now = create_request.job.created_at
    try:
        with Session() as db:
            create_or_replay_job(db, create_request)

        lease_start = Barrier(2)

        def compete_for_lease(worker_id: str, suffix: str) -> tuple[str, int | str]:
            request = CloudImageLeaseClaimRequestV1(
                schema_version="cloud_image_lease_claim.v1",
                operation_id=f"nfop_pg_lease_{suffix}",
                operation_fingerprint="hmac-sha256:" + suffix * 64,
                worker_id=worker_id,
                stage="planning",
                lease_seconds=5,
            )
            lease_start.wait()
            with Session() as db:
                try:
                    result = claim_lease(
                        db,
                        create_request.job.job_id,
                        request,
                        evaluated_at=now,
                    )
                    return ("winner", result.fencing_token)
                except CloudImageStateConflict as exc:
                    return ("conflict", exc.code)

        with ThreadPoolExecutor(max_workers=2) as executor:
            lease_results = list(
                executor.map(
                    lambda args: compete_for_lease(*args),
                    [("worker-a", "d"), ("worker-b", "e")],
                )
            )
        assert sorted(result[0] for result in lease_results) == [
            "conflict",
            "winner",
        ]
        assert [result[1] for result in lease_results if result[0] == "winner"] == [1]
        assert [result[1] for result in lease_results if result[0] == "conflict"] == [
            "lease_held"
        ]

        with Session() as db:
            lease = db.query(CloudImageLease).one()
            guard = CloudImageLeaseGuardV1(
                worker_id=lease.worker_id,
                stage=lease.stage,
                fencing_token=lease.fencing_token,
            )
            expire_lease(
                db,
                create_request.job.job_id,
                CloudImageLeaseExpireRequestV1(
                    schema_version="cloud_image_lease_expire.v1",
                    operation_id="nfop_pg_lease_expire",
                    operation_fingerprint="hmac-sha256:" + "f" * 64,
                    lease=guard,
                    reason_code="lease_timeout",
                ),
                evaluated_at=now + timedelta(seconds=6),
            )
            takeover = claim_lease(
                db,
                create_request.job.job_id,
                CloudImageLeaseClaimRequestV1(
                    schema_version="cloud_image_lease_claim.v1",
                    operation_id="nfop_pg_lease_takeover",
                    operation_fingerprint="hmac-sha256:" + "0" * 64,
                    worker_id="worker-c",
                    stage="planning",
                    lease_seconds=5,
                ),
                evaluated_at=now + timedelta(seconds=7),
            )
            assert takeover.fencing_token == 2

        outbox_start = Barrier(2)

        def compete_for_outbox(dispatcher_id: str, suffix: str) -> int:
            request = CloudImageOutboxClaimRequestV1(
                schema_version="cloud_image_outbox_claim.v1",
                operation_id=f"nfop_pg_outbox_{suffix}",
                operation_fingerprint="hmac-sha256:" + suffix * 64,
                dispatcher_id=dispatcher_id,
                max_items=1,
                lease_seconds=5,
            )
            outbox_start.wait()
            with Session() as db:
                return len(claim_outbox(db, request, evaluated_at=now).items)

        with ThreadPoolExecutor(max_workers=2) as executor:
            outbox_results = list(
                executor.map(
                    lambda args: compete_for_outbox(*args),
                    [("dispatcher-a", "1"), ("dispatcher-b", "2")],
                )
            )
        assert sorted(outbox_results) == [0, 1]
    finally:
        _drop_test_tables(engine)
        engine.dispose()
