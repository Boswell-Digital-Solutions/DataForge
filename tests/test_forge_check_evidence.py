from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError
from forge_telemetry import load_forge_check_v1_bytes

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import (
    MAX_CHECK_EVIDENCE_RESPONSE_BYTES,
    ingest_forge_check_evidence,
    read_forge_check_evidence,
)
from app.auth import ApiKeyInfo
from app.main import app
from app.models.telemetry_models import (
    ForgeCheckResultV1Record,
    ForgeCheckRunReceiptV1Record,
)
from app.models.telemetry_schemas import ForgeCheckEvidenceSubmissionV1

ROOT = Path(__file__).parent.parent
CHECKS = ROOT / "observability" / "checks"


def _fixture(name: str) -> dict:
    raw = files("forge_telemetry").joinpath("contracts", name).read_bytes()
    return json.loads(raw)


def _evidence(
    *,
    tenant_ref: str | None = None,
    result_id: str | None = None,
    run_id: str | None = None,
    receipt_id: str | None = None,
) -> ForgeCheckEvidenceSubmissionV1:
    result = _fixture("forge_check_result.v1.debug_passed.valid.json")
    receipt = _fixture("forge_check_run_receipt.v1.debug_passed.valid.json")
    result_id = result_id or str(uuid4())
    run_id = run_id or str(uuid4())
    receipt_id = receipt_id or str(uuid4())
    result.update(result_id=result_id, run_id=run_id)
    receipt.update(
        receipt_id=receipt_id,
        result_id=result_id,
        run_id=run_id,
        evidence_refs=[result_id],
    )
    return ForgeCheckEvidenceSubmissionV1.model_validate(
        {
            "schema_version": "forge.dataforge.forge-check-evidence.v1",
            "environment": "test",
            "tenant_ref": tenant_ref,
            "result": result,
            "receipt": receipt,
        }
    )


def _auth(
    *,
    service_name: str,
    scope: str,
    environment: str = "test",
    tenant_ref: str | None = None,
) -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="cp4-key",
            key_prefix="cp4-key",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": service_name,
                "environment": environment,
                "tenant_ref": tenant_ref,
                "scopes": [scope],
            },
        ),
    )


def _writer(tenant_ref: str | None = None) -> AuthContext:
    return _auth(
        service_name="forgeagents",
        scope="telemetry:write:checks",
        tenant_ref=tenant_ref,
    )


def _reader(tenant_ref: str | None = None) -> AuthContext:
    return _auth(
        service_name="forge_command",
        scope="telemetry:read:checks",
        tenant_ref=tenant_ref,
    )


def _ingest(db, evidence: ForgeCheckEvidenceSubmissionV1, auth=None):
    response = Response()
    result = ingest_forge_check_evidence(
        evidence,
        response,
        db,
        auth or _writer(evidence.tenant_ref),
    )
    return result, response


def test_cp4_check_routes_are_mounted_without_vendor_routes() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/telemetry/checks/evidence" in paths
    assert "/api/v1/telemetry/checks/results" in paths
    assert not any("checkly" in path or "newrelic" in path for path in paths)


def test_dataforge_check_definitions_are_strict_source_controlled_and_safe() -> None:
    definitions = [
        load_forge_check_v1_bytes(path.read_bytes())[0]
        for path in sorted(CHECKS.glob("*.json"))
    ]
    assert {definition.check_id for definition in definitions} == {
        "bds.dataforge.readiness.debug",
        "bds.dataforge.auth_entitlement.debug",
        "bds.dataforge.canonical_read.debug",
    }
    for definition in definitions:
        assert definition.source.repository == "Boswell-Digital-Solutions/DataForge"
        assert definition.source.commit == ("b1cc9bd45398fb0abc3c7300c4559a717a5d84fb")
        assert (ROOT / definition.source.path).is_file()
        assert definition.evaluation_mode == "debug"
        assert definition.slo.included is False
        assert definition.safety.production_destructive is False
        assert definition.assertion.method in {"GET", "HEAD"}
        assert 100 <= definition.timeout_ms <= 30_000
        encoded = json.dumps(definition.model_dump()).lower()
        assert "authorization" not in encoded
        assert "api_key" not in encoded
        assert "checkly" not in encoded
        assert "newrelic" not in encoded


def test_ingest_persists_exact_debug_result_and_linked_receipt(db) -> None:
    evidence = _evidence()
    result, _response = _ingest(db, evidence)

    assert result.identity_outcome == "inserted"
    assert result.result_id == evidence.result.result_id
    assert result.receipt_id == evidence.receipt.receipt_id
    assert db.query(ForgeCheckResultV1Record).count() == 1
    assert db.query(ForgeCheckRunReceiptV1Record).count() == 1
    stored_result = db.query(ForgeCheckResultV1Record).one()
    stored_receipt = db.query(ForgeCheckRunReceiptV1Record).one()
    assert stored_result.slo_included is False
    assert stored_result.uptime_included is False
    assert stored_result.baseline_included is False
    assert stored_receipt.result_id == stored_result.result_id
    assert stored_receipt.slo_reason == "debug_excluded"
    assert stored_receipt.runner_service_name == "forgeagents"


def test_exact_replay_preserves_identity_and_sink_time(db) -> None:
    evidence = _evidence()
    first, _ = _ingest(db, evidence)
    second, response = _ingest(db, evidence)

    assert second.identity_outcome == "exact_replay"
    assert response.status_code == 200
    assert second.received_at == first.received_at
    assert second.result_digest == first.result_digest
    assert second.receipt_digest == first.receipt_digest
    assert db.query(ForgeCheckResultV1Record).count() == 1
    assert db.query(ForgeCheckRunReceiptV1Record).count() == 1


def test_result_and_receipt_identity_conflicts_roll_back_atomically(db) -> None:
    evidence = _evidence()
    _ingest(db, evidence)

    changed_result = evidence.model_dump(mode="json")
    changed_result["result"]["reason_code"] = "different_reason"
    with pytest.raises(HTTPException) as result_error:
        _ingest(db, ForgeCheckEvidenceSubmissionV1.model_validate(changed_result))
    assert result_error.value.status_code == 409
    assert result_error.value.detail == {"code": "check_result_identity_conflict"}

    changed_receipt = evidence.model_dump(mode="json")
    changed_receipt["receipt"]["runner"]["version"] = "cp4.changed"
    with pytest.raises(HTTPException) as receipt_error:
        _ingest(db, ForgeCheckEvidenceSubmissionV1.model_validate(changed_receipt))
    assert receipt_error.value.status_code == 409
    assert receipt_error.value.detail == {"code": "check_receipt_identity_conflict"}
    assert db.query(ForgeCheckResultV1Record).count() == 1
    assert db.query(ForgeCheckRunReceiptV1Record).count() == 1


def test_submission_rejects_unlinked_or_non_debug_evidence() -> None:
    payload = _evidence().model_dump(mode="json")
    payload["receipt"]["run_id"] = str(uuid4())
    with pytest.raises(ValidationError):
        ForgeCheckEvidenceSubmissionV1.model_validate(payload)

    payload = _evidence().model_dump(mode="json")
    payload["result"]["evaluation_mode"] = "slo"
    payload["result"]["slo"] = {
        "included": True,
        "uptime_included": True,
        "baseline_included": True,
    }
    payload["receipt"]["evaluation_mode"] = "slo"
    payload["receipt"]["slo"] = {
        "included": True,
        "uptime_included": True,
        "baseline_included": True,
        "reason": "slo_declared",
    }
    with pytest.raises(ValidationError):
        ForgeCheckEvidenceSubmissionV1.model_validate(payload)


@pytest.mark.parametrize(
    ("auth", "code"),
    (
        (
            _auth(service_name="forgeagents", scope="telemetry:write"),
            "forge_check_write_scope_required",
        ),
        (
            _auth(service_name="other", scope="telemetry:write:checks"),
            "telemetry_subject_binding_mismatch",
        ),
        (
            _auth(
                service_name="forgeagents",
                scope="telemetry:write:checks",
                environment="production",
            ),
            "telemetry_subject_binding_mismatch",
        ),
    ),
)
def test_ingest_requires_exact_forgeagents_scope_binding(db, auth, code) -> None:
    with pytest.raises(HTTPException) as error:
        _ingest(db, _evidence(), auth)
    assert error.value.status_code == 403
    assert error.value.detail == {"code": code}


def test_read_is_scope_bound_bounded_and_explicit_about_partial_state(db) -> None:
    for _ in range(3):
        _ingest(db, _evidence(tenant_ref="bds-internal"))
    _ingest(db, _evidence(tenant_ref="other"))

    result = read_forge_check_evidence(
        "test",
        "bds-internal",
        None,
        2,
        db,
        _reader("bds-internal"),
    )
    assert result.shared_state == "partial"
    assert len(result.items) == 2
    assert len(result.model_dump_json().encode("utf-8")) <= (
        MAX_CHECK_EVIDENCE_RESPONSE_BYTES
    )
    assert all(item.result.evaluation_mode == "debug" for item in result.items)
    assert all(item.receipt.slo.reason == "debug_excluded" for item in result.items)


def test_missing_read_and_exact_reader_scope_are_explicit(db) -> None:
    result = read_forge_check_evidence(
        "test",
        None,
        None,
        50,
        db,
        _reader(),
    )
    assert result.shared_state == "missing"
    assert result.items == []

    with pytest.raises(HTTPException) as error:
        read_forge_check_evidence(
            "test",
            None,
            None,
            50,
            db,
            _auth(service_name="forge_command", scope="telemetry:read"),
        )
    assert error.value.status_code == 403
    assert error.value.detail == {"code": "forge_check_read_scope_required"}


def test_check_write_and_read_kill_switches_fail_closed(monkeypatch, db) -> None:
    evidence = _evidence()
    monkeypatch.setenv("DATAFORGE_FORGE_CHECK_EVIDENCE_WRITE_ENABLED", "false")
    with pytest.raises(HTTPException) as write_error:
        _ingest(db, evidence)
    assert write_error.value.status_code == 503
    assert write_error.value.detail == {"code": "forge_check_evidence_write_disabled"}

    monkeypatch.setenv("DATAFORGE_FORGE_CHECK_EVIDENCE_READ_ENABLED", "false")
    with pytest.raises(HTTPException) as read_error:
        read_forge_check_evidence("test", None, None, 50, db, _reader())
    assert read_error.value.status_code == 503
    assert read_error.value.detail == {"code": "forge_check_evidence_read_disabled"}


def test_stored_payload_has_no_definition_credentials_or_vendor_binding(db) -> None:
    evidence = _evidence()
    _ingest(db, evidence)
    stored = deepcopy(db.query(ForgeCheckRunReceiptV1Record).one().payload)
    encoded = json.dumps(stored).lower()
    assert "authorization" not in encoded
    assert "api_key" not in encoded
    assert "checkly" not in encoded
    assert "newrelic" not in encoded
