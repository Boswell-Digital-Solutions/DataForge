"""
Smithy Portfolio API Router

REST API endpoints for the Smithy Portfolio & Competency module.
Base path: /api/v1/smithy/portfolio
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.smithy_portfolio_schemas import (
    PortfolioProject,
    ProjectCreate,
    ProjectUpdate,
    EvaluationSnapshot,
    EvaluationSnapshotCreate,
    EvidenceItem,
    EvidenceItemCreate,
)
from app.api import smithy_portfolio_crud as crud

router = APIRouter(prefix="/api/v1/smithy/portfolio", tags=["smithy-portfolio"])


# ═══════════════════════════════════════════════════════════════════════
# Projects
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects", response_model=list[PortfolioProject])
def list_projects(db: Session = Depends(get_db)):
    """
    Get all portfolio projects.

    Returns projects ordered by creation date (newest first).
    """
    projects = crud.get_projects(db)
    return projects


@router.post("/projects", response_model=PortfolioProject, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new portfolio project.

    - **name**: Display name for the project
    - **slug**: URL-safe identifier (lowercase, hyphens only)
    - **repo_url**: Optional repository URL
    - **stack**: Optional list of technologies used
    """
    # Check for slug collision
    existing = crud.get_project_by_slug(db, project.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with slug '{project.slug}' already exists"
        )

    return crud.create_project(db, project)


@router.get("/projects/{slug}", response_model=PortfolioProject)
def get_project(slug: str, db: Session = Depends(get_db)):
    """
    Get a project by its slug.
    """
    project = crud.get_project_by_slug(db, slug)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )
    return project


@router.patch("/projects/{slug}", response_model=PortfolioProject)
def update_project(slug: str, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    """
    Update an existing project.

    Only provided fields will be updated.
    """
    project = crud.update_project(db, slug, project_update)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )
    return project


@router.delete("/projects/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(slug: str, db: Session = Depends(get_db)):
    """
    Delete a project by its slug.

    This also deletes all associated evaluations and evidence.
    """
    deleted = crud.delete_project(db, slug)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )


# ═══════════════════════════════════════════════════════════════════════
# Evaluations
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/evaluations", response_model=list[EvaluationSnapshot])
def list_evaluations(project_id: str, db: Session = Depends(get_db)):
    """
    Get all evaluation snapshots for a project.

    Returns evaluations ordered by creation date (newest first).
    """
    # Verify project exists
    project = crud.get_project_by_id(db, project_id)
    if not project:
        # Also try by slug for flexibility
        project = crud.get_project_by_slug(db, project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    evaluations = crud.get_evaluations_by_project(db, project.id)
    return evaluations


@router.post("/projects/{project_id}/evaluations", response_model=EvaluationSnapshot, status_code=status.HTTP_201_CREATED)
def create_evaluation(project_id: str, evaluation: EvaluationSnapshotCreate, db: Session = Depends(get_db)):
    """
    Create a new evaluation snapshot for a project.

    - **template_key**: Identifier for the checklist template used
    - **template_snapshot**: Full template definition at evaluation time
    - **answers**: Map of checklist item keys to states (pass/partial/fail)
    - **evidence**: Map of checklist item keys to evidence arrays
    - **score_total**: Computed total score
    - **publish_ready**: Whether the project meets publication criteria
    """
    # Verify project exists
    project = crud.get_project_by_id(db, project_id)
    if not project:
        project = crud.get_project_by_slug(db, project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found"
        )

    return crud.create_evaluation(db, project.id, evaluation)


# ═══════════════════════════════════════════════════════════════════════
# Evidence
# ═══════════════════════════════════════════════════════════════════════

@router.get("/evaluations/{evaluation_id}/evidence", response_model=list[EvidenceItem])
def list_evidence(evaluation_id: str, db: Session = Depends(get_db)):
    """
    Get all evidence items for an evaluation.
    """
    # Verify evaluation exists
    evaluation = crud.get_evaluation_by_id(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found"
        )

    evidence = crud.get_evidence_by_evaluation(db, evaluation_id)
    return evidence


@router.post("/evaluations/{evaluation_id}/evidence", response_model=EvidenceItem, status_code=status.HTTP_201_CREATED)
def create_evidence(
    evaluation_id: str,
    evidence: EvidenceItemCreate,
    checklist_item_key: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Attach evidence to an evaluation.

    - **kind**: Type of evidence (link, file, image, snippet)
    - **display_label**: Human-readable label
    - **url**: URL for link/image evidence
    - **path**: File path for file evidence
    - **snippet**: Code/text snippet
    - **notes**: Additional notes
    - **provenance**: How evidence was collected (manual/auto)
    """
    # Verify evaluation exists
    evaluation = crud.get_evaluation_by_id(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found"
        )

    # Use provided key or default to "general"
    item_key = checklist_item_key or "general"

    return crud.create_evidence(db, evaluation_id, item_key, evidence)
