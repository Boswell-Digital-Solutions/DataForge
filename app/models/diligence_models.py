"""
Due Diligence Dashboard - SQLAlchemy Models

Database models for software repository due diligence reviews.
"""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class OverallRating(str, enum.Enum):
    """Overall rating for a review"""
    GREEN = "green"      # Low risk, good quality
    YELLOW = "yellow"    # Medium risk, acceptable quality
    RED = "red"          # High risk, poor quality


class FindingSeverity(str, enum.Enum):
    """Severity level for findings"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingStatus(str, enum.Enum):
    """Status of a finding"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class DiligenceProject(Base):
    """
    A software project under due diligence review.

    Represents a repository or codebase being evaluated.
    """
    __tablename__ = "diligence_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    git_url = Column(String(500))
    repo_path = Column(String(500))  # Local path if cloned
    tags = Column(JSON, default=list)  # ["python", "web", "api"]
    project_metadata = Column(JSON, default=dict)  # Flexible metadata storage (renamed from 'metadata' to avoid SQLAlchemy conflict)

    # Computed from latest review
    current_health_status = Column(SQLEnum(OverallRating), nullable=True)
    latest_review_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="diligence_projects")
    reviews = relationship("DiligenceReview", back_populates="project", cascade="all, delete-orphan")


class DiligenceReview(Base):
    """
    A due diligence review of a project.

    Contains scores, summary, and findings from a review session.
    """
    __tablename__ = "diligence_reviews"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('diligence_projects.id', ondelete='CASCADE'), nullable=False, index=True)

    # Review metadata
    reviewer_name = Column(String(255))  # Human or AI reviewer
    review_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    review_type = Column(String(50))  # "human", "claude", "chatgpt", "augment", "cursor", "automated"

    # Summary
    summary = Column(Text)  # Executive summary
    strengths = Column(JSON, default=list)  # List of strength points
    risks = Column(JSON, default=list)  # List of risk points
    recommendation = Column(Text)  # Final recommendation

    # Scores (1-5 scale)
    code_quality_score = Column(Float, nullable=True)
    security_score = Column(Float, nullable=True)
    architecture_score = Column(Float, nullable=True)
    operations_score = Column(Float, nullable=True)
    documentation_score = Column(Float, nullable=True)

    # Overall rating
    overall_rating = Column(SQLEnum(OverallRating), nullable=True)

    # Raw AI output (if applicable)
    raw_report_text = Column(Text)  # Original markdown from AI

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("DiligenceProject", back_populates="reviews")
    findings = relationship("DiligenceFinding", back_populates="review", cascade="all, delete-orphan")


class DiligenceFinding(Base):
    """
    A specific finding from a review.

    Represents issues, risks, or notable items discovered during review.
    """
    __tablename__ = "diligence_findings"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey('diligence_reviews.id', ondelete='CASCADE'), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text)
    severity = Column(SQLEnum(FindingSeverity), nullable=False, index=True)
    status = Column(SQLEnum(FindingStatus), default=FindingStatus.OPEN, nullable=False, index=True)

    # Optional metadata
    category = Column(String(100))  # "security", "code_quality", "architecture", etc.
    file_path = Column(String(500))  # File where issue was found
    line_number = Column(Integer)   # Line number if applicable
    remediation = Column(Text)      # Suggested fix

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255))

    # Relationships
    review = relationship("DiligenceReview", back_populates="findings")
