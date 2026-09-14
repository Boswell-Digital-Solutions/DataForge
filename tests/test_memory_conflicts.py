"""memory_conflict.v1 storage (BDS-FMEM-OPCOURT-001). Proves the write path
DataForge needed before df_rf_ingest.py's verification_status could ever
resolve MemoryConflict.v1 to "verified" instead of "verification_unavailable".
"""

from __future__ import annotations

KEY = "0" * 64
TENANT = "bds"


def _envelope(artifact_id: str, payload: dict, sensitivity: str = "internal") -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_family": "memory_conflict",
        "artifact_version": 1,
        "produced_by_system": "forge-memory",
        "produced_by_component": "test",
        "source_scope": "shared",
        "lineage_root_id": artifact_id,
        "parent_artifact_id": None,
        "trace_id": "trace-test",
        "idempotency_key": KEY,
        "created_at": "2026-09-14T00:00:00Z",
        "recorded_at": "2026-09-14T00:00:01Z",
        "sensitivity_class": sensitivity,
        "visibility_class": "operator",
        "promotion_class": "local_only",
        "validation_status": "valid",
        "signer_identity": "forge-memory/test",
        "signature": "sha256:test",
        "payload": payload,
    }


def _truth_surface(obj: str, trust_state: str = "trusted") -> dict:
    return {
        "memory_id": f"memory:{obj}",
        "object": obj,
        "authority_class": "observed",
        "trust_state": trust_state,
        "verification_state": "corroborated",
        "valid_from": "2026-09-01T00:00:00Z",
        "valid_to": None,
        "source_refs": ["dataforge-local://runs/run-1"],
    }


def _conflict(
    conflict_id: str,
    *,
    conflict_type: str = "authority_conflict",
    operator_review_required: bool = True,
) -> dict:
    return {
        "schema_version": "forge.memory_conflict.v1",
        "conflict_id": conflict_id,
        "subject_entity_id": "repo:forge-memory",
        "predicate": "contract_authority",
        "scope": {"tenant_id": TENANT, "user_id": None, "project_id": "forge", "repo_id": "forge-memory"},
        "truth_surface_a": _truth_surface("value_a"),
        "truth_surface_b": _truth_surface("value_b", trust_state="disputed"),
        "conflict_type": conflict_type,
        "resolution_recommendation": "Prefer value_a (higher authority_class).",
        "operator_review_required": operator_review_required,
    }


def test_write_requires_authentication(client):
    conflict_id = "22222222-2222-4222-8222-222222222201"
    r = client.post(
        "/api/v1/memory/conflicts",
        json=_envelope(conflict_id, _conflict(conflict_id)),
    )
    assert r.status_code == 401


def test_write_conflict_stores_and_is_idempotent(client, auth_headers):
    conflict_id = "22222222-2222-4222-8222-222222222202"
    body = _envelope(conflict_id, _conflict(conflict_id))

    first = client.post("/api/v1/memory/conflicts", json=body, headers=auth_headers)
    assert first.status_code == 201
    assert first.json()["status"] == "stored"

    second = client.post("/api/v1/memory/conflicts", json=body, headers=auth_headers)
    assert second.status_code == 201
    assert second.json()["status"] == "refreshed"


def test_wrong_family_is_rejected(client, auth_headers):
    conflict_id = "22222222-2222-4222-8222-222222222203"
    body = _envelope(conflict_id, _conflict(conflict_id))
    body["artifact_family"] = "memory_fact"
    r = client.post("/api/v1/memory/conflicts", json=body, headers=auth_headers)
    assert r.status_code == 422


def test_stored_conflict_is_queryable_for_df_rf_verification(client, auth_headers, db):
    # This is the real path df_rf_ingest.py's _compute_verification_status
    # exercises: a caller stores a conflict via the real HTTP surface, then
    # a later evidence-link ingest looks it up by conflict_id.
    from app.models.memory_models import MemoryConflict

    conflict_id = "22222222-2222-4222-8222-222222222204"
    body = _envelope(conflict_id, _conflict(conflict_id))
    r = client.post("/api/v1/memory/conflicts", json=body, headers=auth_headers)
    assert r.status_code == 201

    row = db.query(MemoryConflict).filter(MemoryConflict.conflict_id == conflict_id).first()
    assert row is not None
    assert row.operator_review_required is True
    assert row.conflict_type == "authority_conflict"
