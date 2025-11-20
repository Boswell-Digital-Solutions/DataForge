"""
Due Diligence Dashboard - Pydantic Schemas

Request/response schemas for API validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================
# Enums
# ============================================

class OverallRatingEnum(str, Enum):
    """Overall rating for a review"""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class FindingSeverityEnum(str, Enum):
    """Severity level for findings"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingStatusEnum(str, Enum):
    """Status of a finding"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


# ============================================
# Project Schemas
# ============================================

class DiligenceProjectBase(BaseModel):
    """Base schema for diligence projects"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    git_url: Optional[str] = Field(None, max_length=500)
    repo_path: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    project_metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Project name cannot be empty')
        return v.strip()


class DiligenceProjectCreate(DiligenceProjectBase):
    """Schema for creating a new project"""
    pass


class DiligenceProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    git_url: Optional[str] = Field(None, max_length=500)
    repo_path: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None
    project_metadata: Optional[Dict[str, Any]] = None


class DiligenceProjectSummary(BaseModel):
    """Summary schema for project listings"""
    id: int
    name: str
    description: Optional[str]
    tags: List[str]
    current_health_status: Optional[OverallRatingEnum]
    latest_review_date: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class DiligenceProject(DiligenceProjectBase):
    """Full project schema"""
    id: int
    current_health_status: Optional[OverallRatingEnum]
    latest_review_date: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ============================================
# Review Schemas
# ============================================

class DiligenceReviewBase(BaseModel):
    """Base schema for reviews"""
    reviewer_name: Optional[str] = Field(None, max_length=255)
    review_type: Optional[str] = Field(None, max_length=50)
    summary: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommendation: Optional[str] = None
    code_quality_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    security_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    architecture_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    operations_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    documentation_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    overall_rating: Optional[OverallRatingEnum] = None


class DiligenceReviewCreate(DiligenceReviewBase):
    """Schema for creating a new review"""
    project_id: int
    raw_report_text: Optional[str] = None


class DiligenceReviewUpdate(BaseModel):
    """Schema for updating a review"""
    reviewer_name: Optional[str] = Field(None, max_length=255)
    review_type: Optional[str] = Field(None, max_length=50)
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    recommendation: Optional[str] = None
    code_quality_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    security_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    architecture_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    operations_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    documentation_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    overall_rating: Optional[OverallRatingEnum] = None


class DiligenceReviewSummary(BaseModel):
    """Summary schema for review listings"""
    id: int
    project_id: int
    reviewer_name: Optional[str]
    review_type: Optional[str]
    review_date: datetime
    overall_rating: Optional[OverallRatingEnum]
    code_quality_score: Optional[float]
    security_score: Optional[float]

    model_config = {"from_attributes": True}


class DiligenceReview(DiligenceReviewBase):
    """Full review schema with findings"""
    id: int
    project_id: int
    review_date: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    raw_report_text: Optional[str]

    model_config = {"from_attributes": True}


# ============================================
# Finding Schemas
# ============================================

class DiligenceFindingBase(BaseModel):
    """Base schema for findings"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    severity: FindingSeverityEnum
    status: FindingStatusEnum = FindingStatusEnum.OPEN
    category: Optional[str] = Field(None, max_length=100)
    file_path: Optional[str] = Field(None, max_length=500)
    line_number: Optional[int] = None
    remediation: Optional[str] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Finding title cannot be empty')
        return v.strip()


class DiligenceFindingCreate(DiligenceFindingBase):
    """Schema for creating a new finding"""
    review_id: int


class DiligenceFindingUpdate(BaseModel):
    """Schema for updating a finding"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    severity: Optional[FindingSeverityEnum] = None
    status: Optional[FindingStatusEnum] = None
    category: Optional[str] = Field(None, max_length=100)
    file_path: Optional[str] = Field(None, max_length=500)
    line_number: Optional[int] = None
    remediation: Optional[str] = None
    resolved_by: Optional[str] = Field(None, max_length=255)


class DiligenceFinding(DiligenceFindingBase):
    """Full finding schema"""
    id: int
    review_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]

    model_config = {"from_attributes": True}


# ============================================
# Combined Schemas
# ============================================

class DiligenceReviewWithFindings(DiligenceReview):
    """Review schema including all findings"""
    findings: List[DiligenceFinding] = []

    model_config = {"from_attributes": True}


class DiligenceProjectWithReviews(DiligenceProject):
    """Project schema including all reviews"""
    reviews: List[DiligenceReviewSummary] = []

    model_config = {"from_attributes": True}


# ============================================
# AI Report Parser Schema
# ============================================

class ParsedAIReport(BaseModel):
    """Schema for parsed AI-generated review report"""
    summary: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommendation: Optional[str] = None
    code_quality_score: Optional[float] = None
    security_score: Optional[float] = None
    architecture_score: Optional[float] = None
    operations_score: Optional[float] = None
    documentation_score: Optional[float] = None
    overall_rating: Optional[OverallRatingEnum] = None
    findings: List[Dict[str, Any]] = Field(default_factory=list)  # Parsed findings


class BulkReviewCreate(BaseModel):
    """Schema for creating a review from bulk AI text"""
    project_id: int
    reviewer_name: Optional[str] = None
    review_type: Optional[str] = None
    raw_report_text: str = Field(..., min_length=10)

    @field_validator('raw_report_text')
    @classmethod
    def validate_report_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Report text cannot be empty')
        return v.strip()
