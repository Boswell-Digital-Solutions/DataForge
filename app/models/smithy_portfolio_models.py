"""
Smithy Portfolio Database Models

Models for the Smithy Portfolio & Competency module.
Stores portfolio projects, evaluation snapshots, and evidence items.
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class SmithyPortfolioProject(Base):
    """Portfolio project for tracking developer competency demonstrations."""
    __tablename__ = "smithy_portfolio_projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    repo_url = Column(String(500), nullable=True)
    stack = Column(ARRAY(String), nullable=True)  # e.g., ["SvelteKit", "Tauri", "Rust"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    evaluations = relationship(
        "SmithyEvaluationSnapshot",
        back_populates="project",
        cascade="all, delete-orphan"
    )


class SmithyEvaluationSnapshot(Base):
    """Point-in-time evaluation of a project against a checklist template."""
    __tablename__ = "smithy_evaluation_snapshots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("smithy_portfolio_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    template_key = Column(String(100), nullable=False)  # e.g., "portfolio_readiness_v1"
    template_snapshot = Column(JSONB, nullable=False)  # Full template at evaluation time
    answers = Column(JSONB, nullable=False, default=dict)  # ChecklistAnswerMap: {item_key: "pass"|"partial"|"fail"}
    evidence = Column(JSONB, nullable=False, default=dict)  # {item_key: EvidenceItem[]}
    score_total = Column(Float, nullable=False, default=0.0)
    publish_ready = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("SmithyPortfolioProject", back_populates="evaluations")
    evidence_items = relationship(
        "SmithyEvidenceItem",
        back_populates="evaluation",
        cascade="all, delete-orphan"
    )


class SmithyEvidenceItem(Base):
    """Evidence attached to an evaluation for a specific checklist item."""
    __tablename__ = "smithy_evidence_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    evaluation_id = Column(String(36), ForeignKey("smithy_evaluation_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    checklist_item_key = Column(String(100), nullable=False, index=True)
    kind = Column(String(20), nullable=False)  # "link", "file", "image", "snippet"
    display_label = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=True)
    path = Column(String(500), nullable=True)
    snippet = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    provenance = Column(String(20), nullable=False, default="manual")  # "manual" or "auto"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    evaluation = relationship("SmithyEvaluationSnapshot", back_populates="evidence_items")
