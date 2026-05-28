"""Read-only source trust registry API for LLM provider intelligence."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.llm_intel_schemas import (
    ApprovedSourceListResponse,
    ApprovedSourceResponse,
    SourceTrustPolicyResponse,
    SourceTrustValidationRequest,
    SourceTrustValidationResponse,
)
from app.services.llm_intel_source_trust import (
    list_approved_sources,
    list_source_trust_policies,
    registry_hash,
    validate_registry,
    validate_sources_for_claim,
)

router = APIRouter(
    prefix="/api/v1/llm-intel/source-trust",
    tags=["LLM Intel Source Trust"],
)


@router.get("/classes", response_model=list[SourceTrustPolicyResponse])
def source_trust_classes() -> list[SourceTrustPolicyResponse]:
    """Return canonical source trust classes and their authority semantics."""
    return [
        SourceTrustPolicyResponse(**policy.__dict__)
        for policy in list_source_trust_policies()
    ]


@router.get("/approved-sources", response_model=ApprovedSourceListResponse)
def approved_sources(
    provider_id: str | None = Query(default=None),
    trust_class: str | None = Query(default=None),
    include_blocked: bool = Query(default=False),
) -> ApprovedSourceListResponse:
    """Return approved source registry entries. This endpoint does not fetch sources."""
    validate_registry()
    sources = list_approved_sources(
        provider_id=provider_id,
        trust_class=trust_class,
        include_blocked=include_blocked,
    )
    return ApprovedSourceListResponse(
        items=[
            ApprovedSourceResponse(**source.to_contract_payload())
            for source in sources
        ],
        total=len(sources),
        registry_hash=registry_hash(),
    )


@router.post("/validate", response_model=SourceTrustValidationResponse)
def validate_source_trust(
    request: SourceTrustValidationRequest,
) -> SourceTrustValidationResponse:
    """Validate whether source evidence can support an LLM-intel candidate claim."""
    decision = validate_sources_for_claim(request.source_ids, request.claim_type)
    return SourceTrustValidationResponse(**decision.__dict__)
