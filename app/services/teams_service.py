"""
CRUD services for Team & Organization Learning (Phase 4.1).
Handles database operations for teams, members, invites, projects, and insights.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta, UTC
import secrets
import string

from app.models.team_models import (
    Team,
    TeamInvite,
    TeamProject,
    TeamLearningAggregate,
    TeamInsight,
    TeamRole,
    InviteStatus,
    team_members
)
from app.models.team_schemas import (
    TeamCreate,
    TeamUpdate,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamInviteCreate,
    TeamInviteUpdate,
    TeamProjectCreate,
    TeamProjectUpdate,
    TeamInsightCreate,
    TeamInsightUpdate,
    TeamLearningAggregateCreate
)


# ============================================================================
# Team Service
# ============================================================================

class TeamService:
    """Service for Team CRUD operations."""

    @staticmethod
    def create(db: Session, team: TeamCreate) -> Team:
        """Create a new team."""
        db_team = Team(**team.model_dump())
        db.add(db_team)
        db.commit()
        db.refresh(db_team)

        # Add owner as team member with owner role
        TeamMemberService.add_member(
            db,
            team_id=db_team.id,
            user_id=db_team.owner_id,
            role=TeamRole.owner,
            invited_by=None
        )

        return db_team

    @staticmethod
    def get(db: Session, team_id: int) -> Optional[Team]:
        """Get a team by ID."""
        return db.query(Team).filter(Team.id == team_id).first()

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Team]:
        """Get a team by slug."""
        return db.query(Team).filter(Team.slug == slug).first()

    @staticmethod
    def get_user_teams(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Team]:
        """Get all teams a user belongs to."""
        return (
            db.query(Team)
            .join(team_members)
            .filter(
                team_members.c.user_id == user_id,
                team_members.c.is_active == True
            )
            .order_by(desc(Team.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_owned_teams(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Team]:
        """Get all teams owned by a user."""
        return (
            db.query(Team)
            .filter(Team.owner_id == user_id)
            .order_by(desc(Team.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_public_teams(db: Session, skip: int = 0, limit: int = 100) -> List[Team]:
        """Get all public teams."""
        return (
            db.query(Team)
            .filter(Team.is_public == True, Team.is_active == True)
            .order_by(desc(Team.member_count))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(db: Session, team_id: int, updates: TeamUpdate) -> Optional[Team]:
        """Update a team."""
        db_team = TeamService.get(db, team_id)
        if not db_team:
            return None

        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_team, key, value)

        db_team.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(db_team)
        return db_team

    @staticmethod
    def delete(db: Session, team_id: int) -> bool:
        """Delete a team (soft delete by setting is_active=False)."""
        db_team = TeamService.get(db, team_id)
        if not db_team:
            return False

        db_team.is_active = False
        db.commit()
        return True

    @staticmethod
    def check_membership(db: Session, team_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Check if user is a member of team and return role."""
        result = (
            db.query(team_members)
            .filter(
                team_members.c.team_id == team_id,
                team_members.c.user_id == user_id,
                team_members.c.is_active == True
            )
            .first()
        )
        if result:
            return {"role": result.role, "joined_at": result.joined_at}
        return None

    @staticmethod
    def is_admin(db: Session, team_id: int, user_id: int) -> bool:
        """Check if user is admin or owner of team."""
        membership = TeamService.check_membership(db, team_id, user_id)
        if not membership:
            return False
        return membership["role"] in [TeamRole.owner, TeamRole.admin]


# ============================================================================
# Team Member Service
# ============================================================================

class TeamMemberService:
    """Service for Team Member operations."""

    @staticmethod
    def add_member(
        db: Session,
        team_id: int,
        user_id: int,
        role: TeamRole = TeamRole.member,
        invited_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a member to a team."""
        # Check if already a member
        existing = (
            db.query(team_members)
            .filter(
                team_members.c.team_id == team_id,
                team_members.c.user_id == user_id
            )
            .first()
        )

        if existing:
            # Reactivate if inactive
            if not existing.is_active:
                db.execute(
                    team_members.update()
                    .where(
                        and_(
                            team_members.c.team_id == team_id,
                            team_members.c.user_id == user_id
                        )
                    )
                    .values(is_active=True, role=role)
                )
                db.commit()
                return {"status": "reactivated", "role": role}
            return {"status": "already_member", "role": existing.role}

        # Add new member
        db.execute(
            team_members.insert().values(
                team_id=team_id,
                user_id=user_id,
                role=role,
                invited_by=invited_by,
                is_active=True
            )
        )

        # Update team member count
        db.execute(
            Team.__table__.update()
            .where(Team.id == team_id)
            .values(member_count=Team.member_count + 1)
        )

        db.commit()
        return {"status": "added", "role": role}

    @staticmethod
    def get_members(db: Session, team_id: int) -> List[Dict[str, Any]]:
        """Get all active members of a team."""
        results = (
            db.query(team_members)
            .filter(
                team_members.c.team_id == team_id,
                team_members.c.is_active == True
            )
            .order_by(team_members.c.joined_at)
            .all()
        )
        return [
            {
                "id": r.id,
                "team_id": r.team_id,
                "user_id": r.user_id,
                "role": r.role,
                "joined_at": r.joined_at,
                "invited_by": r.invited_by
            }
            for r in results
        ]

    @staticmethod
    def update_role(db: Session, team_id: int, user_id: int, role: TeamRole) -> bool:
        """Update a member's role."""
        result = db.execute(
            team_members.update()
            .where(
                and_(
                    team_members.c.team_id == team_id,
                    team_members.c.user_id == user_id,
                    team_members.c.is_active == True
                )
            )
            .values(role=role)
        )
        db.commit()
        return result.rowcount > 0

    @staticmethod
    def remove_member(db: Session, team_id: int, user_id: int) -> bool:
        """Remove a member from team (soft delete)."""
        result = db.execute(
            team_members.update()
            .where(
                and_(
                    team_members.c.team_id == team_id,
                    team_members.c.user_id == user_id
                )
            )
            .values(is_active=False)
        )

        if result.rowcount > 0:
            # Update team member count
            db.execute(
                Team.__table__.update()
                .where(Team.id == team_id)
                .values(member_count=Team.member_count - 1)
            )
            db.commit()
            return True

        return False


# ============================================================================
# Team Invite Service
# ============================================================================

class TeamInviteService:
    """Service for Team Invitation operations."""

    @staticmethod
    def _generate_token(length: int = 32) -> str:
        """Generate secure random token for invitations."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def create_invite(
        db: Session,
        invite: TeamInviteCreate
    ) -> TeamInvite:
        """Create a new team invitation."""
        # Generate token and expiration
        token = TeamInviteService._generate_token()
        expires_at = datetime.now(UTC) + timedelta(days=invite.expires_in_days)

        db_invite = TeamInvite(
            team_id=invite.team_id,
            invited_email=invite.invited_email,
            invited_by=invite.invited_by,
            role=invite.role,
            status=InviteStatus.pending,
            invite_token=token,
            expires_at=expires_at
        )
        db.add(db_invite)
        db.commit()
        db.refresh(db_invite)
        return db_invite

    @staticmethod
    def get_invite(db: Session, invite_id: int) -> Optional[TeamInvite]:
        """Get an invitation by ID."""
        return db.query(TeamInvite).filter(TeamInvite.id == invite_id).first()

    @staticmethod
    def get_by_token(db: Session, token: str) -> Optional[TeamInvite]:
        """Get an invitation by token."""
        return db.query(TeamInvite).filter(TeamInvite.invite_token == token).first()

    @staticmethod
    def get_team_invites(db: Session, team_id: int) -> List[TeamInvite]:
        """Get all invitations for a team."""
        return (
            db.query(TeamInvite)
            .filter(TeamInvite.team_id == team_id)
            .order_by(desc(TeamInvite.created_at))
            .all()
        )

    @staticmethod
    def get_pending_invites(db: Session, team_id: int) -> List[TeamInvite]:
        """Get pending invitations for a team."""
        now = datetime.now(UTC)
        return (
            db.query(TeamInvite)
            .filter(
                TeamInvite.team_id == team_id,
                TeamInvite.status == InviteStatus.pending,
                TeamInvite.expires_at > now
            )
            .order_by(desc(TeamInvite.created_at))
            .all()
        )

    @staticmethod
    def accept_invite(db: Session, token: str, user_id: int) -> Optional[TeamInvite]:
        """Accept an invitation."""
        invite = TeamInviteService.get_by_token(db, token)
        if not invite:
            return None

        # Check if expired
        if invite.expires_at < datetime.now(UTC):
            invite.status = InviteStatus.expired
            db.commit()
            return None

        # Check if already accepted/declined
        if invite.status != InviteStatus.pending:
            return None

        # Add user to team
        TeamMemberService.add_member(
            db,
            team_id=invite.team_id,
            user_id=user_id,
            role=invite.role,
            invited_by=invite.invited_by
        )

        # Update invite status
        invite.status = InviteStatus.accepted
        invite.accepted_at = datetime.now(UTC)
        invite.invited_user_id = user_id
        db.commit()
        db.refresh(invite)

        return invite

    @staticmethod
    def decline_invite(db: Session, token: str) -> Optional[TeamInvite]:
        """Decline an invitation."""
        invite = TeamInviteService.get_by_token(db, token)
        if not invite or invite.status != InviteStatus.pending:
            return None

        invite.status = InviteStatus.declined
        db.commit()
        db.refresh(invite)
        return invite

    @staticmethod
    def cancel_invite(db: Session, invite_id: int) -> bool:
        """Cancel an invitation."""
        invite = TeamInviteService.get_invite(db, invite_id)
        if not invite or invite.status != InviteStatus.pending:
            return False

        db.delete(invite)
        db.commit()
        return True


# ============================================================================
# Team Project Service
# ============================================================================

class TeamProjectService:
    """Service for Team Project linking operations."""

    @staticmethod
    def link_project(db: Session, link: TeamProjectCreate) -> TeamProject:
        """Link a project to a team."""
        db_link = TeamProject(**link.model_dump())
        db.add(db_link)

        # Update team project count
        db.execute(
            Team.__table__.update()
            .where(Team.id == link.team_id)
            .values(project_count=Team.project_count + 1)
        )

        db.commit()
        db.refresh(db_link)
        return db_link

    @staticmethod
    def get_team_projects(db: Session, team_id: int, skip: int = 0, limit: int = 100) -> List[TeamProject]:
        """Get all projects linked to a team."""
        return (
            db.query(TeamProject)
            .filter(TeamProject.team_id == team_id)
            .order_by(desc(TeamProject.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_team_templates(db: Session, team_id: int) -> List[TeamProject]:
        """Get team template projects."""
        return (
            db.query(TeamProject)
            .filter(
                TeamProject.team_id == team_id,
                TeamProject.is_team_template == True
            )
            .order_by(desc(TeamProject.created_at))
            .all()
        )

    @staticmethod
    def unlink_project(db: Session, team_id: int, project_id: int) -> bool:
        """Unlink a project from a team."""
        result = (
            db.query(TeamProject)
            .filter(
                TeamProject.team_id == team_id,
                TeamProject.project_id == project_id
            )
            .delete()
        )

        if result > 0:
            # Update team project count
            db.execute(
                Team.__table__.update()
                .where(Team.id == team_id)
                .values(project_count=Team.project_count - 1)
            )
            db.commit()
            return True

        return False


# ============================================================================
# Team Insight Service
# ============================================================================

class TeamInsightService:
    """Service for Team Insight operations."""

    @staticmethod
    def create_insight(db: Session, insight: TeamInsightCreate) -> TeamInsight:
        """Create a new team insight."""
        db_insight = TeamInsight(**insight.model_dump())
        db.add(db_insight)
        db.commit()
        db.refresh(db_insight)
        return db_insight

    @staticmethod
    def get_active_insights(db: Session, team_id: int) -> List[TeamInsight]:
        """Get all active insights for a team."""
        now = datetime.now(UTC)
        return (
            db.query(TeamInsight)
            .filter(
                TeamInsight.team_id == team_id,
                TeamInsight.is_active == True,
                or_(
                    TeamInsight.expires_at == None,
                    TeamInsight.expires_at > now
                )
            )
            .order_by(
                TeamInsight.priority.desc(),
                desc(TeamInsight.created_at)
            )
            .all()
        )

    @staticmethod
    def get_unread_insights(db: Session, team_id: int) -> List[TeamInsight]:
        """Get unread insights for a team."""
        now = datetime.now(UTC)
        return (
            db.query(TeamInsight)
            .filter(
                TeamInsight.team_id == team_id,
                TeamInsight.is_active == True,
                TeamInsight.is_read == False,
                or_(
                    TeamInsight.expires_at == None,
                    TeamInsight.expires_at > now
                )
            )
            .order_by(
                TeamInsight.priority.desc(),
                desc(TeamInsight.created_at)
            )
            .all()
        )

    @staticmethod
    def mark_as_read(db: Session, insight_id: int) -> bool:
        """Mark an insight as read."""
        insight = db.query(TeamInsight).filter(TeamInsight.id == insight_id).first()
        if not insight:
            return False

        insight.is_read = True
        db.commit()
        return True

    @staticmethod
    def mark_as_acted_upon(db: Session, insight_id: int) -> bool:
        """Mark an insight as acted upon."""
        insight = db.query(TeamInsight).filter(TeamInsight.id == insight_id).first()
        if not insight:
            return False

        insight.is_acted_upon = True
        db.commit()
        return True

    @staticmethod
    def dismiss_insight(db: Session, insight_id: int) -> bool:
        """Dismiss an insight."""
        insight = db.query(TeamInsight).filter(TeamInsight.id == insight_id).first()
        if not insight:
            return False

        insight.is_active = False
        insight.dismissed_at = datetime.now(UTC)
        db.commit()
        return True
