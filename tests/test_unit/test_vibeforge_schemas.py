"""
Unit tests for VibeForge learning layer Pydantic schemas and models.
Tests validation rules, constraints, and data integrity.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.vibeforge_schemas import (
    ProjectType,
    OutcomeStatus,
    VibeForgeProjectCreate,
    VibeForgeProjectUpdate,
    VibeForgeProjectResponse,
    ProjectSessionCreate,
    ProjectSessionUpdate,
    ProjectSessionResponse,
    StackOutcomeCreate,
    StackOutcomeUpdate,
    StackOutcomeResponse,
    ModelPerformanceCreate,
    ModelPerformanceUpdate,
    ModelPerformanceResponse,
    LanguagePreferenceUpdate,
    LanguagePreferenceResponse,
    StackSuccessRate,
    LanguageTrend,
    UserPreferenceSummary,
)


# ============================================================================
# ProjectType and OutcomeStatus Enum Tests
# ============================================================================

def test_project_type_enum():
    """Test ProjectType enum values."""
    assert ProjectType.web == "web"
    assert ProjectType.mobile == "mobile"
    assert ProjectType.desktop == "desktop"
    assert ProjectType.api == "api"
    assert ProjectType.ai_ml == "ai_ml"
    assert ProjectType.other == "other"


def test_outcome_status_enum():
    """Test OutcomeStatus enum values."""
    assert OutcomeStatus.success == "success"
    assert OutcomeStatus.partial == "partial"
    assert OutcomeStatus.failure == "failure"
    assert OutcomeStatus.unknown == "unknown"


# ============================================================================
# VibeForgeProject Schema Tests
# ============================================================================

def test_vibeforge_project_create_valid():
    """Test creating a valid project."""
    project = VibeForgeProjectCreate(
        project_name="Test Project",
        project_type=ProjectType.web,
        description="A test project",
        selected_languages=["python", "typescript"],
        selected_stack="nextjs",
        team_size=5,
        timeline_estimate="2 months",
        complexity_score=7.5
    )
    
    assert project.project_name == "Test Project"
    assert project.project_type == ProjectType.web
    assert len(project.selected_languages) == 2
    assert project.team_size == 5
    assert project.complexity_score == 7.5


def test_vibeforge_project_create_minimal():
    """Test creating a project with minimal required fields."""
    project = VibeForgeProjectCreate(
        project_name="Minimal Project",
        project_type=ProjectType.api,
        selected_languages=["python"],
        selected_stack="fastapi"
    )
    
    assert project.project_name == "Minimal Project"
    assert project.description is None
    assert project.team_size is None


def test_vibeforge_project_create_empty_name_fails():
    """Test that empty project name fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        VibeForgeProjectCreate(
            project_name="",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="fastapi"
        )
    
    assert "project_name" in str(exc_info.value)


def test_vibeforge_project_create_empty_languages_fails():
    """Test that empty languages list fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        VibeForgeProjectCreate(
            project_name="Test",
            project_type=ProjectType.web,
            selected_languages=[],
            selected_stack="fastapi"
        )
    
    assert "selected_languages" in str(exc_info.value)


def test_vibeforge_project_team_size_constraints():
    """Test team size validation constraints."""
    # Valid team size
    project = VibeForgeProjectCreate(
        project_name="Test",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="fastapi",
        team_size=5
    )
    assert project.team_size == 5
    
    # Invalid: too small
    with pytest.raises(ValidationError):
        VibeForgeProjectCreate(
            project_name="Test",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="fastapi",
            team_size=0
        )
    
    # Invalid: too large
    with pytest.raises(ValidationError):
        VibeForgeProjectCreate(
            project_name="Test",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="fastapi",
            team_size=1001
        )


def test_vibeforge_project_complexity_constraints():
    """Test complexity score validation constraints."""
    # Valid complexity
    project = VibeForgeProjectCreate(
        project_name="Test",
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="fastapi",
        complexity_score=5.5
    )
    assert project.complexity_score == 5.5
    
    # Invalid: too low
    with pytest.raises(ValidationError):
        VibeForgeProjectCreate(
            project_name="Test",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="fastapi",
            complexity_score=-1.0
        )
    
    # Invalid: too high
    with pytest.raises(ValidationError):
        VibeForgeProjectCreate(
            project_name="Test",
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="fastapi",
            complexity_score=11.0
        )


# ============================================================================
# ProjectSession Schema Tests
# ============================================================================

def test_project_session_create_valid():
    """Test creating a valid session."""
    session = ProjectSessionCreate(
        project_id=1,
        steps_completed=[1, 2, 3],
        languages_viewed=["python", "typescript", "go"],
        languages_final=["python", "typescript"],
        stacks_viewed=["nextjs", "django"],
        stack_final="nextjs",
        llm_queries=5,
        llm_provider_used="openai",
        llm_tokens_consumed=2000
    )
    
    assert session.project_id == 1
    assert len(session.steps_completed) == 3
    assert session.llm_queries == 5
    assert not session.abandoned


def test_project_session_feedback_rating_constraints():
    """Test feedback rating validation."""
    # Valid rating
    session = ProjectSessionCreate(
        project_id=1,
        feedback_rating=4
    )
    assert session.feedback_rating == 4
    
    # Invalid: too low
    with pytest.raises(ValidationError):
        ProjectSessionCreate(
            project_id=1,
            feedback_rating=0
        )
    
    # Invalid: too high
    with pytest.raises(ValidationError):
        ProjectSessionCreate(
            project_id=1,
            feedback_rating=6
        )


def test_project_session_default_values():
    """Test session default values."""
    session = ProjectSessionCreate(project_id=1)
    
    assert session.steps_completed == []
    assert session.steps_revisited == []
    assert session.languages_viewed == []
    assert session.llm_queries == 0
    assert session.llm_tokens_consumed == 0
    assert not session.abandoned
    assert not session.stack_override


# ============================================================================
# StackOutcome Schema Tests
# ============================================================================

def test_stack_outcome_create_valid():
    """Test creating a valid outcome."""
    outcome = StackOutcomeCreate(
        project_id=1,
        stack_id="nextjs",
        project_type=ProjectType.web,
        languages_used=["typescript", "python"],
        outcome_status=OutcomeStatus.success,
        build_successful=True,
        tests_passed=True,
        deployed_successfully=True,
        build_time_seconds=120,
        test_pass_rate=0.95,
        user_satisfaction=5,
        would_recommend=True
    )
    
    assert outcome.stack_id == "nextjs"
    assert outcome.outcome_status == OutcomeStatus.success
    assert outcome.build_successful
    assert outcome.test_pass_rate == 0.95


def test_stack_outcome_test_pass_rate_constraints():
    """Test test pass rate validation."""
    # Valid rate
    outcome = StackOutcomeCreate(
        project_id=1,
        stack_id="test",
        project_type=ProjectType.web,
        languages_used=["python"],
        outcome_status=OutcomeStatus.success,
        test_pass_rate=0.85
    )
    assert outcome.test_pass_rate == 0.85
    
    # Invalid: negative
    with pytest.raises(ValidationError):
        StackOutcomeCreate(
            project_id=1,
            stack_id="test",
            project_type=ProjectType.web,
            languages_used=["python"],
            outcome_status=OutcomeStatus.success,
            test_pass_rate=-0.1
        )
    
    # Invalid: > 1.0
    with pytest.raises(ValidationError):
        StackOutcomeCreate(
            project_id=1,
            stack_id="test",
            project_type=ProjectType.web,
            languages_used=["python"],
            outcome_status=OutcomeStatus.success,
            test_pass_rate=1.1
        )


def test_stack_outcome_satisfaction_constraints():
    """Test user satisfaction validation."""
    # Valid satisfaction
    outcome = StackOutcomeCreate(
        project_id=1,
        stack_id="test",
        project_type=ProjectType.web,
        languages_used=["python"],
        outcome_status=OutcomeStatus.success,
        user_satisfaction=4
    )
    assert outcome.user_satisfaction == 4
    
    # Invalid: too low
    with pytest.raises(ValidationError):
        StackOutcomeCreate(
            project_id=1,
            stack_id="test",
            project_type=ProjectType.web,
            languages_used=["python"],
            outcome_status=OutcomeStatus.success,
            user_satisfaction=0
        )


def test_stack_outcome_default_values():
    """Test outcome default values."""
    outcome = StackOutcomeCreate(
        project_id=1,
        stack_id="test",
        project_type=ProjectType.web,
        languages_used=["python"],
        outcome_status=OutcomeStatus.success
    )
    
    assert outcome.issues_count == 0
    assert outcome.fix_iterations == 0


# ============================================================================
# ModelPerformance Schema Tests
# ============================================================================

def test_model_performance_create_valid():
    """Test creating a valid performance record."""
    perf = ModelPerformanceCreate(
        provider="openai",
        model_name="gpt-4",
        prompt_type="stack_recommendation",
        response_time_ms=1500,
        tokens_prompt=500,
        tokens_completion=300,
        tokens_total=800,
        recommendation_accepted=True,
        recommendation_confidence=0.92
    )
    
    assert perf.provider == "openai"
    assert perf.model_name == "gpt-4"
    assert perf.tokens_total == 800
    assert perf.recommendation_accepted


def test_model_performance_confidence_constraints():
    """Test recommendation confidence validation."""
    # Valid confidence
    perf = ModelPerformanceCreate(
        provider="anthropic",
        model_name="claude-3",
        prompt_type="language_advice",
        recommendation_confidence=0.85
    )
    assert perf.recommendation_confidence == 0.85
    
    # Invalid: negative
    with pytest.raises(ValidationError):
        ModelPerformanceCreate(
            provider="anthropic",
            model_name="claude-3",
            prompt_type="language_advice",
            recommendation_confidence=-0.1
        )
    
    # Invalid: > 1.0
    with pytest.raises(ValidationError):
        ModelPerformanceCreate(
            provider="anthropic",
            model_name="claude-3",
            prompt_type="language_advice",
            recommendation_confidence=1.5
        )


def test_model_performance_token_constraints():
    """Test token count validation."""
    # Valid tokens
    perf = ModelPerformanceCreate(
        provider="openai",
        model_name="gpt-4",
        prompt_type="test",
        tokens_prompt=100,
        tokens_completion=50,
        tokens_total=150
    )
    assert perf.tokens_total == 150
    
    # Invalid: negative tokens
    with pytest.raises(ValidationError):
        ModelPerformanceCreate(
            provider="openai",
            model_name="gpt-4",
            prompt_type="test",
            tokens_prompt=-10
        )


# ============================================================================
# Analytics Schema Tests
# ============================================================================

def test_stack_success_rate_valid():
    """Test StackSuccessRate schema."""
    stats = StackSuccessRate(
        stack_id="nextjs",
        project_type=ProjectType.web,
        total_uses=100,
        success_count=85,
        partial_count=10,
        failure_count=5,
        success_rate=0.85,
        avg_satisfaction=4.2,
        avg_build_time_seconds=150,
        avg_test_pass_rate=0.92
    )
    
    assert stats.success_rate == 0.85
    assert stats.total_uses == 100
    assert stats.avg_satisfaction == 4.2


def test_language_trend_valid():
    """Test LanguageTrend schema."""
    trend = LanguageTrend(
        language_id="python",
        language_name="Python",
        total_selections=250,
        total_projects=180,
        success_rate=0.88,
        avg_satisfaction=4.5,
        most_paired_with=["typescript", "javascript"],
        popular_stacks=["django", "fastapi"]
    )
    
    assert trend.language_id == "python"
    assert trend.total_selections == 250
    assert len(trend.most_paired_with) == 2


def test_user_preference_summary_valid():
    """Test UserPreferenceSummary schema."""
    summary = UserPreferenceSummary(
        user_id=1,
        favorite_languages=["python", "typescript"],
        favorite_stacks=["nextjs", "django"],
        preferred_project_types=[ProjectType.web, ProjectType.ai_ml],
        total_projects=25,
        success_rate=0.92,
        avg_satisfaction=4.6
    )
    
    assert summary.user_id == 1
    assert len(summary.favorite_languages) == 2
    assert summary.success_rate == 0.92


def test_user_preference_summary_defaults():
    """Test UserPreferenceSummary default values."""
    summary = UserPreferenceSummary(user_id=1)
    
    assert summary.favorite_languages == []
    assert summary.favorite_stacks == []
    assert summary.preferred_project_types == []
    assert summary.total_projects == 0
    assert summary.success_rate == 0.0
    assert summary.avg_satisfaction is None


# ============================================================================
# Update Schema Tests
# ============================================================================

def test_project_update_partial():
    """Test partial project update."""
    update = VibeForgeProjectUpdate(
        project_name="Updated Name"
    )
    
    assert update.project_name == "Updated Name"
    assert update.description is None
    assert update.complexity_score is None


def test_session_update_partial():
    """Test partial session update."""
    update = ProjectSessionUpdate(
        abandoned=True,
        feedback_rating=3
    )
    
    assert update.abandoned
    assert update.feedback_rating == 3
    assert update.llm_queries is None


def test_outcome_update_partial():
    """Test partial outcome update."""
    update = StackOutcomeUpdate(
        outcome_status=OutcomeStatus.failure,
        issues_count=5
    )
    
    assert update.outcome_status == OutcomeStatus.failure
    assert update.issues_count == 5
    assert update.build_successful is None


def test_performance_update_partial():
    """Test partial performance update."""
    update = ModelPerformanceUpdate(
        recommendation_accepted=False,
        recommendation_helpful=False
    )
    
    assert not update.recommendation_accepted
    assert not update.recommendation_helpful


# ============================================================================
# Field Constraint Edge Cases
# ============================================================================

def test_string_length_constraints():
    """Test string length validation."""
    # Valid lengths
    project = VibeForgeProjectCreate(
        project_name="A" * 255,  # Max length
        project_type=ProjectType.web,
        selected_languages=["python"],
        selected_stack="a" * 100  # Max length
    )
    assert len(project.project_name) == 255
    assert len(project.selected_stack) == 100
    
    # Invalid: too long
    with pytest.raises(ValidationError):
        VibeForgeProjectCreate(
            project_name="A" * 256,
            project_type=ProjectType.web,
            selected_languages=["python"],
            selected_stack="test"
        )


def test_list_constraints():
    """Test list validation."""
    # Empty list should fail for required min_items
    with pytest.raises(ValidationError):
        StackOutcomeCreate(
            project_id=1,
            stack_id="test",
            project_type=ProjectType.web,
            languages_used=[],  # min_length=1
            outcome_status=OutcomeStatus.success
        )
    
    # Valid list
    outcome = StackOutcomeCreate(
        project_id=1,
        stack_id="test",
        project_type=ProjectType.web,
        languages_used=["python", "typescript", "go"],
        outcome_status=OutcomeStatus.success
    )
    assert len(outcome.languages_used) == 3
