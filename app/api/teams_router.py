"""
Team & Organization Learning API Router (Phase 4.1)

Provides endpoints for:
- Team management (CRUD)
- Member management (add, remove, update roles)
- Invitation system (send, accept, decline)
- Project linking (team projects and templates)
- Team insights and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.models import User
from app.models.team_models import TeamRole, InviteStatus
from app.models.team_schemas import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamSummary,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamMemberResponse,
    TeamInviteCreate,
    TeamInviteUpdate,
    TeamInviteResponse,
    TeamInviteAccept,
    TeamProjectCreate,
    TeamProjectUpdate,
    TeamProjectResponse,
    TeamInsightCreate,
    TeamInsightUpdate,
    TeamInsightResponse,
    TeamAnalyticsRequest,
    TeamAnalyticsResponse
)
from app.services.teams_service import (
    TeamService,
    TeamMemberService,
    TeamInviteService,
    TeamProjectService,
    TeamInsightService
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/teams", tags=["teams"])


# ============================================================================
# Team Endpoints
# ============================================================================

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new team.

    The authenticated user becomes the team owner and is automatically
    added as the first team member with owner role.
    """
    # Set owner_id to current user
    team.owner_id = current_user.id

    # Check if slug is unique
    existing = TeamService.get_by_slug(db, team.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team with slug '{team.slug}' already exists"
        )

    return TeamService.create(db, team)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific team by ID.

    User must be a member of the team or the team must be public.
    """
    team = TeamService.get(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check access: must be member or public team
    membership = TeamService.check_membership(db, team_id, current_user.id)
    if not membership and not team.is_public:
        raise HTTPException(status_code=403, detail="Access denied")

    return team


@router.get("", response_model=List[TeamSummary])
def list_teams(
    owned_only: bool = Query(False, description="Show only teams owned by user"),
    public_only: bool = Query(False, description="Show only public teams"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List teams.

    - If owned_only=true: Returns teams owned by the user
    - If public_only=true: Returns all public teams
    - Default: Returns all teams the user is a member of
    """
    if owned_only:
        return TeamService.get_owned_teams(db, current_user.id, skip, limit)
    elif public_only:
        return TeamService.get_public_teams(db, skip, limit)
    else:
        return TeamService.get_user_teams(db, current_user.id, skip, limit)


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    updates: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a team.

    Requires admin or owner role.
    """
    # Check if user is admin
    if not TeamService.is_admin(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Admin access required")

    team = TeamService.update(db, team_id, updates)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a team (soft delete).

    Requires owner role. Team is deactivated, not permanently deleted.
    """
    team = TeamService.get(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Only owner can delete team
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner access required")

    TeamService.delete(db, team_id)


# ============================================================================
# Team Member Endpoints
# ============================================================================

@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
def get_team_members(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all members of a team.

    User must be a member of the team.
    """
    # Check membership
    if not TeamService.check_membership(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return TeamMemberService.get_members(db, team_id)


@router.put("/{team_id}/members/{user_id}/role", status_code=status.HTTP_200_OK)
def update_member_role(
    team_id: int,
    user_id: int,
    role: TeamRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a team member's role.

    Requires admin or owner role. Cannot change owner role.
    """
    # Check if current user is admin
    if not TeamService.is_admin(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Prevent changing owner role
    team = TeamService.get(db, team_id)
    if team and team.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot change owner role")

    success = TeamMemberService.update_role(db, team_id, user_id, role)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")

    return {"status": "updated", "role": role}


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a member from the team.

    Requires admin or owner role. Cannot remove owner.
    """
    # Check if current user is admin
    if not TeamService.is_admin(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Prevent removing owner
    team = TeamService.get(db, team_id)
    if team and team.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove team owner")

    success = TeamMemberService.remove_member(db, team_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")


# ============================================================================
# Team Invitation Endpoints
# ============================================================================

@router.post("/{team_id}/invites", response_model=TeamInviteResponse, status_code=status.HTTP_201_CREATED)
def send_team_invite(
    team_id: int,
    invite: TeamInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a team invitation.

    Requires admin or owner role.
    """
    # Check if user is admin
    if not TeamService.is_admin(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Set team_id and invited_by
    invite.team_id = team_id
    invite.invited_by = current_user.id

    return TeamInviteService.create_invite(db, invite)


@router.get("/{team_id}/invites", response_model=List[TeamInviteResponse])
def get_team_invites(
    team_id: int,
    pending_only: bool = Query(False, description="Show only pending invites"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get team invitations.

    Requires admin or owner role.
    """
    # Check if user is admin
    if not TeamService.is_admin(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Admin access required")

    if pending_only:
        return TeamInviteService.get_pending_invites(db, team_id)
    return TeamInviteService.get_team_invites(db, team_id)


@router.post("/invites/accept", response_model=TeamInviteResponse)
def accept_team_invite(
    accept: TeamInviteAccept,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept a team invitation.

    User must provide valid invite token.
    """
    invite = TeamInviteService.accept_invite(db, accept.invite_token, current_user.id)
    if not invite:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired invitation"
        )

    return invite


@router.post("/invites/{token}/decline", status_code=status.HTTP_200_OK)
def decline_team_invite(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Decline a team invitation.

    No authentication required - can be done via email link.
    """
    invite = TeamInviteService.decline_invite(db, token)
    if not invite:
        raise HTTPException(
            status_code=400,
            detail="Invalid invitation"
        )

    return {"status": "declined"}


@router.delete("/{team_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_team_invite(
    team_id: int,
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a pending invitation.

    Requires admin or owner role.
    """
    # Check if user is admin
    if not TeamService.is_admin(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Admin access required")

    success = TeamInviteService.cancel_invite(db, invite_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invitation not found")


# ============================================================================
# Team Project Endpoints
# ============================================================================

@router.post("/{team_id}/projects", response_model=TeamProjectResponse, status_code=status.HTTP_201_CREATED)
def link_project_to_team(
    team_id: int,
    project: TeamProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Link a project to a team.

    Requires team membership.
    """
    # Check membership
    if not TeamService.check_membership(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Set team_id and created_by
    project.team_id = team_id
    project.created_by = current_user.id

    return TeamProjectService.link_project(db, project)


@router.get("/{team_id}/projects", response_model=List[TeamProjectResponse])
def get_team_projects(
    team_id: int,
    templates_only: bool = Query(False, description="Show only team templates"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get projects linked to a team.

    Requires team membership.
    """
    # Check membership
    if not TeamService.check_membership(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if templates_only:
        return TeamProjectService.get_team_templates(db, team_id)
    return TeamProjectService.get_team_projects(db, team_id, skip, limit)


@router.delete("/{team_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_project_from_team(
    team_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unlink a project from a team.

    Requires admin or owner role.
    """
    # Check if user is admin
    if not TeamService.is_admin(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Admin access required")

    success = TeamProjectService.unlink_project(db, team_id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project link not found")


# ============================================================================
# Team Insights Endpoints
# ============================================================================

@router.get("/{team_id}/insights", response_model=List[TeamInsightResponse])
def get_team_insights(
    team_id: int,
    unread_only: bool = Query(False, description="Show only unread insights"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get team insights.

    Requires team membership.
    """
    # Check membership
    if not TeamService.check_membership(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    if unread_only:
        return TeamInsightService.get_unread_insights(db, team_id)
    return TeamInsightService.get_active_insights(db, team_id)


@router.put("/{team_id}/insights/{insight_id}/read", status_code=status.HTTP_200_OK)
def mark_insight_as_read(
    team_id: int,
    insight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark an insight as read.

    Requires team membership.
    """
    # Check membership
    if not TeamService.check_membership(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    success = TeamInsightService.mark_as_read(db, insight_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")

    return {"status": "marked_as_read"}


@router.put("/{team_id}/insights/{insight_id}/acted", status_code=status.HTTP_200_OK)
def mark_insight_as_acted_upon(
    team_id: int,
    insight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark an insight as acted upon.

    Requires team membership.
    """
    # Check membership
    if not TeamService.check_membership(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    success = TeamInsightService.mark_as_acted_upon(db, insight_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")

    return {"status": "marked_as_acted_upon"}


@router.delete("/{team_id}/insights/{insight_id}", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_insight(
    team_id: int,
    insight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dismiss an insight.

    Requires team membership.
    """
    # Check membership
    if not TeamService.check_membership(db, team_id, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    success = TeamInsightService.dismiss_insight(db, insight_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")
