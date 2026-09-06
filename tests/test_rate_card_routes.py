"""Route tests for the DataForge RateCardSnapshot.v1 store (RFC-CP-03)."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.admin_keys_router import AuthContext, require_api_key
from app.main import app
from forge_contract_core.validators.cost import compute_rate_card_digest


@pytest.fixture(autouse=True)
def _service_auth():
    """Satisfy the service-auth dependency for these route tests."""
    app.dependency_overrides[require_api_key] = lambda: AuthContext(auth_mode="api_key")
    yield
    app.dependency_overrides.pop(require_api_key, None)


def _snapshot(
    *,
    snapshot_id=None,
    provider="anthropic",
    model="claude-sonnet-4-5-20250929",
    model_version=None,
    status="ACTIVE",
    effective_from="2026-08-01T00:00:00Z",
    effective_to=None,
    uncached_input=3_000_000,
    output=15_000_000,
    approved_by="charlie",
    approved_at="2026-08-01T00:00:00Z",
    revoked_reason=None,
    superseded_by=None,
):
    payload = {
        "schema_version": "RateCardSnapshot.v1",
        "id": snapshot_id or str(uuid.uuid4()),
        "provider": provider,
        "model": model,
        "model_version": model_version,
        "currency": "USD",
        "uncached_input_rate_micros_per_million_tokens": uncached_input,
        "cached_input_rate_micros_per_million_tokens": None,
        "cache_write_rate_micros_per_million_tokens": None,
        "reasoning_rate_micros_per_million_tokens": None,
        "output_rate_micros_per_million_tokens": output,
        "effective_from": effective_from if status not in ("CANDIDATE",) else None,
        "effective_to": effective_to,
        "status": status,
        "source_url": "https://example.com/pricing",
        "retrieved_at": "2026-08-01T00:00:00Z",
        "approved_by": approved_by if status not in ("CANDIDATE",) else None,
        "approved_at": approved_at if status not in ("CANDIDATE",) else None,
        "revoked_reason": revoked_reason,
        "superseded_by": superseded_by,
        "rounding_rule": "ROUND_HALF_UP_PER_CATEGORY_SUBTOTAL_MICROS",
    }
    payload["digest"] = compute_rate_card_digest(payload)
    return payload


def test_store_then_get_active(client: TestClient):
    body = _snapshot()
    r = client.post("/api/v1/rate-cards", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["id"] == body["id"]

    active = client.get(
        "/api/v1/rate-cards/active",
        params={"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    )
    assert active.status_code == 200, active.text
    assert active.json()["output_rate_micros_per_million_tokens"] == 15_000_000


def test_get_active_404_when_no_match(client: TestClient):
    r = client.get(
        "/api/v1/rate-cards/active",
        params={"provider": "nobody", "model": "nothing"},
    )
    assert r.status_code == 404


def test_post_rejects_tampered_digest(client: TestClient):
    body = _snapshot()
    body["digest"] = "sha256:" + "0" * 64
    r = client.post("/api/v1/rate-cards", json=body)
    assert r.status_code == 422


def test_post_rejects_active_overlap(client: TestClient):
    first = _snapshot(effective_from="2026-01-01T00:00:00Z", effective_to=None)
    r1 = client.post("/api/v1/rate-cards", json=first)
    assert r1.status_code == 201, r1.text

    # A second ACTIVE card for the same (provider, model, model_version) with no
    # end date on the first is an overlap no matter what the second's dates are.
    second = _snapshot(effective_from="2026-06-01T00:00:00Z", effective_to=None)
    r2 = client.post("/api/v1/rate-cards", json=second)
    assert r2.status_code == 409, r2.text


def test_post_allows_non_overlapping_active_after_first_is_ended(client: TestClient):
    first = _snapshot(effective_from="2026-01-01T00:00:00Z", effective_to="2026-06-01T00:00:00Z")
    r1 = client.post("/api/v1/rate-cards", json=first)
    assert r1.status_code == 201, r1.text

    second = _snapshot(effective_from="2026-06-01T00:00:00Z", effective_to=None)
    r2 = client.post("/api/v1/rate-cards", json=second)
    assert r2.status_code == 201, r2.text


def test_post_rejects_rate_content_change_on_existing_id(client: TestClient):
    body = _snapshot(status="CANDIDATE", effective_from=None)
    r1 = client.post("/api/v1/rate-cards", json=body)
    assert r1.status_code == 201, r1.text

    tampered = dict(body)
    tampered["output_rate_micros_per_million_tokens"] = 999_999
    tampered["digest"] = compute_rate_card_digest(tampered)
    r2 = client.post("/api/v1/rate-cards", json=tampered)
    assert r2.status_code == 409, r2.text


def test_post_upserts_lifecycle_fields_on_existing_id(client: TestClient):
    sid = str(uuid.uuid4())
    candidate = _snapshot(snapshot_id=sid, status="CANDIDATE", effective_from=None)
    r1 = client.post("/api/v1/rate-cards", json=candidate)
    assert r1.status_code == 201, r1.text
    assert r1.json()["status"] == "CANDIDATE"

    promoted = _snapshot(
        snapshot_id=sid,
        status="ACTIVE",
        effective_from="2026-08-01T00:00:00Z",
        approved_by="charlie",
        approved_at="2026-08-01T00:00:00Z",
    )
    r2 = client.post("/api/v1/rate-cards", json=promoted)
    assert r2.status_code == 201, r2.text
    assert r2.json()["status"] == "ACTIVE"
    assert r2.json()["id"] == sid


def test_list_filters_by_provider_and_status(client: TestClient):
    client.post("/api/v1/rate-cards", json=_snapshot(provider="openai", model="gpt-4.1-mini"))
    client.post(
        "/api/v1/rate-cards",
        json=_snapshot(provider="anthropic", model="claude-sonnet-4-5-20250929"),
    )
    listing = client.get("/api/v1/rate-cards", params={"provider": "openai"}).json()
    assert listing["total"] == 1
    assert listing["items"][0]["provider"] == "openai"

    by_status = client.get("/api/v1/rate-cards", params={"status": "ACTIVE"}).json()
    assert by_status["total"] == 2


def test_raw_get_endpoints_require_auth_but_public_projection_does_not(client: TestClient):
    body = _snapshot()
    stored = client.post("/api/v1/rate-cards", json=body)
    assert stored.status_code == 201, stored.text

    app.dependency_overrides.pop(require_api_key, None)
    r = client.get("/api/v1/rate-cards")
    assert r.status_code == 401
    r2 = client.get(
        "/api/v1/rate-cards/active",
        params={"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    )
    assert r2.status_code == 401

    public = client.get(
        "/api/v1/rate-cards/public/active",
        params={"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    )
    assert public.status_code == 200, public.text
    assert set(public.json()) == {
        "schema_version",
        "provider",
        "model",
        "model_version",
        "currency",
        "uncached_input_rate_micros_per_million_tokens",
        "cached_input_rate_micros_per_million_tokens",
        "cache_write_rate_micros_per_million_tokens",
        "reasoning_rate_micros_per_million_tokens",
        "output_rate_micros_per_million_tokens",
        "effective_from",
        "effective_to",
        "rounding_rule",
    }


def test_post_requires_auth(client: TestClient):
    app.dependency_overrides.pop(require_api_key, None)
    r = client.post("/api/v1/rate-cards", json=_snapshot())
    assert r.status_code == 401


def test_accepts_a_real_forge_contract_core_fixture_with_its_original_digest(client: TestClient):
    """Cross-repo compatibility check: a real, previously Python-computed
    RateCardSnapshot.v1 fixture (forge_contract_core's
    fixtures/cost/valid/rate_card_snapshot.v1.active-partial-rates.valid.json)
    must be accepted with its digest as-shipped — not one recomputed here."""
    fixture = {
        "schema_version": "RateCardSnapshot.v1",
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "model_version": None,
        "currency": "USD",
        "uncached_input_rate_micros_per_million_tokens": 3000000,
        "cached_input_rate_micros_per_million_tokens": 300000,
        "cache_write_rate_micros_per_million_tokens": None,
        "reasoning_rate_micros_per_million_tokens": None,
        "output_rate_micros_per_million_tokens": 15000000,
        "effective_from": "2026-08-26T12:00:00Z",
        "effective_to": None,
        "status": "ACTIVE",
        "source_url": None,
        "retrieved_at": "2026-08-26T12:00:00Z",
        "approved_by": "forge-command-operator:cwb",
        "approved_at": "2026-08-26T12:05:00Z",
        "revoked_reason": None,
        "superseded_by": None,
        "rounding_rule": "ROUND_HALF_UP_PER_CATEGORY_SUBTOTAL_MICROS",
        "digest": "sha256:bb76778c253d86267290633cc4cdef09ba5e4e6dece84ee2f6f00bd3742efe0a",
    }
    r = client.post("/api/v1/rate-cards", json=fixture)
    assert r.status_code == 201, r.text
    assert r.json()["digest"] == fixture["digest"]
