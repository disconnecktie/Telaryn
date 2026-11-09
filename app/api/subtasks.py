"""Expose ticket-scoped Subtask operations and immutable activity snapshots."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import get_db
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket
from app.schemas.subtask import SubtaskCreate, SubtaskRead, SubtasksSave, SubtaskUpdate
from app.services.ticket_activity import add_ticket_activity_event, subtask_activity_snapshot
from app.services.auth import AuthContext, require_auth_context
from app.services.workspaces import (
    activity_actor,
    request_workspace,
    require_active_ticket,
    require_workspace_ticket,
)


# Ticket-scoped CRUD for the executable work that supports a parent ticket.
router = APIRouter(
    prefix="/tickets/{ticket_id}/subtasks",
    tags=["Subtasks"],
)


@router.post("/", response_model=SubtaskRead, status_code=201)
def create_subtask(
    ticket_id: int,
    subtask_data: SubtaskCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)

    subtask = Subtask(
        ticket_id=ticket_id,
        title=subtask_data.title,
        description=subtask_data.description,
        sort_order=subtask_data.sort_order,
    )

    db.add(subtask)
    db.flush()
    add_ticket_activity_event(
        db,
        ticket_id=ticket_id,
        event_type="subtask_added",
        new_value=subtask_activity_snapshot(subtask),
        actor_type=actor_type,
        actor_id=actor_id,
    )
    db.commit()
    db.refresh(subtask)

    return subtask


@router.get("/", response_model=list[SubtaskRead])
def list_subtasks(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)

    statement = (
        select(Subtask)
        .where(Subtask.ticket_id == ticket_id)
        .order_by(Subtask.sort_order, Subtask.created_at)
    )

    return db.scalars(statement).all()


@router.put("/", response_model=list[SubtaskRead])
def save_subtasks(
    ticket_id: int,
    save_data: SubtasksSave,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Atomically save a section while preserving scope-decision context."""
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)

    existing = db.scalars(
        select(Subtask)
        .where(Subtask.ticket_id == ticket_id)
        .order_by(Subtask.sort_order, Subtask.id)
    ).all()
    existing_by_id = {subtask.id: subtask for subtask in existing}
    requested_ids = [item.id for item in save_data.subtasks if item.id is not None]
    if len(requested_ids) != len(set(requested_ids)) or any(
        item_id not in existing_by_id for item_id in requested_ids
    ):
        raise HTTPException(status_code=422, detail="Invalid subtask list.")

    scope_changed = (
        bool(set(existing_by_id) - set(requested_ids))
        or any(
            item.id is not None
            and (existing_by_id[item.id].status == SubtaskStatus.DEFERRED)
            != (item.status == SubtaskStatus.DEFERRED)
            for item in save_data.subtasks
        )
    )
    if scope_changed and not save_data.reason:
        raise HTTPException(status_code=422, detail="A reason is required for deferred, restored, or removed scope.")

    previous_value = [subtask_activity_snapshot(item) for item in existing]
    saved = []
    for sort_order, draft in enumerate(save_data.subtasks, start=1):
        subtask = existing_by_id.get(draft.id) if draft.id is not None else None
        if subtask is None:
            subtask = Subtask(ticket_id=ticket_id)
            db.add(subtask)
        was_deferred = subtask.status == SubtaskStatus.DEFERRED
        subtask.title = draft.title
        subtask.description = draft.description
        subtask.status = draft.status
        subtask.sort_order = sort_order
        subtask.completed_at = (
            utc_now()
            if subtask.status == SubtaskStatus.DONE and subtask.completed_at is None
            else subtask.completed_at
        )
        if subtask.status != SubtaskStatus.DONE:
            subtask.completed_at = None
        if subtask.status == SubtaskStatus.DEFERRED:
            subtask.deferred_at = subtask.deferred_at or utc_now()
            if not was_deferred:
                subtask.deferred_reason = save_data.reason
        else:
            subtask.deferred_at = None
            subtask.deferred_reason = None
        saved.append(subtask)

    for subtask in existing:
        if subtask.id not in requested_ids:
            db.delete(subtask)

    db.flush()
    new_value = [subtask_activity_snapshot(item) for item in saved]
    if previous_value != new_value:
        add_ticket_activity_event(
            db,
            ticket_id=ticket_id,
            event_type="subtasks_changed",
            previous_value=previous_value,
            new_value=new_value,
            note=save_data.reason,
            actor_type=actor_type,
            actor_id=actor_id,
        )
    db.commit()
    for subtask in saved:
        db.refresh(subtask)
    return saved


@router.patch("/{subtask_id}", response_model=SubtaskRead)
def update_subtask(
    ticket_id: int,
    subtask_id: int,
    subtask_data: SubtaskUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)
    subtask = db.get(Subtask, subtask_id)

    if subtask is None or subtask.ticket_id != ticket_id:
        raise HTTPException(
            status_code=404,
            detail="Subtask not found",
        )

    updates = subtask_data.model_dump(exclude_unset=True)
    reason = updates.pop("reason", None)
    next_status = updates.get("status", subtask.status)
    if (subtask.status == SubtaskStatus.DEFERRED) != (next_status == SubtaskStatus.DEFERRED) and not reason:
        raise HTTPException(status_code=422, detail="A reason is required to defer or restore scope.")
    previous_value = {
        "id": subtask.id,
        "title": subtask.title,
        "description": subtask.description,
        "status": subtask.status,
        "deferred_reason": subtask.deferred_reason,
    }

    for field, value in updates.items():
        setattr(subtask, field, value)

    if subtask.status == SubtaskStatus.DONE and subtask.completed_at is None:
        subtask.completed_at = utc_now()

    if subtask.status != SubtaskStatus.DONE:
        subtask.completed_at = None

    if subtask.status == SubtaskStatus.DEFERRED:
        subtask.deferred_at = subtask.deferred_at or utc_now()
        subtask.deferred_reason = reason or subtask.deferred_reason
    else:
        subtask.deferred_at = None
        subtask.deferred_reason = None

    new_value = {
        "id": subtask.id,
        "title": subtask.title,
        "description": subtask.description,
        "status": subtask.status,
        "deferred_reason": subtask.deferred_reason,
    }
    if previous_value != new_value:
        add_ticket_activity_event(
            db,
            ticket_id=ticket_id,
            event_type="subtask_updated",
            previous_value=previous_value,
            new_value=new_value,
            note=reason,
            actor_type=actor_type,
            actor_id=actor_id,
        )

    db.commit()
    db.refresh(subtask)

    return subtask

@router.delete("/{subtask_id}", status_code=204)
def delete_subtask(
    ticket_id: int,
    subtask_id: int,
    reason: str = Query(min_length=1, max_length=2000),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)
    subtask = db.get(Subtask, subtask_id)

    if subtask is None or subtask.ticket_id != ticket_id:
        raise HTTPException(
            status_code=404,
            detail="Subtask not found",
        )

    add_ticket_activity_event(
        db,
        ticket_id=ticket_id,
        event_type="subtask_removed",
        previous_value=subtask_activity_snapshot(subtask),
        note=reason,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    db.delete(subtask)
    db.commit()
