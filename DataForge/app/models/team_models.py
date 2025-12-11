from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float, JSON, Enum, Index, Table
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class TeamRole(str, enum.Enum):
    """Team member role enumeration."""
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class InviteStatus(str, enum.Enum):
    """Team invitation status enumeration."""
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


# Association table for team members (many-to-many relationship)
team_members = Table(
    'team_members',
    Base.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('team_id', Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('role', Enum(TeamRole), nullable=False, default=TeamRole.member, index=True),
    Column('joined_at', DateTime(timezone=True), server_default=func.now(), index=True),
    Column('invited_by', Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    Column('is_active', Boolean, default=True, index=True),
    Index('ix_team_members_team_user', 'team_id', 'user_id', unique=True),
)


class Team(Base):
    """
    Represents a team or organization in the Forge ecosystem.
    Teams enable collaborative learning and shared insights across members.
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text, nullable=True)

    # Organization details
    organization_type = Column(String(50), nullable=True)  # startup, enterprise, agency, educational, personal
    team_size = Column(Integer, nullable=True)
    industry = Column(String(100), nullable=True, index=True)

    # Settings
    settings = Column(JSON, nullable=False, default=dict)  # Flexible team configuration
    is_active = Column(Boolean, default=True, index=True)
    is_public = Column(Boolean, default=False, index=True)  # Public teams can share insights

    # Owner
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Statistics (denormalized for performance)
    member_count = Column(Integer, default=0)
    project_count = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship(
        "User",
        secondary=team_members,
        foreign_keys=[team_members.c.team_id, team_members.c.user_id],
        backref="teams"
    )
    learning_aggregates = relationship("TeamLearningAggregate", back_populates="team", cascade="all, delete-orphan")
    invites = relationship("TeamInvite", back_populates="team", cascade="all, delete-orphan")
    projects = relationship("TeamProject", back_populates="team", cascade="all, delete-orphan")


class TeamInvite(Base):
    """
    Tracks team invitation lifecycle.
    Enables email/username-based team invitations.
    """
    __tablename__ = "team_invites"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)

    # Invite details
    invited_email = Column(String(255), nullable=False, index=True)
    invited_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    invited_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    # Role and status
    role = Column(Enum(TeamRole), nullable=False, default=TeamRole.member)
    status = Column(Enum(InviteStatus), nullable=False, default=InviteStatus.pending, index=True)

    # Security
    invite_token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    team = relationship("Team", back_populates="invites")
    inviter = relationship("User", foreign_keys=[invited_by])
    invitee = relationship("User", foreign_keys=[invited_user_id])


class TeamProject(Base):
    """
    Links projects to teams for collaborative learning.
    Tracks which projects belong to which teams.
    """
    __tablename__ = "team_projects"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('vibeforge_projects.id', ondelete='CASCADE'), nullable=False, index=True)

    # Project metadata in team context
    is_team_template = Column(Boolean, default=False, index=True)  # Reusable team template
    visibility = Column(String(20), default='team', index=True)  # team, organization, public

    # Attribution
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    team = relationship("Team", back_populates="projects")
    creator = relationship("User", foreign_keys=[created_by])

    # Composite index for team + project lookups
    __table_args__ = (
        Index('ix_team_projects_team_project', 'team_id', 'project_id', unique=True),
    )


class TeamLearningAggregate(Base):
    """
    Stores aggregated learning insights for teams.
    Periodically computed from individual member activities.
    """
    __tablename__ = "team_learning_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)

    # Aggregation metadata
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    member_count_snapshot = Column(Integer, nullable=False)  # Members at time of computation

    # Language preferences (team-wide)
    top_languages = Column(JSON, nullable=False, default=list)  # [{language, count, success_rate}]
    language_trends = Column(JSON, nullable=False, default=dict)  # {language: trend_direction}

    # Stack preferences (team-wide)
    top_stacks = Column(JSON, nullable=False, default=list)  # [{stack, count, success_rate}]
    stack_combinations = Column(JSON, nullable=False, default=list)  # Popular multi-stack patterns

    # Project patterns
    common_project_types = Column(JSON, nullable=False, default=list)  # [{type, count}]
    avg_project_complexity = Column(Float, nullable=True)
    avg_team_size_preference = Column(Float, nullable=True)

    # Success metrics
    overall_success_rate = Column(Float, nullable=True)  # 0.0 to 1.0
    projects_completed = Column(Integer, default=0)
    projects_abandoned = Column(Integer, default=0)
    avg_satisfaction_score = Column(Float, nullable=True)  # 1.0 to 5.0

    # LLM usage patterns
    total_llm_queries = Column(Integer, default=0)
    avg_tokens_per_session = Column(Float, nullable=True)
    most_used_provider = Column(String(50), nullable=True)
    most_used_model = Column(String(100), nullable=True)

    # Behavioral insights
    avg_session_duration_minutes = Column(Float, nullable=True)
    avg_steps_revisited = Column(Float, nullable=True)
    recommendation_override_rate = Column(Float, nullable=True)  # How often team overrides AI

    # Recommendations for team
    recommended_languages = Column(JSON, nullable=False, default=list)  # AI-suggested languages
    recommended_stacks = Column(JSON, nullable=False, default=list)  # AI-suggested stacks
    improvement_suggestions = Column(JSON, nullable=False, default=list)  # Actionable insights

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    team = relationship("Team", back_populates="learning_aggregates")

    # Composite index for team + time range lookups
    __table_args__ = (
        Index('ix_team_learning_team_period', 'team_id', 'period_start', 'period_end'),
    )


class TeamInsight(Base):
    """
    Stores individual insights and recommendations for teams.
    Generated by NeuroForge reasoning engine.
    """
    __tablename__ = "team_insights"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)

    # Insight metadata
    insight_type = Column(String(50), nullable=False, index=True)  # pattern, recommendation, warning, trend
    category = Column(String(50), nullable=False, index=True)  # language, stack, workflow, performance
    priority = Column(String(20), nullable=False, default='medium', index=True)  # low, medium, high, critical

    # Content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    actionable_steps = Column(JSON, nullable=True)  # List of recommended actions

    # Evidence
    data_sources = Column(JSON, nullable=False, default=list)  # Which projects/sessions support this
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    impact_estimate = Column(String(20), nullable=True)  # low, medium, high

    # Lifecycle
    is_active = Column(Boolean, default=True, index=True)
    is_read = Column(Boolean, default=False, index=True)
    is_acted_upon = Column(Boolean, default=False, index=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    # Attribution
    generated_by = Column(String(50), nullable=True)  # Which model/system generated this

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Composite index for team + active insights
    __table_args__ = (
        Index('ix_team_insights_team_active', 'team_id', 'is_active', 'created_at'),
    )
