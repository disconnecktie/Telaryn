"""Construct requests with bounded retention; approval never provisions an account."""

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.access_request import AccessRequest, AccessRequestEvent
from app.models.workspace_invitation import WorkspaceInvitation, WorkspaceInvitationEvent
from app.schemas.access_request import AccessRequestCreate

RETENTION_DAYS = 90


def build_access_request(payload: AccessRequestCreate) -> AccessRequest:
    """Return an unsaved record; callers own authorization, transaction, and abuse limits."""
    now = utc_now()
    return AccessRequest(
        **payload.model_dump(), status="new", created_at=now, updated_at=now,
        expires_at=now + timedelta(days=RETENTION_DAYS),
    )


def purge_expired_requests(db: Session, *, now=None) -> int:
    """Delete expired intake and its history atomically; caller commits the transaction."""
    cutoff = now if now is not None else utc_now()
    expired = select(AccessRequest.id).where(AccessRequest.expires_at <= cutoff)
    # Explicit deletion also supports SQLite installations without FK enforcement.
    invitations = select(WorkspaceInvitation.id).where(WorkspaceInvitation.request_id.in_(expired))
    db.execute(delete(WorkspaceInvitationEvent).where(WorkspaceInvitationEvent.invitation_id.in_(invitations)))
    db.execute(delete(WorkspaceInvitation).where(WorkspaceInvitation.request_id.in_(expired)))
    db.execute(delete(AccessRequestEvent).where(AccessRequestEvent.request_id.in_(expired)))
    result = db.execute(delete(AccessRequest).where(AccessRequest.expires_at <= cutoff))
    return result.rowcount
