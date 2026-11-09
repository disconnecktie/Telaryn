"""Expose ticket-scoped Acceptance Criterion operations and activity recording."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import get_db
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.ticket import Ticket
from app.schemas.acceptance_criterion import (
    AcceptanceCriterionCreate,
    AcceptanceCriterionRead,
    AcceptanceCriterionUpdate,
    AcceptanceCriteriaSave,
)
from app.services.ticket_activity import (
    acceptance_criterion_activity_snapshot,
    add_ticket_activity_event,
)
from app.services.auth import AuthContext, require_auth_context
from app.services.workspaces import (
    activity_actor,
    request_workspace,
    require_active_ticket,
    require_workspace_ticket,
)


# Ticket-scoped CRUD for definitions of done; ticket workflow stays authoritative.
router = APIRouter(
    prefix="/tickets/{ticket_id}/acceptance-criteria",
    tags=["Acceptance Criteria"],
)


@router.post("/", response_model=AcceptanceCriterionRead, status_code=201)
def create_acceptance_criterion(
    ticket_id: int,
    criterion_data: AcceptanceCriterionCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)

    criterion = AcceptanceCriterion(
        ticket_id=ticket_id,
        text=criterion_data.text,
        sort_order=criterion_data.sort_order,
    )

    db.add(criterion)
    db.flush()
    add_ticket_activity_event(
        db,
        ticket_id=ticket_id,
        event_type="acceptance_criterion_added",
        new_value=acceptance_criterion_activity_snapshot(criterion),
        actor_type=actor_type,
        actor_id=actor_id,
    )
    db.commit()
    db.refresh(criterion)

    return criterion


@router.get("/", response_model=list[AcceptanceCriterionRead])
def list_acceptance_criteria(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)

    statement = (
        select(AcceptanceCriterion)
        .where(AcceptanceCriterion.ticket_id == ticket_id)
        .order_by(
            AcceptanceCriterion.sort_order,
            AcceptanceCriterion.created_at,
        )
    )

    return db.scalars(statement).all()


@router.put("/", response_model=list[AcceptanceCriterionRead])
def save_acceptance_criteria(
    ticket_id: int,
    save_data: AcceptanceCriteriaSave,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Atomically save a section while preserving scope-decision context."""
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)

    existing = db.scalars(
        select(AcceptanceCriterion)
        .where(AcceptanceCriterion.ticket_id == ticket_id)
        .order_by(AcceptanceCriterion.sort_order, AcceptanceCriterion.id)
    ).all()
    existing_by_id = {criterion.id: criterion for criterion in existing}
    requested_ids = [item.id for item in save_data.criteria if item.id is not None]
    if len(requested_ids) != len(set(requested_ids)) or any(
        item_id not in existing_by_id for item_id in requested_ids
    ):
        raise HTTPException(status_code=422, detail="Invalid acceptance criterion list.")

    scope_changed = (
        bool(set(existing_by_id) - set(requested_ids))
        or any(
            item.id is not None
            and existing_by_id[item.id].deferred != item.deferred
            for item in save_data.criteria
        )
    )
    if scope_changed and not save_data.reason:
        raise HTTPException(status_code=422, detail="A reason is required for deferred, restored, or removed scope.")

    previous_value = [acceptance_criterion_activity_snapshot(item) for item in existing]
    saved = []
    for sort_order, draft in enumerate(save_data.criteria, start=1):
        criterion = existing_by_id.get(draft.id) if draft.id is not None else None
        if criterion is None:
            criterion = AcceptanceCriterion(ticket_id=ticket_id)
            db.add(criterion)
        was_deferred = criterion.deferred
        criterion.text = draft.text
        criterion.completed = draft.completed and not draft.deferred
        criterion.deferred = draft.deferred
        criterion.sort_order = sort_order
        criterion.completed_at = (
            utc_now()
            if criterion.completed and criterion.completed_at is None
            else criterion.completed_at
        )
        if not criterion.completed:
            criterion.completed_at = None
        if criterion.deferred:
            criterion.deferred_at = criterion.deferred_at or utc_now()
            if not was_deferred:
                criterion.deferred_reason = save_data.reason
        else:
            criterion.deferred_at = None
            criterion.deferred_reason = None
        saved.append(criterion)

    for criterion in existing:
        if criterion.id not in requested_ids:
            db.delete(criterion)

    db.flush()
    new_value = [acceptance_criterion_activity_snapshot(item) for item in saved]
    if previous_value != new_value:
        add_ticket_activity_event(
            db,
            ticket_id=ticket_id,
            event_type="acceptance_criteria_changed",
            previous_value=previous_value,
            new_value=new_value,
            note=save_data.reason,
            actor_type=actor_type,
            actor_id=actor_id,
        )
    db.commit()
    for criterion in saved:
        db.refresh(criterion)
    return saved


@router.patch(
    "/{criterion_id}",
    response_model=AcceptanceCriterionRead,
)
def update_acceptance_criterion(
    ticket_id: int,
    criterion_id: int,
    criterion_data: AcceptanceCriterionUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)
    criterion = db.get(AcceptanceCriterion, criterion_id)

    if criterion is None or criterion.ticket_id != ticket_id:
        raise HTTPException(
            status_code=404,
            detail="Acceptance criterion not found",
        )

    updates = criterion_data.model_dump(exclude_unset=True)
    reason = updates.pop("reason", None)
    if "deferred" in updates and updates["deferred"] != criterion.deferred and not reason:
        raise HTTPException(status_code=422, detail="A reason is required to defer or restore scope.")
    previous_value = {
        "id": criterion.id,
        "text": criterion.text,
        "completed": criterion.completed,
        "deferred": criterion.deferred,
        "deferred_reason": criterion.deferred_reason,
    }

    for field, value in updates.items():
        setattr(criterion, field, value)

    if criterion.deferred:
        criterion.completed = False
        criterion.deferred_at = criterion.deferred_at or utc_now()
        criterion.deferred_reason = reason or criterion.deferred_reason
    else:
        criterion.deferred_at = None
        criterion.deferred_reason = None

    if criterion.completed and criterion.completed_at is None:
        criterion.completed_at = utc_now()

    if not criterion.completed:
        criterion.completed_at = None

    new_value = {
        "id": criterion.id,
        "text": criterion.text,
        "completed": criterion.completed,
        "deferred": criterion.deferred,
        "deferred_reason": criterion.deferred_reason,
    }
    if previous_value != new_value:
        add_ticket_activity_event(
            db,
            ticket_id=ticket_id,
            event_type="acceptance_criterion_updated",
            previous_value=previous_value,
            new_value=new_value,
            note=reason,
            actor_type=actor_type,
            actor_id=actor_id,
        )

    db.commit()
    db.refresh(criterion)

    return criterion


@router.delete("/{criterion_id}", status_code=204)
def delete_acceptance_criterion(
    ticket_id: int,
    criterion_id: int,
    reason: str = Query(min_length=1, max_length=2000),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)
    criterion = db.get(AcceptanceCriterion, criterion_id)

    if criterion is None or criterion.ticket_id != ticket_id:
        raise HTTPException(
            status_code=404,
            detail="Acceptance criterion not found",
        )

    add_ticket_activity_event(
        db,
        ticket_id=ticket_id,
        event_type="acceptance_criterion_removed",
        previous_value=acceptance_criterion_activity_snapshot(criterion),
        note=reason,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    db.delete(criterion)
    db.commit()
