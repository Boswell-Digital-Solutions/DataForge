"""
Due Diligence Dashboard - CRUD Operations

Database operations for projects, reviews, and findings.
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, UTC

from app.models.diligence_models import (
    DiligenceProject,
    DiligenceReview,
    DiligenceFinding,
    OverallRating,
    FindingStatus
)
from app.models.diligence_schemas import (
    DiligenceProjectCreate,
    DiligenceProjectUpdate,
    DiligenceReviewCreate,
    DiligenceReviewUpdate,
    DiligenceFindingCreate,
    DiligenceFindingUpdate
)


# ============================================
# Project CRUD
# ============================================

def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[DiligenceProject]:
    """Get all projects with pagination"""
    return db.query(DiligenceProject)\
        .order_by(desc(DiligenceProject.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_project(db: Session, project_id: int) -> Optional[DiligenceProject]:
    """Get a single project by ID"""
    return db.query(DiligenceProject)\
        .options(joinedload(DiligenceProject.reviews))\
        .filter(DiligenceProject.id == project_id)\
        .first()


def create_project(db: Session, project: DiligenceProjectCreate) -> DiligenceProject:
    """Create a new project"""
    db_project = DiligenceProject(
        name=project.name,
        description=project.description,
        git_url=project.git_url,
        repo_path=project.repo_path,
        tags=project.tags,
        project_metadata=project.project_metadata
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def update_project(
    db: Session,
    project_id: int,
    project_update: DiligenceProjectUpdate
) -> Optional[DiligenceProject]:
    """Update a project"""
    db_project = db.query(DiligenceProject).filter(DiligenceProject.id == project_id).first()
    if not db_project:
        return None

    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_project, field, value)

    db.commit()
    db.refresh(db_project)
    return db_project


def delete_project(db: Session, project_id: int) -> bool:
    """Delete a project"""
    db_project = db.query(DiligenceProject).filter(DiligenceProject.id == project_id).first()
    if not db_project:
        return False

    db.delete(db_project)
    db.commit()
    return True


def update_project_health(db: Session, project_id: int) -> Optional[DiligenceProject]:
    """
    Update project health status based on latest review.
    Should be called after creating a new review.
    """
    db_project = db.query(DiligenceProject).filter(DiligenceProject.id == project_id).first()
    if not db_project:
        return None

    # Get latest review
    latest_review = db.query(DiligenceReview)\
        .filter(DiligenceReview.project_id == project_id)\
        .order_by(desc(DiligenceReview.review_date))\
        .first()

    if latest_review:
        db_project.current_health_status = latest_review.overall_rating
        db_project.latest_review_date = latest_review.review_date
        db.commit()
        db.refresh(db_project)

    return db_project


# ============================================
# Review CRUD
# ============================================

def get_reviews(
    db: Session,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[DiligenceReview]:
    """Get reviews, optionally filtered by project"""
    query = db.query(DiligenceReview)

    if project_id:
        query = query.filter(DiligenceReview.project_id == project_id)

    return query\
        .order_by(desc(DiligenceReview.review_date))\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_review(db: Session, review_id: int) -> Optional[DiligenceReview]:
    """Get a single review by ID with findings"""
    return db.query(DiligenceReview)\
        .options(joinedload(DiligenceReview.findings))\
        .filter(DiligenceReview.id == review_id)\
        .first()


def create_review(db: Session, review: DiligenceReviewCreate) -> Optional[DiligenceReview]:
    """Create a new review"""
    # Verify project exists
    db_project = db.query(DiligenceProject).filter(DiligenceProject.id == review.project_id).first()
    if not db_project:
        return None

    db_review = DiligenceReview(
        project_id=review.project_id,
        reviewer_name=review.reviewer_name,
        review_type=review.review_type,
        summary=review.summary,
        strengths=review.strengths,
        risks=review.risks,
        recommendation=review.recommendation,
        code_quality_score=review.code_quality_score,
        security_score=review.security_score,
        architecture_score=review.architecture_score,
        operations_score=review.operations_score,
        documentation_score=review.documentation_score,
        overall_rating=review.overall_rating,
        raw_report_text=review.raw_report_text
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)

    # Update project health
    update_project_health(db, review.project_id)

    return db_review


def update_review(
    db: Session,
    review_id: int,
    review_update: DiligenceReviewUpdate
) -> Optional[DiligenceReview]:
    """Update a review"""
    db_review = db.query(DiligenceReview).filter(DiligenceReview.id == review_id).first()
    if not db_review:
        return None

    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_review, field, value)

    db.commit()
    db.refresh(db_review)

    # Update project health if rating changed
    if 'overall_rating' in update_data:
        update_project_health(db, db_review.project_id)

    return db_review


def delete_review(db: Session, review_id: int) -> bool:
    """Delete a review"""
    db_review = db.query(DiligenceReview).filter(DiligenceReview.id == review_id).first()
    if not db_review:
        return False

    project_id = db_review.project_id
    db.delete(db_review)
    db.commit()

    # Update project health after deletion
    update_project_health(db, project_id)

    return True


# ============================================
# Finding CRUD
# ============================================

def get_findings(
    db: Session,
    review_id: Optional[int] = None,
    status: Optional[FindingStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[DiligenceFinding]:
    """Get findings, optionally filtered by review and/or status"""
    query = db.query(DiligenceFinding)

    if review_id:
        query = query.filter(DiligenceFinding.review_id == review_id)

    if status:
        query = query.filter(DiligenceFinding.status == status)

    return query\
        .order_by(desc(DiligenceFinding.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_finding(db: Session, finding_id: int) -> Optional[DiligenceFinding]:
    """Get a single finding by ID"""
    return db.query(DiligenceFinding)\
        .filter(DiligenceFinding.id == finding_id)\
        .first()


def create_finding(db: Session, finding: DiligenceFindingCreate) -> Optional[DiligenceFinding]:
    """Create a new finding"""
    # Verify review exists
    db_review = db.query(DiligenceReview).filter(DiligenceReview.id == finding.review_id).first()
    if not db_review:
        return None

    db_finding = DiligenceFinding(
        review_id=finding.review_id,
        title=finding.title,
        description=finding.description,
        severity=finding.severity,
        status=finding.status,
        category=finding.category,
        file_path=finding.file_path,
        line_number=finding.line_number,
        remediation=finding.remediation
    )
    db.add(db_finding)
    db.commit()
    db.refresh(db_finding)
    return db_finding


def update_finding(
    db: Session,
    finding_id: int,
    finding_update: DiligenceFindingUpdate
) -> Optional[DiligenceFinding]:
    """Update a finding"""
    db_finding = db.query(DiligenceFinding).filter(DiligenceFinding.id == finding_id).first()
    if not db_finding:
        return None

    update_data = finding_update.model_dump(exclude_unset=True)

    # If status is being set to resolved, set resolved_at timestamp
    if 'status' in update_data and update_data['status'] == FindingStatus.RESOLVED:
        if db_finding.status != FindingStatus.RESOLVED:
            db_finding.resolved_at = datetime.now(UTC)

    for field, value in update_data.items():
        setattr(db_finding, field, value)

    db.commit()
    db.refresh(db_finding)
    return db_finding


def delete_finding(db: Session, finding_id: int) -> bool:
    """Delete a finding"""
    db_finding = db.query(DiligenceFinding).filter(DiligenceFinding.id == finding_id).first()
    if not db_finding:
        return False

    db.delete(db_finding)
    db.commit()
    return True


def bulk_create_findings(
    db: Session,
    review_id: int,
    findings: List[DiligenceFindingCreate]
) -> List[DiligenceFinding]:
    """Create multiple findings at once"""
    # Verify review exists
    db_review = db.query(DiligenceReview).filter(DiligenceReview.id == review_id).first()
    if not db_review:
        return []

    db_findings = []
    for finding in findings:
        db_finding = DiligenceFinding(
            review_id=review_id,
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
            status=finding.status,
            category=finding.category,
            file_path=finding.file_path,
            line_number=finding.line_number,
            remediation=finding.remediation
        )
        db_findings.append(db_finding)

    db.add_all(db_findings)
    db.commit()

    # Refresh all findings
    for db_finding in db_findings:
        db.refresh(db_finding)

    return db_findings
