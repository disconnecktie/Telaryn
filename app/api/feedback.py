"""Accept private feedback and expose review only to feedback reviewers."""

from __future__ import annotations

from math import ceil
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, defer, joinedload

from app.core.config import settings
from app.core.time import utc_now
from app.db.session import get_db
from app.models.feedback import FeedbackAdminEvent, FeedbackSubmission
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.feedback import (
    FeedbackAdminEventRead,
    FeedbackAdminPage,
    FeedbackAdminRead,
    FeedbackAdminSummary,
    FeedbackAdminUpdate,
    FeedbackReceipt,
    FeedbackSubmitterRead,
)
from app.services.auth import AuthContext, require_auth_context
from app.services.feedback import normalize_route, sanitize_screenshot
from app.services.feedback_review import require_feedback_reviewer


router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.get("/reviewer-access")
def feedback_reviewer_access(
    response: Response,
    auth: AuthContext = Depends(require_auth_context),
):
    """Expose only the caller's bounded reviewer decision, never feedback data."""
    response.headers["Cache-Control"] = "no-store"
    return {"allowed": auth.user.id in settings.feedback_reviewer_ids}


def require_feedback(db: Session, reference: str, *, include_screenshot: bool = False) -> FeedbackSubmission:
    options = [
        joinedload(FeedbackSubmission.submitter),
        joinedload(FeedbackSubmission.workspace),
        joinedload(FeedbackSubmission.admin_events).joinedload(FeedbackAdminEvent.actor),
    ]
    if not include_screenshot:
        options.append(defer(FeedbackSubmission.screenshot_data))
    feedback = db.scalar(
        select(FeedbackSubmission)
        .options(*options)
        .where(FeedbackSubmission.public_id == reference.upper())
    )
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found.")
    return feedback


def submitter_read(feedback: FeedbackSubmission) -> FeedbackSubmitterRead:
    return FeedbackSubmitterRead(
        display_name=feedback.submitter.display_name,
        email=feedback.submitter.email,
        workspace_name=feedback.workspace.name,
    )


def detail_read(feedback: FeedbackSubmission) -> FeedbackAdminRead:
    return FeedbackAdminRead(
        reference=feedback.public_id,
        category=feedback.category,
        description=feedback.description,
        status=feedback.status,
        route=feedback.route,
        app_version=feedback.app_version,
        viewport_width=feedback.viewport_width,
        viewport_height=feedback.viewport_height,
        browser_context=feedback.browser_context,
        submitter=submitter_read(feedback),
        has_screenshot=feedback.screenshot_size_bytes is not None,
        screenshot_filename=feedback.screenshot_filename,
        screenshot_content_type=feedback.screenshot_content_type,
        screenshot_size_bytes=feedback.screenshot_size_bytes,
        admin_notes=feedback.admin_notes,
        reviewed_at=feedback.reviewed_at,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        events=[FeedbackAdminEventRead(
            actor_display_name=event.actor.display_name,
            actor_email=event.actor.email,
            previous_status=event.previous_status,
            new_status=event.new_status,
            notes_changed=event.notes_changed,
            created_at=event.created_at,
        ) for event in sorted(feedback.admin_events, key=lambda item: item.created_at)],
    )


@router.post("/", response_model=FeedbackReceipt, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: Request,
    response: Response,
    category: Annotated[Literal["problem", "suggestion", "other"], Form()],
    description: Annotated[str, Form(min_length=10, max_length=5000)],
    route: Annotated[str, Form(max_length=500)] = "/",
    viewport_width: Annotated[int | None, Form(ge=1, le=10000)] = None,
    viewport_height: Annotated[int | None, Form(ge=1, le=10000)] = None,
    screenshot: Annotated[UploadFile | None, File()] = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    response.headers["Cache-Control"] = "no-store"
    clean_description = description.strip()
    if len(clean_description) < 10:
        raise HTTPException(status_code=422, detail="Please provide at least 10 characters of feedback.")
    screenshot_data, screenshot_type, screenshot_filename = await sanitize_screenshot(screenshot)
    feedback = FeedbackSubmission(
        submitted_by_user_id=auth.user.id,
        workspace_id=auth.workspace.id,
        category=category,
        description=clean_description,
        route=normalize_route(route),
        app_version=settings.app_version[:50],
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        browser_context=(request.headers.get("user-agent") or "Unavailable")[:500],
        screenshot_data=screenshot_data,
        screenshot_content_type=screenshot_type,
        screenshot_filename=screenshot_filename,
        screenshot_size_bytes=len(screenshot_data) if screenshot_data is not None else None,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackReceipt(reference=feedback.public_id, status=feedback.status, submitted_at=feedback.created_at)


@router.get("/admin", response_model=FeedbackAdminPage)
def list_feedback(
    state: str = Query("new", pattern="^(new|reviewing|resolved|closed|all)$"),
    category: str = Query("all", pattern="^(problem|suggestion|other|all)$"),
    search: str = Query("", max_length=100),
    page: int = Query(1, ge=1, le=100000),
    db: Session = Depends(get_db),
    _: AuthContext = Depends(require_feedback_reviewer),
):
    filters = []
    if state != "all":
        filters.append(FeedbackSubmission.status == state)
    if category != "all":
        filters.append(FeedbackSubmission.category == category)
    term = search.strip().lower()
    if term:
        filters.append(or_(
            func.lower(FeedbackSubmission.public_id).contains(term, autoescape=True),
            func.lower(FeedbackSubmission.description).contains(term, autoescape=True),
            func.lower(User.email).contains(term, autoescape=True),
            func.lower(User.display_name).contains(term, autoescape=True),
        ))
    base = select(FeedbackSubmission).join(User, User.id == FeedbackSubmission.submitted_by_user_id).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    pages = max(1, ceil(total / 25))
    current_page = min(page, pages)
    items = db.scalars(
        base.options(
            joinedload(FeedbackSubmission.submitter),
            joinedload(FeedbackSubmission.workspace),
            defer(FeedbackSubmission.screenshot_data),
        )
        .order_by(FeedbackSubmission.created_at.desc(), FeedbackSubmission.id.desc())
        .offset((current_page - 1) * 25).limit(25)
    ).unique().all()
    return FeedbackAdminPage(
        items=[FeedbackAdminSummary(
            reference=item.public_id,
            category=item.category,
            status=item.status,
            description_preview=item.description[:180],
            submitter=submitter_read(item),
            has_screenshot=item.screenshot_size_bytes is not None,
            created_at=item.created_at,
        ) for item in items],
        total=total,
        page=current_page,
        pages=pages,
    )


@router.get("/admin/{reference}", response_model=FeedbackAdminRead)
def read_feedback(
    reference: str,
    db: Session = Depends(get_db),
    _: AuthContext = Depends(require_feedback_reviewer),
):
    return detail_read(require_feedback(db, reference))


@router.get("/admin/{reference}/screenshot")
def read_feedback_screenshot(
    reference: str,
    db: Session = Depends(get_db),
    _: AuthContext = Depends(require_feedback_reviewer),
):
    feedback = require_feedback(db, reference, include_screenshot=True)
    if feedback.screenshot_data is None:
        raise HTTPException(status_code=404, detail="Feedback screenshot not found.")
    return Response(
        feedback.screenshot_data,
        media_type=feedback.screenshot_content_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{feedback.screenshot_filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch("/admin/{reference}", response_model=FeedbackAdminRead)
def update_feedback_review(
    reference: str,
    payload: FeedbackAdminUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_feedback_reviewer),
):
    feedback = require_feedback(db, reference)
    clean_notes = payload.admin_notes.strip() if payload.admin_notes else None
    previous_status = feedback.status
    notes_changed = clean_notes != feedback.admin_notes
    if payload.status != previous_status or notes_changed:
        review_time = utc_now()
        db.add(FeedbackAdminEvent(
            feedback_id=feedback.id,
            actor_id=auth.user.id,
            previous_status=previous_status,
            new_status=payload.status,
            notes_changed=notes_changed,
        ))
        feedback.status = payload.status
        feedback.admin_notes = clean_notes
        feedback.reviewed_by_user_id = auth.user.id
        feedback.reviewed_at = review_time
        if payload.status == "closed" and previous_status != "closed":
            feedback.closed_at = review_time
        elif payload.status != "closed" and previous_status == "closed":
            feedback.closed_at = None
        db.commit()
    return detail_read(require_feedback(db, reference))
