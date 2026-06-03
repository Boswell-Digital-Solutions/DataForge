from __future__ import annotations

import copy
import hashlib
import json

import pytest
from sqlalchemy.orm import Session

from app.models.llm_intel_pending_records_schemas import LLMIntelPendingRecordIngestRequest
from app.services.llm_intel_pending_records import (
    PendingRecordConflictError,
    PendingRecordValidationError,
    build_run_summary,
    list_candidate_review_feed,
    store_pending_record,
)


RUN_ID = "run-weekly-2026-05-28"
TIMESTAMP = "2026-05-28T00:00:00Z"
CONTENT_HASH = "sha256:" + "a" * 64
SOURCE_ID = "src-deepseek-pricing-official"
SOURCE_URL = "https://api-docs.deepseek.com/quick_start/pricing-details-usd"
FINGERPRINT_ID = "fingerprint-deepseek-pricing-001"
FETCH_RECEIPT_ID = "fetch-deepseek-pricing-001"
ADAPTER_RECEIPT_ID = "adapter-deepseek-pricing-001"
CLAIM_ID = "claim-deepseek-pricing-001"
CANDIDATE_ID = "candidate-deepseek-pricing-001"
DRIFT_REPORT_ID = "drift-deepseek-pricing-001"
REPLAY_MANIFEST_ID = "replay-deepseek-pricing-001"


def _hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _post_record(db: Session, record_family: str, payload: dict) -> dict:
    response = store_pending_record(
        db,
        LLMIntelPendingRecordIngestRequest(
            record_family=record_family,
            run_id=RUN_ID,
            payload=payload,
        ),
    )
    body = response.model_dump()
    assert body["record_family"] == record_family
    assert body["promotion_application_allowed"] is False
    return body


def source_fingerprint(**overrides) -> dict:
    payload = {
        "schema_version": "llm_intel.source_fingerprint.v1",
        "fingerprint_id": FINGERPRINT_ID,
        "source_id": SOURCE_ID,
        "provider_id": "deepseek",
        "source_url": SOURCE_URL,
        "trust_class": "OFFICIAL",
        "content_hash": CONTENT_HASH,
        "content_length": 4096,
        "captured_at": TIMESTAMP,
        "adapter_id": "deepseek_adapter",
        "adapter_version": "fixture.2026-05-28",
    }
    payload.update(overrides)
    return payload


def fetch_receipt(**overrides) -> dict:
    payload = {
        "schema_version": "llm_intel.fetch_receipt.v1",
        "fetch_receipt_id": FETCH_RECEIPT_ID,
        "run_id": RUN_ID,
        "source_id": SOURCE_ID,
        "provider_id": "deepseek",
        "source_url": SOURCE_URL,
        "trust_class": "OFFICIAL",
        "fetch_status": "succeeded",
        "fetched_at": TIMESTAMP,
        "resolved_url": SOURCE_URL,
        "http_status": 200,
        "content_hash": CONTENT_HASH,
        "fetch_attempt_hash": _hash({"fetch": FETCH_RECEIPT_ID}),
        "error_class": None,
        "error_message": None,
    }
    payload.update(overrides)
    return payload


def adapter_receipt(**overrides) -> dict:
    payload = {
        "schema_version": "llm_intel.provider_adapter_receipt.v1",
        "receipt_id": ADAPTER_RECEIPT_ID,
        "run_id": RUN_ID,
        "provider_id": "deepseek",
        "adapter_id": "deepseek_adapter",
        "adapter_version": "fixture.2026-05-28",
        "profile_id": "profile-deepseek-pricing",
        "status": "succeeded",
        "source_fingerprint_id": FINGERPRINT_ID,
        "input_hash": _hash({"input": FINGERPRINT_ID}),
        "output_hash": _hash({"output": CLAIM_ID}),
        "started_at": TIMESTAMP,
        "finished_at": TIMESTAMP,
        "failure_reason": None,
    }
    payload.update(overrides)
    return payload


def extracted_claim(**overrides) -> dict:
    payload = {
        "schema_version": "llm_intel.extracted_claim.v1",
        "claim_id": CLAIM_ID,
        "run_id": RUN_ID,
        "provider_id": "deepseek",
        "claim_type": "pricing",
        "claim_path": "models.deepseek-chat.pricing.input_per_1m_tokens",
        "claimed_value": {
            "model": "deepseek-chat",
            "currency": "USD",
            "unit": "1m_input_tokens",
            "amount": 0.27,
        },
        "source_evidence": [
            {
                "source_id": SOURCE_ID,
                "trust_class": "OFFICIAL",
                "source_url": SOURCE_URL,
                "content_hash": CONTENT_HASH,
                "anchor": "deepseek-chat pricing",
            }
        ],
        "adapter_id": "deepseek_adapter",
        "adapter_version": "fixture.2026-05-28",
        "extractor_version": "fixture.2026-05-28",
        "extraction_confidence": "high",
    }
    payload.update(overrides)
    return payload


def pricing_candidate(**overrides) -> dict:
    payload = {
        "schema_version": "llm_intel.pricing_candidate.v1",
        "candidate_id": CANDIDATE_ID,
        "run_id": RUN_ID,
        "provider_id": "deepseek",
        "candidate_type": "pricing",
        "claim_type": "pricing",
        "claim_path": "models.deepseek-chat.pricing.input_per_1m_tokens",
        "claim_ids": [CLAIM_ID],
        "source_fingerprint_ids": [FINGERPRINT_ID],
        "receipt_ids": [FETCH_RECEIPT_ID, ADAPTER_RECEIPT_ID],
        "candidate_value": {
            "model": "deepseek-chat",
            "currency": "USD",
            "unit": "1m_input_tokens",
            "amount": 0.27,
        },
        "promotion_state": "candidate_detected",
    }
    payload.update(overrides)
    return payload


def drift_report(**overrides) -> dict:
    old_value = {
        "model": "deepseek-chat",
        "currency": "USD",
        "unit": "1m_input_tokens",
        "amount": 0.14,
    }
    candidate_value = {
        "model": "deepseek-chat",
        "currency": "USD",
        "unit": "1m_input_tokens",
        "amount": 0.27,
    }
    payload = {
        "schema_version": "llm_intel.drift_report.v1",
        "drift_report_id": DRIFT_REPORT_ID,
        "run_id": RUN_ID,
        "provider_id": "deepseek",
        "candidate_id": CANDIDATE_ID,
        "claim_ids": [CLAIM_ID],
        "drift_type": "pricing",
        "impact_class": "medium",
        "old_value": old_value,
        "candidate_value": candidate_value,
        "old_value_hash": _hash(old_value),
        "candidate_value_hash": _hash(candidate_value),
        "source_evidence": [
            {
                "source_id": SOURCE_ID,
                "trust_class": "OFFICIAL",
                "content_hash": CONTENT_HASH,
                "observed_at": TIMESTAMP,
            }
        ],
        "adapter_version": "fixture.2026-05-28",
        "extractor_version": "fixture.2026-05-28",
        "requires_maid": False,
        "maid_result_ref": None,
        "conflict_status": "no_conflict",
        "promotion_state": "drift_classified",
    }
    payload.update(overrides)
    return payload


def replay_manifest(**overrides) -> dict:
    payload = {
        "schema_version": "llm_intel.replay_manifest.v1",
        "replay_manifest_id": REPLAY_MANIFEST_ID,
        "run_id": RUN_ID,
        "manifest_status": "pending",
        "source_fingerprint_ids": [FINGERPRINT_ID],
        "fetch_receipt_ids": [FETCH_RECEIPT_ID],
        "adapter_receipt_ids": [ADAPTER_RECEIPT_ID],
        "claim_ids": [CLAIM_ID],
        "candidate_ids": [CANDIDATE_ID],
        "drift_report_ids": [DRIFT_REPORT_ID],
        "input_manifest_hash": _hash({"input_manifest": RUN_ID}),
        "output_manifest_hash": None,
        "replay_determinism_hash": _hash({"determinism": RUN_ID}),
        "created_at": TIMESTAMP,
    }
    payload.update(overrides)
    return payload


def ingest_full_pending_record_set(db: Session) -> None:
    _post_record(db, "llm_intel_source_fingerprints", source_fingerprint())
    _post_record(db, "llm_intel_fetch_receipts", fetch_receipt())
    _post_record(db, "llm_intel_provider_adapter_receipts", adapter_receipt())
    _post_record(db, "llm_intel_extracted_claims", extracted_claim())
    _post_record(db, "llm_intel_pricing_candidates", pricing_candidate())
    _post_record(db, "llm_intel_drift_reports", drift_report())
    _post_record(db, "llm_intel_replay_manifests", replay_manifest())


@pytest.mark.unit
def test_candidate_review_feed_enriches_with_drift_and_trust(db: Session) -> None:
    ingest_full_pending_record_set(db)

    items = list_candidate_review_feed(db)
    assert len(items) == 1
    item = items[0]
    assert item.candidate_id == CANDIDATE_ID
    assert item.provider_id == "deepseek"
    assert item.candidate_value["amount"] == 0.27  # the new (extracted) price
    assert item.old_value is not None and item.old_value["amount"] == 0.14  # prior truth
    assert item.impact_class == "medium"
    assert item.drift_report_id == DRIFT_REPORT_ID
    assert item.trust_classes == ["OFFICIAL"]
    assert item.has_official_source is True
    assert item.review_packet_id == f"review-{CANDIDATE_ID}"
    assert SOURCE_URL in item.source_urls


@pytest.mark.unit
def test_candidate_review_feed_filters_by_provider(db: Session) -> None:
    ingest_full_pending_record_set(db)

    assert list_candidate_review_feed(db, provider_id="deepseek")
    assert list_candidate_review_feed(db, provider_id="openai") == []


@pytest.mark.unit
def test_candidate_review_feed_excludes_non_reviewable_states(db: Session) -> None:
    ingest_full_pending_record_set(db)
    # Default reviewable set excludes terminal states; restricting to one excludes ours.
    assert list_candidate_review_feed(db, states={"promoted"}) == []


@pytest.mark.unit
def test_pending_record_store_persists_receipts_candidates_drift_and_replay(
    db: Session,
) -> None:
    ingest_full_pending_record_set(db)

    summary = build_run_summary(db, RUN_ID).model_dump()

    assert summary["promotion_application_allowed"] is False
    assert summary["record_counts"] == {
        "llm_intel_receipts": 2,
        "llm_intel_source_fingerprints": 1,
        "llm_intel_extracted_claims": 1,
        "llm_intel_pending_candidates": 1,
        "llm_intel_drift_reports": 1,
        "llm_intel_replay_manifests": 1,
    }
    assert summary["receipt_ids"] == [ADAPTER_RECEIPT_ID, FETCH_RECEIPT_ID]
    assert summary["source_fingerprint_ids"] == [FINGERPRINT_ID]
    assert summary["claim_ids"] == [CLAIM_ID]
    assert summary["candidate_ids"] == [CANDIDATE_ID]
    assert summary["drift_report_ids"] == [DRIFT_REPORT_ID]
    assert summary["replay_manifest_ids"] == [REPLAY_MANIFEST_ID]


@pytest.mark.unit
def test_pending_record_ingest_is_idempotent_for_same_payload(db: Session) -> None:
    _post_record(db, "llm_intel_source_fingerprints", source_fingerprint())
    _post_record(db, "llm_intel_fetch_receipts", fetch_receipt())

    duplicate = _post_record(db, "llm_intel_fetch_receipts", fetch_receipt())

    assert duplicate["record_id"] == FETCH_RECEIPT_ID
    assert duplicate["storage_status"] == "duplicate"


@pytest.mark.unit
def test_pending_record_ingest_rejects_silent_overwrite(db: Session) -> None:
    ingest_full_pending_record_set(db)
    mutated_candidate = copy.deepcopy(pricing_candidate())
    mutated_candidate["candidate_value"]["amount"] = 0.99

    with pytest.raises(PendingRecordConflictError, match="already exists with different payload"):
        _post_record(db, "llm_intel_pricing_candidates", mutated_candidate)


@pytest.mark.unit
def test_pricing_candidate_requires_official_source_fingerprint(
    db: Session,
) -> None:
    secondary_fingerprint = source_fingerprint(
        fingerprint_id="fingerprint-secondary-001",
        source_id="src-transparent-benchmark-secondary",
        provider_id="openai",
        source_url="https://example.org/llm-benchmark-methodology",
        trust_class="TRUSTED_SECONDARY",
        adapter_id="openai_adapter",
    )
    secondary_fetch = fetch_receipt(
        fetch_receipt_id="fetch-secondary-001",
        source_id="src-transparent-benchmark-secondary",
        provider_id="openai",
        source_url="https://example.org/llm-benchmark-methodology",
        trust_class="TRUSTED_SECONDARY",
    )
    candidate = pricing_candidate(
        candidate_id="candidate-secondary-pricing-001",
        provider_id="openai",
        source_fingerprint_ids=["fingerprint-secondary-001"],
        receipt_ids=["fetch-secondary-001"],
        claim_ids=[],
    )

    _post_record(db, "llm_intel_source_fingerprints", secondary_fingerprint)
    _post_record(db, "llm_intel_fetch_receipts", secondary_fetch)

    with pytest.raises(PendingRecordValidationError, match="OFFICIAL source fingerprint"):
        _post_record(db, "llm_intel_pricing_candidates", candidate)


@pytest.mark.unit
def test_pending_candidate_cannot_be_promoted_by_pending_store(
    db: Session,
) -> None:
    _post_record(db, "llm_intel_source_fingerprints", source_fingerprint())
    _post_record(db, "llm_intel_fetch_receipts", fetch_receipt())
    _post_record(db, "llm_intel_provider_adapter_receipts", adapter_receipt())
    _post_record(db, "llm_intel_extracted_claims", extracted_claim())

    with pytest.raises(PendingRecordValidationError, match="pending candidate cannot enter state"):
        _post_record(
            db,
            "llm_intel_pricing_candidates",
            pricing_candidate(promotion_state="promoted"),
        )


@pytest.mark.unit
def test_replay_manifest_requires_existing_frozen_record_refs(db: Session) -> None:
    with pytest.raises(PendingRecordValidationError, match="missing source fingerprint"):
        _post_record(db, "llm_intel_replay_manifests", replay_manifest())
