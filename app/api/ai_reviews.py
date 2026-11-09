"""Expose persisted ticket AI reviews and their separate acceptance boundary."""

import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.factory import get_ai_provider
from app.ai.base import AIProviderError, AIProviderTimeoutError
from app.ai.service import AIReviewService
from app.db.session import get_db
from app.core.diagnostics import log_diagnostic_event
from app.models.ai_review import AIReview
from app.models.ticket import Ticket
from app.schemas.ai_review import AIReviewAccept, AIReviewRead
from app.schemas.progress_review import (
    ProgressReviewAccept,
    ProgressReviewRead,
    ProgressReviewRequest,
)
from app.services.progress_review import ProgressReviewService, serialize_progress_review
from app.services.ai_context_policy import (
    require_project_ai_context,
    require_ticket_ai_context,
)
from app.services.auth import AuthContext, require_auth_context
from app.services.workspaces import (
    activity_actor,
    request_workspace,
    require_active_ticket,
    require_workspace_ticket,
)


# Existing-ticket proposal and explicit-acceptance endpoints.
router = APIRouter(
    prefix="/tickets/{ticket_id}/ai-reviews",
    tags=["AI Reviews"],
)


def _progress_service():
    return ProgressReviewService(get_ai_provider())


@router.post("/progress", response_model=ProgressReviewRead, status_code=201)
def create_progress_review(
    ticket_id: int, request: ProgressReviewRequest,
    db: Session = Depends(get_db), auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket); require_ticket_ai_context(ticket); require_project_ai_context(ticket.project)
    service = _progress_service(); started = perf_counter()
    log_diagnostic_event("ai_operation", operation="ticket_progress_review", outcome="requested",
        provider=service.provider.name, model=service.provider.model_name,
        user_id=auth.user.id, workspace_id=workspace.id)
    try:
        review = service.create(ticket=ticket, request=request, db=db)
    except AIProviderTimeoutError as error:
        log_diagnostic_event("ai_operation", level=logging.WARNING, operation="ticket_progress_review",
            outcome="timeout", user_id=auth.user.id, workspace_id=workspace.id,
            duration_ms=round((perf_counter()-started)*1000))
        raise HTTPException(status_code=504, detail="Telaryn AI did not respond in time. Your recorded update was kept and ticket progress was not changed.") from error
    except AIProviderError as error:
        log_diagnostic_event("ai_operation", level=logging.WARNING, operation="ticket_progress_review",
            outcome="provider_failure", user_id=auth.user.id, workspace_id=workspace.id,
            duration_ms=round((perf_counter()-started)*1000))
        raise HTTPException(status_code=502, detail="Telaryn AI is temporarily unavailable. Your recorded update was kept and ticket progress was not changed.") from error
    return serialize_progress_review(review)


@router.post("/progress/{review_id}/accept", response_model=ProgressReviewRead)
def accept_progress_review(
    ticket_id: int, review_id: int, options: ProgressReviewAccept,
    db: Session = Depends(get_db), auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket); actor_type, actor_id = activity_actor(auth)
    review = db.get(AIReview, review_id)
    if review is None or review.ticket_id != ticket.id: raise HTTPException(404, "Progress review not found")
    try:
        result = _progress_service().accept(review=review, ticket=ticket,
            keys=options.suggestion_keys, db=db, actor_type=actor_type, actor_id=actor_id)
    except ValueError as error: raise HTTPException(409, str(error)) from error
    return serialize_progress_review(result)


@router.post("/progress/{review_id}/reject", response_model=ProgressReviewRead)
def reject_progress_review(
    ticket_id: int, review_id: int,
    db: Session = Depends(get_db), auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    review = db.get(AIReview, review_id)
    if review is None or review.ticket_id != ticket.id: raise HTTPException(404, "Progress review not found")
    try: result = _progress_service().reject(review=review, db=db)
    except ValueError as error: raise HTTPException(409, str(error)) from error
    return serialize_progress_review(result)


@router.post("/", response_model=AIReviewRead, status_code=201)
def create_ai_review(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Create persisted AI proposals; a separate accept request applies user choices."""
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    require_ticket_ai_context(ticket)
    require_project_ai_context(ticket.project)

    provider = get_ai_provider()
    service = AIReviewService(provider)

    started = perf_counter()
    log_diagnostic_event(
        "ai_operation",
        operation="ticket_review",
        outcome="requested",
        provider=provider.name,
        model=provider.model_name,
        user_id=auth.user.id,
        workspace_id=workspace.id,
    )
    try:
        review = service.review_ticket(ticket, db)
    except AIProviderTimeoutError as error:
        log_diagnostic_event(
            "ai_operation",
            level=logging.WARNING,
            operation="ticket_review",
            outcome="timeout",
            provider=provider.name,
            model=provider.model_name,
            user_id=auth.user.id,
            workspace_id=workspace.id,
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(
            status_code=504,
            detail=(
                "Telaryn AI did not respond in time. The ticket was not changed; "
                "please retry when ready."
            ),
        ) from error
    except AIProviderError as error:
        log_diagnostic_event(
            "ai_operation",
            level=logging.WARNING,
            operation="ticket_review",
            outcome="provider_failure",
            provider=provider.name,
            model=provider.model_name,
            user_id=auth.user.id,
            workspace_id=workspace.id,
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "Telaryn AI is temporarily unavailable. The ticket was not "
                "changed; please retry when ready."
            ),
        ) from error

    log_diagnostic_event(
        "ai_operation",
        operation="ticket_review",
        outcome="completed",
        provider=provider.name,
        model=provider.model_name,
        user_id=auth.user.id,
        workspace_id=workspace.id,
        duration_ms=round((perf_counter() - started) * 1000),
    )
    return review

@router.post(
    "/{review_id}/accept",
    response_model=AIReviewRead,
)
def accept_ai_review(
    ticket_id: int,
    review_id: int,
    options: AIReviewAccept,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Apply explicitly selected proposals from a completed review."""
    workspace = request_workspace(db, auth)
    ticket = require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)
    require_active_ticket(ticket)
    actor_type, actor_id = activity_actor(auth)

    review = db.get(AIReview, review_id)

    if review is None or review.ticket_id != ticket_id:
        raise HTTPException(
            status_code=404,
            detail="AI review not found",
        )

    provider = get_ai_provider()
    service = AIReviewService(provider)

    try:
        return service.accept_review(
            review=review,
            ticket=ticket,
            options=options,
            db=db,
            actor_type=actor_type,
            actor_id=actor_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

@router.get("/", response_model=list[AIReviewRead])
def list_ai_reviews(
    ticket_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    require_workspace_ticket(db, workspace_id=workspace.id, ticket_id=ticket_id)

    statement = (
        select(AIReview)
        .where(AIReview.ticket_id == ticket_id)
        .order_by(AIReview.created_at.desc())
    )

    return db.scalars(statement).all()

