"""Build a trustworthy project snapshot from Telaryn's authoritative work data."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.time import as_utc, utc_now
from app.models.subtask import SubtaskStatus
from app.models.ticket import Ticket, TicketStatus
from app.schemas.project import (
    ProjectAttentionTicket,
    ProjectHistoryEntry,
    ProjectProgressCounts,
    ProjectTicketCounts,
    ProjectWorkOverviewRead,
)

ACTIVE_STATUSES = {TicketStatus.READY, TicketStatus.IN_PROGRESS, TicketStatus.BLOCKED, TicketStatus.REVIEW}


def _status_summary(to_status: str) -> str:
    return {
        TicketStatus.DONE.value: "Ticket completed",
        TicketStatus.CANCELLED.value: "Ticket cancelled",
        TicketStatus.BLOCKED.value: "Ticket blocked",
    }.get(to_status, f"Status changed to {to_status.replace("_", " ").title()}")


def _drawer_session_summary(event: object) -> str:
    previous = getattr(event, "previous_value", None)
    current = getattr(event, "new_value", None)
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return "Ticket updated"

    previous_ticket = previous.get("ticket", {})
    current_ticket = current.get("ticket", {})
    if (
        isinstance(previous_ticket, dict)
        and isinstance(current_ticket, dict)
        and previous_ticket.get("status") != current_ticket.get("status")
        and current_ticket.get("status")
    ):
        return _status_summary(current_ticket["status"])

    if (
        previous.get("acceptance_criteria") != current.get("acceptance_criteria")
        or previous.get("subtasks") != current.get("subtasks")
    ):
        return "Scope updated"

    return "Ticket updated"


def _activity_summary(event: object) -> str:
    event_type = getattr(event, "event_type")
    if event_type == "ticket_created":
        return "Ticket created"
    if event_type == "drawer_session_committed":
        return _drawer_session_summary(event)
    if event_type == "ai_review_applied":
        return "Telaryn suggestions applied"
    if event_type == "ticket_field_changed":
        field_name = getattr(event, "field_name", None)
        if field_name == "status":
            return _status_summary(str(getattr(event, "new_value", "")))
        return {
            "title": "Title changed",
            "description": "Description changed",
            "priority": "Priority changed",
            "ticket_type": "Ticket type changed",
            "project_id": "Project changed",
        }.get(field_name, "Ticket updated")
    return "Ticket updated"


def _history_for_ticket(ticket: Ticket) -> list[ProjectHistoryEntry]:
    entries: list[ProjectHistoryEntry] = []
    for update in ticket.update_entries:
        entries.append(ProjectHistoryEntry(ticket_id=ticket.id, workspace_ticket_number=ticket.workspace_ticket_number, ticket_title=ticket.title, ticket_status=ticket.status, occurred_at=update.created_at, event_type="update", summary="Update added", actor="You"))
    for status_event in ticket.status_events:
        entries.append(ProjectHistoryEntry(ticket_id=ticket.id, workspace_ticket_number=ticket.workspace_ticket_number, ticket_title=ticket.title, ticket_status=ticket.status, occurred_at=status_event.created_at, event_type="ticket_status_changed", summary=_status_summary(status_event.to_status), actor="You"))
    for event in ticket.activity_events:
        entries.append(ProjectHistoryEntry(ticket_id=ticket.id, workspace_ticket_number=ticket.workspace_ticket_number, ticket_title=ticket.title, ticket_status=ticket.status, occurred_at=event.created_at, event_type=event.event_type, summary=_activity_summary(event), actor="You"))
    return entries

def build_project_work_overview(
    project_id: int,
    db: Session,
    *,
    now: datetime | None = None,
    stale_after_days: int = 14,
    exclude_private_tickets: bool = False,
) -> ProjectWorkOverviewRead:
    """Aggregate project health, optionally excluding Private Ticket data for AI."""
    generated_at = as_utc(now) or utc_now()
    stale_before = generated_at - timedelta(days=stale_after_days)
    statement = select(Ticket).where(Ticket.project_id == project_id)
    if exclude_private_tickets:
        statement = statement.where(Ticket.ai_context_enabled.is_(True))
    tickets = list(db.scalars(statement.options(
        selectinload(Ticket.acceptance_criteria), selectinload(Ticket.subtasks),
        selectinload(Ticket.activity_events), selectinload(Ticket.status_events), selectinload(Ticket.update_entries),
    ).order_by(Ticket.updated_at.asc(), Ticket.id.asc())).all())
    status_counts = {status: 0 for status in TicketStatus}
    criterion_total = criterion_completed = criterion_deferred = 0
    subtask_total = subtask_completed = subtask_deferred = 0
    attention: list[ProjectAttentionTicket] = []
    history: list[ProjectHistoryEntry] = []

    for ticket in tickets:
        status_counts[ticket.status] += 1
        history.extend(_history_for_ticket(ticket))
        active_criteria = [item for item in ticket.acceptance_criteria if not item.deferred]
        deferred_criteria = [item for item in ticket.acceptance_criteria if item.deferred]
        active_subtasks = [item for item in ticket.subtasks if item.status not in {SubtaskStatus.DEFERRED, SubtaskStatus.CANCELLED}]
        deferred_subtasks = [item for item in ticket.subtasks if item.status == SubtaskStatus.DEFERRED]
        criterion_total += len(active_criteria); criterion_completed += sum(item.completed for item in active_criteria); criterion_deferred += len(deferred_criteria)
        subtask_total += len(active_subtasks); subtask_completed += sum(item.status == SubtaskStatus.DONE for item in active_subtasks); subtask_deferred += len(deferred_subtasks)
        if ticket.status not in ACTIVE_STATUSES: continue
        reasons = []
        if ticket.status == TicketStatus.BLOCKED:
            reasons.append("Blocked")
        if (
            ticket.status == TicketStatus.IN_PROGRESS
            and ticket.updated_at < stale_before
        ):
            reasons.append(f"No activity in {stale_after_days}+ days")
        if reasons: attention.append(ProjectAttentionTicket(id=ticket.id, workspace_ticket_number=ticket.workspace_ticket_number, title=ticket.title, status=ticket.status, priority=ticket.priority, updated_at=ticket.updated_at, reasons=reasons))

    attention.sort(key=lambda item: ("Blocked" not in item.reasons, item.updated_at, item.id))
    history.sort(key=lambda item: item.occurred_at, reverse=True)
    # Keep the history scan useful: one latest entry per ticket.
    latest_history_by_ticket: dict[int, ProjectHistoryEntry] = {}
    for entry in history:
        latest_history_by_ticket.setdefault(entry.ticket_id, entry)
    recent_history = sorted(
        latest_history_by_ticket.values(),
        key=lambda item: item.occurred_at,
        reverse=True,
    )
    return ProjectWorkOverviewRead(project_id=project_id, generated_at=generated_at,
        tickets=ProjectTicketCounts(total=len(tickets), active=sum(status_counts[status] for status in ACTIVE_STATUSES), **{status.value: count for status, count in status_counts.items()}),
        acceptance_criteria=ProjectProgressCounts(completed=criterion_completed, total=criterion_total, deferred=criterion_deferred),
        subtasks=ProjectProgressCounts(completed=subtask_completed, total=subtask_total, deferred=subtask_deferred),
        attention=attention, recent_history=recent_history[:6])
