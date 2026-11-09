"""Create immutable activity snapshots and assemble the unified ticket timeline."""

from enum import Enum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.subtask import Subtask
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket import Ticket
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_attachment import TicketUpdateAttachment
from app.models.ticket_update_entry import TicketUpdateEntry
from app.models.user import User
from app.schemas.ticket import TicketActivityItemRead


def activity_value(value: Any) -> Any:
    """Convert domain values into JSON-safe activity snapshots."""
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {key: activity_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [activity_value(item) for item in value]

    return value


def acceptance_criterion_activity_snapshot(
    criterion: AcceptanceCriterion,
) -> dict[str, Any]:
    """Return the user-meaningful criterion state for an immutable event."""
    return {
        "id": criterion.id,
        "text": criterion.text,
        "completed": criterion.completed,
        "deferred": criterion.deferred,
        "deferred_reason": criterion.deferred_reason,
        "sort_order": criterion.sort_order,
    }


def subtask_activity_snapshot(subtask: Subtask) -> dict[str, Any]:
    """Return the user-meaningful subtask state for an immutable event."""
    return {
        "id": subtask.id,
        "title": subtask.title,
        "description": subtask.description,
        "status": subtask.status,
        "deferred_reason": subtask.deferred_reason,
        "sort_order": subtask.sort_order,
    }


def add_ticket_activity_event(
    db: Session,
    *,
    ticket_id: int,
    event_type: str,
    field_name: str | None = None,
    previous_value: Any = None,
    new_value: Any = None,
    note: str | None = None,
    actor_type: str = "local_user",
    actor_id: str | None = None,
) -> TicketActivityEvent:
    """Stage an activity event in the caller's ticket-change transaction."""
    activity_event = TicketActivityEvent(
        ticket_id=ticket_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        field_name=field_name,
        previous_value=activity_value(previous_value),
        new_value=activity_value(new_value),
        note=note,
    )
    db.add(activity_event)
    return activity_event


def apply_audited_ticket_field(
    db: Session,
    *,
    ticket: Ticket,
    field_name: str,
    new_value: Any,
    note: str | None = None,
    actor_type: str = "local_user",
    actor_id: str | None = None,
) -> TicketActivityEvent | None:
    """Apply one actual ticket-field change and stage its audit event."""
    previous_value = getattr(ticket, field_name)
    if previous_value == new_value:
        return None

    activity_event = add_ticket_activity_event(
        db,
        ticket_id=ticket.id,
        event_type="ticket_field_changed",
        field_name=field_name,
        previous_value=previous_value,
        new_value=new_value,
        note=note,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    setattr(ticket, field_name, new_value)
    return activity_event


def list_ticket_activity(
    db: Session,
    *,
    ticket_id: int,
) -> list[TicketActivityItemRead]:
    """Combine authoritative activity sources without duplicating their content."""
    automatic_events = db.scalars(
        select(TicketActivityEvent).where(
            TicketActivityEvent.ticket_id == ticket_id
        )
    ).all()
    actor_user_ids = {
        int(event.actor_id)
        for event in automatic_events
        if event.actor_type == "user" and event.actor_id and event.actor_id.isdigit()
    }
    grouped_status_event_ids = {
        event.new_value.get("status_event_id")
        for event in automatic_events
        if event.event_type == "drawer_session_committed"
        and isinstance(event.new_value, dict)
        and event.new_value.get("status_event_id") is not None
    }
    grouped_activity_event_ids = {
        event_id
        for event in automatic_events
        if event.event_type == "ai_review_applied"
        and isinstance(event.new_value, dict)
        for event_id in event.new_value.get("activity_event_ids", [])
    }
    status_events = db.scalars(
        select(TicketStatusEvent).where(TicketStatusEvent.ticket_id == ticket_id)
    ).all()
    update_rows = db.execute(
        select(
            TicketUpdateEntry,
            func.count(TicketUpdateAttachment.id).label("attachment_count"),
        )
        .outerjoin(TicketUpdateAttachment)
        .where(TicketUpdateEntry.ticket_id == ticket_id)
        .group_by(TicketUpdateEntry.id)
    ).all()
    actor_user_ids.update(
        event.actor_user_id for event in status_events if event.actor_user_id is not None
    )
    actor_user_ids.update(
        entry.actor_user_id for entry, _ in update_rows if entry.actor_user_id is not None
    )
    actor_names = {
        user.id: user.display_name
        for user in db.scalars(select(User).where(User.id.in_(actor_user_ids))).all()
    } if actor_user_ids else {}

    items = [
        TicketActivityItemRead(
            source_type="activity_event",
            source_id=event.id,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            actor_name=(
                actor_names.get(int(event.actor_id))
                if event.actor_type == "user" and event.actor_id and event.actor_id.isdigit()
                else None
            ),
            field_name=event.field_name,
            previous_value=event.previous_value,
            new_value=event.new_value,
            note=event.note,
            created_at=event.created_at,
        )
        for event in automatic_events
        # Status transitions already have an authoritative, append-only source.
        # Early foundation events may contain a duplicate status field change;
        # keep it stored for audit integrity but omit it from the unified view.
        if event.field_name != "status"
        and event.id not in grouped_activity_event_ids
    ]
    items.extend(
        TicketActivityItemRead(
            source_type="status_event",
            source_id=event.id,
            event_type="status_changed",
            actor_type="user" if event.actor_user_id is not None else "local_user",
            actor_id=str(event.actor_user_id) if event.actor_user_id is not None else None,
            actor_name=actor_names.get(event.actor_user_id),
            field_name="status",
            previous_value=event.from_status,
            new_value=event.to_status,
            note=event.note,
            created_at=event.created_at,
        )
        for event in status_events
        if event.id not in grouped_status_event_ids
    )
    items.extend(
        TicketActivityItemRead(
            source_type="ticket_update",
            source_id=entry.id,
            event_type="ticket_update_added",
            actor_type="user" if entry.actor_user_id is not None else "local_user",
            actor_id=str(entry.actor_user_id) if entry.actor_user_id is not None else None,
            actor_name=actor_names.get(entry.actor_user_id),
            content=entry.content,
            attachment_count=attachment_count,
            created_at=entry.created_at,
        )
        for entry, attachment_count in update_rows
    )

    return sorted(
        items,
        key=lambda item: (item.created_at, item.source_type, item.source_id),
        reverse=True,
    )
