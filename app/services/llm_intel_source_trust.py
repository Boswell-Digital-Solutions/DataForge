"""LLM provider intelligence source trust registry.

Slice 02 is intentionally static and deterministic: DataForge owns the
approved source registry and validates source authority, but it does not fetch
or scrape any source content here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_CONTRACT_CORE = (
    Path(__file__).parent.parent.parent.parent.parent
    / "contracts"
    / "forge-contract-core"
)
if str(_CONTRACT_CORE) not in sys.path:
    sys.path.insert(0, str(_CONTRACT_CORE))

from forge_contract_core.validators.families import (  # noqa: E402
    FamilyValidationError,
    validate_family_payload,
)


OFFICIAL_REQUIRED_CLAIM_TYPES = frozenset(
    {
        "pricing",
        "model_availability",
        "deprecation",
        "terms_safety",
    }
)

LLM_PROVIDER_IDS = frozenset(
    {
        "openai",
        "anthropic",
        "google",
        "xai",
        "deepseek",
        "ollama",
    }
)


@dataclass(frozen=True)
class SourceTrustPolicy:
    trust_class: str
    promotion_authority: str
    can_enter_extraction: bool
    can_support_candidate_promotion: bool
    candidate_disposition: str


@dataclass(frozen=True)
class ApprovedSource:
    source_id: str
    provider_id: str
    source_url: str
    source_type: str
    trust_class: str
    approved_for_extraction: bool
    supports_candidate_promotion: bool
    approved_by: str
    approved_at: str
    review_notes: str | None = None

    @property
    def source_registry_hash(self) -> str:
        return _stable_hash(
            {
                "source_id": self.source_id,
                "provider_id": self.provider_id,
                "source_url": self.source_url,
                "source_type": self.source_type,
                "trust_class": self.trust_class,
                "approved_for_extraction": self.approved_for_extraction,
                "supports_candidate_promotion": self.supports_candidate_promotion,
                "approved_by": self.approved_by,
                "approved_at": self.approved_at,
                "review_notes": self.review_notes,
            }
        )

    def to_contract_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "llm_intel.approved_source.v1",
            "source_id": self.source_id,
            "provider_id": self.provider_id,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "trust_class": self.trust_class,
            "approved_for_extraction": self.approved_for_extraction,
            "supports_candidate_promotion": self.supports_candidate_promotion,
            "source_registry_hash": self.source_registry_hash,
            "approved_at": self.approved_at,
            "approved_by": self.approved_by,
            "review_notes": self.review_notes,
        }


@dataclass(frozen=True)
class SourceTrustDecision:
    allowed: bool
    outcome: str
    reason: str
    source_id: str | None = None
    provider_id: str | None = None
    trust_class: str | None = None
    requires_review: bool = False
    requires_maid: bool = False
    can_support_promotion: bool = False


class SourceTrustRegistryError(ValueError):
    """Raised when a source trust registry entry is invalid."""


SOURCE_TRUST_POLICIES: dict[str, SourceTrustPolicy] = {
    "OFFICIAL": SourceTrustPolicy(
        trust_class="OFFICIAL",
        promotion_authority="can_support_promotion",
        can_enter_extraction=True,
        can_support_candidate_promotion=True,
        candidate_disposition="candidate_supported",
    ),
    "TRUSTED_SECONDARY": SourceTrustPolicy(
        trust_class="TRUSTED_SECONDARY",
        promotion_authority="review_trigger_only",
        can_enter_extraction=True,
        can_support_candidate_promotion=False,
        candidate_disposition="review_required",
    ),
    "ADVISORY": SourceTrustPolicy(
        trust_class="ADVISORY",
        promotion_authority="investigation_note_only",
        can_enter_extraction=False,
        can_support_candidate_promotion=False,
        candidate_disposition="investigation_note_only",
    ),
    "BLOCKED": SourceTrustPolicy(
        trust_class="BLOCKED",
        promotion_authority="audit_only",
        can_enter_extraction=False,
        can_support_candidate_promotion=False,
        candidate_disposition="blocked",
    ),
}


APPROVED_SOURCE_REGISTRY: tuple[ApprovedSource, ...] = (
    ApprovedSource(
        source_id="src-openai-pricing-official",
        provider_id="openai",
        source_url="https://platform.openai.com/docs/pricing/",
        source_type="pricing",
        trust_class="OFFICIAL",
        approved_for_extraction=True,
        supports_candidate_promotion=True,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Official OpenAI API pricing source.",
    ),
    ApprovedSource(
        source_id="src-anthropic-pricing-official",
        provider_id="anthropic",
        source_url="https://platform.claude.com/docs/en/about-claude/pricing",
        source_type="pricing",
        trust_class="OFFICIAL",
        approved_for_extraction=True,
        supports_candidate_promotion=True,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Official Claude API pricing source.",
    ),
    ApprovedSource(
        source_id="src-google-gemini-pricing-official",
        provider_id="google",
        source_url="https://ai.google.dev/gemini-api/docs/pricing",
        source_type="pricing",
        trust_class="OFFICIAL",
        approved_for_extraction=True,
        supports_candidate_promotion=True,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Official Gemini API pricing source.",
    ),
    ApprovedSource(
        source_id="src-xai-models-official",
        provider_id="xai",
        source_url="https://docs.x.ai/developers/models",
        source_type="model_card",
        trust_class="OFFICIAL",
        approved_for_extraction=True,
        supports_candidate_promotion=True,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Official xAI models and pricing source.",
    ),
    ApprovedSource(
        source_id="src-deepseek-pricing-official",
        provider_id="deepseek",
        source_url="https://api-docs.deepseek.com/quick_start/pricing-details-usd",
        source_type="pricing",
        trust_class="OFFICIAL",
        approved_for_extraction=True,
        supports_candidate_promotion=True,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Official DeepSeek pricing source.",
    ),
    ApprovedSource(
        source_id="src-ollama-api-official",
        provider_id="ollama",
        source_url="https://docs.ollama.com/api/introduction",
        source_type="api_reference",
        trust_class="OFFICIAL",
        approved_for_extraction=True,
        supports_candidate_promotion=True,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Official Ollama API reference source.",
    ),
    ApprovedSource(
        source_id="src-transparent-benchmark-secondary",
        provider_id="openai",
        source_url="https://example.org/llm-benchmark-methodology",
        source_type="benchmark",
        trust_class="TRUSTED_SECONDARY",
        approved_for_extraction=True,
        supports_candidate_promotion=False,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Trusted secondary benchmark placeholder for review triggers.",
    ),
    ApprovedSource(
        source_id="src-community-advisory-note",
        provider_id="xai",
        source_url="https://example.org/community/provider-note",
        source_type="community_advisory",
        trust_class="ADVISORY",
        approved_for_extraction=False,
        supports_candidate_promotion=False,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Advisory placeholder. Investigation note only.",
    ),
    ApprovedSource(
        source_id="src-blocked-provider-mirror",
        provider_id="anthropic",
        source_url="https://mirror.example.invalid/provider-doc-copy",
        source_type="blocked",
        trust_class="BLOCKED",
        approved_for_extraction=False,
        supports_candidate_promotion=False,
        approved_by="DataForge/llm_intel.seed_registry@slice02",
        approved_at="2026-05-28T00:00:00Z",
        review_notes="Blocked unverifiable mirror placeholder.",
    ),
)


def list_source_trust_policies() -> tuple[SourceTrustPolicy, ...]:
    return tuple(SOURCE_TRUST_POLICIES[key] for key in sorted(SOURCE_TRUST_POLICIES))


def list_approved_sources(
    *,
    provider_id: str | None = None,
    trust_class: str | None = None,
    include_blocked: bool = False,
) -> tuple[ApprovedSource, ...]:
    sources = APPROVED_SOURCE_REGISTRY
    if provider_id is not None:
        sources = tuple(source for source in sources if source.provider_id == provider_id)
    if trust_class is not None:
        sources = tuple(source for source in sources if source.trust_class == trust_class)
    if not include_blocked:
        sources = tuple(source for source in sources if source.trust_class != "BLOCKED")
    return sources


def get_approved_source(source_id: str) -> ApprovedSource | None:
    for source in APPROVED_SOURCE_REGISTRY:
        if source.source_id == source_id:
            return source
    return None


def registry_hash() -> str:
    return _stable_hash([source.to_contract_payload() for source in APPROVED_SOURCE_REGISTRY])


def validate_registry() -> None:
    seen: set[str] = set()
    for source in APPROVED_SOURCE_REGISTRY:
        if source.source_id in seen:
            raise SourceTrustRegistryError(f"duplicate source_id {source.source_id!r}")
        seen.add(source.source_id)
        validate_approved_source(source)

    missing_providers = LLM_PROVIDER_IDS - {
        source.provider_id for source in APPROVED_SOURCE_REGISTRY if source.trust_class == "OFFICIAL"
    }
    if missing_providers:
        raise SourceTrustRegistryError(
            f"missing official source coverage for providers: {sorted(missing_providers)}"
        )


def validate_approved_source(source: ApprovedSource) -> None:
    if source.trust_class not in SOURCE_TRUST_POLICIES:
        raise SourceTrustRegistryError(f"unknown trust class {source.trust_class!r}")

    policy = SOURCE_TRUST_POLICIES[source.trust_class]
    if source.approved_for_extraction and not policy.can_enter_extraction:
        raise SourceTrustRegistryError(
            f"{source.trust_class} source {source.source_id!r} cannot enter extraction"
        )

    try:
        validate_family_payload("llm_intel_approved_source", 1, source.to_contract_payload())
    except FamilyValidationError as exc:
        raise SourceTrustRegistryError(
            f"approved source {source.source_id!r} failed canonical validation: {exc.errors}"
        ) from exc


def validate_source_for_claim(source_id: str, claim_type: str) -> SourceTrustDecision:
    source = get_approved_source(source_id)
    if source is None:
        return SourceTrustDecision(
            allowed=False,
            outcome="unknown_source",
            reason=f"source_id {source_id!r} is not approved",
            source_id=source_id,
        )
    return _decision_for_sources((source,), claim_type)


def validate_sources_for_claim(source_ids: list[str], claim_type: str) -> SourceTrustDecision:
    sources: list[ApprovedSource] = []
    for source_id in source_ids:
        source = get_approved_source(source_id)
        if source is None:
            return SourceTrustDecision(
                allowed=False,
                outcome="unknown_source",
                reason=f"source_id {source_id!r} is not approved",
                source_id=source_id,
            )
        sources.append(source)
    return _decision_for_sources(tuple(sources), claim_type)


def _decision_for_sources(
    sources: tuple[ApprovedSource, ...],
    claim_type: str,
) -> SourceTrustDecision:
    if not sources:
        return SourceTrustDecision(
            allowed=False,
            outcome="missing_source",
            reason="at least one approved source is required",
        )

    blocked = next((source for source in sources if source.trust_class == "BLOCKED"), None)
    if blocked is not None:
        return SourceTrustDecision(
            allowed=False,
            outcome="blocked_before_extraction",
            reason="BLOCKED sources are ignored except for audit logging",
            source_id=blocked.source_id,
            provider_id=blocked.provider_id,
            trust_class=blocked.trust_class,
        )

    official = next((source for source in sources if source.trust_class == "OFFICIAL"), None)
    if official is not None:
        return SourceTrustDecision(
            allowed=True,
            outcome="candidate_supported",
            reason="OFFICIAL source evidence can support candidate creation",
            source_id=official.source_id,
            provider_id=official.provider_id,
            trust_class=official.trust_class,
            can_support_promotion=True,
        )

    if claim_type in OFFICIAL_REQUIRED_CLAIM_TYPES:
        strongest = sources[0]
        return SourceTrustDecision(
            allowed=False,
            outcome="official_source_required",
            reason=f"{claim_type} claims require OFFICIAL source evidence",
            source_id=strongest.source_id,
            provider_id=strongest.provider_id,
            trust_class=strongest.trust_class,
            requires_review=True,
        )

    trusted = next((source for source in sources if source.trust_class == "TRUSTED_SECONDARY"), None)
    if trusted is not None:
        return SourceTrustDecision(
            allowed=False,
            outcome="review_required",
            reason="TRUSTED_SECONDARY sources may trigger review but cannot promote alone",
            source_id=trusted.source_id,
            provider_id=trusted.provider_id,
            trust_class=trusted.trust_class,
            requires_review=True,
            requires_maid=True,
        )

    advisory = sources[0]
    return SourceTrustDecision(
        allowed=False,
        outcome="investigation_note_only",
        reason="ADVISORY sources may create investigation notes only",
        source_id=advisory.source_id,
        provider_id=advisory.provider_id,
        trust_class=advisory.trust_class,
        requires_review=True,
    )


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
