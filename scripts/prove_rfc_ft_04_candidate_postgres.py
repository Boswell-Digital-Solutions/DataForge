"""RFC-FT-04 candidate round-trip: ForgeAIInferenceSemantics.v1 through ingest.

Authorized by the operator on 2026-09-29 for the admission proof only. Run it
through ``scripts/prove_rfc_ft_04_candidate_postgres.sh`` against a throwaway
PostgreSQL cluster. It uses only the synthetic candidate fixtures vendored
byte-for-byte from forge_contract_core. It changes no route, schema, or
production setting.

It proves that each profile event is stored exactly and replays exactly, that
same-ID/different-content is refused, and that the stored digest equals the
contract authority's digest. It also records what DataForge does NOT do: the
ingest boundary validates ForgeEvent.v1 only, so it stores an event that
violates the profile.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, Response
from sqlalchemy import select

from app.api.admin_keys_router import AuthContext
from app.api.telemetry_router import ingest_forge_event_v1
from app.auth import ApiKeyInfo
from app.database import SessionLocal
from app.models.telemetry_models import ForgeEventV1Record
from app.models.telemetry_schemas import ForgeEventV1Submission, event_digest

VENDOR = Path(__file__).resolve().parents[1] / "tests/fixtures/telemetry/rfc_ft_04_candidate"
REGISTRY = json.loads((VENDOR / "telemetry_contract_registry.v1.json").read_text("utf-8"))
VALID = REGISTRY["fixtures"]["rfc_ft_04_ai_profile_valid"]
INVALID = REGISTRY["fixtures"]["rfc_ft_04_ai_profile_invalid"]


def _auth() -> AuthContext:
    return AuthContext(
        auth_mode="api_key",
        key_info=ApiKeyInfo(
            id="rfc-ft-04-candidate-proof-key",
            key_prefix="rfc-ft-04-",
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "service_name": "neuroforge",
                "environment": "staging",
                "tenant_ref": None,
                "scopes": ["telemetry:write"],
            },
        ),
    )


def _vendored(record: dict) -> dict:
    path = VENDOR / Path(record["path"]).name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], path.name
    return json.loads(path.read_text("utf-8"))


def _case(record: dict) -> str:
    return Path(record["path"]).name.split(".ai_profile.")[1].split(".")[0]


def main() -> None:
    assert REGISTRY["contracts"]["ForgeAIInferenceSemantics.v1"]["status"] == (
        "candidate_rfc_ft_04"
    )
    auth = _auth()
    results = []
    with SessionLocal() as session:
        for record in VALID:
            payload = _vendored(record)
            event = ForgeEventV1Submission.model_validate(payload)
            digest = event_digest(event)
            assert digest == record["expected_event_digest"], _case(record)

            first = ingest_forge_event_v1(event, Response(), session, auth)
            replay_response = Response()
            replay = ingest_forge_event_v1(event, replay_response, session, auth)
            assert first.identity_outcome == "inserted", _case(record)
            assert replay.identity_outcome == "exact_replay", _case(record)
            assert replay_response.status_code == 200
            assert first.event_digest == replay.event_digest == digest
            assert first.received_at == replay.received_at

            stored = session.execute(
                select(ForgeEventV1Record).where(
                    ForgeEventV1Record.event_id == event.event_id
                )
            ).scalar_one()
            # JSONB must keep every profile key, integer type, and float value.
            assert stored.attributes == payload["attributes"], _case(record)
            assert stored.metrics == payload["metrics"], _case(record)
            for name, value in payload["metrics"].items():
                assert type(stored.metrics[name]) is type(value), (_case(record), name)

            conflict = deepcopy(payload)
            conflict["metrics"]["ai.model_latency_ms"] = (
                conflict["metrics"].get("ai.model_latency_ms", 0) + 1
            )
            try:
                ingest_forge_event_v1(
                    ForgeEventV1Submission.model_validate(conflict),
                    Response(),
                    session,
                    auth,
                )
            except HTTPException as exc:
                assert exc.status_code == 409
                assert exc.detail["code"] == "event_identity_conflict"
            else:
                raise AssertionError(f"{_case(record)}: conflict was not rejected")
            results.append((_case(record), first.identity_outcome, replay.identity_outcome))

        # Negative finding: ingest does not enforce the profile's semantics.
        unknown = next(r for r in INVALID if _case(r) == "unknown_ai_key")
        probe = _vendored(unknown)
        probe["event_id"] = "a1000000-0000-4000-8000-0000000000f1"
        outcome = ingest_forge_event_v1(
            ForgeEventV1Submission.model_validate(probe), Response(), session, auth
        ).identity_outcome
        assert outcome == "inserted", "DataForge now enforces the profile; update the report"

    for case, first, replay in results:
        print(f"RFC_FT_04_CANDIDATE {case}: {first} -> {replay}; conflict -> event_identity_conflict")
    print("RFC_FT_04_CANDIDATE profile-invalid event stored: ingest validates ForgeEvent.v1 only")
    print("RFC_FT_04_CANDIDATE_POSTGRES_OK")


if __name__ == "__main__":
    main()
