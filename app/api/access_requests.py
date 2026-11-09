"""Expose deployment intake only to explicitly authorized authenticated reviewers."""

from datetime import timedelta
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.session import get_db
from app.models.access_request import AccessRequest, AccessRequestEvent, AccessRequestLimit
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invitation import WorkspaceInvitation, WorkspaceInvitationEvent
from app.schemas.access_request import AccessRequestCreate, AccessRequestReview, RequestStatus
from app.services.access_requests import build_access_request, purge_expired_requests
from app.services.auth import AuthContext, require_auth_context
from app.services.workspace_invitations import (
    InvitationUnavailable, accept_existing_account, accept_new_account,
    invitation_from_token, invitation_status, issue_invitation, record_delivery,
    revoke_invitation,
)
from app.services.invitation_delivery import (
    InvitationDeliveryUnavailable, deliver_invitation,
)

router = APIRouter(prefix="/access-requests", tags=["Access request review"])


@router.get("/availability")
def availability(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"enabled": bool(settings.access_request_intake_enabled and settings.access_request_reviewer_ids)}


@router.get("/reviewer-access")
def reviewer_access(response: Response, auth: AuthContext = Depends(require_auth_context), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    allowed = auth.user.id in settings.access_request_reviewer_ids
    count = db.scalar(select(func.count()).select_from(AccessRequest).where(
        AccessRequest.status == "new", AccessRequest.expires_at > utc_now()
    )) if allowed else 0
    return {"allowed": allowed, "new_count": count}


@router.post("/", status_code=202)
async def submit_request(request: Request, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    if not settings.access_request_intake_enabled or not settings.access_request_reviewer_ids:
        raise HTTPException(503, "Access requests are not available right now.")
    origins = {value.strip() for value in settings.frontend_origins.split(",")}
    if request.headers.get("origin") not in origins:
        raise HTTPException(403, "Request origin is not allowed.")
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Send a JSON request.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 16384:
            raise HTTPException(413, "Request is too large.")
    try:
        payload = AccessRequestCreate.model_validate(json.loads(body))
    except (ValueError, ValidationError, UnicodeDecodeError):
        # Never echo form values in errors, logs, or support references.
        raise HTTPException(422, "Check the required fields and field lengths.") from None
    now = utc_now()
    # One database counter serves all workers; no untrusted proxy/IP identity is used.
    db.execute(update(AccessRequestLimit).where(
        AccessRequestLimit.id == 1, AccessRequestLimit.window_start <= now - timedelta(hours=1)
    ).values(window_start=now, accepted=0))
    accepted = db.execute(update(AccessRequestLimit).where(
        AccessRequestLimit.id == 1, AccessRequestLimit.accepted < 30
    ).values(accepted=AccessRequestLimit.accepted + 1))
    if accepted.rowcount != 1:
        db.rollback()
        raise HTTPException(429, "Please try again later.", headers={"Retry-After": "3600"})
    purge_expired_requests(db, now=now)
    db.add(build_access_request(payload))
    db.commit()
    # No account lookup, auto-provisioning, email, or AI operation.
    return {"message": "Request received. This does not create an account or grant access."}


def require_reviewer(response: Response, auth: AuthContext = Depends(require_auth_context)):
    if auth.user.id not in settings.access_request_reviewer_ids:
        raise HTTPException(status_code=403, detail="Access request reviewer required.")
    response.headers["Cache-Control"] = "no-store"
    return auth


def record_or_404(db, request_id, *, lock=False):
    query = select(AccessRequest).where(
        AccessRequest.id == request_id, AccessRequest.expires_at > utc_now()
    )
    record = db.scalar(query.with_for_update() if lock else query)
    if record is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    return record


def allowed_public_origin(request: Request):
    origins = {value.strip() for value in settings.frontend_origins.split(",")}
    if request.headers.get("origin") not in origins:
        raise HTTPException(403, "Request origin is not allowed.")


class InvitationToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=40, max_length=200)


class NewAccountAcceptance(InvitationToken):
    password: str = Field(min_length=12, max_length=1024)
    password_confirmation: str = Field(min_length=12, max_length=1024)


class InvitationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_generation: int | None = Field(default=None, gt=0)


class InvitationRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_generation: int = Field(gt=0)


def safe_invitation(invitation):
    return {key: getattr(invitation, key) for key in (
        "id", "workspace_id", "role", "generation", "created_at", "updated_at", "expires_at",
        "delivery_provider", "delivery_attempted_at", "delivered_at",
    )} | {"status": invitation_status(invitation)}


@router.post("/invitations/inspect")
def inspect_invitation(payload: InvitationToken, request: Request,
                       response: Response, db: Session = Depends(get_db)):
    allowed_public_origin(request)
    response.headers["Cache-Control"] = "no-store"
    try:
        invitation = invitation_from_token(db, payload.token)
    except InvitationUnavailable:
        raise HTTPException(404, "This invitation is unavailable.") from None
    workspace = db.get(Workspace, invitation.workspace_id) if invitation.workspace_id else None
    return {
        "account_email": invitation.email,
        "workspace_name": workspace.name if workspace else "Your private workspace",
        "role": "Workspace owner",
        "requires_sign_in": db.scalar(select(User.id).where(User.email == invitation.email)) is not None,
        "expires_at": invitation.expires_at,
    }


@router.post("/invitations/accept-new", status_code=201)
def accept_new_invitation(payload: NewAccountAcceptance, request: Request,
                          response: Response, db: Session = Depends(get_db)):
    allowed_public_origin(request)
    response.headers["Cache-Control"] = "no-store"
    try:
        accept_new_account(db, token=payload.token, password=payload.password,
                           password_confirmation=payload.password_confirmation)
        db.commit()
    except (InvitationUnavailable, IntegrityError):
        db.rollback()
        raise HTTPException(409, "This invitation cannot be activated. It may require sign-in or a new invitation.") from None
    return {"message": "Account activated. Sign in to open your workspace."}


@router.post("/invitations/accept-existing")
def accept_existing_invitation(payload: InvitationToken, response: Response,
                               db: Session = Depends(get_db),
                               auth: AuthContext = Depends(require_auth_context)):
    response.headers["Cache-Control"] = "no-store"
    try:
        accept_existing_account(db, token=payload.token, user=auth.user)
        db.commit()
    except (InvitationUnavailable, IntegrityError):
        db.rollback()
        raise HTTPException(409, "This invitation cannot be accepted by this account.") from None
    return {"message": "Invitation confirmed. This account already has Telaryn access."}


def summary(record):
    return {key: getattr(record, key) for key in (
        "id", "first_name", "last_name", "status", "created_at", "updated_at", "expires_at"
    )}


@router.get("/")
def list_requests(
    after_id: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db), auth: AuthContext = Depends(require_reviewer),
):
    records = db.scalars(select(AccessRequest).where(
        AccessRequest.id > after_id, AccessRequest.expires_at > utc_now()
    ).order_by(AccessRequest.id).limit(limit)).all()
    return [summary(record) for record in records]


class QueueQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: RequestStatus | None = "new"
    search: str = Field(default="", max_length=100)
    page: int = Field(default=1, ge=1, le=100000)


@router.post("/queue")
def request_queue(payload: QueueQuery, db: Session = Depends(get_db), auth: AuthContext = Depends(require_reviewer)):
    # Keep search values out of URLs and ordinary access logs.
    filters = [AccessRequest.expires_at > utc_now()]
    if payload.status is not None:
        filters.append(AccessRequest.status == payload.status)
    term = payload.search.strip().lower()
    if term:
        filters.append(or_(
            func.lower(AccessRequest.first_name + " " + AccessRequest.last_name).contains(term, autoescape=True),
            func.lower(AccessRequest.email).contains(term, autoescape=True),
        ))
    total = db.scalar(select(func.count()).select_from(AccessRequest).where(*filters))
    pages = max(1, (total + 19) // 20)
    page = min(payload.page, pages)
    records = db.scalars(select(AccessRequest).where(*filters).order_by(
        case((AccessRequest.status == "new", 0), else_=1),
        AccessRequest.created_at.desc(), AccessRequest.id.desc(),
    ).offset((page - 1) * 20).limit(20)).all()
    return {"items": [{**summary(record), "email": record.email} for record in records],
            "total": total, "page": page, "pages": pages}


@router.get("/{request_id}")
def read_request(request_id: int, db: Session = Depends(get_db), auth: AuthContext = Depends(require_reviewer)):
    record = record_or_404(db, request_id)
    result = summary(record)
    result.update({key: getattr(record, key) for key in (
        "email", "phone", "biography", "referral_source", "referral_detail", "notes"
    )})
    result["history"] = [
        {key: getattr(event, key) for key in ("reviewer_id", "previous_status", "status", "created_at")}
        for event in db.scalars(select(AccessRequestEvent).where(
            AccessRequestEvent.request_id == request_id
        ).order_by(AccessRequestEvent.id))
    ]
    invitation = db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.request_id == request_id))
    result["invitation"] = safe_invitation(invitation) if invitation else None
    if invitation:
        result["invitation"]["history"] = [
            {key: getattr(event, key) for key in ("actor_id", "workspace_id", "generation", "event", "created_at")}
            for event in db.scalars(select(WorkspaceInvitationEvent).where(
                WorkspaceInvitationEvent.invitation_id == invitation.id
            ).order_by(WorkspaceInvitationEvent.id))
        ]
    return result


@router.post("/{request_id}/invitation")
def create_or_reissue_invitation(request_id: int, payload: InvitationIssue,
                                 response: Response, db: Session = Depends(get_db),
                                 auth: AuthContext = Depends(require_reviewer)):
    response.headers["Cache-Control"] = "no-store"
    try:
        issued = issue_invitation(db, actor_id=auth.user.id, request_id=request_id,
                                  expected_generation=payload.expected_generation)
        db.commit()
        invitation = db.get(WorkspaceInvitation, issued.invitation_id)
    except InvitationUnavailable:
        db.rollback()
        raise HTTPException(409, "Invitation action is unavailable. Refresh and try again.") from None
    request_record = db.get(AccessRequest, request_id)
    try:
        delivery, link = deliver_invitation(
            recipient_email=invitation.email,
            recipient_name=f"{request_record.first_name} {request_record.last_name}".strip(),
            token=issued.token,
        )
        if delivery.provider != "manual":
            record_delivery(db, invitation_id=issued.invitation_id,
                            generation=issued.generation, actor_id=auth.user.id,
                            provider=delivery.provider, message_id=delivery.message_id,
                            succeeded=True)
            db.commit()
            db.refresh(invitation)
    except InvitationDeliveryUnavailable:
        db.rollback()
        try:
            record_delivery(db, invitation_id=issued.invitation_id,
                            generation=issued.generation, actor_id=auth.user.id,
                            provider=settings.invitation_delivery_provider,
                            message_id=None, succeeded=False)
            db.commit()
        except InvitationUnavailable:
            db.rollback()
        raise HTTPException(502, "Telaryn could not deliver the invitation. Refresh and try again.") from None
    except InvitationUnavailable:
        db.rollback()
        raise HTTPException(409, "Invitation state changed during delivery. Refresh and try again.") from None
    result = {"invitation": safe_invitation(invitation), "delivery": delivery.provider}
    # A bearer link leaves the backend only for the explicitly local/manual provider.
    if link:
        result["activation_link"] = link
    return result


@router.post("/{request_id}/invitation/revoke")
def revoke_request_invitation(request_id: int, payload: InvitationRevoke,
                              response: Response, db: Session = Depends(get_db),
                              auth: AuthContext = Depends(require_reviewer)):
    response.headers["Cache-Control"] = "no-store"
    invitation = db.scalar(select(WorkspaceInvitation).where(
        WorkspaceInvitation.request_id == request_id
    ))
    if invitation is None:
        raise HTTPException(409, "Invitation action is unavailable. Refresh and try again.")
    try:
        revoke_invitation(db, actor_id=auth.user.id, invitation_id=invitation.id,
                          expected_generation=payload.expected_generation)
        db.commit()
    except InvitationUnavailable:
        db.rollback()
        raise HTTPException(409, "Invitation action is unavailable. Refresh and try again.") from None
    return {"invitation": safe_invitation(invitation)}


@router.patch("/{request_id}")
def review_request(request_id: int, payload: AccessRequestReview,
                   db: Session = Depends(get_db), auth: AuthContext = Depends(require_reviewer)):
    record = record_or_404(db, request_id, lock=True)
    if record.status != payload.status:
        now = utc_now()
        db.add(AccessRequestEvent(request_id=record.id, reviewer_id=auth.user.id,
                                 previous_status=record.status, status=payload.status, created_at=now))
        record.status = payload.status
        record.updated_at = now
        # Status changes are not retention extensions or account provisioning.
        db.commit()
    return summary(record)

