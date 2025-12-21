"""
Unit tests for VibeForge learning layer CRUD services.
Tests all service methods with mocked database interactions.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.models.vibeforge_models import (
    VibeForgeProject,
    ProjectSession,
    StackOutcome,
    ModelPerformance,
    LanguagePreference,
    ProjectType,
    OutcomeStatus,
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
)
from app.services.vibeforge_service import (
    ProjectService,
    SessionService,
    OutcomeService,
    PerformanceService,
    PreferenceService,
)


# ============================================================================
# ProjectService Tests
# ============================================================================

def test_project_service_create(db: Session):
    """Test creating a project."""
    project_data = VibeForgeProjectCreate(
        project_name="Test Project",
        project_type=ProjectType.web,
        selected_languages=["python", "typescript"],
        selected_stack="nextjs",
        description="Test description",
        team_size=3,
        complexity_score=6.5
    )
    
    project = ProjectService.create(db, project_data)
    
    assert project.id is not None
    assert project.project_name == "Test Project"
    assert project.project_type == ProjectType.web
    assert len(project.selected_languages) == 2
    assert project.team_size == 3


def test_project_service_get(db: Session):
    """Test getting a project by ID."""
    # Create project first
    project_data = VibeForgeProjectCreate(
        project_name="Get Test",
        project_type=ProjectType.api,
        selected_languages=["python"],
        selected_stack="fastapi"
    )
    created = ProjectService.create(db, project_data)
    
    # Get project
    retrieved = ProjectService.get(db, created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.project_name == "Get Test"


def test_project_service_get_nonexistent(db: Session):
    """Test getting a nonexistent project returns None."""
    result = ProjectService.get(db, 99999)
    assert result is None


def test_project_service_get_by_user(db: Session, test_user):
    """Test getting projects by user."""
    # Create multiple projects for user
    for i in range(3):
        project_data = VibeForgeProjectCreate(
            project_name=f"User Project {i}",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="django",
            user_id=test_user.id
        )
        ProjectService.create(db, project_data)
    
    # Get user projects
    projects = ProjectService.get_by_user(db, test_user.id)
    
    assert len(projects) == 3
    assert all(p.user_id == test_user.id for p in projects)


def test_project_service_get_by_stack(db: Session):
    """Test getting projects by stack."""
    # Create projects with different stacks
    for stack in ["nextjs", "django", "nextjs"]:
        project_data = VibeForgeProjectCreate(
            project_name=f"Project with {stack}",
            project_type=ProjectType.web,
            selected_languages=["typescript" if stack == "nextjs" else "python"],
            selected_stack=stack
        )
        ProjectService.create(db, project_data)
    
    # Get nextjs projects
    projects = ProjectService.get_by_stack(db, "nextjs")
    
    assert len(projects) == 2
    assert all(p.selected_stack == "nextjs" for p in projects)


def test_project_service_get_by_type(db: Session):
    """Test getting projects by type."""
    # Create projects of different types
    for ptype in [ProjectType.web, ProjectType.mobile, ProjectType.web]:
        project_data = VibeForgeProjectCreate(
            project_name=f"Project {ptype}",
            project_type=ptype,
            selected_languages=["python"],
            selected_stack="test"
        )
        ProjectService.create(db, project_data)
    
    # Get web projects
    projects = ProjectService.get_by_type(db, ProjectType.web)
    
    assert len(projects) == 2
    assert all(p.project_type == ProjectType.web for p in projects)


def test_project_service_update(db: Session):
    """Test updating a project."""
    # Create project
    project_data = VibeForgeProjectCreate(
        project_name="Original Name",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="django",
        complexity_score=5.0
    )
    project = ProjectService.create(db, project_data)
    
    # Update project
    update_data = VibeForgeProjectUpdate(
        project_name="Updated Name",
        complexity_score=7.5
    )
    updated = ProjectService.update(db, project.id, update_data)
    
    assert updated is not None
    assert updated.project_name == "Updated Name"
    assert updated.complexity_score == 7.5
    assert updated.selected_stack == "django"  # Unchanged


def test_project_service_delete(db: Session):
    """Test deleting a project."""
    # Create project
    project_data = VibeForgeProjectCreate(
        project_name="To Delete",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="django"
    )
    project = ProjectService.create(db, project_data)
    
    # Delete project
    result = ProjectService.delete(db, project.id)
    assert result is True
    
    # Verify deleted
    retrieved = ProjectService.get(db, project.id)
    assert retrieved is None


def test_project_service_delete_nonexistent(db: Session):
    """Test deleting a nonexistent project returns False."""
    result = ProjectService.delete(db, 99999)
    assert result is False


# ============================================================================
# SessionService Tests
# ============================================================================

def test_session_service_create(db: Session):
    """Test creating a session."""
    # Create project first
    project_data = VibeForgeProjectCreate(
        project_name="Session Test",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="django"
    )
    project = ProjectService.create(db, project_data)
    
    # Create session
    session_data = ProjectSessionCreate(
        project_id=project.id,
        steps_completed=[1, 2, 3],
        languages_viewed=["python", "typescript"],
        stack_final="django",
        llm_queries=2
    )
    session = SessionService.create(db, session_data)
    
    assert session.id is not None
    assert session.project_id == project.id
    assert len(session.steps_completed) == 3
    assert session.llm_queries == 2


def test_session_service_get_by_project(db: Session):
    """Test getting all sessions for a project."""
    # Create project
    project_data = VibeForgeProjectCreate(
        project_name="Multi Session",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="django"
    )
    project = ProjectService.create(db, project_data)
    
    # Create multiple sessions
    for i in range(3):
        session_data = ProjectSessionCreate(
            project_id=project.id,
            llm_queries=i
        )
        SessionService.create(db, session_data)
    
    # Get sessions
    sessions = SessionService.get_by_project(db, project.id)
    
    assert len(sessions) == 3
    assert all(s.project_id == project.id for s in sessions)


def test_session_service_mark_completed(db: Session):
    """Test marking a session as completed."""
    # Create project and session
    project_data = VibeForgeProjectCreate(
        project_name="Complete Test",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="django"
    )
    project = ProjectService.create(db, project_data)
    
    session_data = ProjectSessionCreate(project_id=project.id)
    session = SessionService.create(db, session_data)
    
    # Mark completed
    completed = SessionService.mark_completed(db, session.id)
    
    assert completed is not None
    assert completed.session_completed_at is not None
    assert completed.session_duration_seconds is not None
    assert completed.session_duration_seconds >= 0


def test_session_service_mark_abandoned(db: Session):
    """Test marking a session as abandoned."""
    # Create project and session
    project_data = VibeForgeProjectCreate(
        project_name="Abandon Test",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="django"
    )
    project = ProjectService.create(db, project_data)
    
    session_data = ProjectSessionCreate(project_id=project.id)
    session = SessionService.create(db, session_data)
    
    # Mark abandoned
    abandoned = SessionService.mark_abandoned(db, session.id)
    
    assert abandoned is not None
    assert abandoned.abandoned is True


# ============================================================================
# OutcomeService Tests
# ============================================================================

def test_outcome_service_create(db: Session):
    """Test creating an outcome."""
    # Create project
    project_data = VibeForgeProjectCreate(
        project_name="Outcome Test",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="django"
    )
    project = ProjectService.create(db, project_data)
    
    # Create outcome
    outcome_data = StackOutcomeCreate(
        project_id=project.id,
        stack_id="django",
        project_type=ProjectType.web,
        languages_used=["python"],
        outcome_status=OutcomeStatus.success,
        build_successful=True,
        user_satisfaction=5
    )
    outcome = OutcomeService.create(db, outcome_data)
    
    assert outcome.id is not None
    assert outcome.project_id == project.id
    assert outcome.outcome_status == OutcomeStatus.success
    assert outcome.build_successful


def test_outcome_service_get_by_stack(db: Session):
    """Test getting outcomes by stack."""
    # Create projects with outcomes
    for i in range(3):
        project_data = VibeForgeProjectCreate(
            project_name=f"Project {i}",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="django"
        )
        project = ProjectService.create(db, project_data)
        
        outcome_data = StackOutcomeCreate(
            project_id=project.id,
            stack_id="django",
            project_type=ProjectType.web,
            languages_used=["python"],
            outcome_status=OutcomeStatus.success if i < 2 else OutcomeStatus.failure
        )
        OutcomeService.create(db, outcome_data)
    
    # Get outcomes for django
    outcomes = OutcomeService.get_by_stack(db, "django")
    
    assert len(outcomes) == 3


def test_outcome_service_get_stack_success_rate(db: Session):
    """Test calculating stack success rate."""
    # Create multiple outcomes for same stack
    for i, status in enumerate([
        OutcomeStatus.success,
        OutcomeStatus.success,
        OutcomeStatus.failure,
        OutcomeStatus.partial,
    ]):
        project_data = VibeForgeProjectCreate(
            project_name=f"SR Project {i}",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="django"
        )
        project = ProjectService.create(db, project_data)
        
        outcome_data = StackOutcomeCreate(
            project_id=project.id,
            stack_id="django",
            project_type=ProjectType.web,
            languages_used=["python"],
            outcome_status=status,
            user_satisfaction=4,
            build_time_seconds=100
        )
        OutcomeService.create(db, outcome_data)
    
    # Get success rate
    stats = OutcomeService.get_stack_success_rate(db, "django")
    
    assert stats is not None
    assert stats.stack_id == "django"
    assert stats.total_uses == 4
    assert stats.success_count == 2
    assert stats.failure_count == 1
    assert stats.partial_count == 1
    assert stats.success_rate == 0.5  # 2 out of 4
    assert stats.avg_satisfaction == 4.0
    assert stats.avg_build_time_seconds == 100


def test_outcome_service_get_stack_success_rate_nonexistent(db: Session):
    """Test getting success rate for nonexistent stack returns None."""
    stats = OutcomeService.get_stack_success_rate(db, "nonexistent")
    assert stats is None


# ============================================================================
# PerformanceService Tests
# ============================================================================

def test_performance_service_create(db: Session):
    """Test creating a performance record."""
    perf_data = ModelPerformanceCreate(
        provider="openai",
        model_name="gpt-4",
        prompt_type="stack_recommendation",
        response_time_ms=1200,
        tokens_total=500,
        recommendation_accepted=True
    )
    perf = PerformanceService.create(db, perf_data)
    
    assert perf.id is not None
    assert perf.provider == "openai"
    assert perf.recommendation_accepted


def test_performance_service_get_acceptance_rate(db: Session):
    """Test calculating model acceptance rate."""
    # Create multiple performance records
    for accepted in [True, True, False, True, False]:
        perf_data = ModelPerformanceCreate(
            provider="openai",
            model_name="gpt-4",
            prompt_type="test",
            recommendation_accepted=accepted
        )
        PerformanceService.create(db, perf_data)
    
    # Get acceptance rate
    rate = PerformanceService.get_acceptance_rate(db, "openai", "gpt-4")
    
    assert rate == 0.6  # 3 out of 5


def test_performance_service_get_acceptance_rate_no_data(db: Session):
    """Test getting acceptance rate with no data returns 0."""
    rate = PerformanceService.get_acceptance_rate(db, "nonexistent", "model")
    assert rate == 0.0


# ============================================================================
# PreferenceService Tests
# ============================================================================

def test_preference_service_get_or_create(db: Session, test_user):
    """Test getting or creating a preference."""
    # First call creates
    pref1 = PreferenceService.get_or_create(
        db, test_user.id, "python", "Python"
    )
    
    assert pref1.id is not None
    assert pref1.language_id == "python"
    assert pref1.times_selected == 0
    
    # Second call retrieves existing
    pref2 = PreferenceService.get_or_create(
        db, test_user.id, "python", "Python"
    )
    
    assert pref2.id == pref1.id


def test_preference_service_increment_viewed(db: Session, test_user):
    """Test incrementing view count."""
    # Increment views
    pref = PreferenceService.increment_viewed(
        db, test_user.id, "typescript", "TypeScript"
    )
    assert pref.times_viewed == 1
    
    # Increment again
    pref = PreferenceService.increment_viewed(
        db, test_user.id, "typescript", "TypeScript"
    )
    assert pref.times_viewed == 2


def test_preference_service_increment_selected(db: Session, test_user):
    """Test incrementing selection count with pairing data."""
    # Select language
    pref = PreferenceService.increment_selected(
        db,
        test_user.id,
        "python",
        "Python",
        ProjectType.web,
        ["python", "typescript"],
        "django"
    )
    
    # Refresh to get latest data
    db.refresh(pref)
    
    assert pref.times_selected == 1
    assert "web" in pref.project_types_used_in
    assert pref.paired_with_languages.get("typescript") == 1
    assert pref.paired_with_stacks.get("django") == 1
    assert pref.last_used_at is not None


def test_preference_service_get_favorites(db: Session, test_user):
    """Test getting favorite languages."""
    # Create preferences with different selection counts
    languages = [
        ("python", "Python", 10),
        ("typescript", "TypeScript", 5),
        ("go", "Go", 2),
        ("rust", "Rust", 15),
    ]
    
    for lang_id, lang_name, count in languages:
        pref = PreferenceService.get_or_create(db, test_user.id, lang_id, lang_name)
        pref.times_selected = count
        db.commit()
    
    # Get top 3 favorites
    favorites = PreferenceService.get_favorites(db, test_user.id, limit=3)
    
    assert len(favorites) == 3
    assert favorites[0].language_id == "rust"  # Most selected
    assert favorites[1].language_id == "python"
    assert favorites[2].language_id == "typescript"


def test_preference_service_get_user_summary(db: Session, test_user):
    """Test getting comprehensive user summary."""
    # Create some projects and preferences
    for i in range(3):
        project_data = VibeForgeProjectCreate(
            project_name=f"Summary Project {i}",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="django",
            user_id=test_user.id
        )
        project = ProjectService.create(db, project_data)
        
        # Add outcome
        outcome_data = StackOutcomeCreate(
            project_id=project.id,
            stack_id="django",
            project_type=ProjectType.web,
            languages_used=["python"],
            outcome_status=OutcomeStatus.success if i < 2 else OutcomeStatus.failure,
            user_satisfaction=5 if i < 2 else 2
        )
        OutcomeService.create(db, outcome_data)
    
    # Create preferences
    pref = PreferenceService.get_or_create(db, test_user.id, "python", "Python")
    pref.times_selected = 10
    db.commit()
    
    # Get summary
    summary = PreferenceService.get_user_summary(db, test_user.id)
    
    assert summary.user_id == test_user.id
    assert summary.total_projects == 3
    assert "python" in summary.favorite_languages
    assert "django" in summary.favorite_stacks
    assert ProjectType.web in summary.preferred_project_types
    assert 0 <= summary.success_rate <= 1
