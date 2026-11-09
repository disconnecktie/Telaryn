"""Expose deterministic search inside the authenticated workspace boundary."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ticket import TicketStatus
from app.schemas.search import SearchRead
from app.services.auth import AuthContext, require_auth_context
from app.services.search import search_workspace


router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/", response_model=SearchRead)
def search_authorized_work(
    q: str = Query(min_length=2, max_length=200),
    include_completed: bool = False,
    include_cancelled: bool = False,
    include_deferred: bool = False,
    include_archived: bool = False,
    status: list[TicketStatus] | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(
            status_code=422,
            detail="Search requires at least two non-whitespace characters.",
        )
    return search_workspace(
        db,
        workspace_id=auth.workspace.id,
        query=query,
        include_completed=include_completed,
        include_cancelled=include_cancelled,
        include_deferred=include_deferred,
        include_archived=include_archived,
        statuses=set(status) if status else None,
        limit=limit,
    )
