"""
Tests for AAR contracts — "AAR Contract Proof v1" (report Phase 5 / §5.6).

Hermetic: pure Pydantic + stdlib, no DB.

Covers:
    - Versioned schema strings on every contract.
    - Lifecycle state machine: legal path, illegal jumps, reject/fail from any
      non-terminal state, terminal states are sealed.
    - Deterministic evidence hashing (order-independent).
    - Decision/action separation: promotion is a reference, not embedded mutation.
    - extra="forbid" rejects unknown fields.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Load the contract module directly by path. It is deliberately pure (stdlib +
# Pydantic only), so this avoids importing app.models.__init__ (which pulls the
# ORM/DB stack) and keeps this contract test hermetic. Register in sys.modules
# before exec so Pydantic can resolve the deferred (string) annotations.
_MODULE_PATH = Path(__file__).resolve().parents[1] / "models" / "aar_schemas.py"
_spec = importlib.util.spec_from_file_location("aar_schemas_contract", _MODULE_PATH)
aar = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = aar
_spec.loader.exec_module(aar)

AAR_EVIDENCE_BUNDLE_SCHEMA = aar.AAR_EVIDENCE_BUNDLE_SCHEMA
AAR_LESSON_ARTIFACT_SCHEMA = aar.AAR_LESSON_ARTIFACT_SCHEMA
AAR_RECONCILIATION_RESULT_SCHEMA = aar.AAR_RECONCILIATION_RESULT_SCHEMA
AAR_RECORD_SCHEMA = aar.AAR_RECORD_SCHEMA
AAR_REVIEW_ARTIFACT_SCHEMA = aar.AAR_REVIEW_ARTIFACT_SCHEMA
AAR_SCHEMA_VERSIONS = aar.AAR_SCHEMA_VERSIONS
AAREvidenceBundle = aar.AAREvidenceBundle
AAREvidenceItem = aar.AAREvidenceItem
AAREvidenceKind = aar.AAREvidenceKind
AARLessonArtifact = aar.AARLessonArtifact
AARLifecycleState = aar.AARLifecycleState
AARModelObservation = aar.AARModelObservation
AARReconciliationResult = aar.AARReconciliationResult
AARRecord = aar.AARRecord
AARReviewArtifact = aar.AARReviewArtifact
AARReviewDecision = aar.AARReviewDecision
assert_transition = aar.assert_transition
can_transition = aar.can_transition
compute_evidence_hash = aar.compute_evidence_hash


# --- versioning -----------------------------------------------------------


def test_schema_versions_present():
    assert AAREvidenceBundle(bundle_id="b", run_id="r").schema_version == AAR_EVIDENCE_BUNDLE_SCHEMA
    assert AARRecord(aar_id="a", run_id="r").schema_version == AAR_RECORD_SCHEMA
    assert AAR_SCHEMA_VERSIONS["aar_record"] == 1
    assert set(AAR_SCHEMA_VERSIONS) == {
        "aar_evidence_bundle",
        "aar_reconciliation_result",
        "aar_review_artifact",
        "aar_lesson_artifact",
        "aar_record",
    }


# --- state machine --------------------------------------------------------


def test_full_legal_lifecycle_path():
    order = [
        AARLifecycleState.DRAFT,
        AARLifecycleState.EVIDENCE_COLLECTED,
        AARLifecycleState.ANALYZED,
        AARLifecycleState.RECONCILED,
        AARLifecycleState.UNDER_REVIEW,
        AARLifecycleState.REVIEWED,
        AARLifecycleState.RECEIPTED,
        AARLifecycleState.LESSONS_GENERATED,
        AARLifecycleState.PROMOTION_DECIDED,
    ]
    for cur, nxt in zip(order, order[1:]):
        assert can_transition(cur, nxt)


def test_illegal_skip_is_rejected():
    assert not can_transition(AARLifecycleState.DRAFT, AARLifecycleState.REVIEWED)
    assert not can_transition(AARLifecycleState.EVIDENCE_COLLECTED, AARLifecycleState.RECEIPTED)


def test_reject_and_fail_allowed_from_any_nonterminal_state():
    assert can_transition(AARLifecycleState.UNDER_REVIEW, AARLifecycleState.REJECTED)
    assert can_transition(AARLifecycleState.DRAFT, AARLifecycleState.FAILED)


def test_terminal_states_are_sealed():
    for terminal in (
        AARLifecycleState.PROMOTION_DECIDED,
        AARLifecycleState.REJECTED,
        AARLifecycleState.FAILED,
    ):
        assert not can_transition(terminal, AARLifecycleState.FAILED)
        assert not can_transition(terminal, AARLifecycleState.DRAFT)


def test_assert_transition_raises_on_illegal():
    with pytest.raises(ValueError, match="illegal AAR transition"):
        assert_transition(AARLifecycleState.DRAFT, AARLifecycleState.PROMOTION_DECIDED)


def test_record_transition_to_advances_and_enforces():
    rec = AARRecord(aar_id="a", run_id="r")
    rec2 = rec.transition_to(AARLifecycleState.EVIDENCE_COLLECTED)
    assert rec2.state == AARLifecycleState.EVIDENCE_COLLECTED
    assert rec.state == AARLifecycleState.DRAFT  # original unchanged (copy)
    with pytest.raises(ValueError):
        rec.transition_to(AARLifecycleState.RECEIPTED)


# --- evidence hashing -----------------------------------------------------


def test_evidence_hash_is_deterministic_and_order_independent():
    a = AAREvidenceItem(kind=AAREvidenceKind.RUN_REF, ref="run-1")
    b = AAREvidenceItem(kind=AAREvidenceKind.METRIC, ref="latency_ms", description="42")
    h1 = compute_evidence_hash([a, b])
    h2 = compute_evidence_hash([a, b])
    assert h1 == h2
    assert h1.startswith("sha256:")
    # Different content -> different hash.
    assert compute_evidence_hash([a]) != h1


def test_bundle_with_computed_hash():
    bundle = AAREvidenceBundle(
        bundle_id="b1",
        run_id="r1",
        items=[AAREvidenceItem(kind=AAREvidenceKind.LINK, ref="https://x")],
    )
    assert bundle.evidence_hash is None
    stamped = bundle.with_computed_hash()
    assert stamped.evidence_hash and stamped.evidence_hash.startswith("sha256:")


# --- decision/action separation (ADR-005) ---------------------------------


def test_promotion_is_a_reference_not_embedded_mutation():
    rec = AARRecord(
        aar_id="a",
        run_id="r",
        lessons=[
            AARLessonArtifact(
                lesson_id="l1", aar_id="a", lesson="prefer premium tier", memory_candidate=True
            )
        ],
        receipt_ref="receipt_123",
        promotion_decision_ref="promo_456",
    )
    # The record references the decision; it does not carry a mutating verb/action.
    assert rec.receipt_ref == "receipt_123"
    assert rec.promotion_decision_ref == "promo_456"
    assert rec.lessons[0].memory_candidate is True
    # Lesson schema versioned.
    assert rec.lessons[0].schema_version == AAR_LESSON_ARTIFACT_SCHEMA


def test_aggregate_record_holds_all_parts():
    rec = AARRecord(
        aar_id="a",
        run_id="r",
        evidence_bundle=AAREvidenceBundle(bundle_id="b", run_id="r"),
        model_observations=[
            AARModelObservation(provider="anthropic", model="claude-opus", observation="ok", score=0.9)
        ],
        reconciliation=AARReconciliationResult(
            reconciliation_id="rc", aar_id="a", resolved_outcome="consensus"
        ),
        reviews=[
            AARReviewArtifact(
                review_id="rv", aar_id="a", reviewer="charlie", decision=AARReviewDecision.APPROVE
            )
        ],
    )
    assert rec.reconciliation.schema_version == AAR_RECONCILIATION_RESULT_SCHEMA
    assert rec.reviews[0].schema_version == AAR_REVIEW_ARTIFACT_SCHEMA
    assert rec.reviews[0].decision == AARReviewDecision.APPROVE
    # JSON round-trips.
    assert rec.to_canonical_dict()["schema_version"] == AAR_RECORD_SCHEMA


# --- strictness -----------------------------------------------------------


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        AARRecord(aar_id="a", run_id="r", bogus_field="x")


def test_score_bounds_enforced():
    with pytest.raises(ValidationError):
        AARModelObservation(provider="p", model="m", observation="o", score=1.5)
