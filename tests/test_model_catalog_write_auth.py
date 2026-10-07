"""The model catalog write routes need a Forge-Agents service key with the catalog write scope."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import multi_provider_router as api
from app.database import get_db
from app.models.multi_provider_models import ModelCatalog

GOOD = {"Authorization": "Bearer good"}
NEW_ROW = {
    "model_key": "m-new",
    "provider": "anthropic",
    "model_id": "m-new-1",
    "input_cost_per_mtok": "1",
    "output_cost_per_mtok": "5",
    "max_context": 1000,
    "tier": "flagship",
}


@pytest.fixture
def metadata():
    return {"service_name": "forge-agents", "scopes": ["model-catalog:write"]}


@pytest.fixture
def client(monkeypatch, metadata):
    monkeypatch.setattr(
        api,
        "validate_api_key",
        lambda token: SimpleNamespace(metadata=metadata) if token == "good" else None,
    )
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    ModelCatalog.__table__.create(engine)
    factory = sessionmaker(bind=engine)

    def override():
        with factory() as db:
            yield db

    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    engine.dispose()


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/v1/models", NEW_ROW),
        ("put", "/api/v1/models/m-new", {"is_active": False}),
        ("delete", "/api/v1/models/m-new", None),
    ],
)
def test_write_without_a_key_is_refused(client, method, path, body):
    response = getattr(client, method)(path, **({"json": body} if body else {}))
    assert response.status_code == 401


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_write_with_an_unknown_key_is_refused(client, method):
    path = "/api/v1/models" if method == "post" else "/api/v1/models/m-new"
    kwargs = {"json": NEW_ROW} if method != "delete" else {}
    assert getattr(client, method)(path, headers={"Authorization": "Bearer bad"}, **kwargs).status_code == 401


@pytest.mark.parametrize(
    "bad",
    [
        {"service_name": "forge-smithy", "scopes": ["model-catalog:write"]},
        {"service_name": "forge-agents", "scopes": ["bds:sessions:write"]},
        {"service_name": "forge-agents", "scopes": "model-catalog:write"},
        {"service_name": "forge-agents"},
    ],
)
def test_a_key_with_the_wrong_service_or_scope_is_refused(client, metadata, bad):
    metadata.clear()
    metadata.update(bad)
    assert client.post("/api/v1/models", json=NEW_ROW, headers=GOOD).status_code == 403


def test_reads_stay_open(client):
    assert client.get("/api/v1/models").status_code == 200


def test_create_update_model_id_and_delete_with_the_scope(client, caplog):
    assert client.post("/api/v1/models", json=NEW_ROW, headers=GOOD).status_code == 201
    with caplog.at_level("INFO"):
        response = client.put("/api/v1/models/m-new", json={"model_id": "m-new-2"}, headers=GOOD)
    assert response.status_code == 200
    assert response.json()["model_id"] == "m-new-2"
    audit = [r for r in caplog.records if r.getMessage() == "model_catalog_updated"][0]
    assert audit.actor == "forge-agents"
    assert audit.before == {"model_id": "m-new-1"}
    assert audit.after == {"model_id": "m-new-2"}
    assert client.delete("/api/v1/models/m-new", headers=GOOD).status_code == 204


def test_update_of_a_missing_model_is_404(client):
    assert client.put("/api/v1/models/none", json={"is_active": False}, headers=GOOD).status_code == 404


def test_a_deepseek_model_can_be_added(client):
    """The catalog sync adds DeepSeek models; the provider list must allow them."""
    row = dict(NEW_ROW, model_key="deepseek-flash", provider="deepseek", model_id="deepseek-flash")
    response = client.post("/api/v1/models", json=row, headers=GOOD)
    assert response.status_code == 201
    assert response.json()["provider"] == "deepseek"


def test_an_unknown_provider_is_still_refused(client):
    row = dict(NEW_ROW, model_key="x", provider="mystery", model_id="x")
    assert client.post("/api/v1/models", json=row, headers=GOOD).status_code == 422
