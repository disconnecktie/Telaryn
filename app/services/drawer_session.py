"""Apply a reviewed drawer session and one grouped activity record atomically."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket
from app.models.ticket_update_entry import TicketUpdateEntry
from app.models.ticket_status_event import TicketStatusEvent
from app.schemas.drawer_session import DrawerSessionCommit
from app.services.ticket_activity import (
    acceptance_criterion_activity_snapshot,
    activity_value,
    add_ticket_activity_event,
    subtask_activity_snapshot,
)
from app.services.workspaces import require_active_ticket, require_assignable_project


def _ticket_snapshot(ticket: Ticket) -> dict:
    return activity_value({
        "title": ticket.title,
        "description": ticket.description,
        "priority": ticket.priority,
        "ticket_type": ticket.ticket_type,
        "status": ticket.status,
        "project_id": ticket.project_id,
        "ai_context_enabled": ticket.ai_context_enabled,
    })


def commit_drawer_session(
    db: Session,
    *,
    ticket: Ticket,
    commit: DrawerSessionCommit,
    workspace_id: int | None = None,
    actor_type: str = "local_user",
    actor_id: str | None = None,
    actor_user_id: int | None = None,
) -> tuple[Ticket, list[AcceptanceCriterion], list[Subtask]]:
    """Apply the reviewed drawer state and its audit record in one transaction."""
    effective_workspace_id = workspace_id or ticket.workspace_id
    require_active_ticket(ticket)
    if commit.ticket.project_id is not None:
        require_assignable_project(
            db,
            workspace_id=effective_workspace_id,
            project_id=commit.ticket.project_id,
        )

    criteria = list(db.scalars(select(AcceptanceCriterion).where(
        AcceptanceCriterion.ticket_id == ticket.id
    ).order_by(AcceptanceCriterion.sort_order, AcceptanceCriterion.id)).all())
    subtasks = list(db.scalars(select(Subtask).where(
        Subtask.ticket_id == ticket.id
    ).order_by(Subtask.sort_order, Subtask.id)).all())
    criteria_by_id = {item.id: item for item in criteria}
    subtasks_by_id = {item.id: item for item in subtasks}
    criterion_ids = [item.id for item in commit.acceptance_criteria if item.id is not None]
    subtask_ids = [item.id for item in commit.subtasks if item.id is not None]
    if len(criterion_ids) != len(set(criterion_ids)) or any(item_id not in criteria_by_id for item_id in criterion_ids):
        raise HTTPException(status_code=422, detail="Invalid acceptance criterion list.")
    if len(subtask_ids) != len(set(subtask_ids)) or any(item_id not in subtasks_by_id for item_id in subtask_ids):
        raise HTTPException(status_code=422, detail="Invalid subtask list.")

    previous = {
        "ticket": _ticket_snapshot(ticket),
        "acceptance_criteria": [acceptance_criterion_activity_snapshot(item) for item in criteria],
        "subtasks": [subtask_activity_snapshot(item) for item in subtasks],
    }
    previous_status = ticket.status
    requested_status = commit.ticket.status
    # A transferred progress draft becomes one append-only update in this same
    # transaction. Its text can satisfy required scope/status context without
    # creating a second, redundant drawer-activity narrative.
    effective_note = commit.note or commit.update_content

    # Scope decisions must never disappear behind a checkbox or delete action.
    # One human-authored session note explains every defer, restore, or removal
    # committed atomically in this drawer update.
    scope_state_changed = (
        bool(set(criteria_by_id) - set(criterion_ids))
        or bool(set(subtasks_by_id) - set(subtask_ids))
        or any(
            draft.id is not None
            and criteria_by_id[draft.id].deferred != draft.deferred
            for draft in commit.acceptance_criteria
        )
        or any(
            draft.id is not None
            and (
                subtasks_by_id[draft.id].status == SubtaskStatus.DEFERRED
            ) != (draft.status == SubtaskStatus.DEFERRED)
            for draft in commit.subtasks
        )
    )
    if scope_state_changed and not effective_note:
        raise HTTPException(
            status_code=422,
            detail="An update note is required for deferred, restored, or removed scope.",
        )

    if requested_status != previous_status:
        note_required = requested_status.value in {"blocked", "cancelled"}
        if requested_status.value == "done":
            note_required = (
                any(
                    not item.completed and not item.deferred
                    for item in commit.acceptance_criteria
                )
                or any(
                    item.status not in {
                        SubtaskStatus.DONE,
                        SubtaskStatus.CANCELLED,
                        SubtaskStatus.DEFERRED,
                    }
                    for item in commit.subtasks
                )
            )
        if note_required and not effective_note:
            raise HTTPException(
                status_code=422,
                detail="An update note is required for this status change.",
            )

    for field, value in commit.ticket.model_dump().items():
        setattr(ticket, field, value)

    if commit.update_content:
        db.add(TicketUpdateEntry(
            ticket_id=ticket.id,
            content=commit.update_content,
            actor_user_id=actor_user_id,
        ))
        ticket.updated_at = utc_now()

    status_event = None
    if requested_status != previous_status:
        status_event = TicketStatusEvent(
            ticket_id=ticket.id,
            from_status=previous_status.value,
            to_status=requested_status.value,
            note=effective_note,
            actor_user_id=actor_user_id,
        )
        db.add(status_event)

    saved_criteria = []
    for order, draft in enumerate(commit.acceptance_criteria, start=1):
        item = criteria_by_id.get(draft.id) if draft.id is not None else None
        if item is None:
            item = AcceptanceCriterion(ticket_id=ticket.id)
            db.add(item)
        was_deferred = item.deferred
        item.text = draft.text
        item.completed = draft.completed and not draft.deferred
        item.deferred = draft.deferred
        item.sort_order = order
        item.completed_at = utc_now() if item.completed and item.completed_at is None else item.completed_at
        if not item.completed:
            item.completed_at = None
        if item.deferred:
            item.deferred_at = item.deferred_at or utc_now()
            if not was_deferred:
                item.deferred_reason = effective_note
        else:
            item.deferred_at = None
            item.deferred_reason = None
        saved_criteria.append(item)
    for item in criteria:
        if item.id not in criterion_ids:
            db.delete(item)

    saved_subtasks = []
    for order, draft in enumerate(commit.subtasks, start=1):
        item = subtasks_by_id.get(draft.id) if draft.id is not None else None
        if item is None:
            item = Subtask(ticket_id=ticket.id)
            db.add(item)
        was_deferred = item.status == SubtaskStatus.DEFERRED
        item.title = draft.title
        item.description = draft.description
        item.status = draft.status
        item.sort_order = order
        item.completed_at = utc_now() if draft.status == SubtaskStatus.DONE and item.completed_at is None else item.completed_at
        if draft.status != SubtaskStatus.DONE:
            item.completed_at = None
        if draft.status == SubtaskStatus.DEFERRED:
            item.deferred_at = item.deferred_at or utc_now()
            if not was_deferred:
                item.deferred_reason = effective_note
        else:
            item.deferred_at = None
            item.deferred_reason = None
        saved_subtasks.append(item)
    for item in subtasks:
        if item.id not in subtask_ids:
            db.delete(item)

    db.flush()
    current = {
        "ticket": _ticket_snapshot(ticket),
        "acceptance_criteria": [acceptance_criterion_activity_snapshot(item) for item in saved_criteria],
        "subtasks": [subtask_activity_snapshot(item) for item in saved_subtasks],
    }
    if status_event is not None:
        current["status_event_id"] = status_event.id
    if previous != current:
        add_ticket_activity_event(
            db,
            ticket_id=ticket.id,
            event_type="drawer_session_committed",
            previous_value=previous,
            new_value=current,
            note=effective_note if not commit.update_content else None,
            actor_type=actor_type,
            actor_id=actor_id,
        )
    return ticket, saved_criteria, saved_subtasks
