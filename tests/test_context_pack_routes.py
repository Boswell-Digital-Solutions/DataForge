"""Route tests for the cloud DataForge context-pack store.

Uses the shared TestClient / in-memory SQLite fixture from conftest.py. The
ContextPack model is imported in conftest so its table is created by
Base.metadata.create_all() during the db fixture setup.
"""

from fastapi.testclient import TestClient


def _pack():
    return {
        "context_pack_id": "ctxb_1122676813da3fb5",
        "bundle_hash": "1122676813da3fb5",
        "task_intent_id": "ti_codefix_abc",
        "primary": "def add(a, b):\n    return a + b\n",
        "supporting": ["def sub(a, b): ...", "# repo nav map"],
        "metadata": {"source_classes": ["active_scene", "accepted_lore_record"]},
    }


def test_store_then_fetch_returns_neuroforge_read_shape(client: TestClient):
    r = client.post("/df/rag/context-pack", json=_pack())
    assert r.status_code == 201, r.text
    assert r.json() == {"context_pack_id": "ctxb_1122676813da3fb5", "status": "stored"}

    g = client.get("/df/rag/context-pack/ctxb_1122676813da3fb5")
    assert g.status_code == 200, g.text
    body = g.json()
    # NeuroForge build_context reads exactly these three:
    assert body["primary"] == "def add(a, b):\n    return a + b\n"
    assert body["supporting"] == ["def sub(a, b): ...", "# repo nav map"]
    assert body["metadata"]["context_bundle_id"] == "ctxb_1122676813da3fb5"
    assert body["metadata"]["context_bundle_hash"] == "1122676813da3fb5"
    assert body["metadata"]["task_intent_id"] == "ti_codefix_abc"
    assert body["metadata"]["served_from"] == "precomputed_pact_packet"


def test_store_is_idempotent_refresh_on_same_id(client: TestClient):
    client.post("/df/rag/context-pack", json=_pack())
    again = client.post("/df/rag/context-pack", json=_pack())
    assert again.status_code == 201
    assert again.json()["status"] == "refreshed"


def test_fetch_missing_pack_is_404(client: TestClient):
    assert client.get("/df/rag/context-pack/ctxb_missing").status_code == 404


def test_store_requires_id_and_hash(client: TestClient):
    bad = _pack()
    del bad["bundle_hash"]
    assert client.post("/df/rag/context-pack", json=bad).status_code == 422
