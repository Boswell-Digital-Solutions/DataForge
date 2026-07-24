"""Prove concurrent same-ID/different-binding ingest is deterministic."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any

from sqlalchemy import text

from app.database import SessionLocal


EVENT_ID = "66666666-6666-4666-8666-666666666666"


def _candidate(*, service_name: str, event_digest: str) -> tuple[dict[str, Any], str]:
    return (
        {
            "schema_version": "ForgeEvent.v1",
            "event_id": EVENT_ID,
            "occurred_at": "2026-07-23T19:01:00Z",
            "service_name": service_name,
            "service_instance_id": None,
            "environment": "staging",
            "tenant_ref": None,
            "event_type": "release_parity.identity_race",
            "severity": "info",
            "outcome": "ok",
            "evidence_class": "operational",
            "correlation_id": None,
            "trace_id": None,
            "span_id": None,
            "parent_span_id": None,
            "attributes": {},
            "metrics": {},
            "privacy_class": "internal",
            "retention_class": "standard",
            "sampled": False,
            "sample_rate": None,
            "sampling_reason": "rate_limited",
        },
        event_digest,
    )


def _ingest(
    start: Barrier,
    candidate: dict[str, Any],
    event_digest: str,
) -> str:
    with SessionLocal() as session:
        session.execute(text("SET LOCAL statement_timeout = '5000ms'"))
        start.wait(timeout=5)
        outcome = session.execute(
            text(
                """
                SELECT ingest_forge_event_v1(
                    CAST(:candidate AS jsonb),
                    CAST(:event_digest AS char(64))
                )
                """
            ),
            {
                "candidate": json.dumps(
                    candidate,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "event_digest": event_digest,
            },
        ).scalar_one()
        session.commit()
        return outcome


def main() -> None:
    contenders = (
        _candidate(service_name="forgeagents", event_digest="d" * 64),
        _candidate(service_name="rake", event_digest="e" * 64),
    )
    start = Barrier(len(contenders))

    with ThreadPoolExecutor(max_workers=len(contenders)) as executor:
        futures = [
            executor.submit(_ingest, start, candidate, digest)
            for candidate, digest in contenders
        ]
        outcomes = [future.result(timeout=10) for future in futures]

    assert sorted(outcomes) == ["event_identity_conflict", "inserted"], outcomes

    with SessionLocal() as session:
        stored = session.execute(
            text(
                """
                SELECT service_name, event_digest
                FROM forge_events_v1
                WHERE event_id = CAST(:event_id AS uuid)
                """
            ),
            {"event_id": EVENT_ID},
        ).one()
        assert (stored.service_name, stored.event_digest.strip()) in {
            (candidate["service_name"], digest)
            for candidate, digest in contenders
        }

        winner = next(
            (candidate, digest)
            for candidate, digest in contenders
            if candidate["service_name"] == stored.service_name
        )
        replay = session.execute(
            text(
                """
                SELECT ingest_forge_event_v1(
                    CAST(:candidate AS jsonb),
                    CAST(:event_digest AS char(64))
                )
                """
            ),
            {
                "candidate": json.dumps(
                    winner[0],
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "event_digest": winner[1],
            },
        ).scalar_one()
        assert replay == "exact_replay"
        session.commit()

    print("FORGE_EVENT_V1_POSTGRES_BINDING_RACE_OK")


if __name__ == "__main__":
    main()
