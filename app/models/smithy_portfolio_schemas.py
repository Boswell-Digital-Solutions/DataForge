"""
Smithy Portfolio Pydantic Schemas

Request/response schemas for the Smithy Portfolio API.
Matches the TypeScript types in forge-smithy/src/lib/smithy_portfolio/types/index.ts
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
# Evidence Types
# ═══════════════════════════════════════════════════════════════════════

EvidenceKind = Literal["link", "file", "image", "snippet"]
ChecklistItemState = Literal["pass", "partial", "fail"]
EvidenceProvenance = Literal["manual", "auto"]


class EvidenceItemCreate(BaseModel):
    """Create a new evidence item."""
    kind: EvidenceKind
    display_label: str = Field(..., max_length=255)
    url: Optional[str] = Field(None, max_length=1000)
    path: Optional[str] = Field(None, max_length=500)
    snippet: Optional[str] = None
    notes: Optional[str] = None
    provenance: EvidenceProvenance = "manual"


class EvidenceItem(BaseModel):
    """Evidence item response."""
    id: str
    kind: EvidenceKind
    display_label: str
    url: Optional[str] = None
    path: Optional[str] = None
    snippet: Optional[str] = None
    notes: Optional[str] = None
    provenance: EvidenceProvenance = "manual"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



# ═══════════════════════════════════════════════════════════════════════
# Checklist Types (embedded in evaluation snapshots)
# ═══════════════════════════════════════════════════════════════════════

class FailureTrigger(BaseModel):
    """Task generated when a checklist item fails."""
    task_title: str
    task_detail: str
    priority: Literal["low", "medium", "high"]


class ChecklistItem(BaseModel):
    """Single item in a checklist section."""
    key: str
    label: str
    weight: float
    requiresEvidence: bool
    prompts: list[str]
    failure_trigger: FailureTrigger


class ChecklistSection(BaseModel):
    """Section grouping checklist items."""
    key: str
    label: str
    items: list[ChecklistItem]


class ChecklistTemplate(BaseModel):
    """Full checklist template."""
    key: str
    label: str
    version: int
    sections: list[ChecklistSection]


# ═══════════════════════════════════════════════════════════════════════
# Evaluation Types
# ═══════════════════════════════════════════════════════════════════════

class EvaluationSnapshotCreate(BaseModel):
    """Create a new evaluation snapshot."""
    template_key: str = Field(..., max_length=100)
    template_snapshot: ChecklistTemplate
    answers: dict[str, ChecklistItemState] = Field(default_factory=dict)
    evidence: dict[str, list[dict]] = Field(default_factory=dict)
    score_total: float = 0.0
    publish_ready: bool = False


class EvaluationSnapshot(BaseModel):
    """Evaluation snapshot response."""
    id: str
    project_id: str
    template_key: str
    template_snapshot: ChecklistTemplate
    answers: dict[str, ChecklistItemState]
    evidence: dict[str, list[dict]]
    score_total: float
    publish_ready: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



# ═══════════════════════════════════════════════════════════════════════
# Project Types
# ═══════════════════════════════════════════════════════════════════════

class ProjectCreate(BaseModel):
    """Create a new portfolio project."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    repo_url: Optional[str] = Field(None, max_length=500)
    stack: Optional[list[str]] = None


class ProjectUpdate(BaseModel):
    """Update an existing project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    repo_url: Optional[str] = Field(None, max_length=500)
    stack: Optional[list[str]] = None


class PortfolioProject(BaseModel):
    """Portfolio project response."""
    id: str
    name: str
    slug: str
    repo_url: Optional[str] = None
    stack: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

