"""RFC-FT-04 profile enforcement at the canonical ingest boundary.

These tests go through the HTTP request path (``TestClient``). Authentication
is replaced by a synthetic, correctly bound service key here; the PostgreSQL
proof (``scripts/prove_rfc_ft_04_candidate_postgres.sh``) repeats the checks
with a real API key and the dedicated telemetry role.

Ordinary runtime admits no profile. Candidate acceptance is enabled only by
overriding the ``admitted_event_profiles`` dependency inside a test.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.api.admin_keys_router import AuthContext, require_api_key
from app.auth import ApiKeyInfo
from app.main import app
from app.models.telemetry_models import ForgeEventV1Record
from app.services import forge_event_profiles as profiles

VENDOR = Path(__file__).parent / "fixtures" / "telemetry" / "rfc_ft_04_candidate"
REGISTRY = json.loads((VENDOR / "telemetry_contract_registry.v1.json").read_text("utf-8"))
VALID = REGISTRY["fixtures"]["rfc_ft_04_ai_profile_valid"]
INVALID = REGISTRY["fixtures"]["rfc_ft_04_ai_profile_invalid"]
EVENTS_PATH = "/api/v1/telemetry/events"
CANDIDATE = frozenset({profiles.AI_INFERENCE_PROFILE})


def _auth() -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="rfc-ft-04-test-key",
            key_prefix="rfcft04tes",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": "neuroforge",
                "environment": "staging",
                "tenant_ref": None,
                "scopes": ["telemetry:write"],
            },
        ),
    )


def _case(record: dict) -> str:
    return Path(record["path"]).name.split(".ai_profile.")[1].split(".")[0]


def _load(record: dict) -> dict:
    path = VENDOR / Path(record["path"]).name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], path.name
    return json.loads(path.read_text("utf-8"))


def _plain_event(event_id: str) -> dict:
    event = _load(VALID[0])
    event["event_id"] = event_id
    event["attributes"] = {"route": "chat"}
    event["metrics"] = {"latency_ms": 12}
    return event


@pytest.fixture
def api(client):
    app.dependency_overrides[require_api_key] = _auth
    yield client
    app.dependency_overrides.pop(require_api_key, None)
    app.dependency_overrides.pop(profiles.admitted_event_profiles, None)


@pytest.fixture
def candidate_admitted():
    app.dependency_overrides[profiles.admitted_event_profiles] = lambda: CANDIDATE
    yield
    app.dependency_overrides.pop(profiles.admitted_event_profiles, None)


def _rows(db) -> int:
    db.expire_all()
    return db.query(ForgeEventV1Record).count()


def test_vendored_validator_is_the_pinned_authority_module():
    content = profiles._VALIDATOR_PATH.read_bytes()
    assert hashlib.sha256(content).hexdigest() == profiles.AI_INFERENCE_PROFILE_VALIDATOR_SHA256
    assert profiles.PROFILE_VALIDATORS[profiles.AI_INFERENCE_PROFILE] is not None
    assert profiles.ADMITTED_EVENT_PROFILES == frozenset()
    assert REGISTRY["contracts"]["ForgeAIInferenceSemantics.v1"]["status"] == (
        "candidate_rfc_ft_04"
    )


def test_drifted_validator_bytes_never_load(tmp_path):
    drifted = tmp_path / "validator.py"
    drifted.write_bytes(profiles._VALIDATOR_PATH.read_bytes() + b"\n")
    assert (
        profiles._load_pinned_validator(
            drifted, profiles.AI_INFERENCE_PROFILE_VALIDATOR_SHA256
        )
        is None
    )
    assert profiles._load_pinned_validator(tmp_path / "missing.py", "0" * 64) is None


def test_plain_event_without_ai_keys_is_unchanged(api, db):
    response = api.post(EVENTS_PATH, json=_plain_event("b1000000-0000-4000-8000-000000000001"))
    assert response.status_code == 201, response.text
    assert response.json()["identity_outcome"] == "inserted"
    assert _rows(db) == 1


@pytest.mark.parametrize("record", VALID, ids=_case)
def test_ordinary_runtime_rejects_the_unadmitted_candidate(api, db, record):
    response = api.post(EVENTS_PATH, json=_load(record))
    assert response.status_code == 422
    assert response.json()["detail"] == {"code": profiles.PROFILE_UNADMITTED}
    assert _rows(db) == 0


@pytest.mark.parametrize("record", VALID, ids=_case)
def test_harness_admitted_candidate_persists_valid_events(api, db, candidate_admitted, record):
    event = _load(record)
    first = api.post(EVENTS_PATH, json=event)
    replay = api.post(EVENTS_PATH, json=event)
    assert first.status_code == 201, first.text
    assert first.json()["identity_outcome"] == "inserted"
    assert first.json()["event_digest"] == record["expected_event_digest"]
    assert replay.json()["identity_outcome"] == "exact_replay"
    assert _rows(db) == 1


@pytest.mark.parametrize("record", INVALID, ids=_case)
def test_profile_invalid_events_are_rejected_without_a_row(api, db, candidate_admitted, record):
    response = api.post(EVENTS_PATH, json=_load(record))
    body = response.json()
    assert response.status_code == 422, body
    if _case(record) == "undeclared_ai_key":
        assert body["detail"] == {"code": profiles.PROFILE_UNDECLARED}
    elif _case(record) == "declaration_unknown_profile":
        assert body["detail"] == {"code": profiles.PROFILE_UNADMITTED}
    else:
        assert body["detail"] == {
            "code": profiles.PROFILE_VIOLATION,
            "profile_error": record["expected_error_code"],
        }
    assert "identity_outcome" not in json.dumps(body)
    assert _rows(db) == 0


def test_undeclared_ai_key_is_rejected_by_ordinary_runtime(api, db):
    event = _plain_event("b1000000-0000-4000-8000-000000000002")
    event["metrics"]["ai.output_tokens"] = 3
    response = api.post(EVENTS_PATH, json=event)
    assert response.status_code == 422
    assert response.json()["detail"] == {"code": profiles.PROFILE_UNDECLARED}
    assert _rows(db) == 0


def test_unavailable_validator_fails_closed_not_base_only(api, db, candidate_admitted, monkeypatch):
    monkeypatch.setitem(profiles.PROFILE_VALIDATORS, profiles.AI_INFERENCE_PROFILE, None)
    response = api.post(EVENTS_PATH, json=_load(VALID[0]))
    assert response.status_code == 503
    assert response.json()["detail"] == {"code": profiles.PROFILE_VALIDATOR_UNAVAILABLE}
    assert _rows(db) == 0


def test_validator_fault_fails_closed(api, db, candidate_admitted, monkeypatch):
    def broken(_event):
        raise RuntimeError("boom")

    monkeypatch.setitem(profiles.PROFILE_VALIDATORS, profiles.AI_INFERENCE_PROFILE, broken)
    response = api.post(EVENTS_PATH, json=_load(VALID[0]))
    assert response.status_code == 503
    assert "boom" not in response.text
    assert _rows(db) == 0


@pytest.mark.parametrize(
    "value",
    [[], {}, ["provider_reported"], 7, None],
    ids=["list", "object", "list_of_str", "int", "null"],
)
def test_malformed_measurement_class_is_a_controlled_rejection(
    api, db, candidate_admitted, value
):
    event = _load(VALID[0])
    event["attributes"]["ai.token_measurement_class"] = value
    response = api.post(EVENTS_PATH, json=event)
    assert response.status_code == 422
    assert response.json()["detail"]["profile_error"] == "AI_PROFILE_MEASUREMENT_CLASS_INVALID"
    assert _rows(db) == 0


def test_rejection_does_not_echo_submitted_values(api, db, candidate_admitted):
    event = _load(VALID[0])
    event["attributes"]["ai.canary_SECRET_VALUE"] = "CANARY_SECRET_VALUE"
    response = api.post(EVENTS_PATH, json=event)
    assert response.status_code == 422
    assert "CANARY" not in response.text
    assert _rows(db) == 0


def test_direct_handler_call_uses_ordinary_runtime_policy(db):
    from fastapi import HTTPException, Response

    from app.api.telemetry_router import ingest_forge_event_v1
    from app.models.telemetry_schemas import ForgeEventV1Submission

    event = ForgeEventV1Submission.model_validate(_load(VALID[0]))
    with pytest.raises(HTTPException) as raised:
        ingest_forge_event_v1(event, Response(), db, _auth())
    assert raised.value.detail == {"code": profiles.PROFILE_UNADMITTED}
    assert _rows(db) == 0
