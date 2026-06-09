"""Route tests for the DataForge model-outcome receipt store (in-memory sqlite harness)."""
import pytest
from fastapi.testclient import TestClient

from app.api.admin_keys_router import AuthContext, require_api_key
from app.main import app


@pytest.fixture(autouse=True)
def _service_auth():
    """Satisfy the service-auth dependency (P0-5) for these route tests."""
    app.dependency_overrides[require_api_key] = lambda: AuthContext(auth_mode="api_key")
    yield
    app.dependency_overrides.pop(require_api_key, None)


def _outcome(model="deepseek-chat", cell="code_fix:bugfix_logic:python:local", reward=0.6, stage="verified", bundle="ctxb_1"):
    return {
        "context_bundle_id": bundle, "model_id": model, "routing_cell": cell,
        "reward": reward, "stage": stage, "tier": "STANDARD",
        "kind": "bugfix_logic", "language": "python", "complexity": "local", "risk": "standard",
        "evidence": [{"tier": 1, "name": "pact_verify", "passed": True}],
    }


def test_store_then_list_for_replay(client: TestClient):
    r = client.post("/api/v1/model-outcomes", json=_outcome())
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "stored"

    listing = client.get("/api/v1/model-outcomes").json()
    assert listing["count"] == 1
    row = listing["items"][0]
    assert row["model_id"] == "deepseek-chat"
    assert row["reward"] == 0.6
    assert row["evidence"][0]["name"] == "pact_verify"


def test_idempotent_per_bundle_model_stage(client: TestClient):
    client.post("/api/v1/model-outcomes", json=_outcome())
    again = client.post("/api/v1/model-outcomes", json=_outcome())
    assert again.json()["status"] == "exists"
    assert client.get("/api/v1/model-outcomes").json()["count"] == 1  # not double-counted


def test_distinct_stages_and_models_are_separate_receipts(client: TestClient):
    client.post("/api/v1/model-outcomes", json=_outcome(stage="verified"))
    client.post("/api/v1/model-outcomes", json=_outcome(stage="accepted", reward=0.8))
    client.post("/api/v1/model-outcomes", json=_outcome(model="other"))
    assert client.get("/api/v1/model-outcomes").json()["count"] == 3


def test_filter_by_routing_cell_and_model(client: TestClient):
    client.post("/api/v1/model-outcomes", json=_outcome(model="a", cell="code_fix:hygiene:python:trivial"))
    client.post("/api/v1/model-outcomes", json=_outcome(model="b", cell="code_fix:bugfix_logic:python:local"))
    by_cell = client.get("/api/v1/model-outcomes", params={"routing_cell": "code_fix:hygiene:python:trivial"}).json()
    assert by_cell["count"] == 1 and by_cell["items"][0]["model_id"] == "a"
    by_model = client.get("/api/v1/model-outcomes", params={"model_id": "b"}).json()
    assert by_model["count"] == 1


def test_reward_bounds_validated(client: TestClient):
    bad = _outcome(reward=1.5)
    assert client.post("/api/v1/model-outcomes", json=bad).status_code == 422


def test_p0_5_unauthenticated_is_rejected(client: TestClient):
    # Drop the auth override -> no key -> 401 (fail-closed; no anonymous receipts)
    app.dependency_overrides.pop(require_api_key, None)
    assert client.post("/api/v1/model-outcomes", json=_outcome()).status_code == 401
    assert client.get("/api/v1/model-outcomes").status_code == 401


def test_p0_8_keyset_pagination_returns_all_rows_once(client: TestClient):
    for i in range(5):
        client.post("/api/v1/model-outcomes", json=_outcome(bundle=f"b{i}"))

    seen, cursor, pages = [], None, 0
    while True:
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        body = client.get("/api/v1/model-outcomes", params=params).json()
        seen.extend(r["outcome_id"] for r in body["items"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
        assert pages < 10  # guard against infinite loop

    assert len(seen) == 5
    assert len(set(seen)) == 5  # every receipt exactly once
    assert pages == 3           # 2 + 2 + 1
