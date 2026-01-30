"""
Smithy Portfolio CRUD Operations

Database operations for the Smithy Portfolio API.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.models.smithy_portfolio_models import (
    SmithyPortfolioProject,
    SmithyEvaluationSnapshot,
    SmithyEvidenceItem,
)
from app.models.smithy_portfolio_schemas import (
    ProjectCreate,
    ProjectUpdate,
    EvaluationSnapshotCreate,
    EvidenceItemCreate,
)


# ═══════════════════════════════════════════════════════════════════════
# Project CRUD
# ═══════════════════════════════════════════════════════════════════════

def get_projects(db: Session) -> list[SmithyPortfolioProject]:
    """Get all portfolio projects, ordered by most recent first."""
    return db.query(SmithyPortfolioProject).order_by(desc(SmithyPortfolioProject.created_at)).all()


def get_project_by_slug(db: Session, slug: str) -> Optional[SmithyPortfolioProject]:
    """Get a project by its slug."""
    return db.query(SmithyPortfolioProject).filter(SmithyPortfolioProject.slug == slug).first()


def get_project_by_id(db: Session, project_id: str) -> Optional[SmithyPortfolioProject]:
    """Get a project by its ID."""
    return db.query(SmithyPortfolioProject).filter(SmithyPortfolioProject.id == project_id).first()


def create_project(db: Session, project: ProjectCreate) -> SmithyPortfolioProject:
    """Create a new portfolio project."""
    db_project = SmithyPortfolioProject(
        name=project.name,
        slug=project.slug,
        repo_url=project.repo_url,
        stack=project.stack,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(db: Session, slug: str, project_update: ProjectUpdate) -> Optional[SmithyPortfolioProject]:
    """Update an existing project."""
    db_project = get_project_by_slug(db, slug)
    if not db_project:
        return None

    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_project, field, value)

    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, slug: str) -> bool:
    """Delete a project by slug. Returns True if deleted, False if not found."""
    db_project = get_project_by_slug(db, slug)
    if not db_project:
        return False

    db.delete(db_project)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════
# Evaluation CRUD
# ═══════════════════════════════════════════════════════════════════════

def get_evaluations_by_project(db: Session, project_id: str) -> list[SmithyEvaluationSnapshot]:
    """Get all evaluations for a project, ordered by most recent first."""
    return (
        db.query(SmithyEvaluationSnapshot)
        .filter(SmithyEvaluationSnapshot.project_id == project_id)
        .order_by(desc(SmithyEvaluationSnapshot.created_at))
        .all()
    )


def get_evaluation_by_id(db: Session, evaluation_id: str) -> Optional[SmithyEvaluationSnapshot]:
    """Get an evaluation by its ID."""
    return db.query(SmithyEvaluationSnapshot).filter(SmithyEvaluationSnapshot.id == evaluation_id).first()


def create_evaluation(
    db: Session, project_id: str, evaluation: EvaluationSnapshotCreate
) -> SmithyEvaluationSnapshot:
    """Create a new evaluation snapshot for a project."""
    db_evaluation = SmithyEvaluationSnapshot(
        project_id=project_id,
        template_key=evaluation.template_key,
        template_snapshot=evaluation.template_snapshot.model_dump(),
        answers=evaluation.answers,
        evidence=evaluation.evidence,
        score_total=evaluation.score_total,
        publish_ready=evaluation.publish_ready,
    )
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation


# ═══════════════════════════════════════════════════════════════════════
# Evidence CRUD
# ═══════════════════════════════════════════════════════════════════════

def get_evidence_by_evaluation(db: Session, evaluation_id: str) -> list[SmithyEvidenceItem]:
    """Get all evidence items for an evaluation."""
    return (
        db.query(SmithyEvidenceItem)
        .filter(SmithyEvidenceItem.evaluation_id == evaluation_id)
        .order_by(SmithyEvidenceItem.created_at)
        .all()
    )


def create_evidence(
    db: Session, evaluation_id: str, checklist_item_key: str, evidence: EvidenceItemCreate
) -> SmithyEvidenceItem:
    """Create a new evidence item for an evaluation."""
    db_evidence = SmithyEvidenceItem(
        evaluation_id=evaluation_id,
        checklist_item_key=checklist_item_key,
        kind=evidence.kind,
        display_label=evidence.display_label,
        url=evidence.url,
        path=evidence.path,
        snippet=evidence.snippet,
        notes=evidence.notes,
        provenance=evidence.provenance,
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence
