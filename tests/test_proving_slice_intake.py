"""Tests: proving-slice intake router.

Uses the shared TestClient / SQLite fixture from conftest.py.
validate_artifact is patched in most tests to isolate router logic from
contract-validation details (contract-core has its own test suite).
One end-to-end test submits a truly malformed artifact without patching
to verify the rejection path is wired correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# ── Register proving-slice ORM models with Base.metadata before create_all ───
# conftest.py calls Base.metadata.create_all() during the db fixture setup.
# These imports must happen at collection time (before fixtures run).
from app.models.proving_slice_models import PSCloudIntakeRecord, PSCloudReceipt  # noqa: F401

_CONTRACT_CORE = (
    Path(__file__).parent.parent.parent.parent.parent
    / "contracts"
    / "forge-contract-core"
)
if str(_CONTRACT_CORE) not in sys.path:
    sys.path.insert(0, str(_CONTRACT_CORE))

from forge_contract_core.validators.artifact import ArtifactValidationError

_VALIDATE_PATH = "app.api.proving_slice_router.validate_artifact"

INTAKE_URL = "/api/v1/proving-slice/intake"
RECEIPT_URL = "/api/v1/proving-slice/receipts/by-artifact"


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _valid_drift_artifact(**overrides: Any) -> dict:
    """Minimal valid source_drift_finding artifact body."""
    base = {
        "artifact_id": "a1b2c3d4-0001-0001-0001-000000000001",
        "artifact_family": "source_drift_finding",
        "artifact_version": 1,
        "produced_by_system": "dataforge-Local",
        "produced_by_component": "drift_detector",
        "source_scope": "local",
        "lineage_root_id": "a1b2c3d4-0001-0001-0001-000000000001",
        "parent_artifact_id": None,
        "trace_id": "trace-00000000-0001",
        "idempotency_key": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "created_at": "2026-04-04T10:00:00Z",
        "recorded_at": "2026-04-04T10:00:01Z",
        "sensitivity_class": "internal",
        "visibility_class": "internal",
        "promotion_class": "promotable",
        "validation_status": "valid",
        "signer_identity": "dataforge-Local/drift_detector@proving-slice-v1",
        "signature": "sha256:fixture-sig-placeholder",
        "payload": {
            "system_id": "forge-local",
            "drift_class": "schema_drift",
            "declared_truth_ref": "users:v1",
            "observed_truth_ref": "users:v2",
            "impact_scope": "local",
            "confidence": "high",
            "operator_summary": "Schema drift detected in users table.",
        },
    }
    base.update(overrides)
    return base


# ── Accepted path ─────────────────────────────────────────────────────────────

class TestIntakeAccepted:
    def test_returns_200_with_receipt(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        assert resp.status_code == 200

    def test_receipt_is_promotion_receipt_family(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        body = resp.json()
        assert body["artifact_family"] == "promotion_receipt"
        assert body["artifact_version"] == 1

    def test_intake_outcome_is_accepted(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        assert resp.json()["payload"]["intake_outcome"] == "accepted"

    def test_shared_record_ref_is_set(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        ref = resp.json()["payload"]["shared_record_ref"]
        assert ref is not None
        assert "source_drift_finding" in ref
        assert "shared" in ref

    def test_produced_by_system_is_dataforge(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        assert resp.json()["produced_by_system"] == "DataForge"

    def test_parent_artifact_id_is_submitted_artifact(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        assert resp.json()["parent_artifact_id"] == "a1b2c3d4-0001-0001-0001-000000000001"

    def test_intake_record_persisted(self, client: TestClient, db: Session):
        with patch(_VALIDATE_PATH):
            client.post(INTAKE_URL, json=_valid_drift_artifact())
        row = db.query(PSCloudIntakeRecord).filter_by(
            artifact_id="a1b2c3d4-0001-0001-0001-000000000001"
        ).first()
        assert row is not None
        assert row.intake_outcome == "accepted"

    def test_receipt_row_persisted(self, client: TestClient, db: Session):
        with patch(_VALIDATE_PATH):
            client.post(INTAKE_URL, json=_valid_drift_artifact())
        intake = db.query(PSCloudIntakeRecord).filter_by(
            artifact_id="a1b2c3d4-0001-0001-0001-000000000001"
        ).first()
        assert intake is not None
        receipt = db.query(PSCloudReceipt).filter_by(intake_id=intake.intake_id).first()
        assert receipt is not None
        assert receipt.intake_outcome == "accepted"


# ── Duplicate reconciliation ──────────────────────────────────────────────────

class TestIntakeDuplicate:
    def test_second_submit_returns_duplicate_reconciled(self, client: TestClient):
        artifact = _valid_drift_artifact()
        with patch(_VALIDATE_PATH):
            client.post(INTAKE_URL, json=artifact)
            resp = client.post(INTAKE_URL, json=artifact)
        assert resp.json()["payload"]["intake_outcome"] == "duplicate_reconciled"

    def test_duplicate_does_not_create_second_intake_record(
        self, client: TestClient, db: Session
    ):
        artifact = _valid_drift_artifact()
        with patch(_VALIDATE_PATH):
            client.post(INTAKE_URL, json=artifact)
            client.post(INTAKE_URL, json=artifact)
        count = (
            db.query(PSCloudIntakeRecord)
            .filter_by(idempotency_key=artifact["idempotency_key"])
            .count()
        )
        assert count == 1

    def test_duplicate_preserves_shared_record_ref(self, client: TestClient):
        artifact = _valid_drift_artifact()
        with patch(_VALIDATE_PATH):
            first = client.post(INTAKE_URL, json=artifact).json()
            second = client.post(INTAKE_URL, json=artifact).json()
        assert (
            first["payload"]["shared_record_ref"]
            == second["payload"]["shared_record_ref"]
        )


# ── Rejected path ─────────────────────────────────────────────────────────────

class TestIntakeRejected:
    def test_validation_failure_returns_rejected_receipt(self, client: TestClient):
        with patch(
            _VALIDATE_PATH,
            side_effect=ArtifactValidationError("missing field", cause="invalid_envelope"),
        ):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        assert resp.status_code == 200
        assert resp.json()["payload"]["intake_outcome"] == "rejected"

    def test_rejected_receipt_has_rejection_class(self, client: TestClient):
        with patch(
            _VALIDATE_PATH,
            side_effect=ArtifactValidationError("bad payload", cause="invalid_payload"),
        ):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        assert resp.json()["payload"]["rejection_class"] == "invalid_payload"

    def test_rejected_receipt_retry_allowed_is_false(self, client: TestClient):
        with patch(
            _VALIDATE_PATH,
            side_effect=ArtifactValidationError("bad", cause="invalid_envelope"),
        ):
            resp = client.post(INTAKE_URL, json=_valid_drift_artifact())
        assert resp.json()["payload"]["retry_allowed"] is False

    def test_rejected_intake_record_persisted(self, client: TestClient, db: Session):
        with patch(
            _VALIDATE_PATH,
            side_effect=ArtifactValidationError("bad", cause="invalid_envelope"),
        ):
            client.post(INTAKE_URL, json=_valid_drift_artifact())
        row = db.query(PSCloudIntakeRecord).filter_by(
            artifact_id="a1b2c3d4-0001-0001-0001-000000000001"
        ).first()
        assert row is not None
        assert row.intake_outcome == "rejected"
        assert row.rejection_class == "invalid_envelope"

    def test_malformed_artifact_without_patch_is_rejected(self, client: TestClient):
        """End-to-end: sends a structurally invalid artifact (wrong payload).
        validate_artifact is NOT patched — verifies the router rejection path fires."""
        artifact = _valid_drift_artifact()
        # Corrupt the payload so family validation fails
        artifact["payload"] = {"unexpected_field": "garbage"}
        resp = client.post(INTAKE_URL, json=artifact)
        assert resp.status_code == 200
        assert resp.json()["payload"]["intake_outcome"] == "rejected"


# ── Family gate ───────────────────────────────────────────────────────────────

class TestIntakeFamilyGate:
    def test_promotion_receipt_family_rejected_with_422(self, client: TestClient):
        artifact = _valid_drift_artifact(artifact_family="promotion_receipt")
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=artifact)
        assert resp.status_code == 422

    def test_unsupported_family_rejected_with_422(self, client: TestClient):
        artifact = _valid_drift_artifact(artifact_family="approval_artifact")
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=artifact)
        assert resp.status_code == 422

    def test_promotion_envelope_is_admitted(self, client: TestClient):
        artifact = _valid_drift_artifact(
            artifact_family="promotion_envelope",
            payload={
                "promoted_artifact_ref": "source_drift_finding:a1b2c3d4-0001-0001-0001-000000000001:v1",
                "promotion_reason": "Drift finding meets criteria.",
                "redaction_class": "none",
                "policy_check_result": "passed",
                "promotion_batch_id": "a1b2c3d4-0001-0001-0001-000000000001",
            },
        )
        with patch(_VALIDATE_PATH):
            resp = client.post(INTAKE_URL, json=artifact)
        assert resp.status_code == 200


# ── Receipt lookup ────────────────────────────────────────────────────────────

class TestReceiptLookup:
    def test_get_receipt_returns_200_after_intake(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            client.post(INTAKE_URL, json=_valid_drift_artifact())
        resp = client.get(f"{RECEIPT_URL}/a1b2c3d4-0001-0001-0001-000000000001")
        assert resp.status_code == 200

    def test_get_receipt_contains_artifact_id(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            client.post(INTAKE_URL, json=_valid_drift_artifact())
        body = client.get(
            f"{RECEIPT_URL}/a1b2c3d4-0001-0001-0001-000000000001"
        ).json()
        assert body["artifact_id"] == "a1b2c3d4-0001-0001-0001-000000000001"

    def test_get_receipt_has_promotion_receipt_family(self, client: TestClient):
        with patch(_VALIDATE_PATH):
            client.post(INTAKE_URL, json=_valid_drift_artifact())
        body = client.get(
            f"{RECEIPT_URL}/a1b2c3d4-0001-0001-0001-000000000001"
        ).json()
        assert body["receipt"]["artifact_family"] == "promotion_receipt"

    def test_get_receipt_unknown_artifact_returns_404(self, client: TestClient):
        resp = client.get(f"{RECEIPT_URL}/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
