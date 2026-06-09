"""Route tests for the DataForge model-outcome receipt store (in-memory sqlite harness)."""
from fastapi.testclient import TestClient


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
