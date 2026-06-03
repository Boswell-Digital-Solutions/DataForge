from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.llm_intel_pending_records_models import (
    LLMIntelPendingCandidateRecord,
    LLMIntelPromotedRecord,
)
from app.models.llm_intel_pending_records_schemas import LLMIntelPromotionDecisionApplyRequest
from app.services.llm_intel_promotion_application import (
    PromotionApplicationValidationError,
    apply_promotion_decision,
    list_promoted_records,
)
from forge_contract_core.validators.families import validate_family_payload
from tests.test_llm_intel_pending_records import (
    CANDIDATE_ID,
    DRIFT_REPORT_ID,
    TIMESTAMP,
    _post_record,
    ingest_full_pending_record_set,
    pricing_candidate,
)


EVIDENCE_BUNDLE_HASH = "sha256:" + "1" * 64


def promotion_decision(**overrides) -> dict:
    payload = {
        "schema_version": "llm_intel.promotion_decision.v1",
        "decision_id": "decision-deepseek-pricing-001",
        "review_packet_id": "review-deepseek-pricing-001",
        "candidate_id": CANDIDATE_ID,
        "operator_id": "operator:charlie",
        "authority_ring": "operator",
        "decision": "approve",
        "decided_at": TIMESTAMP,
        "evidence_bundle_hash": EVIDENCE_BUNDLE_HASH,
        "reason": "Official DeepSeek pricing evidence and old/new diff validated.",
        "affected_record_refs": [f"llm_intel_drift_report:{DRIFT_REPORT_ID}:v1"],
        "constraints": ["DataForge must preserve supersession lineage."],
        "resulting_state": "approved_for_promotion",
    }
    payload.update(overrides)
    return payload


def _apply(db: Session, payload: dict):
    return apply_promotion_decision(
        db,
        LLMIntelPromotionDecisionApplyRequest(payload=payload),
    )


@pytest.mark.unit
def test_promotion_projects_pricing_onto_model_catalog(db: Session) -> None:
    """Promoting a pricing candidate for a model already in the catalog projects the
    new price onto model_catalog (the dashboard's read model) — the weekly price-change
    path. The LLMIntelPromotedRecord remains the canonical truth."""
    from decimal import Decimal

    from app.models.multi_provider_models import ModelCatalog

    db.add(
        ModelCatalog(
            model_key="deepseek-chat",
            provider="deepseek",
            model_id="deepseek-chat",
            input_cost_per_mtok=Decimal("9.99"),  # sentinel; should be overwritten
            output_cost_per_mtok=Decimal("1.10"),
            max_context=64000,
            cache_read_discount=Decimal("0.26"),
            supports_batch=False,
            supports_structured_output=True,
            tier="workhorse",
            is_active=True,
        )
    )
    db.commit()

    ingest_full_pending_record_set(db)
    result = _apply(db, promotion_decision()).model_dump()
    assert result["promotion_applied"] is True

    db.expire_all()
    row = db.query(ModelCatalog).filter(ModelCatalog.model_key == "deepseek-chat").one()
    assert row.input_cost_per_mtok != Decimal("9.99")
    assert row.updated_by == "llm_intel_promotion"


@pytest.mark.unit
def test_promotion_decision_approval_creates_dataforge_promoted_record(
    db: Session,
) -> None:
    ingest_full_pending_record_set(db)

    response = _apply(db, promotion_decision()).model_dump()

    assert response["promotion_applied"] is True
    assert response["application_status"] == "stored"
    assert response["decision_resulting_state"] == "approved_for_promotion"
    assert response["promotion_state"] == "promoted"
    assert response["promotion_action"] == "promote"
    assert response["supersedes_record_id"] is None

    promoted_payload = response["promoted_payload"]
    validate_family_payload("llm_intel_promoted_record", 1, promoted_payload)
    assert promoted_payload["provider_id"] == "deepseek"
    assert promoted_payload["record_type"] == "pricing"
    assert promoted_payload["candidate_id"] == CANDIDATE_ID
    assert promoted_payload["dataforge_promotion_metadata"]["promoted_by_system"] == "DataForge"
    assert promoted_payload["source_evidence"][0]["trust_class"] == "OFFICIAL"

    candidate = (
        db.query(LLMIntelPendingCandidateRecord)
        .filter(LLMIntelPendingCandidateRecord.candidate_id == CANDIDATE_ID)
        .one()
    )
    assert candidate.promotion_state == "promoted"


@pytest.mark.unit
def test_promotion_decision_apply_is_idempotent_for_same_decision(
    db: Session,
) -> None:
    ingest_full_pending_record_set(db)

    first = _apply(db, promotion_decision()).model_dump()
    second = _apply(db, promotion_decision()).model_dump()

    assert second["application_status"] == "duplicate"
    assert second["promoted_record_id"] == first["promoted_record_id"]
    assert db.query(LLMIntelPromotedRecord).count() == 1


@pytest.mark.unit
def test_non_approval_decision_does_not_create_promoted_truth(db: Session) -> None:
    ingest_full_pending_record_set(db)

    response = _apply(
        db,
        promotion_decision(
            decision_id="decision-deepseek-pricing-reject-001",
            decision="reject",
            resulting_state="rejected",
            reason="Operator rejected the candidate for insufficient review context.",
        ),
    ).model_dump()

    assert response["promotion_applied"] is False
    assert response["application_status"] == "recorded_no_promotion"
    assert response["decision_resulting_state"] == "rejected"
    assert response["promotion_state"] == "rejected"
    assert db.query(LLMIntelPromotedRecord).count() == 0


@pytest.mark.unit
def test_promotion_application_requires_existing_pending_candidate(
    db: Session,
) -> None:
    with pytest.raises(PromotionApplicationValidationError, match="missing pending candidate"):
        _apply(
            db,
            promotion_decision(
                decision_id="decision-missing-candidate-001",
                candidate_id="candidate-missing-001",
            ),
        )


@pytest.mark.unit
def test_second_approval_supersedes_current_promoted_record(db: Session) -> None:
    ingest_full_pending_record_set(db)
    first = _apply(db, promotion_decision()).model_dump()

    second_candidate_id = "candidate-deepseek-pricing-002"
    _post_record(
        db,
        "llm_intel_pricing_candidates",
        pricing_candidate(
            candidate_id=second_candidate_id,
            candidate_value={
                "model": "deepseek-chat",
                "currency": "USD",
                "unit": "1m_input_tokens",
                "amount": 0.28,
            },
            promotion_state="candidate_detected",
        ),
    )

    second = _apply(
        db,
        promotion_decision(
            decision_id="decision-deepseek-pricing-002",
            review_packet_id="review-deepseek-pricing-002",
            candidate_id=second_candidate_id,
            evidence_bundle_hash="sha256:" + "2" * 64,
            affected_record_refs=[
                f"llm_intel_promoted_record:{first['promoted_record_id']}:v1",
                f"llm_intel_pending_candidate:{second_candidate_id}:v1",
            ],
        ),
    ).model_dump()

    assert second["promotion_action"] == "supersede"
    assert second["supersedes_record_id"] == first["promoted_record_id"]
    assert second["lineage_root_id"] == first["lineage_root_id"]

    first_row = (
        db.query(LLMIntelPromotedRecord)
        .filter(LLMIntelPromotedRecord.promoted_record_id == first["promoted_record_id"])
        .one()
    )
    assert first_row.is_current is False
    assert first_row.superseded_by_record_id == second["promoted_record_id"]

    current_records = list_promoted_records(db)
    assert [row.promoted_record_id for row in current_records] == [second["promoted_record_id"]]
    current = current_records[0]
    metadata = current.payload["dataforge_promotion_metadata"]

    assert current.is_current is True
    assert current.candidate_id == second_candidate_id
    assert current.lineage_root_id == first["lineage_root_id"]
    assert current.promotion_action == "supersede"
    assert current.supersedes_record_id == first["promoted_record_id"]
    assert current.payload["promoted_value"]["amount"] == 0.28
    assert current.payload["source_decision_ref"] == (
        "llm_intel_promotion_decision:decision-deepseek-pricing-002:v1"
    )
    assert metadata["promotion_action"] == "supersede"
    assert metadata["supersedes_record_id"] == first["promoted_record_id"]
