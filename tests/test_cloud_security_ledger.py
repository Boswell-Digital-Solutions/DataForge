"""CSSA security ledger tests (authority plan §22; ForgeAgents Phase 3 gate).

Proves the DataForge side of the recorder gate: append-only immutability,
server-side hash verification, idempotent retry, cardinality law, and
monotonic anti-rollback counters.
"""

import hashlib
from typing import Any

from fastapi.testclient import TestClient

from app.utils.cssa_canonical_json import canonicalize_json

AUTH = {"Authorization": "Bearer test-service-token"}


def attach_hash(payload: dict[str, Any], hash_field: str) -> dict[str, Any]:
    body = {k: v for k, v in payload.items() if k != hash_field}
    digest = hashlib.sha256(canonicalize_json(body)).hexdigest()
    return {**payload, hash_field: f"sha256:{digest}"}


def decision(decision_id: str = "dec-1", attempt_id: str = "att-1", **extra: Any) -> dict[str, Any]:
    return attach_hash(
        {
            "schema_version": "cloud_security.decision.v1",
            "decision_id": decision_id,
            "attempt_id": attempt_id,
            "correlation_id": "cor-1",
            "decision": "allow",
            **extra,
        },
        "decision_hash",
    )


def authorization(
    authorization_id: str = "auth-1", attempt_id: str = "att-1", **extra: Any
) -> dict[str, Any]:
    return attach_hash(
        {
            "schema_version": "cloud_security.authorization.v1",
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "correlation_id": "cor-1",
            "single_use": True,
            **extra,
        },
        "authorization_hash",
    )


def outcome(
    outcome_id: str = "out-1",
    attempt_id: str = "att-1",
    execution_state: str = "completed",
    **extra: Any,
) -> dict[str, Any]:
    return attach_hash(
        {
            "schema_version": "cloud_security.outcome.v1",
            "outcome_id": outcome_id,
            "attempt_id": attempt_id,
            "correlation_id": "cor-1",
            "execution_state": execution_state,
            "cost": {"currency": "USD", "estimated": 0.012, "actual": 0.011},
            **extra,
        },
        "outcome_hash",
    )


class TestAppendAndReadBack:
    def test_append_then_read_back_hash_matches(self, client: TestClient):
        payload = decision()
        r = client.post("/api/v1/cloud-security/decisions", json={"payload": payload}, headers=AUTH)
        assert r.status_code == 201, r.text
        rb = client.get("/api/v1/cloud-security/decisions/dec-1", headers=AUTH)
        assert rb.status_code == 200
        assert rb.json()["payload"] == payload
        assert rb.json()["record_hash"] == payload["decision_hash"]

    def test_requires_bearer(self, client: TestClient):
        r = client.post("/api/v1/cloud-security/decisions", json={"payload": decision()})
        assert r.status_code == 401

    def test_wrong_schema_version_rejected(self, client: TestClient):
        bad = decision()
        bad["schema_version"] = "cloud_security.decision.v2"
        r = client.post("/api/v1/cloud-security/decisions", json={"payload": bad}, headers=AUTH)
        assert r.status_code == 422

    def test_tampered_hash_rejected(self, client: TestClient):
        bad = decision()
        bad["decision"] = "block"  # mutate after hashing
        r = client.post("/api/v1/cloud-security/decisions", json={"payload": bad}, headers=AUTH)
        assert r.status_code == 422
        assert "canonical payload" in r.json()["detail"]


class TestImmutabilityAndIdempotency:
    def test_idempotent_retry_returns_200(self, client: TestClient):
        payload = authorization()
        first = client.post(
            "/api/v1/cloud-security/authorizations", json={"payload": payload}, headers=AUTH
        )
        retry = client.post(
            "/api/v1/cloud-security/authorizations", json={"payload": payload}, headers=AUTH
        )
        assert first.status_code == 201
        assert retry.status_code == 200
        assert retry.json()["payload"] == payload

    def test_same_id_different_content_conflicts(self, client: TestClient):
        client.post(
            "/api/v1/cloud-security/decisions", json={"payload": decision()}, headers=AUTH
        )
        conflicting = decision(attempt_id="att-2", note="changed")
        r = client.post(
            "/api/v1/cloud-security/decisions", json={"payload": conflicting}, headers=AUTH
        )
        assert r.status_code == 409
        assert "different hash" in r.json()["detail"]

    def test_no_mutation_endpoints_exist(self, client: TestClient):
        client.post(
            "/api/v1/cloud-security/decisions", json={"payload": decision()}, headers=AUTH
        )
        assert client.put(
            "/api/v1/cloud-security/decisions/dec-1", json={}, headers=AUTH
        ).status_code == 405
        assert client.delete(
            "/api/v1/cloud-security/decisions/dec-1", headers=AUTH
        ).status_code == 405


class TestCardinalityLaw:
    def test_one_authorization_per_attempt(self, client: TestClient):
        client.post(
            "/api/v1/cloud-security/authorizations",
            json={"payload": authorization()},
            headers=AUTH,
        )
        second = authorization(authorization_id="auth-2")  # same attempt
        r = client.post(
            "/api/v1/cloud-security/authorizations", json={"payload": second}, headers=AUTH
        )
        assert r.status_code == 409
        assert "cardinality" in r.json()["detail"]

    def test_one_terminal_outcome_per_attempt(self, client: TestClient):
        ok = client.post(
            "/api/v1/cloud-security/outcomes", json={"payload": outcome()}, headers=AUTH
        )
        assert ok.status_code == 201
        second_terminal = outcome(outcome_id="out-2", execution_state="failed")
        r = client.post(
            "/api/v1/cloud-security/outcomes", json={"payload": second_terminal}, headers=AUTH
        )
        assert r.status_code == 409

    def test_started_outcome_does_not_block_terminal(self, client: TestClient):
        started = outcome(outcome_id="out-started", execution_state="started")
        terminal = outcome(outcome_id="out-terminal", execution_state="completed")
        assert (
            client.post(
                "/api/v1/cloud-security/outcomes", json={"payload": started}, headers=AUTH
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/cloud-security/outcomes", json={"payload": terminal}, headers=AUTH
            ).status_code
            == 201
        )


class TestAntiRollbackCounters:
    def test_unset_counter_reads_none(self, client: TestClient):
        r = client.get("/api/v1/cloud-security/counters/policy_bundle", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["high_water"] is None

    def test_monotonic_advance(self, client: TestClient):
        put = "/api/v1/cloud-security/counters/policy_bundle"
        assert client.put(put, json={"high_water": 5}, headers=AUTH).status_code == 200
        regress = client.put(put, json={"high_water": 4}, headers=AUTH)
        assert regress.status_code == 409
        assert "monotonic" in regress.json()["detail"]
        assert client.put(put, json={"high_water": 7}, headers=AUTH).json()["high_water"] == 7
