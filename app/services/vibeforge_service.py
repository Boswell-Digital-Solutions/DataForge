"""
CRUD services for VibeForge learning layer.
Handles database operations for projects, sessions, outcomes, performance, and preferences.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta, UTC

from app.models.vibeforge_models import (
    VibeForgeProject,
    ProjectSession,
    StackOutcome,
    ModelPerformance,
    LanguagePreference,
    ProjectType,
    OutcomeStatus
)
from app.models.vibeforge_schemas import (
    VibeForgeProjectCreate,
    VibeForgeProjectUpdate,
    ProjectSessionCreate,
    ProjectSessionUpdate,
    StackOutcomeCreate,
    StackOutcomeUpdate,
    ModelPerformanceCreate,
    ModelPerformanceUpdate,
    LanguagePreferenceUpdate,
    StackSuccessRate,
    LanguageTrend,
    UserPreferenceSummary
)


# ============================================================================
# Project Service
# ============================================================================

class ProjectService:
    """Service for VibeForge project CRUD operations."""
    
    @staticmethod
    def create(db: Session, project: VibeForgeProjectCreate) -> VibeForgeProject:
        """Create a new VibeForge project."""
        db_project = VibeForgeProject(**project.model_dump())
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def get(db: Session, project_id: int) -> Optional[VibeForgeProject]:
        """Get a project by ID."""
        return db.query(VibeForgeProject).filter(VibeForgeProject.id == project_id).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[VibeForgeProject]:
        """Get all projects for a user."""
        return (
            db.query(VibeForgeProject)
            .filter(VibeForgeProject.user_id == user_id)
            .order_by(desc(VibeForgeProject.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_by_stack(db: Session, stack_id: str, skip: int = 0, limit: int = 100) -> List[VibeForgeProject]:
        """Get all projects using a specific stack."""
        return (
            db.query(VibeForgeProject)
            .filter(VibeForgeProject.selected_stack == stack_id)
            .order_by(desc(VibeForgeProject.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_by_type(db: Session, project_type: ProjectType, skip: int = 0, limit: int = 100) -> List[VibeForgeProject]:
        """Get all projects of a specific type."""
        return (
            db.query(VibeForgeProject)
            .filter(VibeForgeProject.project_type == project_type)
            .order_by(desc(VibeForgeProject.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def update(db: Session, project_id: int, project_update: VibeForgeProjectUpdate) -> Optional[VibeForgeProject]:
        """Update a project."""
        db_project = ProjectService.get(db, project_id)
        if not db_project:
            return None
        
        update_data = project_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_project, field, value)
        
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def delete(db: Session, project_id: int) -> bool:
        """Delete a project."""
        db_project = ProjectService.get(db, project_id)
        if not db_project:
            return False
        
        db.delete(db_project)
        db.commit()
        return True
    
    @staticmethod
    def get_recent(db: Session, days: int = 30, limit: int = 100) -> List[VibeForgeProject]:
        """Get recent projects within specified days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        return (
            db.query(VibeForgeProject)
            .filter(VibeForgeProject.created_at >= cutoff)
            .order_by(desc(VibeForgeProject.created_at))
            .limit(limit)
            .all()
        )


# ============================================================================
# Session Service
# ============================================================================

class SessionService:
    """Service for project session CRUD operations."""
    
    @staticmethod
    def create(db: Session, session: ProjectSessionCreate) -> ProjectSession:
        """Create a new project session."""
        db_session = ProjectSession(**session.model_dump())
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session
    
    @staticmethod
    def get(db: Session, session_id: int) -> Optional[ProjectSession]:
        """Get a session by ID."""
        return db.query(ProjectSession).filter(ProjectSession.id == session_id).first()
    
    @staticmethod
    def get_by_project(db: Session, project_id: int) -> List[ProjectSession]:
        """Get all sessions for a project."""
        return (
            db.query(ProjectSession)
            .filter(ProjectSession.project_id == project_id)
            .order_by(desc(ProjectSession.session_started_at))
            .all()
        )
    
    @staticmethod
    def update(db: Session, session_id: int, session_update: ProjectSessionUpdate) -> Optional[ProjectSession]:
        """Update a session."""
        db_session = SessionService.get(db, session_id)
        if not db_session:
            return None
        
        update_data = session_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_session, field, value)
        
        db.commit()
        db.refresh(db_session)
        return db_session
    
    @staticmethod
    def mark_completed(db: Session, session_id: int) -> Optional[ProjectSession]:
        """Mark a session as completed with calculated duration."""
        db_session = SessionService.get(db, session_id)
        if not db_session:
            return None
        
        completed_at = datetime.now(UTC)
        started_at = db_session.session_started_at
        # PostgreSQL preserves timezone awareness, while SQLite (used by the
        # deterministic unit suite) returns the same DateTime column as naive.
        # Normalize the latter as UTC before duration arithmetic.
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        db_session.session_completed_at = completed_at
        duration = (completed_at - started_at).total_seconds()
        db_session.session_duration_seconds = int(duration)
        
        db.commit()
        db.refresh(db_session)
        return db_session
    
    @staticmethod
    def mark_abandoned(db: Session, session_id: int) -> Optional[ProjectSession]:
        """Mark a session as abandoned."""
        db_session = SessionService.get(db, session_id)
        if not db_session:
            return None
        
        db_session.abandoned = True
        db.commit()
        db.refresh(db_session)
        return db_session
    
    @staticmethod
    def get_abandoned_sessions(db: Session, days: int = 7) -> List[ProjectSession]:
        """Get sessions that appear abandoned (not completed within time window)."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        return (
            db.query(ProjectSession)
            .filter(
                and_(
                    ProjectSession.session_completed_at.is_(None),
                    ProjectSession.session_started_at < cutoff,
                    ProjectSession.abandoned == False
                )
            )
            .all()
        )


# ============================================================================
# Outcome Service
# ============================================================================

class OutcomeService:
    """Service for stack outcome CRUD operations."""
    
    @staticmethod
    def create(db: Session, outcome: StackOutcomeCreate) -> StackOutcome:
        """Create a new stack outcome record."""
        db_outcome = StackOutcome(**outcome.model_dump())
        db.add(db_outcome)
        db.commit()
        db.refresh(db_outcome)
        return db_outcome
    
    @staticmethod
    def get(db: Session, outcome_id: int) -> Optional[StackOutcome]:
        """Get an outcome by ID."""
        return db.query(StackOutcome).filter(StackOutcome.id == outcome_id).first()
    
    @staticmethod
    def get_by_project(db: Session, project_id: int) -> List[StackOutcome]:
        """Get all outcomes for a project."""
        return (
            db.query(StackOutcome)
            .filter(StackOutcome.project_id == project_id)
            .order_by(desc(StackOutcome.recorded_at))
            .all()
        )
    
    @staticmethod
    def get_by_stack(db: Session, stack_id: str, skip: int = 0, limit: int = 100) -> List[StackOutcome]:
        """Get all outcomes for a specific stack."""
        return (
            db.query(StackOutcome)
            .filter(StackOutcome.stack_id == stack_id)
            .order_by(desc(StackOutcome.recorded_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def update(db: Session, outcome_id: int, outcome_update: StackOutcomeUpdate) -> Optional[StackOutcome]:
        """Update an outcome record."""
        db_outcome = OutcomeService.get(db, outcome_id)
        if not db_outcome:
            return None
        
        update_data = outcome_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_outcome, field, value)
        
        db.commit()
        db.refresh(db_outcome)
        return db_outcome
    
    @staticmethod
    def get_stack_success_rate(db: Session, stack_id: str, project_type: Optional[ProjectType] = None) -> Optional[StackSuccessRate]:
        """Calculate success rate for a stack."""
        query = db.query(StackOutcome).filter(StackOutcome.stack_id == stack_id)
        
        if project_type:
            query = query.filter(StackOutcome.project_type == project_type)
        
        outcomes = query.all()
        if not outcomes:
            return None
        
        total_uses = len(outcomes)
        success_count = sum(1 for o in outcomes if o.outcome_status == OutcomeStatus.success)
        partial_count = sum(1 for o in outcomes if o.outcome_status == OutcomeStatus.partial)
        failure_count = sum(1 for o in outcomes if o.outcome_status == OutcomeStatus.failure)
        
        success_rate = success_count / total_uses if total_uses > 0 else 0.0
        
        satisfactions = [o.user_satisfaction for o in outcomes if o.user_satisfaction is not None]
        avg_satisfaction = sum(satisfactions) / len(satisfactions) if satisfactions else None
        
        build_times = [o.build_time_seconds for o in outcomes if o.build_time_seconds is not None]
        avg_build_time = int(sum(build_times) / len(build_times)) if build_times else None
        
        test_rates = [o.test_pass_rate for o in outcomes if o.test_pass_rate is not None]
        avg_test_pass_rate = sum(test_rates) / len(test_rates) if test_rates else None
        
        return StackSuccessRate(
            stack_id=stack_id,
            project_type=project_type or outcomes[0].project_type,
            total_uses=total_uses,
            success_count=success_count,
            partial_count=partial_count,
            failure_count=failure_count,
            success_rate=success_rate,
            avg_satisfaction=avg_satisfaction,
            avg_build_time_seconds=avg_build_time,
            avg_test_pass_rate=avg_test_pass_rate
        )


# ============================================================================
# Performance Service
# ============================================================================

class PerformanceService:
    """Service for model performance CRUD operations."""
    
    @staticmethod
    def create(db: Session, performance: ModelPerformanceCreate) -> ModelPerformance:
        """Create a new model performance record."""
        db_performance = ModelPerformance(**performance.model_dump())
        db.add(db_performance)
        db.commit()
        db.refresh(db_performance)
        return db_performance
    
    @staticmethod
    def get(db: Session, performance_id: int) -> Optional[ModelPerformance]:
        """Get a performance record by ID."""
        return db.query(ModelPerformance).filter(ModelPerformance.id == performance_id).first()
    
    @staticmethod
    def get_by_session(db: Session, session_id: int) -> List[ModelPerformance]:
        """Get all performance records for a session."""
        return (
            db.query(ModelPerformance)
            .filter(ModelPerformance.session_id == session_id)
            .order_by(desc(ModelPerformance.created_at))
            .all()
        )
    
    @staticmethod
    def get_by_provider(db: Session, provider: str, skip: int = 0, limit: int = 100) -> List[ModelPerformance]:
        """Get performance records for a specific provider."""
        return (
            db.query(ModelPerformance)
            .filter(ModelPerformance.provider == provider)
            .order_by(desc(ModelPerformance.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def update(db: Session, performance_id: int, performance_update: ModelPerformanceUpdate) -> Optional[ModelPerformance]:
        """Update a performance record."""
        db_performance = PerformanceService.get(db, performance_id)
        if not db_performance:
            return None
        
        update_data = performance_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_performance, field, value)
        
        db.commit()
        db.refresh(db_performance)
        return db_performance
    
    @staticmethod
    def get_acceptance_rate(db: Session, provider: str, model_name: str) -> float:
        """Calculate recommendation acceptance rate for a model."""
        records = (
            db.query(ModelPerformance)
            .filter(
                and_(
                    ModelPerformance.provider == provider,
                    ModelPerformance.model_name == model_name,
                    ModelPerformance.recommendation_accepted.is_not(None)
                )
            )
            .all()
        )
        
        if not records:
            return 0.0
        
        accepted = sum(1 for r in records if r.recommendation_accepted)
        return accepted / len(records)


# ============================================================================
# Preference Service
# ============================================================================

class PreferenceService:
    """Service for language preference CRUD operations."""
    
    @staticmethod
    def get_or_create(
        db: Session,
        user_id: int,
        language_id: str,
        language_name: str
    ) -> LanguagePreference:
        """Get or create a language preference record."""
        db_pref = (
            db.query(LanguagePreference)
            .filter(
                and_(
                    LanguagePreference.user_id == user_id,
                    LanguagePreference.language_id == language_id
                )
            )
            .first()
        )
        
        if not db_pref:
            db_pref = LanguagePreference(
                user_id=user_id,
                language_id=language_id,
                language_name=language_name
            )
            db.add(db_pref)
            db.commit()
            db.refresh(db_pref)
        
        return db_pref
    
    @staticmethod
    def increment_viewed(db: Session, user_id: int, language_id: str, language_name: str) -> LanguagePreference:
        """Increment view count for a language."""
        db_pref = PreferenceService.get_or_create(db, user_id, language_id, language_name)
        db_pref.times_viewed += 1
        db.commit()
        db.refresh(db_pref)
        return db_pref
    
    @staticmethod
    def increment_considered(db: Session, user_id: int, language_id: str, language_name: str) -> LanguagePreference:
        """Increment considered count for a language."""
        db_pref = PreferenceService.get_or_create(db, user_id, language_id, language_name)
        db_pref.times_considered += 1
        db.commit()
        db.refresh(db_pref)
        return db_pref
    
    @staticmethod
    def increment_selected(
        db: Session,
        user_id: int,
        language_id: str,
        language_name: str,
        project_type: ProjectType,
        paired_languages: List[str],
        stack_id: str
    ) -> LanguagePreference:
        """Increment selection count and update pairing data."""
        db_pref = PreferenceService.get_or_create(db, user_id, language_id, language_name)
        
        db_pref.times_selected += 1
        db_pref.last_used_at = datetime.now(UTC)
        
        # Update project types
        project_types_used_in = list(db_pref.project_types_used_in or [])
        if project_type.value not in project_types_used_in:
            project_types_used_in.append(project_type.value)
        db_pref.project_types_used_in = project_types_used_in
        
        # Update language pairings
        paired_with_languages = dict(db_pref.paired_with_languages or {})
        for lang in paired_languages:
            if lang != language_id:
                paired_with_languages[lang] = paired_with_languages.get(lang, 0) + 1
        db_pref.paired_with_languages = paired_with_languages
        
        # Update stack pairings
        paired_with_stacks = dict(db_pref.paired_with_stacks or {})
        paired_with_stacks[stack_id] = paired_with_stacks.get(stack_id, 0) + 1
        db_pref.paired_with_stacks = paired_with_stacks
        
        db.commit()
        db.refresh(db_pref)
        return db_pref
    
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> List[LanguagePreference]:
        """Get all language preferences for a user."""
        return (
            db.query(LanguagePreference)
            .filter(LanguagePreference.user_id == user_id)
            .order_by(desc(LanguagePreference.times_selected))
            .all()
        )
    
    @staticmethod
    def get_favorites(db: Session, user_id: int, limit: int = 5) -> List[LanguagePreference]:
        """Get user's favorite languages by selection count."""
        return (
            db.query(LanguagePreference)
            .filter(
                and_(
                    LanguagePreference.user_id == user_id,
                    LanguagePreference.times_selected > 0
                )
            )
            .order_by(desc(LanguagePreference.times_selected))
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def update(db: Session, preference_id: int, preference_update: LanguagePreferenceUpdate) -> Optional[LanguagePreference]:
        """Update a language preference record."""
        db_pref = db.query(LanguagePreference).filter(LanguagePreference.id == preference_id).first()
        if not db_pref:
            return None
        
        update_data = preference_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_pref, field, value)
        
        db.commit()
        db.refresh(db_pref)
        return db_pref
    
    @staticmethod
    def get_user_summary(db: Session, user_id: int) -> UserPreferenceSummary:
        """Get comprehensive preference summary for a user."""
        preferences = PreferenceService.get_by_user(db, user_id)
        projects = ProjectService.get_by_user(db, user_id)
        
        favorite_languages = [p.language_id for p in preferences[:5] if p.times_selected > 0]
        
        # Get favorite stacks from projects
        stack_counts: Dict[str, int] = {}
        for project in projects:
            stack_counts[project.selected_stack] = stack_counts.get(project.selected_stack, 0) + 1
        favorite_stacks = sorted(stack_counts.keys(), key=lambda k: stack_counts[k], reverse=True)[:5]
        
        # Get preferred project types
        type_counts: Dict[str, int] = {}
        for project in projects:
            type_counts[project.project_type.value] = type_counts.get(project.project_type.value, 0) + 1
        preferred_types = [ProjectType(t) for t in sorted(type_counts.keys(), key=lambda k: type_counts[k], reverse=True)]
        
        # Calculate success metrics
        total_projects = len(projects)
        if total_projects > 0:
            # Get outcomes for user's projects
            project_ids = [p.id for p in projects]
            outcomes = db.query(StackOutcome).filter(StackOutcome.project_id.in_(project_ids)).all()
            
            if outcomes:
                success_count = sum(1 for o in outcomes if o.outcome_status == OutcomeStatus.success)
                success_rate = success_count / len(outcomes)
                
                satisfactions = [o.user_satisfaction for o in outcomes if o.user_satisfaction is not None]
                avg_satisfaction = sum(satisfactions) / len(satisfactions) if satisfactions else None
            else:
                success_rate = 0.0
                avg_satisfaction = None
        else:
            success_rate = 0.0
            avg_satisfaction = None
        
        return UserPreferenceSummary(
            user_id=user_id,
            favorite_languages=favorite_languages,
            favorite_stacks=favorite_stacks,
            preferred_project_types=preferred_types,
            total_projects=total_projects,
            success_rate=success_rate,
            avg_satisfaction=avg_satisfaction
        )
