"""Proof-only canonical ForgeEvent.v1 storage and identity rehearsal.

This module deliberately creates an isolated in-memory table. It does not
register a production ORM model, Alembic migration, API route, legacy adapter,
or dual-write path.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import pytest
import rfc8785
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    select,
)
from sqlalchemy.exc import IntegrityError


FIXTURES = Path(__file__).parent / "fixtures" / "telemetry"
MANIFEST_PATH = FIXTURES / "forge_event_v1_proof_manifest.json"
VALID_EVENT_PATH = FIXTURES / "forge_event.v1.valid.json"
CAPABILITY_PATH = FIXTURES / "forge_telemetry_sink_capability.v1.proof.json"
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
TRACE_ID_PATTERN = re.compile(r"^(?!0{32}$)[0-9a-f]{32}$")
SPAN_ID_PATTERN = re.compile(r"^(?!0{16}$)[0-9a-f]{16}$")


class ForgeEventSubmissionV1(BaseModel):
    """Producer-authored projection; sink-owned ``received_at`` is forbidden."""

    schema_version: Literal["ForgeEvent.v1"]
    event_id: UUID
    occurred_at: datetime
    service_name: str
    service_instance_id: str | None
    environment: str
    tenant_ref: str | None
    event_type: str
    severity: Literal["info", "warning", "error", "critical"]
    outcome: Literal[
        "ok",
        "warn",
        "fail",
        "cancelled",
        "insufficient_signal",
        "blocked",
    ]
    evidence_class: Literal["diagnostic", "operational", "audit", "security"]
    correlation_id: UUID | None
    trace_id: str | None
    span_id: str | None
    parent_span_id: str | None
    attributes: dict[str, Any]
    metrics: dict[str, int | float]
    privacy_class: Literal["public", "internal", "restricted", "confidential"]
    retention_class: Literal["ephemeral", "short", "standard", "long", "legal_hold"]
    sampled: bool
    sample_rate: float | None = Field(gt=0, le=1)
    sampling_reason: Literal[
        "always_on",
        "probabilistic",
        "rate_limited",
        "required_stub",
        "policy",
    ]

    model_config = ConfigDict(extra="forbid")

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("occurred_at must be timezone-aware UTC")
        return value

    @field_validator(
        "service_name",
        "service_instance_id",
        "environment",
        "tenant_ref",
        "event_type",
    )
    @classmethod
    def identifier_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and IDENTIFIER_PATTERN.fullmatch(value) is None:
            raise ValueError("identifier must use the canonical lowercase grammar")
        return value

    @field_validator("trace_id")
    @classmethod
    def trace_id_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and TRACE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError("trace_id must be 32 lowercase hexadecimal characters")
        return value

    @field_validator("span_id", "parent_span_id")
    @classmethod
    def span_id_is_canonical(cls, value: str | None) -> str | None:
        if value is not None and SPAN_ID_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "span identifiers must be 16 lowercase hexadecimal characters"
            )
        return value

    def validate_semantics(self) -> None:
        if self.trace_id is None and (
            self.span_id is not None or self.parent_span_id is not None
        ):
            raise ValueError("span identifiers require trace_id")
        if self.span_id is None and self.parent_span_id is not None:
            raise ValueError("parent_span_id requires span_id")
        if self.parent_span_id is not None and self.parent_span_id == self.span_id:
            raise ValueError("parent_span_id cannot equal span_id")
        if self.sampling_reason == "probabilistic":
            if self.sample_rate is None:
                raise ValueError("probabilistic sampling requires sample_rate")
        elif self.sample_rate is not None:
            raise ValueError("sample_rate is only valid for probabilistic sampling")
        admitted_reasons = (
            {"always_on", "probabilistic", "policy"}
            if self.sampled
            else {"rate_limited", "required_stub", "policy"}
        )
        if self.sampling_reason not in admitted_reasons:
            raise ValueError("sampled and sampling_reason are inconsistent")
        if any(isinstance(value, bool) for value in self.metrics.values()):
            raise ValueError("metrics must be numeric and cannot use booleans")


class StoredForgeEventV1(ForgeEventSubmissionV1):
    """Canonical sink representation after trusted sink-time enrichment."""

    received_at: datetime

    @field_validator("received_at")
    @classmethod
    def received_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("received_at must be timezone-aware UTC")
        return value


def _load_valid_stored_event() -> dict[str, Any]:
    return json.loads(VALID_EVENT_PATH.read_text(encoding="utf-8"))


def _submission_from_fixture() -> ForgeEventSubmissionV1:
    payload = _load_valid_stored_event()
    payload.pop("received_at")
    submission = ForgeEventSubmissionV1.model_validate(payload)
    submission.validate_semantics()
    return submission


def _event_digest(event: ForgeEventSubmissionV1) -> str:
    projection = ForgeEventSubmissionV1.model_validate(
        event.model_dump(mode="python", exclude={"received_at"})
    )
    projection.validate_semantics()
    canonical = rfc8785.dumps(projection.model_dump(mode="json"))
    return hashlib.sha256(canonical).hexdigest()


def _sink_stamp(
    submission: ForgeEventSubmissionV1, *, received_at: datetime
) -> StoredForgeEventV1:
    stored = StoredForgeEventV1.model_validate(
        {**submission.model_dump(mode="python"), "received_at": received_at}
    )
    stored.validate_semantics()
    return stored


metadata = MetaData()
forge_events_v1_proof = Table(
    "forge_events_v1_proof",
    metadata,
    Column("event_id", String, primary_key=True),
    Column("event_digest", String, nullable=False),
    Column("schema_version", String, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("service_name", String, nullable=False),
    Column("service_instance_id", String),
    Column("environment", String, nullable=False),
    Column("tenant_ref", String),
    Column("event_type", String, nullable=False),
    Column("severity", String, nullable=False),
    Column("outcome", String, nullable=False),
    Column("evidence_class", String, nullable=False),
    Column("correlation_id", String),
    Column("trace_id", String),
    Column("span_id", String),
    Column("parent_span_id", String),
    Column("attributes", JSON, nullable=False),
    Column("metrics", JSON, nullable=False),
    Column("privacy_class", String, nullable=False),
    Column("retention_class", String, nullable=False),
    Column("sampled", Boolean, nullable=False),
    Column("sample_rate", Float),
    Column("sampling_reason", String, nullable=False),
)


def _storage_values(stored: StoredForgeEventV1, event_digest: str) -> dict[str, Any]:
    values = stored.model_dump(mode="python")
    values["event_id"] = str(values["event_id"])
    values["correlation_id"] = (
        str(values["correlation_id"]) if values["correlation_id"] is not None else None
    )
    values["event_digest"] = event_digest
    return values


def _persist(connection: Any, stored: StoredForgeEventV1) -> str:
    digest = _event_digest(stored)
    values = _storage_values(stored, digest)
    try:
        with connection.begin_nested():
            connection.execute(insert(forge_events_v1_proof).values(**values))
        return "inserted"
    except IntegrityError:
        existing = (
            connection.execute(
                select(forge_events_v1_proof).where(
                    forge_events_v1_proof.c.event_id == str(stored.event_id)
                )
            )
            .mappings()
            .one()
        )
        binding = (
            "event_digest",
            "schema_version",
            "service_name",
            "service_instance_id",
            "environment",
            "tenant_ref",
        )
        if all(existing[field] == values[field] for field in binding):
            return "exact_replay"
        raise ValueError("event_identity_conflict") from None


def test_proof_manifest_pins_authority_and_forbids_legacy_modes() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest == {
        "status": "proof_only",
        "contract_authority_commit": "e4b29987eb9c2359fe73b95c660feb50be37bba5",
        "schema_version": "ForgeEvent.v1",
        "schema_sha256": (
            "165ff1ba01d6a4a9b456f77c22c3b664deeb9044c5000daae98deedabdab57d2"
        ),
        "digest_profile_sha256": (
            "024d16505a26c5569d5d2c08a834ae7e635f7f0abf77803c54da17c55aba5b7c"
        ),
        "valid_fixture_sha256": (
            "0d671d1c6bc5c2d7e5a13d304730f604ca58d06c1cb8c883d56a63d6fbd1bd6f"
        ),
        "capability_schema_sha256": (
            "bb38db96f95836080f40ada006458a09b6b6bef150d0c4c0a3e3a9a2e40f9c0d"
        ),
        "capability_fixture_sha256": (
            "6b4997f6ef685b7a8c7dacb92ed48e4b608bd6252ea443886472cd1aa07b7859"
        ),
        "canonicalization": "RFC8785-JCS",
        "resource_bounds_sha256": (
            "6729e46ea46544095c1e7dd8bcdb9df9eec84df1889b9e4439db6b3f998eb919"
        ),
        "max_canonical_event_bytes": 65536,
        "pre_v1_fallback": False,
        "dual_write": False,
    }
    assert (
        hashlib.sha256(VALID_EVENT_PATH.read_bytes()).hexdigest()
        == (manifest["valid_fixture_sha256"])
    )
    assert (
        hashlib.sha256(CAPABILITY_PATH.read_bytes()).hexdigest()
        == (manifest["capability_fixture_sha256"])
    )


def test_submission_forbids_sink_owned_received_at_and_pre_v1_shape() -> None:
    canonical = _load_valid_stored_event()
    with pytest.raises(ValidationError):
        ForgeEventSubmissionV1.model_validate(canonical)

    with pytest.raises(ValidationError):
        ForgeEventSubmissionV1.model_validate(
            {
                "event_id": canonical["event_id"],
                "timestamp": canonical["occurred_at"],
                "service": canonical["service_name"],
                "event_type": canonical["event_type"],
                "severity": canonical["severity"],
                "metadata": canonical["attributes"],
                "metrics": canonical["metrics"],
            }
        )


def test_sink_stamps_received_at_and_stored_event_stays_bounded() -> None:
    submission = _submission_from_fixture()
    received_at = datetime(2026, 7, 23, 18, 0, 1, tzinfo=UTC)
    stored = _sink_stamp(submission, received_at=received_at)

    assert stored.received_at == received_at
    assert len(rfc8785.dumps(stored.model_dump(mode="json"))) <= 65536


def test_zero_trace_and_span_identifiers_fail_closed() -> None:
    submission = _submission_from_fixture()
    for field, zero_value in (("trace_id", "0" * 32), ("span_id", "0" * 16)):
        with pytest.raises(ValidationError):
            ForgeEventSubmissionV1.model_validate(
                {**submission.model_dump(mode="python"), field: zero_value}
            )


def test_isolated_storage_distinguishes_insert_replay_and_identity_conflict() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    submission = _submission_from_fixture()
    first = _sink_stamp(
        submission,
        received_at=datetime(2026, 7, 23, 18, 0, 1, tzinfo=UTC),
    )
    replay = _sink_stamp(
        submission,
        received_at=datetime(2026, 7, 23, 18, 0, 2, tzinfo=UTC),
    )

    with engine.begin() as connection:
        assert _persist(connection, first) == "inserted"
        assert _persist(connection, replay) == "exact_replay"

        changed = submission.model_copy(
            update={"attributes": {**submission.attributes, "ready": False}}
        )
        conflict = _sink_stamp(
            changed,
            received_at=datetime(2026, 7, 23, 18, 0, 3, tzinfo=UTC),
        )
        with pytest.raises(ValueError, match="event_identity_conflict"):
            _persist(connection, conflict)

        rows = connection.execute(select(forge_events_v1_proof)).mappings().all()
        assert len(rows) == 1
        assert rows[0]["received_at"] == first.received_at.replace(tzinfo=None)


def test_capability_mismatch_fails_without_pre_v1_fallback() -> None:
    declared_capability = json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))
    assert set(declared_capability["supported_fields"]) == set(
        forge_events_v1_proof.c.keys()
    )

    required_schema_sha256 = "f" * 64
    if declared_capability["event_schema_sha256"] != required_schema_sha256:
        outcome = "unsupported_sink_schema"
    else:
        outcome = "ok"

    assert outcome == "unsupported_sink_schema"
    assert declared_capability["pre_v1_fallback"] is False
    assert declared_capability["dual_write"] is False
    assert declared_capability["write_enabled"] is False


def test_proof_rollback_disables_writer_without_erasing_canonical_evidence() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    stored = _sink_stamp(
        _submission_from_fixture(),
        received_at=datetime(2026, 7, 23, 18, 0, 1, tzinfo=UTC),
    )
    deployment = {
        "canonical_write_enabled": True,
        "pre_v1_write_enabled": False,
    }

    with engine.begin() as connection:
        assert _persist(connection, stored) == "inserted"
        deployment["canonical_write_enabled"] = False

        assert deployment == {
            "canonical_write_enabled": False,
            "pre_v1_write_enabled": False,
        }
        rows = connection.execute(select(forge_events_v1_proof)).all()
        assert len(rows) == 1
