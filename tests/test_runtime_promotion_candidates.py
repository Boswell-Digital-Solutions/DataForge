from __future__ import annotations

from datetime import UTC, datetime
import uuid

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.usefixtures("forge_command_candidate_key", "receipt_producer_key")
PRODUCER_HEADERS = {"Authorization": "Bearer producer-key"}

def _build_local_failure_pattern_request() -> dict:
    unique_suffix = uuid.uuid4().hex

    return {
        "envelope_type": "local_failure_pattern",
        "envelope_version": "v1",
        "fleet_member_id": "fleet-dev-001",
        "runtime_bundle_id": "forge-local-runtime",
        "runtime_bundle_version": "1.0.0",
        "service": "df_local_foundation",
        "dedupe_key": f"pytest-runtime-promotion-{unique_suffix}",
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
        headers=PRODUCER_HEADERS,
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
            "reason": "Looks valid for governed handoff.",
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


def test_runtime_promotion_ingest_materializes_candidate_and_dedupes(
    client: TestClient,
) -> None:
    request_body = _build_local_failure_pattern_request()

    first_response = client.post(
        "/api/v1/runtime-promotion/receipts/local-failure-pattern",
        json=request_body,
        headers=PRODUCER_HEADERS,
    )
    assert first_response.status_code == 201, first_response.text

    first_ack = first_response.json()
    assert first_ack["status"] == "accepted"
    assert first_ack["envelope_type"] == "local_failure_pattern"
    assert first_ack["envelope_version"] == "v1"

    receipt_id = first_ack["receipt_id"]
    assert receipt_id.startswith("rpr_")

    second_response = client.post(
        "/api/v1/runtime-promotion/receipts/local-failure-pattern",
        json=request_body,
        headers=PRODUCER_HEADERS,
    )
    assert second_response.status_code == 201, second_response.text

    second_ack = second_response.json()
    assert second_ack["receipt_id"] == receipt_id
    assert second_ack["status"] == "accepted"

    list_response = client.get("/api/v1/runtime-promotion/candidates")
    assert list_response.status_code == 200, list_response.text

    candidates = list_response.json()
    matching_candidates = [
        candidate for candidate in candidates if candidate["receipt_id"] == receipt_id
    ]

    assert len(matching_candidates) == 1, (
        "Expected exactly one candidate for the deduped receipt, "
        f"but found {len(matching_candidates)}"
    )

    candidate = matching_candidates[0]
    assert candidate["candidate_id"].startswith("rpc_")
    assert candidate["candidate_type"] == "runtime_improvement_recommendation"
    assert candidate["source_envelope_type"] == "local_failure_pattern"
    assert candidate["service"] == "df_local_foundation"
    assert candidate["fleet_member_id"] == "fleet-dev-001"
    assert candidate["issue_class"] == "migration_failure"
    assert candidate["severity"] == "high"
    assert candidate["status"] == "review_ready"

    detail = _get_candidate_detail(client, candidate["candidate_id"])
    assert detail["candidate_id"] == candidate["candidate_id"]
    assert detail["receipt_id"] == receipt_id
    assert detail["evidence"]["receipt_id"] == receipt_id
    assert detail["evidence"]["dedupe_key"] == request_body["dedupe_key"]
    assert detail["evidence"]["frequency_window"] == "15m"
    assert detail["evidence"]["occurrence_count"] == 4
    assert (
        detail["evidence"]["affected_contract_or_capability"]
        == "runtime_promotion_queue"
    )
    assert detail["source_payload"]["failure_pattern_type"] == "migration_failure"
    assert detail["source_payload"]["severity"] == "high"
    assert detail["execution_handoff"] is None


def test_runtime_promotion_candidate_approve_creates_execution_handoff(
    client: TestClient,
) -> None:
    receipt_id, candidate_id = _ingest_and_get_candidate(client)

    pre_detail = _get_candidate_detail(client, candidate_id)
    assert pre_detail["candidate_id"] == candidate_id
    assert pre_detail["receipt_id"] == receipt_id
    assert pre_detail["execution_handoff"] is None

    approve_payload = _approve_candidate(client, candidate_id)
    assert approve_payload["ok"] is True
    assert approve_payload["candidate_id"] == candidate_id
    assert approve_payload["status"] == "approved"
    assert "Execution handoff" in approve_payload["message"]

    detail = _get_candidate_detail(client, candidate_id)
    assert detail["candidate_id"] == candidate_id
    assert detail["status"] == "approved"
    assert len(detail["decision_history"]) >= 1

    latest_decision = detail["decision_history"][0]
    assert latest_decision["candidate_id"] == candidate_id
    assert latest_decision["new_status"] == "approved"
    assert latest_decision["operator_identity"] == "forgecommand"
    assert latest_decision["operator_note"] == "Looks valid for governed handoff."

    execution_handoff = detail["execution_handoff"]
    assert execution_handoff is not None
    assert execution_handoff["handoff_exists"] is True
    assert execution_handoff["handoff_status"] == "handoff_eligible"
    assert execution_handoff["decision_artifact_id"]
    assert execution_handoff["trace_id"]
    assert execution_handoff["root_decision_artifact_id"]
    assert execution_handoff["lineage_step"] == 0
    assert execution_handoff["emitting_subsystem"] == "dataforge"

    execution_request = execution_handoff["execution_request"]
    assert execution_request is not None
    assert execution_request["candidate_id"] == candidate_id
    assert (
        execution_request["decision_artifact_id"]
        == execution_handoff["decision_artifact_id"]
    )
    assert execution_request["trace_id"] == execution_handoff["trace_id"]
    assert (
        execution_request["root_decision_artifact_id"]
        == execution_handoff["root_decision_artifact_id"]
    )
    assert (
        execution_request["parent_artifact_id"]
        == execution_handoff["decision_artifact_id"]
    )
    assert execution_request["lineage_step"] == 1
    assert execution_request["emitting_subsystem"] == "dataforge"
    assert execution_request["target_lane"] == "local_runtime_action"
    assert execution_request["target_subsystem"] == "forge_local_runtime"
    assert execution_request["request_status"] == "created"

    latest_execution_status = execution_handoff["latest_execution_status"]
    assert latest_execution_status is None

    latest_execution_summary = execution_handoff["latest_execution_summary"]
    assert (
        latest_execution_summary["execution_request_id"]
        == execution_request["execution_request_id"]
    )
    assert latest_execution_summary["latest_execution_state"] is None
    assert latest_execution_summary["latest_status_summary"] is None
    assert latest_execution_summary["latest_failure_reason_class"] is None
    assert latest_execution_summary["last_status_recorded_at"] is None

    latest_verification = execution_handoff["latest_verification"]
    assert latest_verification is None

    latest_verification_summary = execution_handoff["latest_verification_summary"]
    assert (
        latest_verification_summary["execution_request_id"]
        == execution_request["execution_request_id"]
    )
    assert latest_verification_summary["observed_outcome"] is None
    assert latest_verification_summary["verification_summary"] is None
    assert latest_verification_summary["regression_detected"] is False
    assert latest_verification_summary["rollback_recommended"] is False
    assert latest_verification_summary["verified_at"] is None


def test_runtime_promotion_candidate_reject_does_not_create_execution_handoff(
    client: TestClient,
) -> None:
    _, candidate_id = _ingest_and_get_candidate(client)

    reject_response = client.post(
        f"/api/v1/runtime-promotion/candidates/{candidate_id}/reject",
        json={
            "reason": "Not appropriate for approval.",
            "operator_identity": "forgecommand",
        },
    )
    assert reject_response.status_code == 200, reject_response.text

    reject_payload = reject_response.json()
    assert reject_payload["ok"] is True
    assert reject_payload["candidate_id"] == candidate_id
    assert reject_payload["status"] == "rejected"

    detail = _get_candidate_detail(client, candidate_id)
    assert detail["candidate_id"] == candidate_id
    assert detail["status"] == "rejected"
    assert len(detail["decision_history"]) >= 1
    assert detail["decision_history"][0]["new_status"] == "rejected"
    assert detail["execution_handoff"] is None


def test_runtime_promotion_candidate_detail_shows_verification_separate_from_execution(
    client: TestClient,
    db,
) -> None:
    from app.runtime_promotion.execution_handoff.contracts import (
        ExecutionState,
        VerificationObservedOutcome,
    )
    from app.runtime_promotion.execution_handoff.models import (
        RuntimePromotionExecutionRequest,
    )
    from app.runtime_promotion.execution_handoff.service import (
        VerificationResultCreate,
        create_verification_result,
    )
    from app.runtime_promotion.execution_handoff.status_service import (
        ExecutionStatusCreate,
        append_execution_status,
    )

    _, candidate_id = _ingest_and_get_candidate(client)

    approve_payload = _approve_candidate(client, candidate_id)
    assert approve_payload["ok"] is True

    detail_after_approve = _get_candidate_detail(client, candidate_id)
    execution_handoff = detail_after_approve["execution_handoff"]
    assert execution_handoff is not None

    execution_request = execution_handoff["execution_request"]
    assert execution_request is not None
    execution_request_id = execution_request["execution_request_id"]

    append_execution_status(
        db,
        ExecutionStatusCreate(
            execution_request_id=execution_request_id,
            execution_state=ExecutionState.COMPLETED,
            status_summary="Execution completed successfully.",
            completed_at=datetime.now(UTC),
            emitting_subsystem="forge_local_runtime",
        ),
    )
    db.commit()

    request_row = db.get(RuntimePromotionExecutionRequest, execution_request_id)
    assert request_row is not None

    bounded_parameters = dict(request_row.bounded_parameters_json or {})
    bounded_parameters["worker_execution_result"] = {
        "worker_action": "process_local_failure_pattern",
        "candidate_id": candidate_id,
        "issue_class": "migration_failure",
        "service": "df_local_foundation",
        "executed_at": datetime.now(UTC).isoformat(),
        "emitting_subsystem": "forge_local_runtime",
        "result_class": "bounded_runtime_maintenance_marker",
        "maintenance_action_class": "runtime_metadata_writeback",
        "target_capability": "runtime_promotion_execution_request",
        "precondition_summary": (
            "Approved local runtime action request was claimed and validated."
        ),
        "postcondition_summary": (
            "Execution request now carries a richer bounded maintenance evidence payload."
        ),
        "verification_hint": (
            "Confirm worker_execution_result is present and candidate-detail readback exposes it."
        ),
        "operator_summary": (
            "Bounded local runtime action recorded maintenance evidence for operator review."
        ),
    }
    request_row.bounded_parameters_json = bounded_parameters
    db.add(request_row)
    db.commit()

    detail_after_execution = _get_candidate_detail(client, candidate_id)
    execution_handoff = detail_after_execution["execution_handoff"]
    assert execution_handoff is not None

    latest_execution_status = execution_handoff["latest_execution_status"]
    assert latest_execution_status is not None
    assert latest_execution_status["execution_state"] == "completed"
    assert latest_execution_status["status_summary"] == "Execution completed successfully."

    latest_execution_summary = execution_handoff["latest_execution_summary"]
    assert latest_execution_summary["latest_execution_state"] == "completed"
    assert (
        latest_execution_summary["latest_status_summary"]
        == "Execution completed successfully."
    )

    latest_verification = execution_handoff["latest_verification"]
    assert latest_verification is None

    latest_verification_summary = execution_handoff["latest_verification_summary"]
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
            evidence_refs=["verification:evidence:001"],
            emitting_subsystem="dataforge",
        ),
    )
    db.commit()

    detail_after_verification = _get_candidate_detail(client, candidate_id)
    execution_handoff = detail_after_verification["execution_handoff"]
    assert execution_handoff is not None

    latest_execution_summary = execution_handoff["latest_execution_summary"]
    assert latest_execution_summary["latest_execution_state"] == "completed"
    assert (
        latest_execution_summary["latest_status_summary"]
        == "Execution completed successfully."
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
        "Verification passed. Expected improvement was observed. "
        "Verification basis: worker_execution_result present; "
        "maintenance_action_class=runtime_metadata_writeback; "
        "target_capability=runtime_promotion_execution_request."
    )
    assert latest_verification["regression_detected"] is False
    assert latest_verification["rollback_recommended"] is False
    assert latest_verification["evidence_refs"] == [
        "verification:evidence:001",
        "verification:evidence:worker_execution_result_present",
        "verification:evidence:maintenance_action_class:runtime_metadata_writeback",
        "verification:evidence:target_capability:runtime_promotion_execution_request",
    ]
    assert latest_verification["trace_id"] == execution_request["trace_id"]
    assert (
        latest_verification["root_decision_artifact_id"]
        == execution_request["root_decision_artifact_id"]
    )
    assert latest_verification["parent_artifact_id"] == execution_request_id

    latest_verification_summary = execution_handoff["latest_verification_summary"]
    assert latest_verification_summary["execution_request_id"] == execution_request_id
    assert latest_verification_summary["observed_outcome"] == "verified_success"
    assert latest_verification_summary["verification_summary"] == (
        "Verification passed. Expected improvement was observed. "
        "Verification basis: worker_execution_result present; "
        "maintenance_action_class=runtime_metadata_writeback; "
        "target_capability=runtime_promotion_execution_request."
    )
    assert latest_verification_summary["regression_detected"] is False
    assert latest_verification_summary["rollback_recommended"] is False
    assert latest_verification_summary["verified_at"] is not None

    assert latest_execution_summary["latest_execution_state"] == "completed"
    assert latest_verification_summary["observed_outcome"] == "verified_success"
    assert (
        latest_execution_summary["latest_execution_state"]
        != latest_verification_summary["observed_outcome"]
    )

# --- Authentication: FC-RT-20260930-012 -------------------------------------------------


@pytest.fixture
def anonymous(client: TestClient) -> TestClient:
    client.headers.pop("Authorization", None)
    return client


CANDIDATES = "/api/v1/runtime-promotion/candidates"


def test_candidate_routes_refuse_a_request_with_no_credential(anonymous: TestClient) -> None:
    assert anonymous.get(CANDIDATES).status_code == 401
    assert anonymous.get(f"{CANDIDATES}/rpc_x").status_code == 401
    body = {"reason": "no key"}
    assert anonymous.post(f"{CANDIDATES}/rpc_x/approve", json=body).status_code == 401
    assert anonymous.post(f"{CANDIDATES}/rpc_x/reject", json=body).status_code == 401


def test_candidate_routes_refuse_an_unknown_key(client: TestClient) -> None:
    client.headers["Authorization"] = "Bearer not-a-key"
    assert client.get(CANDIDATES).status_code == 401
    assert client.post(f"{CANDIDATES}/rpc_x/approve", json={}).status_code == 401


def test_a_read_only_key_cannot_decide(
    client: TestClient, forge_command_candidate_key: dict
) -> None:
    forge_command_candidate_key["scopes"] = ["runtime-promotion:candidates:read"]
    assert client.get(CANDIDATES).status_code == 200
    denied = client.post(f"{CANDIDATES}/rpc_x/approve", json={"reason": "x"})
    assert denied.status_code == 403
    assert denied.json()["detail"]["scope"] == "runtime-promotion:candidates:decide"


def test_a_key_for_another_service_is_refused(
    client: TestClient, forge_command_candidate_key: dict
) -> None:
    forge_command_candidate_key["service_name"] = "forge-agents"
    assert client.get(CANDIDATES).status_code == 403
    assert client.post(f"{CANDIDATES}/rpc_x/reject", json={}).status_code == 403


def test_a_refused_decision_changes_nothing(
    client: TestClient, forge_command_candidate_key: dict
) -> None:
    _, candidate_id = _ingest_and_get_candidate(client)
    forge_command_candidate_key["scopes"] = ["runtime-promotion:candidates:read"]
    assert client.post(f"{CANDIDATES}/{candidate_id}/approve", json={}).status_code == 403
    detail = _get_candidate_detail(client, candidate_id)
    assert detail["status"] != "approved"
    assert detail["decision_history"] == []


def test_the_recorded_identity_comes_from_the_key_not_the_body(client: TestClient) -> None:
    _, candidate_id = _ingest_and_get_candidate(client)
    response = client.post(
        f"{CANDIDATES}/{candidate_id}/reject",
        json={"reason": "spoof check", "operator_identity": "someone-else"},
    )
    assert response.status_code == 200, response.text
    history = _get_candidate_detail(client, candidate_id)["decision_history"]
    assert history[0]["operator_identity"] == "forgecommand"


def test_receipt_ingest_without_a_key_is_refused_and_writes_nothing(client: TestClient) -> None:
    body = _build_local_failure_pattern_request()
    response = client.post(
        "/api/v1/runtime-promotion/receipts/local-failure-pattern",
        json=body,
        headers={"Authorization": ""},
    )
    assert response.status_code == 401
    listing = client.get("/api/v1/runtime-promotion/candidates").json()
    assert all(c["dedupe_key"] != body["dedupe_key"] for c in listing if "dedupe_key" in c)


def test_receipt_ingest_with_the_forge_command_key_is_refused(client: TestClient) -> None:
    # The candidate key is a different service. It must not be able to create receipts.
    response = client.post(
        "/api/v1/runtime-promotion/receipts/local-failure-pattern",
        json=_build_local_failure_pattern_request(),
    )
    assert response.status_code == 401


def test_receipt_ingest_needs_the_write_scope(
    client: TestClient, receipt_producer_key: dict
) -> None:
    receipt_producer_key["scopes"] = ["runtime-promotion:receipts:read"]
    response = client.post(
        "/api/v1/runtime-promotion/receipts/local-failure-pattern",
        json=_build_local_failure_pattern_request(),
        headers=PRODUCER_HEADERS,
    )
    assert response.status_code == 403


def test_receipt_ingest_needs_the_local_runtime_service(
    client: TestClient, receipt_producer_key: dict
) -> None:
    receipt_producer_key["service_name"] = "forgecommand"
    response = client.post(
        "/api/v1/runtime-promotion/receipts/local-failure-pattern",
        json=_build_local_failure_pattern_request(),
        headers=PRODUCER_HEADERS,
    )
    assert response.status_code == 403
