from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class RuntimePromotionCandidate(Base):
    __tablename__ = "runtime_promotion_candidates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String(64), nullable=False, unique=True, index=True)

    receipt_id = Column(String(64), nullable=False, unique=True, index=True)

    candidate_type = Column(String(100), nullable=False, index=True)
    source_envelope_type = Column(String(100), nullable=False, index=True)

    service = Column(String(100), nullable=False, index=True)
    fleet_member_id = Column(String(255), nullable=False, index=True)

    issue_class = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)

    evidence = Column(JSONB, nullable=False)
    source_payload = Column(JSONB, nullable=False)

    status = Column(String(30), nullable=False, default="review_ready", index=True)
    source = Column(String(50), nullable=False, default="runtime_promotion")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )


class RuntimePromotionCandidateDecision(Base):
    __tablename__ = "runtime_promotion_candidate_decisions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        String(64),
        ForeignKey("runtime_promotion_candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    prior_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)

    operator_note = Column(Text, nullable=True)
    operator_identity = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)