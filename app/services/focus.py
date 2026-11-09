"""Own Current Focus eligibility and preference mutation across Telaryn surfaces."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.models.ticket import Ticket, TicketStatus
from app.services.my_work import effective_availability


FOCUS_ELIGIBLE_STATUSES = {TicketStatus.READY, TicketStatus.IN_PROGRESS}


def require_focus_eligible(ticket: Ticket, *, workspace_id: int) -> None:
    """Reject focus changes that cross a workspace or target inactive workflow state."""
    if ticket.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    if ticket.project is not None and ticket.project.archived_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Tickets in archived Projects cannot become Current Focus.",
        )
    if ticket.status not in FOCUS_ELIGIBLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Only Ready or In Progress Tickets can become Current Focus.",
        )


def focus_ticket(
    db: Session,
    *,
    ticket: Ticket,
    workspace_id: int,
    user_id: int,
    make_available: bool = False,
) -> int | None:
    """Set one user-scoped focus without changing authoritative Ticket state."""
    require_focus_eligible(ticket, workspace_id=workspace_id)
    preference = db.scalar(
        select(MyWorkPreference).where(
            MyWorkPreference.user_id == user_id,
            MyWorkPreference.workspace_id == workspace_id,
            MyWorkPreference.ticket_id == ticket.id,
        )
    )
    mode, _available_on = effective_availability(
        ticket,
        preference,
        today=utc_now().date(),
    )
    if mode != FocusAvailabilityMode.AVAILABLE and not make_available:
        raise HTTPException(
            status_code=409,
            detail=(
                "This Ticket is intentionally unavailable. "
                "Use Make Available and Focus to continue."
            ),
        )

    previous = db.scalar(
        select(MyWorkPreference).where(
            MyWorkPreference.user_id == user_id,
            MyWorkPreference.workspace_id == workspace_id,
            MyWorkPreference.is_current_focus.is_(True),
        )
    )
    if previous is not None and previous.ticket_id == ticket.id:
        return previous.ticket_id

    db.execute(
        update(MyWorkPreference)
        .where(
            MyWorkPreference.user_id == user_id,
            MyWorkPreference.workspace_id == workspace_id,
        )
        .values(is_current_focus=False)
    )
    if preference is None:
        preference = MyWorkPreference(
            user_id=user_id,
            workspace_id=workspace_id,
            ticket_id=ticket.id,
        )
        db.add(preference)

    preference.is_current_focus = True
    # Expired date/context restrictions are no longer active. An explicit
    # Make Available and Focus action also clears a still-active restriction.
    preference.availability_mode = FocusAvailabilityMode.AVAILABLE
    preference.available_on = None
    preference.context_ticket_updated_at = None
    return previous.ticket_id if previous is not None else None


def clear_all_current_focus(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
) -> None:
    """Clear the user-scoped focus slot without changing Ticket workflow state."""
    db.execute(
        update(MyWorkPreference)
        .where(
            MyWorkPreference.user_id == user_id,
            MyWorkPreference.workspace_id == workspace_id,
        )
        .values(is_current_focus=False)
    )


def clear_current_focus(
    db: Session,
    *,
    ticket_id: int,
    workspace_id: int,
    user_id: int,
) -> None:
    """Clear a matching focus without affecting any Ticket workflow fields."""
    preference = db.scalar(
        select(MyWorkPreference).where(
            MyWorkPreference.user_id == user_id,
            MyWorkPreference.workspace_id == workspace_id,
            MyWorkPreference.ticket_id == ticket_id,
        )
    )
    if preference is not None:
        preference.is_current_focus = False

