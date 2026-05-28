"""Tests for LLM provider intelligence source trust registry."""

from __future__ import annotations

import pytest

from app.api.llm_intel_source_trust_router import approved_sources, validate_source_trust
from app.models.llm_intel_schemas import SourceTrustValidationRequest
from app.services.llm_intel_source_trust import (
    LLM_PROVIDER_IDS,
    SourceTrustRegistryError,
    get_approved_source,
    list_approved_sources,
    registry_hash,
    validate_approved_source,
    validate_registry,
    validate_source_for_claim,
    validate_sources_for_claim,
)


@pytest.mark.unit
def test_registry_validates_against_contract_core() -> None:
    validate_registry()


@pytest.mark.unit
def test_registry_has_official_source_for_each_initial_provider() -> None:
    official_providers = {
        source.provider_id
        for source in list_approved_sources(trust_class="OFFICIAL")
    }

    assert LLM_PROVIDER_IDS.issubset(official_providers)


@pytest.mark.unit
def test_registry_includes_deepseek_official_source() -> None:
    source = get_approved_source("src-deepseek-pricing-official")

    assert source is not None
    assert source.provider_id == "deepseek"
    assert source.trust_class == "OFFICIAL"
    assert source.supports_candidate_promotion is True


@pytest.mark.unit
def test_official_source_supports_candidate_creation() -> None:
    decision = validate_source_for_claim("src-openai-pricing-official", "pricing")

    assert decision.allowed is True
    assert decision.outcome == "candidate_supported"
    assert decision.can_support_promotion is True


@pytest.mark.unit
def test_trusted_secondary_triggers_review_only() -> None:
    decision = validate_source_for_claim("src-transparent-benchmark-secondary", "capability")

    assert decision.allowed is False
    assert decision.outcome == "review_required"
    assert decision.requires_review is True
    assert decision.requires_maid is True


@pytest.mark.unit
def test_advisory_creates_investigation_note_only() -> None:
    decision = validate_source_for_claim("src-community-advisory-note", "capability")

    assert decision.allowed is False
    assert decision.outcome == "investigation_note_only"
    assert decision.requires_review is True


@pytest.mark.unit
def test_blocked_source_is_rejected_before_extraction() -> None:
    decision = validate_source_for_claim("src-blocked-provider-mirror", "pricing")

    assert decision.allowed is False
    assert decision.outcome == "blocked_before_extraction"
    assert decision.trust_class == "BLOCKED"


@pytest.mark.unit
@pytest.mark.parametrize("claim_type", ["pricing", "model_availability", "deprecation", "terms_safety"])
def test_truth_critical_claim_types_require_official_evidence(claim_type: str) -> None:
    decision = validate_sources_for_claim(["src-transparent-benchmark-secondary"], claim_type)

    assert decision.allowed is False
    assert decision.outcome == "official_source_required"
    assert "OFFICIAL" in decision.reason


@pytest.mark.unit
def test_official_plus_secondary_evidence_can_support_candidate() -> None:
    decision = validate_sources_for_claim(
        ["src-transparent-benchmark-secondary", "src-openai-pricing-official"],
        "pricing",
    )

    assert decision.allowed is True
    assert decision.outcome == "candidate_supported"


@pytest.mark.unit
def test_registry_hash_is_stable() -> None:
    assert registry_hash() == registry_hash()
    assert registry_hash().startswith("sha256:")


@pytest.mark.unit
def test_source_validation_rejects_advisory_extraction_misconfiguration() -> None:
    source = get_approved_source("src-community-advisory-note")
    assert source is not None
    mutated = source.__class__(
        source_id=source.source_id,
        provider_id=source.provider_id,
        source_url=source.source_url,
        source_type=source.source_type,
        trust_class=source.trust_class,
        approved_for_extraction=True,
        supports_candidate_promotion=source.supports_candidate_promotion,
        approved_by=source.approved_by,
        approved_at=source.approved_at,
        review_notes=source.review_notes,
    )

    with pytest.raises(SourceTrustRegistryError):
        validate_approved_source(mutated)


@pytest.mark.unit
def test_source_trust_api_lists_approved_sources() -> None:
    response = approved_sources(provider_id=None, trust_class=None, include_blocked=False)

    assert response.total >= 6
    assert response.registry_hash.startswith("sha256:")
    assert all(item.trust_class != "BLOCKED" for item in response.items)


@pytest.mark.unit
def test_source_trust_api_validates_pricing_claim() -> None:
    response = validate_source_trust(
        SourceTrustValidationRequest(
            source_ids=["src-openai-pricing-official"],
            claim_type="pricing",
        )
    )

    assert response.allowed is True
    assert response.outcome == "candidate_supported"
