from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float, JSON, Enum, Index
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ProjectType(str, enum.Enum):
    """Project type enumeration."""
    web = "web"
    mobile = "mobile"
    desktop = "desktop"
    api = "api"
    ai_ml = "ai_ml"
    other = "other"


class OutcomeStatus(str, enum.Enum):
    """Outcome status enumeration."""
    success = "success"
    partial = "partial"
    failure = "failure"
    unknown = "unknown"


class VibeForgeProject(Base):
    """
    Tracks projects created through VibeForge wizard.
    Stores core metadata about each project for learning purposes.
    """
    __tablename__ = "vibeforge_projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(255), nullable=False, index=True)
    project_type = Column(Enum(ProjectType), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Selected configurations
    selected_languages = Column(JSON, nullable=False)  # List of language IDs
    selected_stack = Column(String(100), nullable=False, index=True)  # Stack profile ID
    
    # Context from wizard
    intent_description = Column(Text, nullable=True)
    team_size = Column(Integer, nullable=True)
    timeline_estimate = Column(String(50), nullable=True)
    complexity_score = Column(Float, nullable=True)
    
    # User context
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    sessions = relationship("ProjectSession", back_populates="project", cascade="all, delete-orphan")
    outcomes = relationship("StackOutcome", back_populates="project", cascade="all, delete-orphan")


class ProjectSession(Base):
    """
    Tracks individual wizard sessions, including steps taken and choices made.
    Captures the user's journey through the wizard for behavior analysis.
    """
    __tablename__ = "project_sessions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('vibeforge_projects.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Session metadata
    session_started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    session_completed_at = Column(DateTime(timezone=True), nullable=True)
    session_duration_seconds = Column(Integer, nullable=True)
    
    # Step interaction tracking
    steps_completed = Column(JSON, nullable=False, default=list)  # List of step numbers
    steps_revisited = Column(JSON, nullable=False, default=list)  # Steps user went back to
    
    # Language selection journey
    languages_viewed = Column(JSON, nullable=False, default=list)  # All languages user viewed
    languages_considered = Column(JSON, nullable=False, default=list)  # Languages user clicked/explored
    languages_final = Column(JSON, nullable=False, default=list)  # Final language selection
    
    # Stack selection journey
    stacks_viewed = Column(JSON, nullable=False, default=list)  # All stacks viewed
    stacks_compared = Column(JSON, nullable=False, default=list)  # Stacks compared
    stack_recommended = Column(String(100), nullable=True)  # AI-recommended stack
    stack_final = Column(String(100), nullable=True)  # User's final choice
    stack_override = Column(Boolean, default=False)  # Did user override recommendation?
    
    # LLM interaction tracking
    llm_queries = Column(Integer, default=0)  # Number of times LLM was consulted
    llm_provider_used = Column(String(50), nullable=True)  # Which provider was used
    llm_tokens_consumed = Column(Integer, default=0)  # Token usage
    
    # User experience indicators
    abandoned = Column(Boolean, default=False)  # Session abandoned before completion
    feedback_rating = Column(Integer, nullable=True)  # 1-5 stars if collected
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("VibeForgeProject", back_populates="sessions")
    model_performance = relationship("ModelPerformance", back_populates="session", cascade="all, delete-orphan")


class StackOutcome(Base):
    """
    Records the success/failure outcomes for projects using specific stacks.
    Enables learning which stacks work well for which project types.
    """
    __tablename__ = "stack_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('vibeforge_projects.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Stack information
    stack_id = Column(String(100), nullable=False, index=True)
    project_type = Column(Enum(ProjectType), nullable=False, index=True)
    languages_used = Column(JSON, nullable=False)  # Language combination
    
    # Outcome tracking
    outcome_status = Column(Enum(OutcomeStatus), nullable=False, index=True)
    build_successful = Column(Boolean, nullable=True)
    tests_passed = Column(Boolean, nullable=True)
    deployed_successfully = Column(Boolean, nullable=True)
    
    # Performance metrics
    build_time_seconds = Column(Integer, nullable=True)
    test_pass_rate = Column(Float, nullable=True)  # 0.0 to 1.0
    deployment_time_seconds = Column(Integer, nullable=True)
    
    # User satisfaction
    user_satisfaction = Column(Integer, nullable=True)  # 1-5 rating
    would_recommend = Column(Boolean, nullable=True)
    
    # Issues encountered
    issues_count = Column(Integer, default=0)
    issue_types = Column(JSON, nullable=True)  # List of issue categories
    fix_iterations = Column(Integer, default=0)  # How many times user had to fix
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("VibeForgeProject", back_populates="outcomes")


class ModelPerformance(Base):
    """
    Tracks LLM model performance for recommendations and prompts.
    Enables A/B testing and model effectiveness analysis.
    """
    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('project_sessions.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Model information
    provider = Column(String(50), nullable=False, index=True)  # openai, anthropic, etc.
    model_name = Column(String(100), nullable=False, index=True)  # gpt-4, claude-3, etc.
    prompt_type = Column(String(50), nullable=False)  # stack_recommendation, language_advice, etc.
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    tokens_prompt = Column(Integer, nullable=True)
    tokens_completion = Column(Integer, nullable=True)
    tokens_total = Column(Integer, nullable=True)
    
    # Quality metrics
    recommendation_accepted = Column(Boolean, nullable=True)  # Did user accept AI suggestion?
    recommendation_helpful = Column(Boolean, nullable=True)  # User feedback
    recommendation_confidence = Column(Float, nullable=True)  # Model's confidence score
    
    # A/B testing
    experiment_id = Column(String(100), nullable=True, index=True)  # For A/B test tracking
    variant = Column(String(50), nullable=True)  # test variant identifier
    
    # Context
    context_data = Column(JSON, nullable=True)  # Prompt context for analysis
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    session = relationship("ProjectSession", back_populates="model_performance")


class LanguagePreference(Base):
    """
    Tracks user language preferences over time.
    Auto-populated from project selections to personalize recommendations.
    """
    __tablename__ = "language_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Language information
    language_id = Column(String(50), nullable=False, index=True)
    language_name = Column(String(100), nullable=False)
    
    # Usage statistics
    times_selected = Column(Integer, default=0)
    times_viewed = Column(Integer, default=0)
    times_considered = Column(Integer, default=0)  # Clicked but not selected
    
    # Success metrics
    successful_projects = Column(Integer, default=0)
    failed_projects = Column(Integer, default=0)
    avg_satisfaction = Column(Float, nullable=True)  # Average 1-5 rating
    
    # Contextual usage
    project_types_used_in = Column(JSON, nullable=False, default=list)  # List of project types
    paired_with_languages = Column(JSON, nullable=False, default=dict)  # {lang_id: count}
    paired_with_stacks = Column(JSON, nullable=False, default=dict)  # {stack_id: count}
    
    # Recency
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    first_used_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Composite index for user + language lookups
    __table_args__ = (
        Index('ix_language_preferences_user_language', 'user_id', 'language_id'),
    )
