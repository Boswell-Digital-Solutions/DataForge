from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.runtime_promotion.execution_handoff.contracts import (
    FailureReasonClass,
    VerificationObservedOutcome,
)
from app.runtime_promotion.execution_handoff.models import (
    RuntimePromotionExecutionRequest,
    RuntimePromotionExecutionStatus,
)
from app.runtime_promotion.execution_handoff.service import (
    VerificationResultCreate,
    create_verification_result,
)
from app.runtime_promotion.execution_handoff.status_service import (
    mark_execution_request_dead_lettered,
)
from app.runtime_promotion.execution_handoff.worker import (
    FIRST_LOCAL_RUNTIME_ACTION,
    claim_next_local_runtime_action_request,
    execute_claimed_local_runtime_action,
    run_one_local_runtime_action,
)


def _build_local_failure_pattern_request() -> dict:
    unique_suffix = uuid.uuid4().hex

    return {
        "envelope_type": "local_failure_pattern",
        "envelope_version": "v1",
        "fleet_member_id": "fleet-dev-001",
        "runtime_bundle_id": "forge-local-runtime",
        "runtime_bundle_version": "1.0.0",
        "service": "df_local_foundation",
        "dedupe_key": f"pytest-runtime-promotion-worker-{unique_suffix}",
        "observed_at": datetime.now(UTC).isoformat(),
        "payload": {
            "pattern_id": f"pattern-{unique_suffix}",
            "failure_pattern_type": "migration_failure",
            "frequency_window": "15m",
            "occurrence_count": 4,
            "severity": "high",
            "affected_contract_or_capability": "runtime_promotion_queue",
            "supporting_examples": [
                "migration_failed: Migration failed during startup"
            ],
        },
    }


def _ingest_and_get_candidate(
    client: TestClient,
    *,
    request_body: dict | None = None,
) -> tuple[str, str]:
    body = request_body or _build_local_failure_pattern_request()

    response = client.post(
        "/api/v1/runtime-promotion/receipts/local-failure-pattern",
        json=body,
    )
    assert response.status_code == 201, response.text

    ack = response.json()
    receipt_id = ack["receipt_id"]

    list_response = client.get("/api/v1/runtime-promotion/candidates")
    assert list_response.status_code == 200, list_response.text

    candidates = list_response.json()
    matching_candidates = [
        candidate for candidate in candidates if candidate["receipt_id"] == receipt_id
    ]
    assert len(matching_candidates) == 1, (
        "Expected exactly one candidate for the ingested receipt, "
        f"but found {len(matching_candidates)}"
    )

    candidate_id = matching_candidates[0]["candidate_id"]
    return receipt_id, candidate_id


def _approve_candidate(
    client: TestClient,
    candidate_id: str,
) -> dict:
    approve_response = client.post(
        f"/api/v1/runtime-promotion/candidates/{candidate_id}/approve",
        json={
            "reason": "Looks valid for bounded worker execution.",
            "operator_identity": "forgecommand",
        },
    )
    assert approve_response.status_code == 200, approve_response.text
    return approve_response.json()


def _get_candidate_detail(
    client: TestClient,
    candidate_id: str,
) -> dict:
    detail_response = client.get(
        f"/api/v1/runtime-promotion/candidates/{candidate_id}"
    )
    assert detail_response.status_code == 200, detail_response.text
    return detail_response.json()


def _create_approved_execution_request(
    client: TestClient,
) -> tuple[str, str]:
    _, candidate_id = _ingest_and_get_candidate(client)
    approve_payload = _approve_candidate(client, candidate_id)
    assert approve_payload["ok"] is True

    detail = _get_candidate_detail(client, candidate_id)
    execution_handoff = detail["execution_handoff"]
    assert execution_handoff is not None

    execution_request = execution_handoff["execution_request"]
    assert execution_request is not None
    assert execution_request["requested_action"] == FIRST_LOCAL_RUNTIME_ACTION

    return candidate_id, execution_request["execution_request_id"]


def _list_statuses(
    db: Session,
    execution_request_id: str,
) -> list[RuntimePromotionExecutionStatus]:
    return (
        db.query(RuntimePromotionExecutionStatus)
        .filter(
            RuntimePromotionExecutionStatus.execution_request_id == execution_request_id
        )
        .order_by(RuntimePromotionExecutionStatus.recorded_at.asc())
        .all()
    )


def test_claim_next_local_runtime_action_request_is_duplicate_safe(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    claimed_request = claim_next_local_runtime_action_request(db)
    assert claimed_request is not None
    assert claimed_request.execution_request_id == execution_request_id
    db.commit()

    second_claim = claim_next_local_runtime_action_request(db)
    assert second_claim is None
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "accepted"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == ["accepted"]
    assert (
        statuses[0].status_summary
        == "Execution request accepted by bounded local runtime lane."
    )


def test_claim_next_local_runtime_action_request_accepts_queued_request(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    request_row.request_status = "queued"
    db.add(request_row)
    db.commit()

    claimed_request = claim_next_local_runtime_action_request(db)
    assert claimed_request is not None
    assert claimed_request.execution_request_id == execution_request_id
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "accepted"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == ["accepted"]
    assert (
        statuses[0].status_summary
        == "Execution request accepted by bounded local runtime lane."
    )


def test_claim_next_local_runtime_action_request_does_not_claim_terminal_states(
    client: TestClient,
    db: Session,
) -> None:
    terminal_statuses = [
        "completed",
        "failed",
        "timed_out",
        "dead_lettered",
    ]

    for terminal_status in terminal_statuses:
        _, execution_request_id = _create_approved_execution_request(client)

        request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
        assert request_row is not None
        request_row.request_status = terminal_status
        db.add(request_row)
        db.commit()

        claimed_request = claim_next_local_runtime_action_request(db)
        assert claimed_request is None, (
            f"Expected no claim for terminal status {terminal_status}, "
            f"but got {claimed_request!r}"
        )
        db.commit()

        request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
        assert request_row is not None
        assert request_row.request_status == terminal_status

        statuses = _list_statuses(db, execution_request_id)
        assert statuses == []


def test_claim_next_local_runtime_action_request_allows_only_one_winner_across_sessions(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    SessionLocal = sessionmaker(bind=db.get_bind())
    session_a = SessionLocal()
    session_b = SessionLocal()

    try:
        claimed_a = claim_next_local_runtime_action_request(session_a)
        session_a.commit()

        claimed_b = claim_next_local_runtime_action_request(session_b)
        session_b.commit()

        winners = [claim for claim in (claimed_a, claimed_b) if claim is not None]
        assert len(winners) == 1
        assert winners[0].execution_request_id == execution_request_id

        request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
        assert request_row is not None
        assert request_row.request_status == "accepted"

        statuses = _list_statuses(db, execution_request_id)
        assert [status.execution_state for status in statuses] == ["accepted"]
        assert (
            statuses[0].status_summary
            == "Execution request accepted by bounded local runtime lane."
        )
    finally:
        session_a.close()
        session_b.close()


def test_claim_next_local_runtime_action_request_repeated_multi_session_contention_keeps_one_winner_per_round(
    client: TestClient,
    db: Session,
) -> None:
    SessionLocal = sessionmaker(bind=db.get_bind())

    for _ in range(5):
        _, execution_request_id = _create_approved_execution_request(client)

        sessions = [SessionLocal() for _ in range(4)]

        try:
            claims: list[RuntimePromotionExecutionRequest | None] = []

            for session in sessions:
                claimed = claim_next_local_runtime_action_request(session)
                session.commit()
                claims.append(claimed)

            winners = [claim for claim in claims if claim is not None]
            assert len(winners) == 1
            assert winners[0].execution_request_id == execution_request_id

            request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
            assert request_row is not None
            assert request_row.request_status == "accepted"

            statuses = _list_statuses(db, execution_request_id)
            assert [status.execution_state for status in statuses] == ["accepted"]
            assert (
                statuses[0].status_summary
                == "Execution request accepted by bounded local runtime lane."
            )
        finally:
            for session in sessions:
                session.close()


def test_run_one_local_runtime_action_completes_and_writes_durable_statuses(
    client: TestClient,
    db: Session,
) -> None:
    candidate_id, execution_request_id = _create_approved_execution_request(client)

    result = run_one_local_runtime_action(db)
    assert result is not None
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "completed"
    assert result.status_summary == "Bounded local runtime action completed successfully."
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "completed"

    worker_execution_result = request_row.bounded_parameters_json.get(
        "worker_execution_result"
    )
    assert worker_execution_result is not None
    assert worker_execution_result["worker_action"] == FIRST_LOCAL_RUNTIME_ACTION
    assert worker_execution_result["candidate_id"] == candidate_id
    assert worker_execution_result["issue_class"] == "migration_failure"
    assert worker_execution_result["service"] == "df_local_foundation"
    assert worker_execution_result["emitting_subsystem"] == "forge_local_runtime"
    assert worker_execution_result["result_class"] == "bounded_runtime_maintenance_marker"
    assert worker_execution_result["executed_at"]

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == [
        "accepted",
        "running",
        "completed",
    ]

    completed_status = statuses[-1]
    assert completed_status.status_summary == (
        "Bounded local runtime action completed successfully."
    )
    assert completed_status.failure_reason_class == "none"
    assert completed_status.completed_at is not None
    assert completed_status.artifact_refs_json == [
        f"worker_action:{FIRST_LOCAL_RUNTIME_ACTION}",
        f"candidate:{candidate_id}",
        "service:df_local_foundation",
        "issue_class:migration_failure",
        "side_effect:worker_execution_result_written",
    ]


def test_run_one_local_runtime_action_writes_real_low_risk_side_effect_marker(
    client: TestClient,
    db: Session,
) -> None:
    candidate_id, execution_request_id = _create_approved_execution_request(client)

    result = run_one_local_runtime_action(db)
    assert result is not None
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "completed"
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None

    bounded_parameters = request_row.bounded_parameters_json
    assert isinstance(bounded_parameters, dict)

    worker_execution_result = bounded_parameters.get("worker_execution_result")
    assert worker_execution_result is not None
    assert worker_execution_result["worker_action"] == FIRST_LOCAL_RUNTIME_ACTION
    assert worker_execution_result["candidate_id"] == candidate_id
    assert worker_execution_result["issue_class"] == "migration_failure"
    assert worker_execution_result["service"] == "df_local_foundation"
    assert worker_execution_result["emitting_subsystem"] == "forge_local_runtime"
    assert worker_execution_result["result_class"] == "bounded_runtime_maintenance_marker"
    assert worker_execution_result["executed_at"]

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == [
        "accepted",
        "running",
        "completed",
    ]


def test_execute_claimed_local_runtime_action_fails_closed_on_invalid_parameters(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    claimed_request = claim_next_local_runtime_action_request(db)
    assert claimed_request is not None
    assert claimed_request.execution_request_id == execution_request_id
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    request_row.bounded_parameters_json = {
        "candidate_id": request_row.candidate_id,
        "worker_action": FIRST_LOCAL_RUNTIME_ACTION,
    }
    db.add(request_row)
    db.commit()

    result = execute_claimed_local_runtime_action(
        db,
        execution_request_id=execution_request_id,
    )
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "failed"
    assert result.status_summary == "bounded_parameters_json.issue_class is required."
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "failed"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == [
        "accepted",
        "failed",
    ]

    failed_status = statuses[-1]
    assert failed_status.failure_reason_class == "invalid_request"
    assert failed_status.failed_at is not None
    assert failed_status.status_summary == (
        "bounded_parameters_json.issue_class is required."
    )


def test_execute_claimed_local_runtime_action_fails_closed_on_unsupported_subsystem(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    claimed_request = claim_next_local_runtime_action_request(db)
    assert claimed_request is not None
    assert claimed_request.execution_request_id == execution_request_id
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    request_row.target_subsystem = "unsupported_subsystem"
    db.add(request_row)
    db.commit()

    result = execute_claimed_local_runtime_action(
        db,
        execution_request_id=execution_request_id,
    )
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "failed"
    assert result.status_summary == "Unsupported target subsystem for bounded worker."
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "failed"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == [
        "accepted",
        "failed",
    ]

    failed_status = statuses[-1]
    assert failed_status.failure_reason_class == "invalid_request"
    assert failed_status.failed_at is not None
    assert failed_status.status_summary == (
        "Unsupported target subsystem for bounded worker."
    )


def test_execute_claimed_local_runtime_action_fails_closed_on_unsupported_requested_action(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    claimed_request = claim_next_local_runtime_action_request(db)
    assert claimed_request is not None
    assert claimed_request.execution_request_id == execution_request_id
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    request_row.requested_action = "unsupported_requested_action"
    db.add(request_row)
    db.commit()

    result = execute_claimed_local_runtime_action(
        db,
        execution_request_id=execution_request_id,
    )
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "failed"
    assert result.status_summary == "Unsupported requested_action for bounded worker."
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "failed"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == [
        "accepted",
        "failed",
    ]

    failed_status = statuses[-1]
    assert failed_status.failure_reason_class == "invalid_request"
    assert failed_status.failed_at is not None
    assert failed_status.status_summary == (
        "Unsupported requested_action for bounded worker."
    )


def test_execute_claimed_local_runtime_action_fails_closed_on_unacceptable_authorization_class(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    claimed_request = claim_next_local_runtime_action_request(db)
    assert claimed_request is not None
    assert claimed_request.execution_request_id == execution_request_id
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    request_row.authorization_class = "second_review_required"
    db.add(request_row)
    db.commit()

    result = execute_claimed_local_runtime_action(
        db,
        execution_request_id=execution_request_id,
    )
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "failed"
    assert result.status_summary == (
        "Authorization class is not acceptable for bounded worker execution."
    )
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "failed"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == [
        "accepted",
        "failed",
    ]

    failed_status = statuses[-1]
    assert failed_status.failure_reason_class == "policy_blocked"
    assert failed_status.failed_at is not None
    assert failed_status.status_summary == (
        "Authorization class is not acceptable for bounded worker execution."
    )


def test_mark_execution_request_dead_lettered_writes_terminal_dead_letter_state(
    client: TestClient,
    db: Session,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    dead_lettered_status = mark_execution_request_dead_lettered(
        db,
        execution_request_id=execution_request_id,
        status_summary="Request preserved for operator review after unrecoverable validation failure.",
        failure_reason_class=FailureReasonClass.INVALID_REQUEST,
        operator_visible_notes="Dead-lettered intentionally for explicit review.",
        artifact_refs=["dead_letter_reason:invalid_request"],
    )
    assert dead_lettered_status.execution_request_id == execution_request_id
    assert dead_lettered_status.execution_state == "dead_lettered"
    assert dead_lettered_status.status_summary == (
        "Request preserved for operator review after unrecoverable validation failure."
    )
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "dead_lettered"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == ["dead_lettered"]

    latest_status = statuses[-1]
    assert latest_status.failure_reason_class == "invalid_request"
    assert latest_status.status_summary == (
        "Request preserved for operator review after unrecoverable validation failure."
    )
    assert latest_status.operator_visible_notes == (
        "Dead-lettered intentionally for explicit review."
    )
    assert latest_status.artifact_refs_json == [
        "dead_letter_reason:invalid_request"
    ]


def test_run_one_local_runtime_action_times_out_and_writes_terminal_timeout(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    _, execution_request_id = _create_approved_execution_request(client)

    monotonic_values = iter([0.0, 999.0])
    monkeypatch.setattr(
        "app.runtime_promotion.execution_handoff.worker.monotonic",
        lambda: next(monotonic_values),
    )

    result = run_one_local_runtime_action(db, timeout_seconds=30.0)
    assert result is not None
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "timed_out"
    assert result.status_summary == "Execution exceeded bounded timeout budget."
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None
    assert request_row.request_status == "timed_out"

    statuses = _list_statuses(db, execution_request_id)
    assert [status.execution_state for status in statuses] == [
        "accepted",
        "running",
        "timed_out",
    ]

    timed_out_status = statuses[-1]
    assert timed_out_status.failure_reason_class == "timeout"
    assert timed_out_status.timed_out_at is not None
    assert timed_out_status.status_summary == (
        "Execution exceeded bounded timeout budget."
    )


def test_run_one_local_runtime_action_completed_then_verification_reads_back_separately(
    client: TestClient,
    db: Session,
) -> None:
    candidate_id, execution_request_id = _create_approved_execution_request(client)

    result = run_one_local_runtime_action(db)
    assert result is not None
    assert result.execution_request_id == execution_request_id
    assert result.terminal_state == "completed"
    assert result.status_summary == "Bounded local runtime action completed successfully."
    db.commit()

    detail_after_execution = _get_candidate_detail(client, candidate_id)
    execution_handoff = detail_after_execution["execution_handoff"]
    assert execution_handoff is not None

    latest_execution_status = execution_handoff["latest_execution_status"]
    assert latest_execution_status is not None
    assert latest_execution_status["execution_state"] == "completed"
    assert latest_execution_status["status_summary"] == (
        "Bounded local runtime action completed successfully."
    )

    latest_execution_summary = execution_handoff["latest_execution_summary"]
    assert latest_execution_summary["execution_request_id"] == execution_request_id
    assert latest_execution_summary["latest_execution_state"] == "completed"
    assert latest_execution_summary["latest_status_summary"] == (
        "Bounded local runtime action completed successfully."
    )
    assert latest_execution_summary["latest_failure_reason_class"] == "none"
    assert latest_execution_summary["last_status_recorded_at"] is not None

    latest_verification = execution_handoff["latest_verification"]
    assert latest_verification is None

    latest_verification_summary = execution_handoff["latest_verification_summary"]
    assert latest_verification_summary["execution_request_id"] == execution_request_id
    assert latest_verification_summary["observed_outcome"] is None
    assert latest_verification_summary["verification_summary"] is None
    assert latest_verification_summary["regression_detected"] is False
    assert latest_verification_summary["rollback_recommended"] is False
    assert latest_verification_summary["verified_at"] is None

    create_verification_result(
        db,
        VerificationResultCreate(
            execution_request_id=execution_request_id,
            candidate_id=candidate_id,
            verification_scope="local_runtime_action",
            expected_gain="Reduce migration-failure handoff risk.",
            observed_outcome=VerificationObservedOutcome.VERIFIED_SUCCESS,
            verification_summary="Verification passed. Expected improvement was observed.",
            regression_detected=False,
            rollback_recommended=False,
            evidence_refs=["verification:evidence:worker-closeout:001"],
            emitting_subsystem="dataforge",
        ),
    )
    db.commit()

    detail_after_verification = _get_candidate_detail(client, candidate_id)
    execution_handoff = detail_after_verification["execution_handoff"]
    assert execution_handoff is not None

    latest_execution_summary = execution_handoff["latest_execution_summary"]
    assert latest_execution_summary["execution_request_id"] == execution_request_id
    assert latest_execution_summary["latest_execution_state"] == "completed"
    assert latest_execution_summary["latest_status_summary"] == (
        "Bounded local runtime action completed successfully."
    )

    latest_verification = execution_handoff["latest_verification"]
    assert latest_verification is not None
    assert latest_verification["execution_request_id"] == execution_request_id
    assert latest_verification["candidate_id"] == candidate_id
    assert latest_verification["verification_scope"] == "local_runtime_action"
    assert (
        latest_verification["expected_gain"]
        == "Reduce migration-failure handoff risk."
    )
    assert latest_verification["observed_outcome"] == "verified_success"
    assert latest_verification["verification_summary"] == (
        "Verification passed. Expected improvement was observed."
    )
    assert latest_verification["regression_detected"] is False
    assert latest_verification["rollback_recommended"] is False
    assert latest_verification["evidence_refs"] == [
        "verification:evidence:worker-closeout:001"
    ]

    latest_verification_summary = execution_handoff["latest_verification_summary"]
    assert latest_verification_summary["execution_request_id"] == execution_request_id
    assert latest_verification_summary["observed_outcome"] == "verified_success"
    assert latest_verification_summary["verification_summary"] == (
        "Verification passed. Expected improvement was observed."
    )
    assert latest_verification_summary["regression_detected"] is False
    assert latest_verification_summary["rollback_recommended"] is False
    assert latest_verification_summary["verified_at"] is not None

    assert (
        latest_execution_summary["latest_execution_state"]
        != latest_verification_summary["observed_outcome"]
    )