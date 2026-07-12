"""FMEM-02 — Forge Memory spine: authenticated, scoped, bitemporal, deletable.

Proves the plan's required agent-memory acceptance path against the real service
(episode → claim → fact → supersede → current/historical retrieval) plus the
FMEM-00 gaps now closed: authenticated writes, scope isolation, real deletion
with a receipt, and the secret fail-closed rule.
"""

from __future__ import annotations

import pytest

KEY = "0" * 64
TENANT = "bds"
SUBJECT = "repo:forge-memory"
PREDICATE = "contract_authority"


def _scope(tenant: str = TENANT) -> dict:
    return {"tenant_id": tenant, "user_id": None, "project_id": "forge", "repo_id": "forge-memory"}


def _envelope(family: str, artifact_id: str, payload: dict, sensitivity: str = "internal") -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_family": family,
        "artifact_version": 1,
        "produced_by_system": "forge-memory",
        "produced_by_component": "test",
        "source_scope": "shared",
        "lineage_root_id": artifact_id,
        "parent_artifact_id": None,
        "trace_id": "trace-test",
        "idempotency_key": KEY,
        "created_at": "2026-07-12T06:40:00Z",
        "recorded_at": "2026-07-12T06:40:01Z",
        "sensitivity_class": sensitivity,
        "visibility_class": "operator",
        "promotion_class": "local_only",
        "validation_status": "valid",
        "signer_identity": "forge-memory/test",
        "signature": "sha256:test",
        "payload": payload,
    }


def _episode(artifact_id: str, tenant: str = TENANT) -> dict:
    return _envelope("memory_episode", artifact_id, {
        "schema_version": "forge.memory_episode.v1",
        "episode_id": artifact_id,
        "run_ref": {"run_id": "run-1", "tool_call_id": "tc-1", "agent_id": "developer", "agent_archetype": "developer"},
        "producer": {"system": "ForgeAgents", "component": "dev"},
        "episode_type": "tool_call",
        "origin_class": "first_party",
        "occurred_at": "2026-07-12T06:39:58Z",
        "recorded_at": "2026-07-12T06:40:01Z",
        "scope": _scope(tenant),
        "content_summary": "read the registry",
        "source_refs": [{"ref": "dataforge-local://runs/run-1/tc-1", "ref_kind": "agent_tool_call", "content_hash": None}],
        "residency": "cloud_allowed",
        "sensitivity_class": "internal",
        "instruction_capability": "none",
        "quarantined": False,
        "grants_authority": False,
    })


def _claim(artifact_id: str, tenant: str = TENANT) -> dict:
    return _envelope("memory_claim", artifact_id, {
        "schema_version": "forge.memory_claim.v1",
        "claim_id": artifact_id,
        "derived_from_episode_refs": ["memory_episode:e1:v1"],
        "subject_entity_id": SUBJECT,
        "predicate": PREDICATE,
        "object": "forge_contract_core",
        "scope": _scope(tenant),
        "authority_class": "inferred",
        "trust_state": "quarantined",
        "verification_state": "unverified",
        "confidence": 0.6,
        "extractor": {"extractor_system": "NeuroForge", "extractor_version": "1.0.0", "model_ref": None},
        "lineage_independence": {"independent_source_count": 1, "self_corroboration_detected": False},
        "instruction_capability": "advisory",
    })


def _fact(memory_id: str, obj: str, valid_from: str, tenant: str = TENANT,
          supersedes: str | None = None, sensitivity: str = "internal") -> dict:
    return _envelope("memory_fact", memory_id, {
        "schema_version": "forge.memory_fact.v1",
        "memory_id": memory_id,
        "subject_entity_id": SUBJECT,
        "predicate": PREDICATE,
        "object": obj,
        "scope": _scope(tenant),
        "authority_class": "canonical",
        "trust_state": "trusted",
        "verification_state": "validated",
        "status": "active",
        "valid_from": valid_from,
        "valid_to": None,
        "observed_at": "2026-07-12T06:39:58Z",
        "recorded_at": valid_from,
        "source_refs": ["memory_claim:c1:v1"],
        "payload_hash": "sha256:" + "a" * 64,
        "supersedes_memory_id": supersedes,
        "promoted_from_claim_ref": "memory_claim:c1:v1",
        "sensitivity_class": sensitivity,
        "residency": "cloud_allowed",
        "retention_class": "standard",
    }, sensitivity=sensitivity)


@pytest.mark.integration
def test_write_requires_authentication(client):
    r = client.post("/api/v1/memory/episodes", json=_episode("e-auth"))
    assert r.status_code == 401


@pytest.mark.integration
def test_episode_claim_fact_write(client, auth_headers):
    assert client.post("/api/v1/memory/episodes", json=_episode("e1"), headers=auth_headers).status_code == 201
    assert client.post("/api/v1/memory/claims", json=_claim("c1"), headers=auth_headers).status_code == 201
    assert client.post("/api/v1/memory/facts", json=_fact("fa", "v_a", "2026-07-12T06:41:00Z"), headers=auth_headers).status_code == 201


@pytest.mark.integration
def test_promote_supersede_current_and_historical(client, auth_headers):
    t_a, t_b = "2026-07-12T06:41:00Z", "2026-07-12T08:00:00Z"
    client.post("/api/v1/memory/facts", json=_fact("fa", "value_a", t_a), headers=auth_headers)
    body = {"new_fact": _fact("fb", "value_b", t_b, supersedes="fa"), "effective_at": t_b}
    assert client.post("/api/v1/memory/facts/fa/supersede", json=body, headers=auth_headers).status_code == 200

    # Current → B
    cur = client.get(
        "/api/v1/memory/facts",
        params={"tenant_id": TENANT, "subject_entity_id": SUBJECT, "predicate": PREDICATE},
        headers=auth_headers,
    ).json()
    assert cur["count"] == 1
    assert cur["facts"][0]["payload"]["memory_id"] == "fb"
    assert cur["facts"][0]["payload"]["object"] == "value_b"

    # Historical (between t_a and t_b) → A
    hist = client.get(
        "/api/v1/memory/facts",
        params={"tenant_id": TENANT, "subject_entity_id": SUBJECT, "predicate": PREDICATE,
                "as_of": "2026-07-12T07:00:00Z"},
        headers=auth_headers,
    ).json()
    assert hist["count"] == 1
    assert hist["facts"][0]["payload"]["memory_id"] == "fa"
    assert hist["facts"][0]["payload"]["object"] == "value_a"


@pytest.mark.integration
def test_scope_isolation(client, auth_headers):
    client.post("/api/v1/memory/facts", json=_fact("fa", "value_a", "2026-07-12T06:41:00Z", tenant="tenant-a"), headers=auth_headers)
    # A caller scoped to a different tenant sees nothing.
    other = client.get(
        "/api/v1/memory/facts",
        params={"tenant_id": "tenant-b", "subject_entity_id": SUBJECT, "predicate": PREDICATE},
        headers=auth_headers,
    ).json()
    assert other["count"] == 0


@pytest.mark.integration
def test_delete_removes_eligibility_with_receipt(client, auth_headers):
    client.post("/api/v1/memory/facts", json=_fact("fa", "value_a", "2026-07-12T06:41:00Z"), headers=auth_headers)
    r = client.delete("/api/v1/memory/facts/fa", params={"tenant_id": TENANT, "reason": "test"}, headers=auth_headers)
    assert r.status_code == 200
    receipt = r.json()
    assert receipt["deleted"] is True
    assert receipt["target_id"] == "fa"
    # Gone from current retrieval.
    cur = client.get(
        "/api/v1/memory/facts",
        params={"tenant_id": TENANT, "subject_entity_id": SUBJECT, "predicate": PREDICATE},
        headers=auth_headers,
    ).json()
    assert cur["count"] == 0
    # Re-delete is a 404 (already gone).
    assert client.delete("/api/v1/memory/facts/fa", params={"tenant_id": TENANT}, headers=auth_headers).status_code == 404


@pytest.mark.integration
def test_secret_sensitivity_is_rejected(client, auth_headers):
    r = client.post(
        "/api/v1/memory/facts",
        json=_fact("fs", "value", "2026-07-12T06:41:00Z", sensitivity="secret_or_credential"),
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "secret_or_credential" in r.text
