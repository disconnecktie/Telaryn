"""Derive onboarding progress from approved work in the active workspace."""

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.my_work_preference import MyWorkPreference
from app.models.onboarding_state import OnboardingState
from app.models.subtask import Subtask
from app.models.ticket import Ticket
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry


MILESTONES = (
    ("capture", "Capture work", "Turn a real request or rough idea into a Ticket."),
    ("shape", "Refine and approve", "Give the work a useful definition of done and concrete steps."),
    ("focus", "Choose focus", "Make one Ticket your Current Focus."),
    ("record", "Record progress", "Capture an update, completion, or outcome on the work."),
)


def onboarding_progress(db: Session, *, user_id: int, workspace_id: int) -> dict:
    ticket_ids = select(Ticket.id).where(Ticket.workspace_id == workspace_id)
    captured = db.scalar(select(exists().where(Ticket.workspace_id == workspace_id)))
    shaped = db.scalar(select(exists().where(
        AcceptanceCriterion.ticket_id.in_(ticket_ids)
    ))) or db.scalar(select(exists().where(Subtask.ticket_id.in_(ticket_ids))))
    focused = db.scalar(select(exists().where(
        MyWorkPreference.user_id == user_id,
        MyWorkPreference.workspace_id == workspace_id,
        MyWorkPreference.is_current_focus.is_(True),
    )))
    recorded = db.scalar(select(exists().where(
        TicketUpdateEntry.actor_user_id == user_id,
        TicketUpdateEntry.ticket_id.in_(ticket_ids),
    ))) or db.scalar(select(exists().where(
        TicketStatusEvent.actor_user_id == user_id,
        TicketStatusEvent.ticket_id.in_(ticket_ids),
    )))
    values = (bool(captured), bool(shaped), bool(focused), bool(recorded))
    state = db.scalar(select(OnboardingState).where(
        OnboardingState.user_id == user_id,
        OnboardingState.workspace_id == workspace_id,
    ))
    milestones = [
        {"key": key, "label": label, "description": description, "completed": value}
        for (key, label, description), value in zip(MILESTONES, values, strict=True)
    ]
    dismissed = bool(state and state.dismissed_at)
    return {
        "dismissed": dismissed,
        "completed": all(values),
        "show_panel": not dismissed,
        "milestones": milestones,
    }
