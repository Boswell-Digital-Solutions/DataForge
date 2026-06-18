"""
AAR (After-Action Review) contracts — "AAR Contract Proof v1".

Implements the BDS Formal Architecture Investigation Report v1.0 Phase 5 / §5.6.
Before this module the AAR types (AAREvidenceBundle.v1, AARRecord.v1,
AARReconciliationResult.v1, AARReviewArtifact.v1, AARLessonArtifact.v1) existed
only in Forge_Command planning docs (`bds_dashboard_protocol_set`). This module is
the first code-backed definition.

These are **contract schemas only** — no persistence (Alembic migration) or router
is wired here. DataForge owns durable state, so the canonical AAR schemas live
here; persistence and an operator-review surface in Forge_Command are the
documented next steps.

Design constraints honored from the report:
- Explicit lifecycle state machine with legal transitions (§2.5 / §9.5 State
  Machine Protocol) — invalid states are hard to create.
- Decision separated from action (§2.6 / ADR-005): an AARRecord holds *candidates*
  (lessons, memory/eval candidates) and *references* to the promotion decision and
  receipt; it does not itself perform the promotion mutation.
- Every cross-system object is versioned (`schema_version`) and named by business
  authority (§2.3).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# Canonical schema-version strings (snake_case.vN, matching operational_error.v1 /
# provider_result.v1 shipped elsewhere in the ecosystem).
AAR_EVIDENCE_BUNDLE_SCHEMA = "aar_evidence_bundle.v1"
AAR_RECONCILIATION_RESULT_SCHEMA = "aar_reconciliation_result.v1"
AAR_REVIEW_ARTIFACT_SCHEMA = "aar_review_artifact.v1"
AAR_LESSON_ARTIFACT_SCHEMA = "aar_lesson_artifact.v1"
AAR_RECORD_SCHEMA = "aar_record.v1"

#: Discoverability registry: contract name -> current version.
AAR_SCHEMA_VERSIONS: dict[str, int] = {
    "aar_evidence_bundle": 1,
    "aar_reconciliation_result": 1,
    "aar_review_artifact": 1,
    "aar_lesson_artifact": 1,
    "aar_record": 1,
}


# ---------------------------------------------------------------------------
# Lifecycle state machine (§2.5 / §9.5)
# ---------------------------------------------------------------------------


class AARLifecycleState(str, Enum):
    """Explicit AAR lifecycle states, mirroring the §5.6 workflow."""

    DRAFT = "draft"
    EVIDENCE_COLLECTED = "evidence_collected"
    ANALYZED = "analyzed"  # comparative model analysis complete
    RECONCILED = "reconciled"  # deterministic reconciliation complete
    UNDER_REVIEW = "under_review"
    REVIEWED = "reviewed"  # operator review complete
    RECEIPTED = "receipted"  # receipt issued
    LESSONS_GENERATED = "lessons_generated"
    PROMOTION_DECIDED = "promotion_decided"  # terminal (success)
    REJECTED = "rejected"  # terminal
    FAILED = "failed"  # terminal


_TERMINAL_STATES: frozenset[AARLifecycleState] = frozenset(
    {
        AARLifecycleState.PROMOTION_DECIDED,
        AARLifecycleState.REJECTED,
        AARLifecycleState.FAILED,
    }
)

# Legal forward transitions. Any state may move to REJECTED or FAILED (a review can
# reject; any stage can fail). Mirrors Forge_Command's can_transition/assert pattern.
_LEGAL_TRANSITIONS: dict[AARLifecycleState, frozenset[AARLifecycleState]] = {
    AARLifecycleState.DRAFT: frozenset({AARLifecycleState.EVIDENCE_COLLECTED}),
    AARLifecycleState.EVIDENCE_COLLECTED: frozenset({AARLifecycleState.ANALYZED}),
    AARLifecycleState.ANALYZED: frozenset({AARLifecycleState.RECONCILED}),
    AARLifecycleState.RECONCILED: frozenset({AARLifecycleState.UNDER_REVIEW}),
    AARLifecycleState.UNDER_REVIEW: frozenset({AARLifecycleState.REVIEWED}),
    AARLifecycleState.REVIEWED: frozenset({AARLifecycleState.RECEIPTED}),
    AARLifecycleState.RECEIPTED: frozenset({AARLifecycleState.LESSONS_GENERATED}),
    AARLifecycleState.LESSONS_GENERATED: frozenset({AARLifecycleState.PROMOTION_DECIDED}),
    AARLifecycleState.PROMOTION_DECIDED: frozenset(),
    AARLifecycleState.REJECTED: frozenset(),
    AARLifecycleState.FAILED: frozenset(),
}


def can_transition(current: AARLifecycleState, target: AARLifecycleState) -> bool:
    """Whether moving ``current -> target`` is a legal AAR lifecycle transition."""
    if current in _TERMINAL_STATES:
        return False
    if target in (AARLifecycleState.REJECTED, AARLifecycleState.FAILED):
        return True
    return target in _LEGAL_TRANSITIONS.get(current, frozenset())


def assert_transition(current: AARLifecycleState, target: AARLifecycleState) -> None:
    """Raise ``ValueError`` if ``current -> target`` is not a legal transition."""
    if not can_transition(current, target):
        raise ValueError(f"illegal AAR transition: {current.value} -> {target.value}")


# ---------------------------------------------------------------------------
# Supporting value objects
# ---------------------------------------------------------------------------


class AAREvidenceKind(str, Enum):
    RUN_REF = "run_ref"
    METRIC = "metric"
    SNIPPET = "snippet"
    FILE = "file"
    LINK = "link"
    MODEL_OUTPUT = "model_output"


class AARReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_evidence_hash(items: list["AAREvidenceItem"]) -> str:
    """Deterministic ``sha256:...`` digest over evidence items.

    Dependency-light (stdlib only): canonical JSON with sorted keys so the digest
    is stable regardless of field/insertion order.
    """
    canonical = json.dumps(
        [item.model_dump(mode="json") for item in items],
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AAREvidenceItem(BaseModel):
    """A single piece of evidence collected for an AAR."""

    model_config = ConfigDict(extra="forbid")

    kind: AAREvidenceKind
    ref: str = Field(..., description="Stable reference: run id, URL, path, or inline key")
    description: Optional[str] = None
    content_hash: Optional[str] = Field(
        default=None, description="sha256:... of the referenced content, when available"
    )


class AARModelObservation(BaseModel):
    """One model's contribution to the comparative analysis (§5.6 step 2).

    Provider-specific shapes do not leak here (ADR-004): only the normalized
    provider/model identity plus the observation and an optional score.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    route_class: Optional[str] = None
    observation: str
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Versioned contracts
# ---------------------------------------------------------------------------


class AAREvidenceBundle(BaseModel):
    """AAREvidenceBundle.v1 — the evidence collected for an AAR."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = AAR_EVIDENCE_BUNDLE_SCHEMA
    bundle_id: str
    run_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    items: list[AAREvidenceItem] = Field(default_factory=list)
    evidence_hash: Optional[str] = Field(
        default=None, description="sha256:... digest over items; see compute_evidence_hash"
    )
    source_system: Optional[str] = None

    def with_computed_hash(self) -> "AAREvidenceBundle":
        """Return a copy with ``evidence_hash`` filled deterministically."""
        return self.model_copy(update={"evidence_hash": compute_evidence_hash(self.items)})


class AARReconciliationResult(BaseModel):
    """AARReconciliationResult.v1 — deterministic reconciliation (§5.6 step 3)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = AAR_RECONCILIATION_RESULT_SCHEMA
    reconciliation_id: str
    aar_id: str
    method: str = Field(default="deterministic")
    deterministic: bool = True
    inputs_hash: Optional[str] = None
    agreements: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    resolved_outcome: str
    created_at: datetime = Field(default_factory=_utcnow)


class AARReviewArtifact(BaseModel):
    """AARReviewArtifact.v1 — operator review of an AAR (§5.6 step 4)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = AAR_REVIEW_ARTIFACT_SCHEMA
    review_id: str
    aar_id: str
    reviewer: str
    decision: AARReviewDecision
    reason: Optional[str] = None
    reviewed_at: datetime = Field(default_factory=_utcnow)


class AARLessonArtifact(BaseModel):
    """AARLessonArtifact.v1 — a lesson / candidate produced by an AAR (§5.6 step 6).

    These are *candidates* (memory_candidate / eval_candidate). Promotion into
    durable memory is a separate, authorized decision (ADR-005) referenced by
    ``AARRecord.promotion_decision_ref`` — never performed by this artifact.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = AAR_LESSON_ARTIFACT_SCHEMA
    lesson_id: str
    aar_id: str
    lesson: str
    category: Optional[str] = None
    memory_candidate: bool = False
    eval_candidate: bool = False
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=_utcnow)


class AARRecord(BaseModel):
    """AARRecord.v1 — the aggregate lifecycle record tying an AAR together.

    Holds the evidence bundle, comparative model observations, reconciliation,
    operator reviews, and lesson candidates, plus *references* (not embedded
    mutations) to the issued receipt and the promotion decision.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = AAR_RECORD_SCHEMA
    aar_id: str
    run_id: str
    state: AARLifecycleState = AARLifecycleState.DRAFT
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    evidence_bundle: Optional[AAREvidenceBundle] = None
    model_observations: list[AARModelObservation] = Field(default_factory=list)
    reconciliation: Optional[AARReconciliationResult] = None
    reviews: list[AARReviewArtifact] = Field(default_factory=list)
    lessons: list[AARLessonArtifact] = Field(default_factory=list)

    # Decision/action separation (ADR-005): references to authority issued elsewhere.
    receipt_ref: Optional[str] = Field(
        default=None, description="Reference to the issued receipt (e.g. a promotion receipt id)"
    )
    promotion_decision_ref: Optional[str] = Field(
        default=None,
        description="Reference to the PromotionDecision that acted on this AAR's candidates",
    )

    def transition_to(self, target: AARLifecycleState) -> "AARRecord":
        """Return a copy advanced to ``target``, enforcing legal transitions."""
        assert_transition(self.state, target)
        return self.model_copy(update={"state": target, "updated_at": _utcnow()})

    def to_canonical_dict(self) -> dict[str, Any]:
        """JSON-mode dump (stable, serializable) for hashing/persistence."""
        return self.model_dump(mode="json")
