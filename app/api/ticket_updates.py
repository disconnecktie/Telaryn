"""Store append-only human progress notes separately from automatic activity."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import get_db
from app.models.ticket import Ticket
from app.models.ticket_update_attachment import TicketUpdateAttachment
from app.models.ticket_update_entry import TicketUpdateEntry
from app.schemas.ticket_update_entry import (
    TicketUpdateEntryCreate,
    TicketUpdateEntryRead,
)
from app.services.auth import AuthContext, require_auth_context
from app.services.workspaces import (
    request_workspace,
    require_active_ticket,
    require_workspace_ticket,
)


# Append-only ticket progress notes, kept distinct from formal status transitions.
router = APIRouter(
    prefix="/tickets/{ticket_id}/updates",
    tags=["Ticket Updates"],
)


def _get_ticket_or_404(ticket_id: int, db: Session, auth: AuthContext | object) -> Ticket:
    workspace = request_workspace(db, auth)
    return require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)


def _to_read_model(
    entry: TicketUpdateEntry,
    attachment_count: int = 0,
) -> TicketUpdateEntryRead:
    return TicketUpdateEntryRead(
        id=entry.id,
        ticket_id=entry.ticket_id,
        content=entry.content,
        created_at=entry.created_at,
        attachment_count=attachment_count,
    )


@router.post("/", response_model=TicketUpdateEntryRead, status_code=201)
def create_ticket_update(
    ticket_id: int,
    update_data: TicketUpdateEntryCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    ticket = _get_ticket_or_404(ticket_id, db, auth)
    require_active_ticket(ticket)

    entry = TicketUpdateEntry(
        ticket_id=ticket_id,
        content=update_data.content,
        actor_user_id=auth.user.id if isinstance(auth, AuthContext) else None,
    )
    db.add(entry)
    ticket.updated_at = utc_now()
    db.commit()
    db.refresh(entry)

    return _to_read_model(entry)


@router.get("/", response_model=list[TicketUpdateEntryRead])
def list_ticket_updates(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    _get_ticket_or_404(ticket_id, db, auth)

    statement = (
        select(
            TicketUpdateEntry,
            func.count(TicketUpdateAttachment.id).label("attachment_count"),
        )
        .outerjoin(TicketUpdateAttachment)
        .where(TicketUpdateEntry.ticket_id == ticket_id)
        .group_by(TicketUpdateEntry.id)
        .order_by(
            TicketUpdateEntry.created_at.desc(),
            TicketUpdateEntry.id.desc(),
        )
    )

    return [
        _to_read_model(entry, attachment_count)
        for entry, attachment_count in db.execute(statement).all()
    ]
