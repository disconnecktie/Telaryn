"""Expose authenticated My Work recommendations and user-directed focus choices."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.schemas.my_work import MyWorkPreferenceUpdate, MyWorkRead
from app.services.auth import AuthContext, require_auth_context
from app.services.focus import clear_current_focus, focus_ticket
from app.services.my_work import build_my_work, ticket_context_updated_at
from app.services.workspaces import require_workspace_ticket


router = APIRouter(prefix="/my-work", tags=["My Work"])


@router.get("/", response_model=MyWorkRead)
def get_my_work(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    return build_my_work(auth.workspace.id, auth.user.id, db)


@router.patch("/tickets/{ticket_id}", response_model=MyWorkRead)
def update_my_work_preference(
    ticket_id: int,
    preference_data: MyWorkPreferenceUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Record attention choices separately from authoritative ticket workflow state."""
    ticket = require_workspace_ticket(
        db,
        workspace_id=auth.workspace.id,
        ticket_id=ticket_id,
    )
    if preference_data.current_focus is True:
        focus_ticket(
            db,
            ticket=ticket,
            workspace_id=auth.workspace.id,
            user_id=auth.user.id,
            make_available=preference_data.make_available_and_focus,
        )
        db.commit()
        return build_my_work(auth.workspace.id, auth.user.id, db)

    if preference_data.current_focus is False:
        clear_current_focus(
            db,
            ticket_id=ticket.id,
            workspace_id=auth.workspace.id,
            user_id=auth.user.id,
        )

    preference = db.scalar(
        select(MyWorkPreference).where(
            MyWorkPreference.user_id == auth.user.id,
            MyWorkPreference.workspace_id == auth.workspace.id,
            MyWorkPreference.ticket_id == ticket_id,
        )
    )
    mode = preference_data.availability_mode
    if mode is not None:
        if preference is None:
            preference = MyWorkPreference(
                user_id=auth.user.id,
                workspace_id=auth.workspace.id,
                ticket_id=ticket_id,
            )
            db.add(preference)
        preference.availability_mode = mode
        preference.available_on = (
            preference_data.available_on
            if mode == FocusAvailabilityMode.DATE
            else None
        )
        preference.context_ticket_updated_at = (
            ticket_context_updated_at(ticket)
            if mode == FocusAvailabilityMode.CONTEXT_CHANGE
            else None
        )
        if mode != FocusAvailabilityMode.AVAILABLE:
            preference.is_current_focus = False

    db.commit()
    return build_my_work(auth.workspace.id, auth.user.id, db)
