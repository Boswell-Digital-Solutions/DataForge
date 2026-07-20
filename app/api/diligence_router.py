"""
Due Diligence Dashboard - API Router

FastAPI endpoints for projects, reviews, and findings.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from pydantic import BaseModel

from app.database import get_db
from app.models import models
from app.models.diligence_models import DiligenceProject as DiligenceProjectModel
from app.models.diligence_models import FindingStatus
from app.models.diligence_schemas import (
    DiligenceProject,
    DiligenceProjectCreate,
    DiligenceProjectUpdate,
    DiligenceProjectSummary,
    DiligenceProjectWithReviews,
    DiligenceReview,
    DiligenceReviewCreate,
    DiligenceReviewUpdate,
    DiligenceReviewSummary,
    DiligenceReviewWithFindings,
    DiligenceFinding,
    DiligenceFindingCreate,
    DiligenceFindingUpdate,
    BulkReviewCreate,
    FindingSeverityEnum,
    FindingStatusEnum
)
from app.api import diligence_crud
from app.utils.auth import get_current_admin_user, get_current_user, get_optional_user
from app.utils.diligence_parser import parse_ai_report

# Router for API endpoints
router = APIRouter(prefix="/api/diligence", tags=["diligence"])

# Router for UI pages
ui_router = APIRouter(tags=["diligence_ui"])

# Templates
templates = None
if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")


class LegacyDiligenceFindingPayload(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str
    status: FindingStatusEnum = FindingStatusEnum.OPEN
    category: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    remediation: Optional[str] = None


class LegacyDiligenceClosePayload(BaseModel):
    rating: Optional[str] = None
    recommendation: Optional[str] = None


def _legacy_project_id_for_review(review: object) -> int:
    project_metadata = getattr(getattr(review, "project", None), "project_metadata", None) or {}
    source_project_id = project_metadata.get("source_project_id")
    if isinstance(source_project_id, int):
        return source_project_id
    return getattr(review, "project_id")


def _legacy_review_status(review: object) -> str:
    if getattr(review, "overall_rating", None) is not None or getattr(review, "recommendation", None):
        return "closed"
    return "open"


def _serialize_legacy_review_response(review: object, *, include_findings: bool = False) -> dict:
    schema = DiligenceReviewWithFindings if include_findings else DiligenceReview
    payload = schema.model_validate(review, from_attributes=True).model_dump(mode="json")
    payload["project_id"] = _legacy_project_id_for_review(review)
    payload["status"] = _legacy_review_status(review)
    return payload


def _resolve_legacy_diligence_project_id(
    db: Session,
    *,
    current_user_id: int,
    legacy_project_id: int,
) -> Optional[int]:
    diligence_project = db.query(DiligenceProjectModel).filter(
        DiligenceProjectModel.id == legacy_project_id,
        DiligenceProjectModel.user_id == current_user_id,
    ).first()
    if diligence_project:
        return diligence_project.id

    # Historical behavior queried the legacy AuthorForge ``projects`` table and
    # copied its title/description into diligence.  That crosses the local-only
    # AuthorForge content boundary, so this compatibility fallback is retired.
    return None


def _normalize_legacy_finding_severity(severity: str) -> FindingSeverityEnum:
    normalized = severity.strip().lower()
    if normalized == "info":
        normalized = FindingSeverityEnum.LOW.value
    try:
        return FindingSeverityEnum(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unsupported finding severity: {severity}") from exc


def _normalize_legacy_review_rating(rating: Optional[str]):
    if rating is None:
        return None
    normalized = rating.strip().lower()
    rating_map = {
        "recommended": "green",
        "proceed": "green",
        "conditional": "yellow",
        "caution": "yellow",
        "not_recommended": "red",
        "do_not_proceed": "red",
        "reject": "red",
        "green": "green",
        "yellow": "yellow",
        "red": "red",
    }
    mapped = rating_map.get(normalized)
    if mapped is None:
        raise HTTPException(status_code=422, detail=f"Unsupported review rating: {rating}")
    return mapped


def _build_legacy_review_report(review: object) -> dict:
    findings = [
        DiligenceFinding.model_validate(finding, from_attributes=True).model_dump(mode="json")
        for finding in getattr(review, "findings", [])
    ]
    severity_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for finding in findings:
        severity = finding.get("severity", "unknown")
        status = finding.get("status", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "review_id": getattr(review, "id"),
        "project_id": _legacy_project_id_for_review(review),
        "status": _legacy_review_status(review),
        "overall_rating": getattr(review, "overall_rating", None),
        "recommendation": getattr(review, "recommendation", None),
        "summary": getattr(review, "summary", None),
        "findings": findings,
        "findings_summary": {
            "total": len(findings),
            "by_severity": severity_counts,
            "by_status": status_counts,
        },
    }


# ============================================
# Project API Endpoints
# ============================================

@router.get("", response_model=List[DiligenceReviewSummary])
def list_reviews_legacy(
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Legacy compatibility endpoint for listing diligence reviews."""
    return diligence_crud.get_reviews(db, user_id=current_user.id, project_id=project_id, skip=skip, limit=limit)


@router.post("", response_model=DiligenceReview)
def create_review_legacy(
    review: DiligenceReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Legacy compatibility endpoint for creating a diligence review."""
    diligence_project_id = _resolve_legacy_diligence_project_id(
        db,
        current_user_id=current_user.id,
        legacy_project_id=review.project_id,
    )
    if diligence_project_id is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db_review = diligence_crud.create_review(
        db,
        user_id=current_user.id,
        review=review.model_copy(update={"project_id": diligence_project_id}),
    )
    if not db_review:
        raise HTTPException(status_code=404, detail="Project not found")
    return _serialize_legacy_review_response(db_review)


@router.get("/projects", response_model=List[DiligenceProjectSummary])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Get all due diligence projects for current user.

    Returns a list of projects with summary information including
    current health status and latest review date.
    """
    projects = diligence_crud.get_projects(db, user_id=current_user.id, skip=skip, limit=limit)
    return projects


@router.post("/projects", response_model=DiligenceProject, status_code=status.HTTP_201_CREATED)
def create_project(
    project: DiligenceProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Create a new due diligence project.

    Provide project name, description, git URL, and optional metadata.
    """
    # Set user_id on the project
    project.user_id = current_user.id
    return diligence_crud.create_project(db, user_id=current_user.id, project=project)


@router.get("/projects/{project_id}", response_model=DiligenceProjectWithReviews)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Get a specific project with all its reviews.

    Returns detailed project information including review history.
    """
    project = diligence_crud.get_project(db, user_id=current_user.id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=DiligenceProject)
def update_project(
    project_id: int,
    project_update: DiligenceProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Update a project's information.

    Allows updating name, description, URLs, tags, and metadata.
    """
    project = diligence_crud.update_project(db, user_id=current_user.id, project_id=project_id, project_update=project_update)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Delete a project and all its reviews.

    This will cascade delete all associated reviews and findings.
    """
    success = diligence_crud.delete_project(db, user_id=current_user.id, project_id=project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")


# ============================================
# Review API Endpoints
# ============================================

@router.get("/reviews", response_model=List[DiligenceReviewSummary])
def list_reviews(
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Get reviews for current user, optionally filtered by project.

    Returns a list of reviews with summary information.
    """
    reviews = diligence_crud.get_reviews(db, user_id=current_user.id, project_id=project_id, skip=skip, limit=limit)
    return reviews


@router.post("/reviews", response_model=DiligenceReview, status_code=status.HTTP_201_CREATED)
def create_review(
    review: DiligenceReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Create a new due diligence review.

    Provide review scores, summary, strengths, risks, and findings.
    """
    db_review = diligence_crud.create_review(db, user_id=current_user.id, review=review)
    if not db_review:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_review


@router.get("/reviews/{review_id}", response_model=DiligenceReviewWithFindings)
def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Get a specific review with all its findings.

    Returns complete review details including all findings.
    """
    review = diligence_crud.get_review(db, user_id=current_user.id, review_id=review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.put("/reviews/{review_id}", response_model=DiligenceReview)
def update_review(
    review_id: int,
    review_update: DiligenceReviewUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Update a review's information.

    Allows updating scores, summary, strengths, risks, and recommendation.
    """
    review = diligence_crud.update_review(db, user_id=current_user.id, review_id=review_id, review_update=review_update)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Delete a review and all its findings.

    This will cascade delete all associated findings.
    """
    success = diligence_crud.delete_review(db, user_id=current_user.id, review_id=review_id)
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")


# ============================================
# Finding API Endpoints
# ============================================

@router.get("/findings", response_model=List[DiligenceFinding])
def list_findings(
    review_id: Optional[int] = None,
    status_filter: Optional[FindingStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Get findings for current user, optionally filtered by review and/or status.

    Returns a list of findings with all details.
    """
    findings = diligence_crud.get_findings(
        db,
        user_id=current_user.id,
        review_id=review_id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    return findings


@router.post("/findings", response_model=DiligenceFinding, status_code=status.HTTP_201_CREATED)
def create_finding(
    finding: DiligenceFindingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Create a new finding.

    Provide title, description, severity, and optional details.
    """
    db_finding = diligence_crud.create_finding(db, user_id=current_user.id, finding=finding)
    if not db_finding:
        raise HTTPException(status_code=404, detail="Review not found")
    return db_finding


@router.get("/{review_id}")
def get_review_legacy(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Legacy compatibility endpoint for fetching a diligence review."""
    review = diligence_crud.get_review(db, user_id=current_user.id, review_id=review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize_legacy_review_response(review, include_findings=True)


@router.post("/{review_id}/findings", response_model=DiligenceFinding)
def create_finding_legacy(
    review_id: int,
    finding: LegacyDiligenceFindingPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Legacy compatibility endpoint for adding a finding to a diligence review."""
    db_finding = diligence_crud.create_finding(
        db,
        user_id=current_user.id,
        finding=DiligenceFindingCreate(
            review_id=review_id,
            **finding.model_dump(exclude={"severity"}),
            severity=_normalize_legacy_finding_severity(finding.severity),
        ),
    )
    if not db_finding:
        raise HTTPException(status_code=404, detail="Review not found")
    return db_finding


@router.get("/{review_id}/report")
def get_review_report_legacy(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Legacy compatibility endpoint for a structured diligence report."""
    review = diligence_crud.get_review(db, user_id=current_user.id, review_id=review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return _build_legacy_review_report(review)


@router.post("/{review_id}/close")
def close_review_legacy(
    review_id: int,
    close_payload: LegacyDiligenceClosePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Legacy compatibility endpoint for closing a diligence review."""
    review = diligence_crud.update_review(
        db,
        user_id=current_user.id,
        review_id=review_id,
        review_update=DiligenceReviewUpdate(
            overall_rating=_normalize_legacy_review_rating(close_payload.rating),
            recommendation=close_payload.recommendation,
        ),
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize_legacy_review_response(review)


@router.get("/findings/{finding_id}", response_model=DiligenceFinding)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Get a specific finding by ID.

    Returns complete finding details.
    """
    finding = diligence_crud.get_finding(db, user_id=current_user.id, finding_id=finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.put("/findings/{finding_id}", response_model=DiligenceFinding)
def update_finding(
    finding_id: int,
    finding_update: DiligenceFindingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Update a finding.

    Allows updating status, severity, description, and remediation.
    """
    finding = diligence_crud.update_finding(db, user_id=current_user.id, finding_id=finding_id, finding_update=finding_update)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.delete("/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Delete a finding.
    """
    success = diligence_crud.delete_finding(db, user_id=current_user.id, finding_id=finding_id)
    if not success:
        raise HTTPException(status_code=404, detail="Finding not found")


# ============================================
# Bulk/Parser Endpoints
# ============================================

@router.post("/reviews/bulk", response_model=DiligenceReviewWithFindings, status_code=status.HTTP_201_CREATED)
def create_review_from_bulk_text(
    bulk_review: BulkReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """
    Create a review by parsing bulk AI-generated text.

    Paste markdown from Claude, ChatGPT, etc. and it will be parsed into
    structured review data with scores, findings, etc.
    """
    # Parse the AI report
    parsed = parse_ai_report(bulk_review.raw_report_text)

    # Create the review
    review_create = DiligenceReviewCreate(
        project_id=bulk_review.project_id,
        reviewer_name=bulk_review.reviewer_name,
        review_type=bulk_review.review_type,
        summary=parsed.summary,
        strengths=parsed.strengths,
        risks=parsed.risks,
        recommendation=parsed.recommendation,
        code_quality_score=parsed.code_quality_score,
        security_score=parsed.security_score,
        architecture_score=parsed.architecture_score,
        operations_score=parsed.operations_score,
        documentation_score=parsed.documentation_score,
        overall_rating=parsed.overall_rating,
        raw_report_text=bulk_review.raw_report_text
    )

    db_review = diligence_crud.create_review(db, user_id=current_user.id, review=review_create)
    if not db_review:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create findings
    if parsed.findings:
        finding_creates = [
            DiligenceFindingCreate(
                review_id=db_review.id,
                **finding_dict
            )
            for finding_dict in parsed.findings
        ]
        diligence_crud.bulk_create_findings(db, user_id=current_user.id, review_id=db_review.id, findings=finding_creates)

    # Reload review with findings
    db_review = diligence_crud.get_review(db, user_id=current_user.id, review_id=db_review.id)
    return db_review


# ============================================
# UI Page Endpoints
# ============================================

@ui_router.get("/diligence", response_class=HTMLResponse)
@ui_router.get("/diligence/dashboard", response_class=HTMLResponse)
async def diligence_dashboard(request: Request, db: Session = Depends(get_db), current_user: Optional[models.User] = Depends(get_optional_user)):
    """
    Main Due Diligence Dashboard page for current user.

    Shows all projects with their health status.
    """
    if templates is None:
        return HTMLResponse(
            content="<h1>Templates not configured</h1>",
            status_code=500
        )

    # If no user is authenticated, show empty projects list
    if current_user is None:
        projects = []
    else:
        projects = diligence_crud.get_projects(db, user_id=current_user.id, limit=100)
    
    return templates.TemplateResponse(
        "diligence/dashboard.html",
        {"request": request, "projects": projects, "current_user": current_user}
    )


@ui_router.get("/diligence/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """
    Project detail page.

    Shows project information and review history.
    """
    if templates is None:
        return HTMLResponse(
            content="<h1>Templates not configured</h1>",
            status_code=500
        )

    project = diligence_crud.get_project(db, user_id=current_user.id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    reviews = diligence_crud.get_reviews(db, user_id=current_user.id, project_id=project_id, limit=50)

    return templates.TemplateResponse(
        "diligence/project_detail.html",
        {"request": request, "project": project, "reviews": reviews}
    )


@ui_router.get("/diligence/reviews/{review_id}", response_class=HTMLResponse)
async def review_detail(request: Request, review_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """
    Review detail page.

    Shows complete review report with findings.
    """
    if templates is None:
        return HTMLResponse(
            content="<h1>Templates not configured</h1>",
            status_code=500
        )

    review = diligence_crud.get_review(db, user_id=current_user.id, review_id=review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    project = diligence_crud.get_project(db, user_id=current_user.id, project_id=review.project_id)

    return templates.TemplateResponse(
        "diligence/review_detail.html",
        {"request": request, "review": review, "project": project}
    )


@ui_router.get("/diligence/new", response_class=HTMLResponse)
async def new_review(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    """
    Create new review page.

    Form for creating projects and reviews, including bulk paste.
    """
    if templates is None:
        return HTMLResponse(
            content="<h1>Templates not configured</h1>",
            status_code=500
        )

    projects = diligence_crud.get_projects(db, user_id=current_user.id, limit=100)

    return templates.TemplateResponse(
        "diligence/new_review.html",
        {"request": request, "projects": projects}
    )
