"""RFC-FT-04 candidate proof through the real HTTP ingest path on PostgreSQL.

Authorized by the operator on 2026-09-29 (corrective pass) for the admission
proof only. Run it through ``scripts/prove_rfc_ft_04_candidate_postgres.sh``
against a throwaway cluster. It uses synthetic fixtures vendored byte-for-byte
from forge_contract_core, a synthetic API key minted in that cluster, and the
dedicated least-privilege telemetry role. It changes no production setting.

Every request goes through ``TestClient(app)``: bearer-key authentication,
subject binding, request validation, profile enforcement, the telemetry pool
with its role preflight, and persistence. Candidate acceptance is enabled only
by overriding the ``admitted_event_profiles`` dependency inside this process.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.api_keys import _init_db as init_api_keys_table
from app.auth.api_keys import create_api_key
from app.database import SessionLocal
from app.main import app
from app.models.telemetry_models import ForgeEventV1Record
from app.services import forge_event_profiles as profiles

VENDOR = Path(__file__).resolve().parents[1] / "tests/fixtures/telemetry/rfc_ft_04_candidate"
REGISTRY = json.loads((VENDOR / "telemetry_contract_registry.v1.json").read_text("utf-8"))
VALID = REGISTRY["fixtures"]["rfc_ft_04_ai_profile_valid"]
INVALID = REGISTRY["fixtures"]["rfc_ft_04_ai_profile_invalid"]
EVENTS = "/api/v1/telemetry/events"


def _vendored(record: dict) -> dict:
    path = VENDOR / Path(record["path"]).name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], path.name
    return json.loads(path.read_text("utf-8"))


def _case(record: dict) -> str:
    return Path(record["path"]).name.split(".ai_profile.")[1].split(".")[0]


def _rows() -> int:
    with SessionLocal() as session:
        return session.execute(select(func.count()).select_from(ForgeEventV1Record)).scalar_one()


def _key(service_name: str) -> dict[str, str]:
    plaintext, _ = create_api_key(
        metadata={
            "service_name": service_name,
            "environment": "staging",
            "tenant_ref": None,
            "scopes": ["telemetry:write"],
        }
    )
    return {"Authorization": f"Bearer {plaintext}"}


def main() -> None:
    assert REGISTRY["contracts"]["ForgeAIInferenceSemantics.v1"]["status"] == (
        "candidate_rfc_ft_04"
    )
    assert profiles.ADMITTED_EVENT_PROFILES == frozenset()
    assert profiles.PROFILE_VALIDATORS[profiles.AI_INFERENCE_PROFILE] is not None

    init_api_keys_table()
    headers = _key("neuroforge")
    wrong_subject = _key("forgeagents")
    client = TestClient(app)
    lines: list[str] = []

    # 1. Authentication and subject binding still come first.
    first_valid = _vendored(VALID[0])
    response = client.post(EVENTS, json=first_valid)
    assert response.status_code == 401, response.text
    response = client.post(EVENTS, json=first_valid, headers=wrong_subject)
    assert response.status_code == 403, response.text
    assert _rows() == 0
    lines.append("auth: no key -> 401; wrong subject -> 403; rows 0")

    # 2. Ordinary runtime: the unadmitted candidate is rejected, nothing stored.
    for record in VALID:
        response = client.post(EVENTS, json=_vendored(record), headers=headers)
        assert response.status_code == 422, (_case(record), response.text)
        assert response.json()["detail"] == {"code": profiles.PROFILE_UNADMITTED}
    undeclared = deepcopy(first_valid)
    del undeclared["attributes"]["ai.profile"]
    response = client.post(EVENTS, json=undeclared, headers=headers)
    assert response.json()["detail"] == {"code": profiles.PROFILE_UNDECLARED}
    assert _rows() == 0
    lines.append(f"ordinary runtime: {len(VALID)} candidate events -> 422 unadmitted; rows 0")

    # 3. Isolated harness: admit the candidate in this process only.
    app.dependency_overrides[profiles.admitted_event_profiles] = lambda: frozenset(
        {profiles.AI_INFERENCE_PROFILE}
    )
    try:
        for record in INVALID:
            before = _rows()
            response = client.post(EVENTS, json=_vendored(record), headers=headers)
            detail = response.json()["detail"]
            assert response.status_code == 422, (_case(record), response.text)
            assert "identity_outcome" not in response.text
            assert detail["code"] in {
                profiles.PROFILE_VIOLATION,
                profiles.PROFILE_UNDECLARED,
                profiles.PROFILE_UNADMITTED,
            }
            if detail["code"] == profiles.PROFILE_VIOLATION:
                assert detail["profile_error"] == record["expected_error_code"], _case(record)
            assert _rows() == before
            lines.append(f"invalid {_case(record)}: 422 {detail['code']} "
                         f"{detail.get('profile_error', '')}; no row")

        with SessionLocal() as session:
            for record in VALID:
                payload = _vendored(record)
                first = client.post(EVENTS, json=payload, headers=headers)
                replay = client.post(EVENTS, json=payload, headers=headers)
                assert first.status_code == 201, (_case(record), first.text)
                assert first.json()["identity_outcome"] == "inserted"
                assert replay.status_code == 200
                assert replay.json()["identity_outcome"] == "exact_replay"
                assert first.json()["event_digest"] == record["expected_event_digest"]
                assert first.json()["received_at"] == replay.json()["received_at"]

                stored = session.execute(
                    select(ForgeEventV1Record).where(
                        ForgeEventV1Record.event_id == payload["event_id"]
                    )
                ).scalar_one()
                assert stored.attributes == payload["attributes"], _case(record)
                assert stored.metrics == payload["metrics"], _case(record)
                for name, value in payload["metrics"].items():
                    assert type(stored.metrics[name]) is type(value), (_case(record), name)

                conflict = deepcopy(payload)
                conflict["metrics"]["ai.model_latency_ms"] += 1
                clash = client.post(EVENTS, json=conflict, headers=headers)
                assert clash.status_code == 409
                assert clash.json()["detail"]["code"] == "event_identity_conflict"
                lines.append(f"valid {_case(record)}: inserted -> exact_replay; "
                             "conflict -> 409 event_identity_conflict")
            stored_count = _rows()

        # 4. A missing validator fails closed, never base-only.
        original = profiles.PROFILE_VALIDATORS[profiles.AI_INFERENCE_PROFILE]
        profiles.PROFILE_VALIDATORS[profiles.AI_INFERENCE_PROFILE] = None
        try:
            probe = deepcopy(first_valid)
            probe["event_id"] = "a1000000-0000-4000-8000-0000000000f2"
            response = client.post(EVENTS, json=probe, headers=headers)
            assert response.status_code == 503
            assert response.json()["detail"] == {
                "code": profiles.PROFILE_VALIDATOR_UNAVAILABLE
            }
            assert _rows() == stored_count
        finally:
            profiles.PROFILE_VALIDATORS[profiles.AI_INFERENCE_PROFILE] = original
        lines.append("validator unavailable: 503; no row")
    finally:
        app.dependency_overrides.pop(profiles.admitted_event_profiles, None)

    assert _rows() == len(VALID)
    for line in lines:
        print(f"RFC_FT_04_CANDIDATE {line}")
    print("RFC_FT_04_CANDIDATE_POSTGRES_HTTP_OK")


if __name__ == "__main__":
    main()
