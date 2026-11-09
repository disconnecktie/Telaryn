"""Turn private workspace tickets into a deterministic, user-directed focus stack."""

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.time import as_utc, utc_now
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.models.subtask import SubtaskStatus
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.schemas.my_work import (
    MyWorkItem,
    MyWorkNextAction,
    MyWorkProgress,
    MyWorkRead,
)


PRIORITY_ORDER = {
    TicketPriority.CRITICAL: 0,
    TicketPriority.HIGH: 1,
    TicketPriority.MEDIUM: 2,
    TicketPriority.LOW: 3,
}
ACTIVE_TICKET_STATUSES = {TicketStatus.READY, TicketStatus.IN_PROGRESS}


def _sort_key(item: MyWorkItem) -> tuple[int, float, int]:
    return (PRIORITY_ORDER[item.priority], -item.updated_at.timestamp(), item.id)


def _recommendation_sort_key(item: MyWorkItem) -> tuple[int, int, date, float, int]:
    """Prefer resumable work, then urgency, explicit dates, and recent context."""
    return (
        0 if item.status == TicketStatus.IN_PROGRESS else 1,
        PRIORITY_ORDER[item.priority],
        item.project_target_date or date.max,
        -item.updated_at.timestamp(),
        item.id,
    )


def _attention_sort_key(item: MyWorkItem) -> tuple[int, int, float, int]:
    if "Blocked" in item.reasons:
        reason_order = 0
    elif any(reason.startswith("No activity") for reason in item.reasons):
        reason_order = 1
    else:
        reason_order = 2
    return (reason_order, *_sort_key(item))


def ticket_context_updated_at(ticket: Ticket) -> datetime:
    """Capture changes that can materially alter whether a ticket is actionable."""
    timestamps = [ticket.updated_at]
    if ticket.project is not None:
        timestamps.append(ticket.project.updated_at)
    timestamps.extend(item.updated_at for item in ticket.acceptance_criteria)
    timestamps.extend(item.updated_at for item in ticket.subtasks)
    normalized = [as_utc(value) for value in timestamps]
    return max(value for value in normalized if value is not None)


def effective_availability(
    ticket: Ticket,
    preference: MyWorkPreference | None,
    today: date,
) -> tuple[FocusAvailabilityMode, date | None]:
    if preference is None:
        return FocusAvailabilityMode.AVAILABLE, None
    if preference.availability_mode == FocusAvailabilityMode.DATE:
        if preference.available_on is None or preference.available_on <= today:
            return FocusAvailabilityMode.AVAILABLE, None
    if preference.availability_mode == FocusAvailabilityMode.CONTEXT_CHANGE:
        snapshot = preference.context_ticket_updated_at
        if snapshot is None or ticket_context_updated_at(ticket) > as_utc(snapshot):
            return FocusAvailabilityMode.AVAILABLE, None
    return preference.availability_mode, preference.available_on


def _next_action(ticket: Ticket) -> MyWorkNextAction | None:
    actionable = [
        item
        for item in ticket.subtasks
        if item.status in {SubtaskStatus.IN_PROGRESS, SubtaskStatus.TODO}
    ]
    actionable.sort(
        key=lambda item: (
            0 if item.status == SubtaskStatus.IN_PROGRESS else 1,
            item.sort_order,
            item.id,
        )
    )
    if not actionable:
        return None
    item = actionable[0]
    return MyWorkNextAction(subtask_id=item.id, title=item.title, status=item.status)


def _bounded_ticket_context(value: str | None, limit: int = 240) -> str | None:
    """Keep authored Ticket context useful without turning focus into a detail view."""
    if not value:
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    if len(compact) > limit:
        compact = compact[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    elif compact[-1] not in ".!?":
        compact += "."
    return compact


def _focus_rationale(
    ticket: Ticket,
    criteria: MyWorkProgress,
    subtasks: MyWorkProgress,
    next_action: MyWorkNextAction | None,
) -> str:
    """Explain why focused work deserves attention using only Ticket state."""
    if ticket.status == TicketStatus.IN_PROGRESS:
        state = "Work is already underway."
    elif ticket.status == TicketStatus.READY:
        state = "The ticket is ready to begin."
    elif ticket.status == TicketStatus.BLOCKED:
        state = "The ticket is blocked and needs attention."
    elif ticket.status == TicketStatus.REVIEW:
        state = "The ticket is waiting for review."
    else:
        state = f"The ticket is {ticket.status.value.replace('_', ' ')}."

    details = [state]
    if ticket.priority in {TicketPriority.CRITICAL, TicketPriority.HIGH}:
        details.append(f"It is marked {ticket.priority.value} priority.")

    context = _bounded_ticket_context(ticket.description)
    if context:
        details.append(f"It addresses: {context}")

    remaining_scope: list[str] = []
    if criteria.total:
        remaining = criteria.total - criteria.completed
        label = "acceptance criterion" if criteria.total == 1 else "acceptance criteria"
        remaining_scope.append(f"{remaining} of {criteria.total} {label}")
    if subtasks.total:
        remaining = subtasks.total - subtasks.completed
        label = "subtask" if subtasks.total == 1 else "subtasks"
        remaining_scope.append(f"{remaining} of {subtasks.total} {label}")
    if remaining_scope:
        details.append(f"Remaining scope: {' and '.join(remaining_scope)}.")

    if next_action is None:
        details.append("A concrete next action still needs to be defined.")
    return " ".join(details)


def _work_item(
    ticket: Ticket,
    reasons: list[str],
    preference: MyWorkPreference | None = None,
    *,
    today: date,
) -> MyWorkItem:
    active_criteria = [item for item in ticket.acceptance_criteria if not item.deferred]
    active_subtasks = [
        item
        for item in ticket.subtasks
        if item.status not in {SubtaskStatus.CANCELLED, SubtaskStatus.DEFERRED}
    ]
    availability_mode, available_on = effective_availability(ticket, preference, today)
    next_action = _next_action(ticket)
    criteria_progress = MyWorkProgress(
        completed=sum(item.completed for item in active_criteria),
        total=len(active_criteria),
    )
    subtask_progress = MyWorkProgress(
        completed=sum(item.status == SubtaskStatus.DONE for item in active_subtasks),
        total=len(active_subtasks),
    )
    return MyWorkItem(
        id=ticket.id,
        workspace_ticket_number=ticket.workspace_ticket_number,
        title=ticket.title,
        description=ticket.description,
        project_id=ticket.project_id,
        project_name=ticket.project.name if ticket.project else None,
        project_purpose=ticket.project.purpose if ticket.project else None,
        project_why_it_matters=ticket.project.why_it_matters if ticket.project else None,
        project_target_date=ticket.project.target_date if ticket.project else None,
        focus_rationale=_focus_rationale(
            ticket,
            criteria_progress,
            subtask_progress,
            next_action,
        ),
        status=ticket.status,
        priority=ticket.priority,
        updated_at=ticket.updated_at,
        reasons=reasons,
        acceptance_criteria=criteria_progress,
        subtasks=subtask_progress,
        next_action=next_action,
        availability_mode=availability_mode,
        available_on=available_on,
    )


def build_my_work(
    workspace_id: int,
    user_id: int,
    db: Session,
    *,
    now: datetime | None = None,
    stale_after_days: int = 14,
    completed_limit: int = 5,
    suggestion_limit: int = 3,
) -> MyWorkRead:
    """Build one chosen focus, three eligible suggestions, and supporting context."""
    generated_at = as_utc(now) or utc_now()
    today = generated_at.date()
    stale_before = generated_at - timedelta(days=stale_after_days)
    tickets = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.workspace_id == workspace_id)
            .options(
                selectinload(Ticket.project),
                selectinload(Ticket.acceptance_criteria),
                selectinload(Ticket.subtasks),
            )
        ).all()
    )
    preferences = {
        item.ticket_id: item
        for item in db.scalars(
            select(MyWorkPreference).where(
                MyWorkPreference.workspace_id == workspace_id,
                MyWorkPreference.user_id == user_id,
            )
        ).all()
    }

    current_focus: MyWorkItem | None = None
    candidates: list[MyWorkItem] = []
    upcoming: list[MyWorkItem] = []
    focus_now: list[MyWorkItem] = []
    needs_attention: list[MyWorkItem] = []
    up_next: list[MyWorkItem] = []
    in_review: list[MyWorkItem] = []
    completed: list[MyWorkItem] = []

    for ticket in tickets:
        # Archived Project work remains retrievable by direct history views but
        # cannot occupy active personal execution surfaces.
        if ticket.project is not None and ticket.project.archived_at is not None:
            continue
        preference = preferences.get(ticket.id)
        if ticket.status == TicketStatus.CANCELLED:
            continue
        if ticket.status == TicketStatus.DONE:
            completed.append(_work_item(ticket, ["Completed"], preference, today=today))
            continue
        if ticket.status == TicketStatus.REVIEW:
            in_review.append(
                _work_item(ticket, ["Waiting for your review"], preference, today=today)
            )
            continue

        reasons = [
            "Resume work already in progress"
            if ticket.status == TicketStatus.IN_PROGRESS
            else "Ready to begin"
        ]
        if ticket.project and ticket.project.target_date:
            reasons.append(f"Project target: {ticket.project.target_date.isoformat()}")
        if _next_action(ticket) is None:
            reasons.append("Needs a concrete next action")

        item = _work_item(ticket, reasons, preference, today=today)
        if item.availability_mode != FocusAvailabilityMode.AVAILABLE:
            upcoming.append(item)
            continue

        if (
            preference
            and preference.is_current_focus
            and ticket.status in ACTIVE_TICKET_STATUSES
        ):
            current_focus = item
            continue

        attention_reasons: list[str] = []
        if ticket.status == TicketStatus.BLOCKED:
            attention_reasons.append("Blocked")
        if (
            ticket.status == TicketStatus.IN_PROGRESS
            and ticket.updated_at < stale_before
        ):
            attention_reasons.append(f"No activity in {stale_after_days}+ days")
        if attention_reasons:
            needs_attention.append(
                _work_item(ticket, attention_reasons, preference, today=today)
            )
            continue

        if ticket.status in ACTIVE_TICKET_STATUSES:
            candidates.append(item)
            if ticket.status == TicketStatus.IN_PROGRESS:
                focus_now.append(item)
            else:
                up_next.append(item)

    candidates.sort(key=_recommendation_sort_key)
    upcoming.sort(
        key=lambda item: (
            item.available_on or date.max,
            PRIORITY_ORDER[item.priority],
            item.id,
        )
    )
    focus_now.sort(key=_recommendation_sort_key)
    needs_attention.sort(key=_attention_sort_key)
    up_next.sort(key=_recommendation_sort_key)
    in_review.sort(key=_sort_key)
    completed.sort(key=lambda item: (-item.updated_at.timestamp(), item.id))

    suggestions = candidates[:suggestion_limit]
    return MyWorkRead(
        generated_at=generated_at,
        current_focus=current_focus,
        suggestions=suggestions,
        upcoming=upcoming,
        focus_now=focus_now,
        needs_attention=needs_attention,
        up_next=up_next[:suggestion_limit],
        ready_later_count=max(0, len(candidates) - len(suggestions)),
        in_review=in_review,
        recently_completed=completed[:completed_limit],
    )
