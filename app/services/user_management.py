"""Enforce deployment-level account lifecycle administration boundaries."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.session import get_db
from app.models.account_admin_event import AccountAdminEvent
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import AuthContext, require_auth_context


def require_deployment_administrator(
    response: Response,
    auth: AuthContext = Depends(require_auth_context),
) -> AuthContext:
    """Authorize only the explicitly configured deployment administration role."""
    response.headers["Cache-Control"] = "no-store"
    if auth.user.id not in settings.deployment_administrator_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deployment administrator required.",
        )
    return auth


def record_account_admin_event(
    db: Session, *, actor_id: int, affected_user_id: int, event: str, outcome: str
) -> None:
    """Store only lifecycle metadata, never credentials or workspace content."""
    db.add(AccountAdminEvent(
        actor_id=actor_id,
        affected_user_id=affected_user_id,
        event=event,
        outcome=outcome,
        created_at=utc_now(),
    ))


def revoke_user_sessions(db: Session, *, user_id: int) -> int:
    """Invalidate every current session without deleting security audit history."""
    result = db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )
    return result.rowcount or 0


def would_disable_last_active_owner(db: Session, *, user_id: int) -> bool:
    """Do not leave any workspace without an active owner account."""
    workspace_ids = db.scalars(
        select(WorkspaceMembership.workspace_id).where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.role == "owner",
        )
    ).all()
    for workspace_id in workspace_ids:
        if would_leave_workspace_without_active_owner(
            db, workspace_id=workspace_id, excluded_user_id=user_id
        ):
            return True
    return False


def would_leave_workspace_without_active_owner(
    db: Session, *, workspace_id: int, excluded_user_id: int
) -> bool:
    """Confirm an owner removal/demotion cannot orphan an active workspace."""
    remaining = db.scalar(
        select(func.count())
        .select_from(WorkspaceMembership)
        .join(User, User.id == WorkspaceMembership.user_id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.user_id != excluded_user_id,
            User.account_status == "active",
        )
    )
    return not remaining


def require_managed_user(db: Session = Depends(get_db), user_id: int = 0) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user
