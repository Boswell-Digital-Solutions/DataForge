"""
Due Diligence Dashboard - CRUD Operations (SECURED)

Database operations with user ownership enforcement and error handling.
Includes Redis caching for performance optimization.
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
import logging
import json

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

if TYPE_CHECKING:
    import redis as redis_type
else:
    redis_type = object

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
    DiligenceProjectSummary,
    DiligenceProjectWithReviews,
    DiligenceReviewCreate,
    DiligenceReviewUpdate,
    DiligenceReviewSummary,
    DiligenceFindingCreate,
    DiligenceFindingUpdate
)
from app.utils.cache_governance import redis_set_with_ttl_sync

logger = logging.getLogger(__name__)

# Redis client for caching (initialized lazily)
_redis_client: Optional["redis_type.Redis"] = None


def get_redis_client() -> Optional["redis_type.Redis"]:
    """Get or initialize Redis client (sync version for CRUD operations)."""
    global _redis_client
    
    if not REDIS_AVAILABLE:
        return None
    
    if _redis_client is None:
        try:
            from app.config import REDIS_URL
            if REDIS_URL:
                _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
                _redis_client.ping()
                logger.info("Redis sync client initialized for CRUD operations")
        except Exception as e:
            logger.warning(f"Redis sync client initialization failed: {e}")
    
    return _redis_client


def cache_get(key: str) -> Optional[dict]:
    """Get value from Redis cache."""
    try:
        client = get_redis_client()
        if not client:
            return None
        cached = client.get(key)
        if cached:
            return json.loads(cached)  # type: ignore
    except Exception as e:
        logger.debug(f"Cache get error: {e}")
    return None


def cache_set(key: str, value: any, ttl: int = 300) -> bool:  # type: ignore
    """Set value in Redis cache."""
    try:
        client = get_redis_client()
        if not client:
            return False
        redis_set_with_ttl_sync(client, key, json.dumps(value, default=str), ttl)
        return True
    except Exception as e:
        logger.debug(f"Cache set error: {e}")
    return False


def cache_delete(pattern: str) -> int:
    """Delete cache entries matching pattern."""
    try:
        client = get_redis_client()
        if not client:
            return 0
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)  # type: ignore
    except Exception as e:
        logger.debug(f"Cache delete error: {e}")
    return 0


# ============================================
# Project CRUD (with user ownership)
# ============================================

def _serialize_project_summary(project: DiligenceProject) -> dict:
    return DiligenceProjectSummary.model_validate(project, from_attributes=True).model_dump(mode="json")


def _serialize_project_with_reviews(project: DiligenceProject) -> dict:
    payload = DiligenceProjectWithReviews.model_validate(project, from_attributes=True).model_dump(mode="json")
    payload["reviews"] = [
        DiligenceReviewSummary.model_validate(review, from_attributes=True).model_dump(mode="json")
        for review in project.reviews
    ]
    return payload

def get_projects(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[DiligenceProject]:
    """Get all projects for a specific user with pagination (cached for 5 minutes)"""
    cache_key = f"projects:user:{user_id}:skip:{skip}:limit:{limit}"
    
    # Try cache first
    cached = cache_get(cache_key)
    if isinstance(cached, list):
        logger.debug(f"Cache hit for projects: {cache_key}")
        return [DiligenceProjectSummary.model_validate(project) for project in cached]  # type: ignore
    
    try:
        results = db.query(DiligenceProject)\
            .filter(DiligenceProject.user_id == user_id)\
            .order_by(desc(DiligenceProject.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        # Cache results for 5 minutes
        cache_set(cache_key, [_serialize_project_summary(project) for project in results], ttl=300)
        return results  # type: ignore
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching projects for user {user_id}: {e}")
        raise


def get_project(db: Session, project_id: int, user_id: int) -> Optional[DiligenceProject]:
    """Get a single project by ID with caching (cached for 5 minutes)"""
    cache_key = f"project:{project_id}:user:{user_id}"
    
    # Try cache first
    cached = cache_get(cache_key)
    if isinstance(cached, dict):
        logger.debug(f"Cache hit for project: {cache_key}")
        return DiligenceProjectWithReviews.model_validate(cached)  # type: ignore
    
    try:
        result = db.query(DiligenceProject)\
            .options(joinedload(DiligenceProject.reviews))\
            .filter(
                DiligenceProject.id == project_id,
                DiligenceProject.user_id == user_id
            )\
            .first()
        
        # Cache result for 5 minutes
        if result:
            cache_set(cache_key, _serialize_project_with_reviews(result), ttl=300)
        
        return result  # type: ignore
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching project {project_id} for user {user_id}: {e}")
        raise


def create_project(db: Session, project: DiligenceProjectCreate, user_id: int) -> DiligenceProject:
    """Create a new project for the authenticated user"""
    try:
        db_project = DiligenceProject(
            user_id=user_id,
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
        
        # Invalidate user's project list cache
        cache_delete(f"projects:user:{user_id}:*")
        
        logger.info(f"User {user_id} created project {db_project.id}: {db_project.name}")
        return db_project
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating project for user {user_id}: {e}")
        raise


def update_project(
    db: Session,
    project_id: int,
    user_id: int,
    project_update: DiligenceProjectUpdate
) -> Optional[DiligenceProject]:
    """Update a project (user ownership enforced) and invalidate cache"""
    try:
        db_project: Optional[DiligenceProject] = db.query(DiligenceProject).filter(
            DiligenceProject.id == project_id,
            DiligenceProject.user_id == user_id
        ).first()

        if not db_project:
            logger.warning(f"User {user_id} attempted to update non-existent/unauthorized project {project_id}")
            return None

        update_data = project_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_project, field, value)

        db.commit()
        db.refresh(db_project)
        
        # Invalidate related caches
        cache_delete(f"projects:user:{user_id}:*")
        cache_delete(f"project:{project_id}:*")
        
        logger.info(f"User {user_id} updated project {project_id}")
        return db_project  # type: ignore
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating project {project_id} for user {user_id}: {e}")
        raise


def delete_project(db: Session, project_id: int, user_id: int) -> bool:
    """Delete a project (user ownership enforced) and invalidate cache"""
    try:
        db_project = db.query(DiligenceProject).filter(
            DiligenceProject.id == project_id,
            DiligenceProject.user_id == user_id
        ).first()

        if not db_project:
            logger.warning(f"User {user_id} attempted to delete non-existent/unauthorized project {project_id}")
            return False

        db.delete(db_project)
        db.commit()
        
        # Invalidate related caches
        cache_delete(f"projects:user:{user_id}:*")
        cache_delete(f"project:{project_id}:*")
        
        logger.info(f"User {user_id} deleted project {project_id}: {db_project.name}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting project {project_id} for user {user_id}: {e}")
        raise


def update_project_health(db: Session, project_id: int, user_id: int) -> Optional[DiligenceProject]:
    """
    Update project health status based on latest review (user ownership enforced).
    """
    try:
        db_project: Optional[DiligenceProject] = db.query(DiligenceProject).filter(
            DiligenceProject.id == project_id,
            DiligenceProject.user_id == user_id
        ).first()

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

        return db_project  # type: ignore
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating health for project {project_id}: {e}")
        raise


# ============================================
# Review CRUD (with project ownership verification)
# ============================================

def get_reviews(
    db: Session,
    user_id: int,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[DiligenceReview]:
    """
    Get reviews for user's projects with pagination and eager loading.
    
    Performance optimizations:
    - Uses index on project_id and user_id
    - Eager loads findings to avoid N+1 queries
    - Paginates results with skip/limit
    """
    try:
        query = db.query(DiligenceReview)\
            .options(joinedload(DiligenceReview.findings))\
            .join(DiligenceProject)\
            .filter(DiligenceProject.user_id == user_id)

        if project_id:
            query = query.filter(DiligenceReview.project_id == project_id)

        results = query\
            .order_by(desc(DiligenceReview.review_date))\
            .offset(skip)\
            .limit(limit)\
            .all()
        return results  # type: ignore
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching reviews for user {user_id}: {e}")
        raise


def get_review(db: Session, review_id: int, user_id: int) -> Optional[DiligenceReview]:
    """Get a single review (user ownership enforced)"""
    try:
        result = db.query(DiligenceReview)\
            .options(joinedload(DiligenceReview.findings))\
            .join(DiligenceProject)\
            .filter(
                DiligenceReview.id == review_id,
                DiligenceProject.user_id == user_id
            )\
            .first()
        return result  # type: ignore
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching review {review_id} for user {user_id}: {e}")
        raise


def create_review(db: Session, review: DiligenceReviewCreate, user_id: int) -> Optional[DiligenceReview]:
    """Create a new review (project ownership enforced)"""
    try:
        # Verify project exists and belongs to user
        db_project = db.query(DiligenceProject).filter(
            DiligenceProject.id == review.project_id,
            DiligenceProject.user_id == user_id
        ).first()

        if not db_project:
            logger.warning(f"User {user_id} attempted to create review for unauthorized project {review.project_id}")
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
        logger.info(f"User {user_id} created review {db_review.id} for project {review.project_id}")

        # Update project health
        update_project_health(db, review.project_id, user_id)

        return db_review
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating review for user {user_id}: {e}")
        raise


def update_review(
    db: Session,
    review_id: int,
    user_id: int,
    review_update: DiligenceReviewUpdate
) -> Optional[DiligenceReview]:
    """Update a review (project ownership enforced)"""
    try:
        db_review: Optional[DiligenceReview] = db.query(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(
                DiligenceReview.id == review_id,
                DiligenceProject.user_id == user_id
            )\
            .first()

        if not db_review:
            logger.warning(f"User {user_id} attempted to update unauthorized review {review_id}")
            return None

        update_data = review_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_review, field, value)

        db.commit()
        db.refresh(db_review)
        logger.info(f"User {user_id} updated review {review_id}")

        # Update project health if rating changed
        if 'overall_rating' in update_data:
            update_project_health(db, db_review.project_id, user_id)

        return db_review  # type: ignore
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating review {review_id} for user {user_id}: {e}")
        raise


def delete_review(db: Session, review_id: int, user_id: int) -> bool:
    """Delete a review (project ownership enforced)"""
    try:
        db_review = db.query(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(
                DiligenceReview.id == review_id,
                DiligenceProject.user_id == user_id
            )\
            .first()

        if not db_review:
            logger.warning(f"User {user_id} attempted to delete unauthorized review {review_id}")
            return False

        project_id = db_review.project_id
        db.delete(db_review)
        db.commit()
        logger.info(f"User {user_id} deleted review {review_id}")

        # Update project health after deletion
        update_project_health(db, project_id, user_id)

        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting review {review_id} for user {user_id}: {e}")
        raise


# ============================================
# Finding CRUD (with review ownership verification)
# ============================================

def get_findings(
    db: Session,
    user_id: int,
    review_id: Optional[int] = None,
    status: Optional[FindingStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[DiligenceFinding]:
    """
    Get findings for user's reviews with filtering and pagination.
    
    Performance optimizations:
    - Uses index on status field for filtering
    - Uses index on review_id for quick lookups
    - Paginates results to avoid loading all findings
    """
    try:
        query = db.query(DiligenceFinding)\
            .join(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(DiligenceProject.user_id == user_id)

        if review_id:
            query = query.filter(DiligenceFinding.review_id == review_id)

        if status:
            query = query.filter(DiligenceFinding.status == status)

        results = query\
            .order_by(desc(DiligenceFinding.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
        return results  # type: ignore
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching findings for user {user_id}: {e}")
        raise


def get_finding(db: Session, finding_id: int, user_id: int) -> Optional[DiligenceFinding]:
    """Get a single finding (user ownership enforced)"""
    try:
        result = db.query(DiligenceFinding)\
            .join(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(
                DiligenceFinding.id == finding_id,
                DiligenceProject.user_id == user_id
            )\
            .first()
        return result  # type: ignore
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching finding {finding_id} for user {user_id}: {e}")
        raise


def create_finding(db: Session, finding: DiligenceFindingCreate, user_id: int) -> Optional[DiligenceFinding]:
    """Create a new finding (review ownership enforced)"""
    try:
        # Verify review exists and belongs to user
        db_review = db.query(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(
                DiligenceReview.id == finding.review_id,
                DiligenceProject.user_id == user_id
            )\
            .first()

        if not db_review:
            logger.warning(f"User {user_id} attempted to create finding for unauthorized review {finding.review_id}")
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
        logger.info(f"User {user_id} created finding {db_finding.id} for review {finding.review_id}")
        return db_finding
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating finding for user {user_id}: {e}")
        raise


def update_finding(
    db: Session,
    finding_id: int,
    user_id: int,
    finding_update: DiligenceFindingUpdate
) -> Optional[DiligenceFinding]:
    """Update a finding (review ownership enforced)"""
    try:
        db_finding: Optional[DiligenceFinding] = db.query(DiligenceFinding)\
            .join(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(
                DiligenceFinding.id == finding_id,
                DiligenceProject.user_id == user_id
            )\
            .first()

        if not db_finding:
            logger.warning(f"User {user_id} attempted to update unauthorized finding {finding_id}")
            return None

        update_data = finding_update.model_dump(exclude_unset=True)

        # If status is being set to resolved, set resolved_at timestamp
        if 'status' in update_data and update_data['status'] == FindingStatus.RESOLVED:
            if db_finding.status != FindingStatus.RESOLVED:
                db_finding.resolved_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(db_finding, field, value)

        db.commit()
        db.refresh(db_finding)
        logger.info(f"User {user_id} updated finding {finding_id}")
        return db_finding  # type: ignore
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating finding {finding_id} for user {user_id}: {e}")
        raise


def delete_finding(db: Session, finding_id: int, user_id: int) -> bool:
    """Delete a finding (review ownership enforced)"""
    try:
        db_finding = db.query(DiligenceFinding)\
            .join(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(
                DiligenceFinding.id == finding_id,
                DiligenceProject.user_id == user_id
            )\
            .first()

        if not db_finding:
            logger.warning(f"User {user_id} attempted to delete unauthorized finding {finding_id}")
            return False

        db.delete(db_finding)
        db.commit()
        logger.info(f"User {user_id} deleted finding {finding_id}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting finding {finding_id} for user {user_id}: {e}")
        raise


def bulk_create_findings(
    db: Session,
    review_id: int,
    user_id: int,
    findings: List[DiligenceFindingCreate]
) -> List[DiligenceFinding]:
    """Create multiple findings at once (review ownership enforced)"""
    try:
        # Verify review exists and belongs to user
        db_review = db.query(DiligenceReview)\
            .join(DiligenceProject)\
            .filter(
                DiligenceReview.id == review_id,
                DiligenceProject.user_id == user_id
            )\
            .first()

        if not db_review:
            logger.warning(f"User {user_id} attempted to bulk create findings for unauthorized review {review_id}")
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
        logger.info(f"User {user_id} bulk created {len(db_findings)} findings for review {review_id}")

        # Refresh all findings
        for db_finding in db_findings:
            db.refresh(db_finding)

        return db_findings
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error bulk creating findings for user {user_id}: {e}")
        raise
