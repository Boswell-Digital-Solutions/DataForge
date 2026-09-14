"""BDS-DF-RF-001 Receipt-to-Finding Knowledge Spine -- ingest service tests.

Covers: idempotent evidence-link/disposition ingest, deterministic candidate_id
derivation from natural_key (RFC-DF-RF-01 Finding 1), real verification_status
computation against DataForge's own forge_check_run_receipts_v1 table
(Finding 2 -- verified/unverified/verification_unavailable, never trusted from
the caller), referential integrity, the terminal-candidate boundary (OD-02:
no promotion path exists), and the review feed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.df_rf_schemas import DfRfIngestRequest
from app.models.memory_models import MemoryConflict
from app.models.telemetry_models import ForgeCheckRunReceiptV1Record
from app.services.df_rf_ingest import (
    DF_RF_NAMESPACE,
    DfRfConflictError,
    DfRfValidationError,
    list_candidate_review_feed,
    store_df_rf_record,
)


SOURCE_PLAN_ID = "BDS-RMCP-FC-GIR-v0.1"
RUN_ID = "e0000000-0000-4000-8000-00000000000e"


def _ingest(db: Session, family: str, payload: dict) -> dict:
    response = store_df_rf_record(db, DfRfIngestRequest(family=family, payload=payload))
    return response.model_dump()


def evidence_link_payload(**overrides) -> dict:
    payload = {
        "schema_version": "forge.df_rf_evidence_link.v1",
        "evidence_link_id": str(uuid.uuid4()),
        "source_plan_id": SOURCE_PLAN_ID,
        "upstream_family": "ForgeCheckRunReceipt.v1",
        "upstream_record_id": str(uuid.uuid4()),
        "observed_at": "2026-09-14T00:00:00Z",
        "collected_by": "forge_command",
        "verification_status": "verified",  # deliberately wrong -- service must overwrite
        "privacy_class": "internal",
        "created_at": "2026-09-14T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def candidate_payload(*, natural_key: str, evidence_link_ids: list[str], **overrides) -> dict:
    payload = {
        "schema_version": "forge.df_rf_finding_candidate.v1",
        "candidate_id": str(uuid.uuid4()),  # deliberately wrong -- service must overwrite
        "record_family": "rmcp_fc_gir_render_incident",
        "natural_key": natural_key,
        "run_id": RUN_ID,
        "category": "release_qualification_gap",
        "evidence_link_ids": evidence_link_ids,
        "disposition_state": "under_review",
        "summary": "Render dashboard Build Command drift.",
        "payload_hash": "sha256:" + "0" * 64,
        "payload": {},
        "classification": "internal",
        "created_at": "2026-09-14T00:05:00Z",
        "updated_at": "2026-09-14T00:05:00Z",
    }
    payload.update(overrides)
    return payload


def disposition_payload(*, candidate_id: str, **overrides) -> dict:
    payload = {
        "schema_version": "forge.df_rf_disposition.v1",
        "disposition_id": str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "operator_id": "charlie.boswell",
        "decision": "accepted",
        "rationale": "Confirmed real drift.",
        "evidence_bundle_hash": "sha256:" + "1" * 64,
        "decided_at": "2026-09-14T00:10:00Z",
        "created_at": "2026-09-14T00:10:00Z",
    }
    payload.update(overrides)
    return payload


# ── verification_status: computed honestly by DataForge, never trusted ────────


def test_verification_status_is_verified_for_a_real_stored_receipt(db: Session) -> None:
    result_id = uuid.uuid4()
    receipt_id = uuid.uuid4()
    db.add(
        _make_check_result(result_id),
    )
    db.commit()
    db.add(_make_check_receipt(receipt_id, result_id))
    db.commit()

    body = _ingest(
        db,
        "df_rf_evidence_link",
        evidence_link_payload(upstream_record_id=str(receipt_id)),
    )
    stored = _get_evidence_link(db, body["record_id"])
    assert stored.verification_status == "verified"


def test_verification_status_is_verified_against_a_string_primary_key_column(
    db: Session,
) -> None:
    # Regression test for a real bug found and fixed while wiring up
    # MemoryConflict.v1: _compute_verification_status used to convert
    # upstream_record_id to a uuid.UUID object before querying, which works
    # for ForgeCheckRunReceipt.v1's Postgres UUID column but would silently
    # fail to match MemoryConflict.conflict_id, a plain String(64) column.
    conflict_id = str(uuid.uuid4())
    db.add(
        MemoryConflict(
            artifact_id=conflict_id,
            conflict_id=conflict_id,
            tenant_id="bds",
            subject_entity_id="repo:forge-memory",
            predicate="contract_authority",
            conflict_type="authority_conflict",
            operator_review_required=True,
            payload={"schema_version": "forge.memory_conflict.v1"},
        )
    )
    db.commit()

    body = _ingest(
        db,
        "df_rf_evidence_link",
        evidence_link_payload(
            upstream_family="MemoryConflict.v1", upstream_record_id=conflict_id
        ),
    )
    stored = _get_evidence_link(db, body["record_id"])
    assert stored.verification_status == "verified"


def test_verification_status_is_unverified_for_a_missing_memory_conflict(
    db: Session,
) -> None:
    body = _ingest(
        db,
        "df_rf_evidence_link",
        evidence_link_payload(
            upstream_family="MemoryConflict.v1", upstream_record_id=str(uuid.uuid4())
        ),
    )
    stored = _get_evidence_link(db, body["record_id"])
    assert stored.verification_status == "unverified"


def test_verification_status_is_unverified_for_a_missing_receipt(db: Session) -> None:
    body = _ingest(
        db,
        "df_rf_evidence_link",
        evidence_link_payload(upstream_record_id=str(uuid.uuid4())),
    )
    stored = _get_evidence_link(db, body["record_id"])
    assert stored.verification_status == "unverified"


def test_verification_status_is_unavailable_for_an_unqueryable_family(db: Session) -> None:
    body = _ingest(
        db,
        "df_rf_evidence_link",
        evidence_link_payload(upstream_family="TelemetryEmitReceipt.v1"),
    )
    stored = _get_evidence_link(db, body["record_id"])
    assert stored.verification_status == "verification_unavailable"


def test_caller_claimed_verification_status_is_ignored(db: Session) -> None:
    # The fixture payload claims "verified" but the receipt doesn't exist --
    # DataForge must compute its own answer, never trust the caller's claim.
    body = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    stored = _get_evidence_link(db, body["record_id"])
    assert stored.verification_status == "unverified"


# ── candidate_id: deterministic from natural_key, not caller-chosen ───────────


def test_candidate_id_is_deterministic_from_natural_key(db: Session) -> None:
    link_body = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    link_id = link_body["record_id"]

    expected_id = str(
        uuid.uuid5(DF_RF_NAMESPACE, "rmcp_fc_gir_render_incident|render-build-drift-0001")
    )

    body = _ingest(
        db,
        "df_rf_finding_candidate",
        candidate_payload(natural_key="render-build-drift-0001", evidence_link_ids=[link_id]),
    )
    assert body["record_id"] == expected_id
    assert body["record_id"] != candidate_payload(
        natural_key="x", evidence_link_ids=[link_id]
    )["candidate_id"]


def test_redelivering_the_same_natural_key_updates_not_duplicates(db: Session) -> None:
    link_body = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    link_id = link_body["record_id"]

    first = _ingest(
        db,
        "df_rf_finding_candidate",
        candidate_payload(
            natural_key="render-build-drift-0002",
            evidence_link_ids=[link_id],
            summary="Initial detection.",
        ),
    )
    second = _ingest(
        db,
        "df_rf_finding_candidate",
        candidate_payload(
            natural_key="render-build-drift-0002",
            evidence_link_ids=[link_id],
            summary="Confirmed after re-check.",
        ),
    )
    assert first["record_id"] == second["record_id"]
    assert second["storage_status"] == "stored"

    from app.models.df_rf_models import DfRfFindingCandidateRecord

    row = (
        db.query(DfRfFindingCandidateRecord)
        .filter(DfRfFindingCandidateRecord.candidate_id == first["record_id"])
        .first()
    )
    assert row.summary == "Confirmed after re-check."


def test_identical_redelivery_is_a_duplicate(db: Session) -> None:
    link_body = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    link_id = link_body["record_id"]
    payload = candidate_payload(natural_key="render-build-drift-0003", evidence_link_ids=[link_id])

    first = _ingest(db, "df_rf_finding_candidate", dict(payload))
    second = _ingest(db, "df_rf_finding_candidate", dict(payload))
    assert first["storage_status"] == "stored"
    assert second["storage_status"] == "duplicate"
    assert first["record_id"] == second["record_id"]


# ── Referential integrity ──────────────────────────────────────────────────────


def test_candidate_requires_non_empty_evidence_link_ids(db: Session) -> None:
    with pytest.raises(DfRfValidationError, match="evidence_link_ids is required"):
        _ingest(
            db,
            "df_rf_finding_candidate",
            candidate_payload(natural_key="empty-evidence-0001", evidence_link_ids=[]),
        )


def test_evidence_link_requires_upstream_family_and_record_id(db: Session) -> None:
    payload = evidence_link_payload()
    del payload["upstream_family"]
    with pytest.raises(DfRfValidationError, match="upstream_family and upstream_record_id"):
        _ingest(db, "df_rf_evidence_link", payload)


def test_malformed_upstream_record_id_is_unverified_not_a_crash(db: Session) -> None:
    body = _ingest(
        db,
        "df_rf_evidence_link",
        evidence_link_payload(upstream_record_id="not-a-uuid"),
    )
    stored = _get_evidence_link(db, body["record_id"])
    assert stored.verification_status == "unverified"


def test_malformed_observed_at_timestamp_is_rejected(db: Session) -> None:
    with pytest.raises(DfRfValidationError, match="observed_at must be an ISO 8601"):
        _ingest(db, "df_rf_evidence_link", evidence_link_payload(observed_at="not-a-date"))


def test_candidate_requires_existing_evidence_links(db: Session) -> None:
    with pytest.raises(DfRfValidationError, match="missing evidence link"):
        _ingest(
            db,
            "df_rf_finding_candidate",
            candidate_payload(natural_key="orphan-0001", evidence_link_ids=[str(uuid.uuid4())]),
        )


def test_disposition_requires_existing_candidate(db: Session) -> None:
    with pytest.raises(DfRfValidationError, match="missing finding candidate"):
        _ingest(db, "df_rf_disposition", disposition_payload(candidate_id=str(uuid.uuid4())))


# ── Idempotent evidence_link / disposition ingest (immutable, unlike candidate) ─


def test_evidence_link_conflict_on_same_id_different_payload(db: Session) -> None:
    payload = evidence_link_payload()
    _ingest(db, "df_rf_evidence_link", dict(payload))
    payload["source_plan_id"] = "BDS-FPRS-v0.1"
    with pytest.raises(DfRfConflictError):
        _ingest(db, "df_rf_evidence_link", payload)


# ── OD-02: terminal candidate, no promotion path exists to test against ───────


def test_disposition_decision_enum_rejects_promotion_vocabulary(db: Session) -> None:
    link_body = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    candidate_body = _ingest(
        db,
        "df_rf_finding_candidate",
        candidate_payload(natural_key="promo-test-0001", evidence_link_ids=[link_body["record_id"]]),
    )
    with pytest.raises(DfRfValidationError):
        _ingest(
            db,
            "df_rf_disposition",
            disposition_payload(
                candidate_id=candidate_body["record_id"], decision="approved_for_promotion"
            ),
        )


def test_accepted_disposition_closes_the_candidate(db: Session) -> None:
    link_body = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    candidate_body = _ingest(
        db,
        "df_rf_finding_candidate",
        candidate_payload(natural_key="close-test-0001", evidence_link_ids=[link_body["record_id"]]),
    )
    _ingest(db, "df_rf_disposition", disposition_payload(candidate_id=candidate_body["record_id"]))

    from app.models.df_rf_models import DfRfFindingCandidateRecord

    row = (
        db.query(DfRfFindingCandidateRecord)
        .filter(DfRfFindingCandidateRecord.candidate_id == candidate_body["record_id"])
        .first()
    )
    assert row.disposition_state == "accepted"


# ── Review feed ─────────────────────────────────────────────────────────────────


def test_review_feed_excludes_closed_candidates_and_shows_verification_status(
    db: Session,
) -> None:
    open_link = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    open_candidate = _ingest(
        db,
        "df_rf_finding_candidate",
        candidate_payload(natural_key="feed-open-0001", evidence_link_ids=[open_link["record_id"]]),
    )

    closed_link = _ingest(db, "df_rf_evidence_link", evidence_link_payload())
    closed_candidate = _ingest(
        db,
        "df_rf_finding_candidate",
        candidate_payload(
            natural_key="feed-closed-0001", evidence_link_ids=[closed_link["record_id"]]
        ),
    )
    _ingest(
        db, "df_rf_disposition", disposition_payload(candidate_id=closed_candidate["record_id"])
    )

    feed = list_candidate_review_feed(db, run_id=RUN_ID)
    candidate_ids = {item.candidate_id for item in feed}
    assert open_candidate["record_id"] in candidate_ids
    assert closed_candidate["record_id"] not in candidate_ids

    item = next(i for i in feed if i.candidate_id == open_candidate["record_id"])
    assert item.evidence_verification_statuses[open_link["record_id"]] == "unverified"
    assert item.disposition is None


def _make_check_result(result_id: uuid.UUID):
    from app.models.telemetry_models import ForgeCheckResultV1Record

    now = datetime.now(timezone.utc)
    return ForgeCheckResultV1Record(
        result_id=result_id,
        payload_digest="a" * 64,
        payload={},
        run_id=uuid.uuid4(),
        check_id="check-df-rf-test",
        check_revision=1,
        definition_sha256="b" * 64,
        environment="test",
        evaluation_mode="advisory",
        status="pass",
        reason_code="ok",
        started_at=now,
        finished_at=now,
        duration_ms=1,
        slo_included=False,
        uptime_included=False,
        baseline_included=False,
        cost_units_observed=0,
        privacy_class="internal",
    )


def _make_check_receipt(receipt_id: uuid.UUID, result_id: uuid.UUID) -> ForgeCheckRunReceiptV1Record:
    now = datetime.now(timezone.utc)
    return ForgeCheckRunReceiptV1Record(
        receipt_id=receipt_id,
        payload_digest="a" * 64,
        payload={},
        run_id=uuid.uuid4(),
        result_id=result_id,
        check_id="check-df-rf-test",
        definition_sha256="b" * 64,
        environment="test",
        source_repository="Boswell-Digital-Solutions/Forge_Command",
        source_commit="c" * 40,
        source_path="ci/check.yml",
        runner_service_name="forge-agents",
        runner_version="1.0.0",
        trigger="ci",
        evaluation_mode="advisory",
        status="pass",
        started_at=now,
        observed_at=now,
        slo_included=False,
        uptime_included=False,
        baseline_included=False,
        slo_reason="not_applicable",
        max_cost_units=0,
        observed_cost_units=0,
        cost_unit="units",
        kill_switch_ref="none",
        kill_switch_enabled=False,
        evidence_refs=[],
    )


def _get_evidence_link(db: Session, evidence_link_id: str):
    from app.models.df_rf_models import DfRfEvidenceLinkRecord

    return (
        db.query(DfRfEvidenceLinkRecord)
        .filter(DfRfEvidenceLinkRecord.evidence_link_id == evidence_link_id)
        .first()
    )
