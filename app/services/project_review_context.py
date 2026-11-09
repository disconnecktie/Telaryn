"""Assemble authorized, bounded Project Review context without invoking a provider."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.time import as_utc, utc_now
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.models.project import Project
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry
from app.schemas.project_review import (
    ProjectReviewActivityContext,
    ProjectReviewAvailabilityContext,
    ProjectReviewContextPolicy,
    ProjectReviewCriterionContext,
    ProjectReviewProjectContext,
    ProjectReviewSnapshotRead,
    ProjectReviewSubtaskContext,
    ProjectReviewTicketContext,
    ProjectReviewUpdateContext,
)
from app.services.project_work_overview import build_project_work_overview


TERMINAL_STATUSES = {TicketStatus.DONE, TicketStatus.CANCELLED}
DEFAULT_RECENT_ACTIVITY_LIMIT = 20


def list_private_ticket_exclusions(
    project: Project,
    *,
    workspace_id: int,
    db: Session,
) -> list[dict[str, int | str]]:
    """Return local-only labels for tickets deliberately absent from AI context."""
    return [
        {"id": ticket.id, "title": ticket.title}
        for ticket in db.scalars(
            select(Ticket)
            .where(
                Ticket.project_id == project.id,
                Ticket.workspace_id == workspace_id,
                Ticket.ai_context_enabled.is_(False),
            )
            .order_by(Ticket.id.asc())
        ).all()
    ]


def _compact_text(value: str | None, *, fallback: str) -> str:
    """Keep activity evidence meaningful without copying complete historical records."""
    cleaned = " ".join((value or "").split())
    if not cleaned:
        return fallback
    return cleaned if len(cleaned) <= 240 else f"{cleaned[:237]}..."


def _recent_activity(
    db: Session,
    *,
    active_tickets: list[Ticket],
    limit: int,
) -> list[ProjectReviewActivityContext]:
    """Combine compact active-ticket activity evidence and apply one project-wide bound."""
    if not active_tickets or limit <= 0:
        return []

    ticket_by_id = {ticket.id: ticket for ticket in active_tickets}
    ticket_ids = list(ticket_by_id)
    items: list[ProjectReviewActivityContext] = []

    activity_events = db.scalars(
        select(TicketActivityEvent).where(TicketActivityEvent.ticket_id.in_(ticket_ids))
    ).all()
    for event in activity_events:
        ticket = ticket_by_id[event.ticket_id]
        fallback = (
            f"{event.field_name.replace('_', ' ').title()} changed"
            if event.field_name
            else event.event_type.replace("_", " ").title()
        )
        items.append(
            ProjectReviewActivityContext(
                ticket_id=ticket.id,
                ticket_title=ticket.title,
                source_type="activity_event",
                source_id=event.id,
                summary=_compact_text(event.note, fallback=fallback),
                occurred_at=event.created_at,
            )
        )

    status_events = db.scalars(
        select(TicketStatusEvent).where(TicketStatusEvent.ticket_id.in_(ticket_ids))
    ).all()
    for event in status_events:
        ticket = ticket_by_id[event.ticket_id]
        items.append(
            ProjectReviewActivityContext(
                ticket_id=ticket.id,
                ticket_title=ticket.title,
                source_type="status_event",
                source_id=event.id,
                summary=_compact_text(
                    event.note,
                    fallback=f"Status changed from {event.from_status} to {event.to_status}",
                ),
                occurred_at=event.created_at,
            )
        )

    update_entries = db.scalars(
        select(TicketUpdateEntry).where(TicketUpdateEntry.ticket_id.in_(ticket_ids))
    ).all()
    for entry in update_entries:
        ticket = ticket_by_id[entry.ticket_id]
        items.append(
            ProjectReviewActivityContext(
                ticket_id=ticket.id,
                ticket_title=ticket.title,
                source_type="ticket_update",
                source_id=entry.id,
                summary="Meaningful ticket update recorded",
                occurred_at=entry.created_at,
            )
        )

    items.sort(
        key=lambda item: (item.occurred_at, item.source_type, item.source_id),
        reverse=True,
    )
    return items[:limit]


def _snapshot_version(snapshot: ProjectReviewSnapshotRead) -> str:
    """Hash authoritative snapshot content while excluding request-time metadata."""
    content = snapshot.model_dump(mode="json")
    content.pop("snapshot_version", None)
    content.pop("generated_at", None)
    content["work_overview"].pop("generated_at", None)
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def build_project_review_snapshot(
    project: Project,
    *,
    workspace_id: int,
    user_id: int,
    db: Session,
    now: datetime | None = None,
    recent_activity_limit: int = DEFAULT_RECENT_ACTIVITY_LIMIT,
) -> ProjectReviewSnapshotRead:
    """Build one deterministic review snapshot from authorized project records."""
    generated_at = as_utc(now) or utc_now()
    tickets = list(
        db.scalars(
            select(Ticket)
            .where(
                Ticket.project_id == project.id,
                Ticket.workspace_id == workspace_id,
                Ticket.ai_context_enabled.is_(True),
            )
            .options(
                selectinload(Ticket.acceptance_criteria),
                selectinload(Ticket.subtasks),
                selectinload(Ticket.update_entries),
            )
            .order_by(Ticket.id.asc())
        ).all()
    )
    ticket_ids = [ticket.id for ticket in tickets]
    preferences = {
        preference.ticket_id: preference
        for preference in (
            db.scalars(
                select(MyWorkPreference).where(
                    MyWorkPreference.workspace_id == workspace_id,
                    MyWorkPreference.user_id == user_id,
                    MyWorkPreference.ticket_id.in_(ticket_ids),
                )
            ).all()
            if ticket_ids
            else []
        )
    }

    ticket_context: list[ProjectReviewTicketContext] = []
    active_tickets: list[Ticket] = []
    current_focus_ticket_id: int | None = None

    for ticket in tickets:
        preference = preferences.get(ticket.id)
        detail_included = ticket.status not in TERMINAL_STATUSES
        if detail_included:
            active_tickets.append(ticket)
        if preference and preference.is_current_focus:
            current_focus_ticket_id = ticket.id

        latest_update = None
        if detail_included and ticket.update_entries:
            entry = max(
                ticket.update_entries,
                key=lambda item: (item.created_at, item.id),
            )
            latest_update = ProjectReviewUpdateContext(
                id=entry.id,
                content=entry.content,
                created_at=entry.created_at,
            )

        ticket_context.append(
            ProjectReviewTicketContext(
                id=ticket.id,
                title=ticket.title,
                description=ticket.description if detail_included else None,
                status=ticket.status,
                priority=ticket.priority,
                ticket_type=ticket.ticket_type,
                updated_at=ticket.updated_at,
                detail_included=detail_included,
                acceptance_criteria=(
                    [
                        ProjectReviewCriterionContext(
                            id=item.id,
                            text=item.text,
                            completed=item.completed,
                            deferred=item.deferred,
                            deferred_reason=item.deferred_reason,
                            sort_order=item.sort_order,
                            updated_at=item.updated_at,
                        )
                        for item in sorted(
                            ticket.acceptance_criteria,
                            key=lambda item: (item.sort_order, item.id),
                        )
                    ]
                    if detail_included
                    else []
                ),
                subtasks=(
                    [
                        ProjectReviewSubtaskContext(
                            id=item.id,
                            title=item.title,
                            description=item.description,
                            status=item.status,
                            deferred_reason=item.deferred_reason,
                            sort_order=item.sort_order,
                            updated_at=item.updated_at,
                        )
                        for item in sorted(
                            ticket.subtasks,
                            key=lambda item: (item.sort_order, item.id),
                        )
                    ]
                    if detail_included
                    else []
                ),
                latest_update=latest_update,
                availability=ProjectReviewAvailabilityContext(
                    mode=(
                        preference.availability_mode
                        if preference
                        else FocusAvailabilityMode.AVAILABLE
                    ),
                    available_on=preference.available_on if preference else None,
                    is_current_focus=bool(preference and preference.is_current_focus),
                ),
            )
        )

    snapshot = ProjectReviewSnapshotRead(
        project=ProjectReviewProjectContext(
            id=project.id,
            name=project.name,
            description=project.description,
            purpose=project.purpose,
            why_it_matters=project.why_it_matters,
            target_date=project.target_date,
            updated_at=project.updated_at,
        ),
        snapshot_version="pending",
        generated_at=generated_at,
        work_overview=build_project_work_overview(
            project.id,
            db,
            now=generated_at,
            exclude_private_tickets=True,
        ),
        current_focus_ticket_id=current_focus_ticket_id,
        tickets=ticket_context,
        recent_activity=_recent_activity(
            db,
            active_tickets=active_tickets,
            limit=recent_activity_limit,
        ),
        context_policy=ProjectReviewContextPolicy(
            recent_activity_limit=recent_activity_limit,
        ),
    )
    return snapshot.model_copy(update={"snapshot_version": _snapshot_version(snapshot)})
