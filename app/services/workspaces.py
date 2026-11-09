"""Centralize workspace ownership resolution and non-revealing authorization."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import settings
from app.models.project import Project
from app.models.ticket import Ticket
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import AuthContext


def get_or_create_bootstrap_workspace(db: Session) -> Workspace:
    """Return the local owner's workspace used until request authentication exists.

    This bridge keeps the current single-user experience working while ensuring
    every new top-level work record is already owned by a real workspace.
    """
    user = db.scalar(select(User).where(User.email == settings.bootstrap_user_email))
    if user is None:
        existing_user = db.scalar(select(User).limit(1))
        if existing_user is not None:
            raise RuntimeError(
                "The configured bootstrap user does not match the existing Telaryn "
                "owner. Check ATLAS_BOOTSTRAP_USER_EMAIL before starting Telaryn."
            )
        user = User(
            email=settings.bootstrap_user_email,
            display_name=settings.bootstrap_user_display_name,
        )
        db.add(user)
        db.flush()

    workspace = db.scalar(
        select(Workspace).where(Workspace.created_by_user_id == user.id)
    )
    if workspace is None:
        workspace = Workspace(
            name=settings.bootstrap_workspace_name,
            created_by_user_id=user.id,
        )
        db.add(workspace)
        db.flush()

    membership = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if membership is None:
        db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner"))
        db.flush()

    return workspace


def get_workspace_project(db: Session, *, workspace_id: int, project_id: int) -> Project | None:
    """Resolve a project only when it belongs to the active workspace."""
    return db.scalar(
        select(Project).where(Project.id == project_id, Project.workspace_id == workspace_id)
    )


def require_assignable_project(
    db: Session, *, workspace_id: int, project_id: int
) -> Project:
    """Resolve an active Project suitable for a new or changed Ticket assignment."""
    project = get_workspace_project(
        db, workspace_id=workspace_id, project_id=project_id
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.archived_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Archived Projects cannot receive Tickets. Restore the Project first.",
        )
    return project


def require_active_project(project: Project) -> None:
    """Keep archived Projects readable while rejecting active-workflow mutation."""
    if project.archived_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Archived Projects are view-only. Restore the Project to continue.",
        )


def require_active_ticket(ticket: Ticket) -> None:
    """Reject mutation of a Ticket whose Project is archived."""
    if ticket.project is not None and ticket.project.archived_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Tickets in archived Projects are view-only. Restore the Project first.",
        )


def get_workspace_ticket(db: Session, *, workspace_id: int, ticket_id: int) -> Ticket | None:
    """Resolve a ticket only when it belongs to the active workspace."""
    return db.scalar(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.workspace_id == workspace_id)
    )


def request_workspace(db: Session, auth: AuthContext | object) -> Workspace:
    """Use authenticated identity for HTTP calls while supporting direct service tests."""
    return auth.workspace if isinstance(auth, AuthContext) else get_or_create_bootstrap_workspace(db)


def require_workspace_project(
    db: Session, *, workspace_id: int, project_id: int
) -> Project:
    """Resolve a project without disclosing whether another workspace owns its ID."""
    project = get_workspace_project(db, workspace_id=workspace_id, project_id=project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_workspace_ticket(
    db: Session, *, workspace_id: int, ticket_id: int
) -> Ticket:
    """Resolve the parent authorization boundary for every ticket child resource."""
    ticket = get_workspace_ticket(db, workspace_id=workspace_id, ticket_id=ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def activity_actor(auth: AuthContext | object) -> tuple[str, str | None]:
    """Return immutable attribution for new human actions; direct legacy calls stay legacy."""
    if isinstance(auth, AuthContext):
        return "user", str(auth.user.id)
    return "local_user", None

