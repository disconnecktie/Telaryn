"""Compose a workspace-authorized Project export from canonical Ticket snapshots.

No AI provider, network fetch, filesystem write, or unrelated workspace data
is involved. Private Project/Ticket metadata is deliberately included for an
authenticated member of the owning workspace; AI-context policy is unrelated
to human authorization.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_ai_policy_event import ProjectAIPolicyEvent
from app.models.project_lifecycle_event import ProjectLifecycleEvent
from app.models.ticket import Ticket
from app.models.user import User
from app.services.ticket_export import (
    SCHEMA_VERSION as TICKET_SCHEMA_VERSION,
    _iso,
    build_ticket_export_snapshot,
)
from app.core.time import utc_now


PROJECT_EXPORT_SCHEMA_VERSION = "1.0"


def build_project_export_snapshot(
    db: Session, *, project: Project, workspace_id: int
) -> dict[str, Any]:
    """Build a complete snapshot for a previously authorized Project.

    The workspace predicate on every child query protects against accidentally
    reassigning or including unrelated Tickets/Project history. The API must
    first resolve the Project using require_workspace_project.
    """
    if project.workspace_id != workspace_id:
        raise ValueError("Project does not belong to the authorized workspace.")

    ticket_ids = db.scalars(
        select(Ticket.id)
        .where(Ticket.workspace_id == workspace_id, Ticket.project_id == project.id)
        .order_by(Ticket.workspace_ticket_number, Ticket.id)
    ).all()
    # Reuse the canonical ticket serializer, preserving its existing field
    # filtering, child histories, public references, and version contract.
    tickets = [
        build_ticket_export_snapshot(
            db,
            ticket_id=ticket_id,
            workspace_id=workspace_id,
            project_id=project.id,
        )
        for ticket_id in ticket_ids
    ]

    lifecycle = db.execute(
        select(ProjectLifecycleEvent, User.display_name)
        .outerjoin(User, ProjectLifecycleEvent.actor_user_id == User.id)
        .where(
            ProjectLifecycleEvent.workspace_id == workspace_id,
            ProjectLifecycleEvent.project_id == project.id,
        )
        .order_by(ProjectLifecycleEvent.created_at, ProjectLifecycleEvent.id)
    ).all()
    policy_history = db.execute(
        select(ProjectAIPolicyEvent, User.display_name)
        .outerjoin(User, ProjectAIPolicyEvent.actor_id == User.id)
        .where(
            ProjectAIPolicyEvent.workspace_id == workspace_id,
            ProjectAIPolicyEvent.project_id == project.id,
        )
        .order_by(ProjectAIPolicyEvent.created_at, ProjectAIPolicyEvent.id)
    ).all()

    return {
        "schema": "atlas.project-export",
        "schema_version": PROJECT_EXPORT_SCHEMA_VERSION,
        "exported_at": _iso(utc_now()),
        "ticket_schema_version": TICKET_SCHEMA_VERSION,
        "project": {
            "local_reference": f"PRJ-{project.workspace_project_number:03d}",
            "public_reference": project.public_id,
            "name": project.name,
            "description": project.description,
            "purpose": project.purpose,
            "why_it_matters": project.why_it_matters,
            "target_date": project.target_date.isoformat() if project.target_date else None,
            "life_context": project.life_context,
            "private": not project.ai_context_enabled,
            "archived": project.archived_at is not None,
            "archived_at": _iso(project.archived_at),
            "archive_reason": project.archive_reason,
            "archive_reason_note": project.archive_reason_note,
            "created_at": _iso(project.created_at),
            "updated_at": _iso(project.updated_at),
        },
        "ticket_count": len(tickets),
        "tickets": tickets,
        "lifecycle_history": [
            {
                "action": event.action,
                "archive_reason": event.archive_reason,
                "archive_reason_note": event.archive_reason_note,
                "previous_life_context": event.previous_life_context,
                "new_life_context": event.new_life_context,
                "author": actor,
                "created_at": _iso(event.created_at),
            }
            for event, actor in lifecycle
        ],
        "ai_context_policy_history": [
            {
                "previous_ai_context_enabled": event.previous_ai_context_enabled,
                "new_ai_context_enabled": event.new_ai_context_enabled,
                "author": actor,
                "created_at": _iso(event.created_at),
            }
            for event, actor in policy_history
        ],
    }


def project_export_filename(snapshot: dict[str, Any]) -> str:
    """Derived from the server-assigned numeric local reference only."""
    reference = snapshot["project"]["local_reference"].lower()
    return f"{reference}-export.json"
