"""Expose core ticket lifecycle, exports, drawer commits, and unified activity reads."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.project import Project
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.schemas.ticket import (
    TicketActivityEventRead,
    TicketActivityItemRead,
    TicketCreate,
    TicketRead,
    TicketStatusEventRead,
    TicketUpdate,
)
from app.schemas.drawer_session import DrawerSessionCommit, DrawerSessionResult
from app.services.drawer_session import commit_drawer_session
from app.services.ticket_activity import (
    add_ticket_activity_event,
    apply_audited_ticket_field,
    list_ticket_activity,
)
from app.services.ticket_export import (
    build_ticket_export_snapshot,
    render_ticket_export_pdf,
    ticket_export_filename,
)
from app.services.workspaces import (
    activity_actor,
    request_workspace,
    require_active_ticket,
    require_assignable_project,
    require_workspace_ticket,
)
from app.services.auth import AuthContext, require_auth_context


# Core ticket lifecycle endpoints, including the append-only status audit rule.
router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"],
)


@router.post("/", response_model=TicketRead, status_code=201)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    actor_type, actor_id = activity_actor(auth)
    if ticket_data.project_id is not None:
        require_assignable_project(
            db,
            workspace_id=workspace.id,
            project_id=ticket_data.project_id,
        )

    ticket = Ticket(
        workspace_id=workspace.id,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority,
        ticket_type=ticket_data.ticket_type,
        project_id=ticket_data.project_id,
        ai_context_enabled=ticket_data.ai_context_enabled,
    )

    db.add(ticket)
    db.flush()

    criteria = [
        AcceptanceCriterion(
            ticket_id=ticket.id,
            text=item.text,
            sort_order=item.sort_order or index,
        )
        for index, item in enumerate(ticket_data.acceptance_criteria, start=1)
    ]
    subtasks = [
        Subtask(
            ticket_id=ticket.id,
            title=item.title,
            description=item.description,
            sort_order=item.sort_order or index,
        )
        for index, item in enumerate(ticket_data.subtasks, start=1)
    ]
    db.add_all([*criteria, *subtasks])
    db.flush()

    add_ticket_activity_event(
        db,
        ticket_id=ticket.id,
        event_type="ticket_created",
        new_value={
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "ticket_type": ticket.ticket_type,
            "project_id": ticket.project_id,
            "ai_context_enabled": ticket.ai_context_enabled,
            "acceptance_criteria": [
                {
                    "id": item.id,
                    "text": item.text,
                    "completed": item.completed,
                }
                for item in criteria
            ],
            "subtasks": [
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "status": item.status,
                }
                for item in subtasks
            ],
        },
        actor_type=actor_type,
        actor_id=actor_id,
    )
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("/", response_model=list[TicketRead])
def list_tickets(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    statement = (
        select(Ticket)
        .outerjoin(Project, Ticket.project_id == Project.id)
        .where(Ticket.workspace_id == workspace.id)
    )
    if not include_archived:
        statement = statement.where(
            or_(Ticket.project_id.is_(None), Project.archived_at.is_(None))
        )
    statement = statement.order_by(Ticket.created_at.desc())
    tickets = db.scalars(statement).all()

    return tickets


@router.get("/public/{public_id}", response_model=TicketRead)
def get_ticket_by_public_id(
    public_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = db.scalar(
        select(Ticket).where(
            Ticket.public_id == public_id,
            Ticket.workspace_id == workspace.id,
        )
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    return require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)


@router.get("/{ticket_id}/export.json")
def export_ticket_json(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    snapshot = build_ticket_export_snapshot(db, ticket_id=ticket.id)
    filename = ticket_export_filename(snapshot, "json")
    content = json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{ticket_id}/export.pdf")
def export_ticket_pdf(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    snapshot = build_ticket_export_snapshot(db, ticket_id=ticket.id)
    filename = ticket_export_filename(snapshot, "pdf")
    return Response(
        content=render_ticket_export_pdf(snapshot),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{ticket_id}/status-history",
    response_model=list[TicketStatusEventRead],
)
def list_ticket_status_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)

    statement = (
        select(TicketStatusEvent)
        .where(TicketStatusEvent.ticket_id == ticket_id)
        .order_by(
            TicketStatusEvent.created_at.desc(),
            TicketStatusEvent.id.desc(),
        )
    )

    return db.scalars(statement).all()


@router.get(
    "/{ticket_id}/activity-events",
    response_model=list[TicketActivityEventRead],
)
def list_ticket_activity_events(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)

    statement = (
        select(TicketActivityEvent)
        .where(TicketActivityEvent.ticket_id == ticket_id)
        .order_by(
            TicketActivityEvent.created_at.desc(),
            TicketActivityEvent.id.desc(),
        )
    )

    return db.scalars(statement).all()


@router.get(
    "/{ticket_id}/activity",
    response_model=list[TicketActivityItemRead],
)
def list_ticket_activity_timeline(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)

    return list_ticket_activity(db, ticket_id=ticket_id)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)

    updates = ticket_data.model_dump(exclude_unset=True)
    status_note = updates.pop("status_note", None)

    if "project_id" in updates and updates["project_id"] is not None:
        require_assignable_project(
            db,
            workspace_id=workspace.id,
            project_id=updates["project_id"],
        )

    requested_status = updates.get("status")

    if requested_status is not None and requested_status != ticket.status:
        # Status history is append-only: ordinary field edits do not create
        # transition events, while meaningful state changes always remain traceable.
        note_required = requested_status.value in {"blocked", "cancelled"}
        required_note_message = (
            "A blocker reason is required when marking a ticket blocked."
            if requested_status.value == "blocked"
            else "A cancellation reason is required when cancelling a ticket."
        )

        if requested_status.value == "done":
            has_incomplete_criteria = any(
                not criterion.completed
                for criterion in ticket.acceptance_criteria
            )
            has_incomplete_subtasks = any(
                subtask.status
                not in {SubtaskStatus.DONE, SubtaskStatus.CANCELLED}
                for subtask in ticket.subtasks
            )
            note_required = has_incomplete_criteria or has_incomplete_subtasks
            required_note_message = (
                "A completion note is required because unfinished subtasks "
                "or acceptance criteria remain."
            )

        # These transitions need human context so the audit record explains why
        # work stopped, was cancelled, or finished with incomplete structure.
        if note_required and not status_note:
            raise HTTPException(
                status_code=422,
                detail=required_note_message,
            )

        db.add(
            TicketStatusEvent(
                ticket_id=ticket.id,
                from_status=ticket.status.value,
                to_status=requested_status.value,
                note=status_note,
                actor_user_id=auth.user.id if isinstance(auth, AuthContext) else None,
            )
        )

    for field, value in updates.items():
        if field == "status":
            setattr(ticket, field, value)
        else:
            apply_audited_ticket_field(
                db,
                ticket=ticket,
                field_name=field,
                new_value=value,
                actor_type=actor_type,
                actor_id=actor_id,
            )

    db.commit()
    db.refresh(ticket)

    return ticket


@router.put("/{ticket_id}/drawer-session", response_model=DrawerSessionResult)
def save_ticket_drawer_session(
    ticket_id: int,
    commit: DrawerSessionCommit,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Persist one reviewed drawer state as one transaction and activity event."""
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)

    try:
        ticket, criteria, subtasks = commit_drawer_session(
            db,
            ticket=ticket,
            commit=commit,
            workspace_id=workspace.id,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_user_id=auth.user.id if isinstance(auth, AuthContext) else None,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(ticket)
    for item in [*criteria, *subtasks]:
        db.refresh(item)
    return DrawerSessionResult(
        ticket=ticket,
        acceptance_criteria=criteria,
        subtasks=subtasks,
    )
