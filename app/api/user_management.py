"""Deployment-administrator account lifecycle controls with metadata-only visibility."""

from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.user_management import (
    DeploymentAdminAccess,
    ManagedUserDetailRead,
    ManagedUserPage,
    ManagedUserRead,
    ManagedWorkspaceRead,
    UserLifecycleAction,
    WorkspaceMembershipRoleAction,
)
from app.services.auth import AuthContext, require_auth_context
from app.services.user_management import (
    record_account_admin_event,
    require_deployment_administrator,
    revoke_user_sessions,
    would_leave_workspace_without_active_owner,
    would_disable_last_active_owner,
)


router = APIRouter(prefix="/user-management", tags=["User management"])


def user_summary(db: Session, user: User) -> ManagedUserRead:
    workspace_count = db.scalar(select(func.count()).select_from(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user.id
    )) or 0
    return ManagedUserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        account_status=user.account_status,
        created_at=user.created_at,
        disabled_at=user.disabled_at,
        workspace_count=workspace_count,
    )


@router.get("/access", response_model=DeploymentAdminAccess)
def deployment_admin_access(
    response: Response,
    auth: AuthContext = Depends(require_auth_context),
):
    response.headers["Cache-Control"] = "no-store"
    return DeploymentAdminAccess(allowed=auth.user.id in settings.deployment_administrator_ids)


@router.get("/users", response_model=ManagedUserPage)
def list_users(
    status: str = Query("active", pattern="^(active|disabled|all)$"),
    search: str = Query("", max_length=100),
    page: int = Query(1, ge=1, le=100000),
    db: Session = Depends(get_db),
    _: AuthContext = Depends(require_deployment_administrator),
):
    filters = []
    if status != "all":
        filters.append(User.account_status == status)
    term = search.strip().lower()
    if term:
        filters.append(or_(
            func.lower(User.email).contains(term, autoescape=True),
            func.lower(User.display_name).contains(term, autoescape=True),
        ))
    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    pages = max(1, ceil(total / 25))
    current_page = min(page, pages)
    users = db.scalars(
        select(User).where(*filters).order_by(User.created_at.desc(), User.id.desc())
        .offset((current_page - 1) * 25).limit(25)
    ).all()
    return ManagedUserPage(
        items=[user_summary(db, user) for user in users], total=total, page=current_page, pages=pages
    )


@router.get("/users/{user_id}", response_model=ManagedUserDetailRead)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: AuthContext = Depends(require_deployment_administrator),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    summary = user_summary(db, user)
    memberships = db.execute(
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(WorkspaceMembership.user_id == user.id)
        .order_by(Workspace.name)
    ).all()
    session_count = db.scalar(select(func.count()).select_from(AuthSession).where(AuthSession.user_id == user.id)) or 0
    active_sessions = db.scalar(select(func.count()).select_from(AuthSession).where(
        AuthSession.user_id == user.id,
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > utc_now(),
    )) or 0
    return ManagedUserDetailRead(
        **summary.model_dump(),
        workspaces=[ManagedWorkspaceRead(id=workspace.id, name=workspace.name, role=membership.role) for membership, workspace in memberships],
        session_count=session_count,
        active_session_count=active_sessions,
    )


@router.post("/users/{user_id}/disable", response_model=ManagedUserDetailRead)
def disable_user(
    user_id: int,
    _: UserLifecycleAction,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_deployment_administrator),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == auth.user.id:
        raise HTTPException(status_code=409, detail="You cannot disable your own account.")
    if user.account_status == "disabled":
        raise HTTPException(status_code=409, detail="This account is already disabled.")
    if would_disable_last_active_owner(db, user_id=user.id):
        raise HTTPException(status_code=409, detail="Add another active workspace owner before disabling this account.")
    user.account_status = "disabled"
    user.disabled_at = utc_now()
    revoke_user_sessions(db, user_id=user.id)
    record_account_admin_event(db, actor_id=auth.user.id, affected_user_id=user.id, event="account_disabled", outcome="success")
    db.commit()
    db.refresh(user)
    return read_user(user.id, db, auth)


@router.post("/users/{user_id}/reactivate", response_model=ManagedUserDetailRead)
def reactivate_user(
    user_id: int,
    _: UserLifecycleAction,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_deployment_administrator),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.account_status == "active":
        raise HTTPException(status_code=409, detail="This account is already active.")
    user.account_status = "active"
    user.disabled_at = None
    record_account_admin_event(db, actor_id=auth.user.id, affected_user_id=user.id, event="account_reactivated", outcome="success")
    db.commit()
    db.refresh(user)
    return read_user(user.id, db, auth)


@router.post("/users/{user_id}/revoke-sessions", response_model=ManagedUserDetailRead)
def revoke_sessions(
    user_id: int,
    _: UserLifecycleAction,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_deployment_administrator),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    revoke_user_sessions(db, user_id=user.id)
    record_account_admin_event(db, actor_id=auth.user.id, affected_user_id=user.id, event="sessions_revoked", outcome="success")
    db.commit()
    return read_user(user.id, db, auth)


@router.patch("/users/{user_id}/workspaces/{workspace_id}", response_model=ManagedUserDetailRead)
def change_workspace_role(
    user_id: int,
    workspace_id: int,
    payload: WorkspaceMembershipRoleAction,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_deployment_administrator),
):
    user = db.get(User, user_id)
    membership = db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user_id,
        WorkspaceMembership.workspace_id == workspace_id,
    ))
    if user is None or membership is None:
        raise HTTPException(status_code=404, detail="Workspace membership not found.")
    if membership.role == payload.role:
        return read_user(user.id, db, auth)
    if membership.role == "owner" and payload.role != "owner" and user.account_status == "active" and would_leave_workspace_without_active_owner(
        db, workspace_id=workspace_id, excluded_user_id=user_id
    ):
        raise HTTPException(status_code=409, detail="Add another active workspace owner before changing this role.")
    membership.role = payload.role
    record_account_admin_event(db, actor_id=auth.user.id, affected_user_id=user.id, event="workspace_role_changed", outcome="success")
    db.commit()
    return read_user(user.id, db, auth)


@router.delete("/users/{user_id}/workspaces/{workspace_id}", response_model=ManagedUserDetailRead)
def remove_workspace_membership(
    user_id: int,
    workspace_id: int,
    _: UserLifecycleAction,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_deployment_administrator),
):
    user = db.get(User, user_id)
    membership = db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user_id,
        WorkspaceMembership.workspace_id == workspace_id,
    ))
    if user is None or membership is None:
        raise HTTPException(status_code=404, detail="Workspace membership not found.")
    if membership.role == "owner" and user.account_status == "active" and would_leave_workspace_without_active_owner(
        db, workspace_id=workspace_id, excluded_user_id=user_id
    ):
        raise HTTPException(status_code=409, detail="Add another active workspace owner before removing this membership.")
    db.delete(membership)
    record_account_admin_event(db, actor_id=auth.user.id, affected_user_id=user.id, event="workspace_membership_removed", outcome="success")
    db.commit()
    return read_user(user.id, db, auth)
