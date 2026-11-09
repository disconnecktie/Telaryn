"""Internal invitation lifecycle foundation; no public issuance/acceptance route yet.

Callers must commit before delivery and roll back on any error. Raw tokens are
returned once to the future delivery adapter and must never be logged or stored.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from hashlib import sha256
import secrets

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.models.access_request import AccessRequest
from app.models.workspace_invitation import WorkspaceInvitation, WorkspaceInvitationEvent
from app.models.workspace_membership import WorkspaceMembership
from app.models.workspace import Workspace
from app.models.user import User
from app.services.auth import hash_password


class InvitationUnavailable(ValueError):
    """Safe error without recipient, workspace, or credential details."""

    def __init__(self):
        super().__init__("Invitation action is unavailable. Refresh and try again.")


@dataclass(frozen=True)
class IssuedInvitation:
    invitation_id: int
    generation: int
    token: str = field(repr=False)


def digest_invitation_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def invitation_status(invitation: WorkspaceInvitation, *, now=None) -> str:
    if invitation.status in {"pending", "delivery_failed"} and invitation.expires_at <= (now or utc_now()):
        return "expired"
    return invitation.status


def _authorize(db: Session, actor_id: int):
    if actor_id not in settings.access_request_reviewer_ids:
        raise InvitationUnavailable()
    membership = db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == actor_id,
        WorkspaceMembership.role == "owner",
    ).with_for_update())
    if membership is None:
        raise InvitationUnavailable()


def _event(db: Session, invitation: WorkspaceInvitation, actor_id: int, event: str, now):
    db.add(WorkspaceInvitationEvent(
        invitation_id=invitation.id, actor_id=actor_id,
        workspace_id=invitation.workspace_id, generation=invitation.generation,
        event=event, created_at=now,
    ))
    db.flush()


def issue_invitation(db: Session, *, actor_id: int, request_id: int,
                     expected_generation: int | None = None) -> IssuedInvitation:
    """Issue once or explicitly reissue a displayed generation atomically.

    A write lock on the intake serializes issue/reissue on SQLite and PostgreSQL.
    A stale confirmation cannot replace a newer invitation. The workspace is not
    selected by the reviewer; activation creates one owned by the recipient.
    """
    _authorize(db, actor_id)
    now = utc_now()
    locked = db.execute(update(AccessRequest).where(
        AccessRequest.id == request_id, AccessRequest.status == "approved",
        AccessRequest.expires_at > now,
    ).values(updated_at=AccessRequest.updated_at))
    if locked.rowcount != 1:
        raise InvitationUnavailable()
    request = db.scalar(select(AccessRequest).where(AccessRequest.id == request_id).execution_options(populate_existing=True))
    invitation = db.scalar(select(WorkspaceInvitation).where(
        WorkspaceInvitation.request_id == request_id,
    ).execution_options(populate_existing=True))
    if invitation is None:
        if expected_generation is not None:
            raise InvitationUnavailable()
        invitation = WorkspaceInvitation(request_id=request_id, workspace_id=None,
            role="owner", generation=1, created_at=now)
        db.add(invitation)
        event = "issued"
    else:
        if (expected_generation != invitation.generation or invitation.status == "accepted"
                or invitation.workspace_id is not None):
            raise InvitationUnavailable()
        invitation.generation += 1
        event = "reissued"
    raw = secrets.token_urlsafe(48)
    invitation.inviter_id = actor_id
    invitation.email = request.email.strip().lower()
    invitation.role = "owner"
    invitation.token_hash = digest_invitation_token(raw)
    invitation.status = "pending"
    invitation.delivery_provider = None
    invitation.delivery_message_id = None
    invitation.delivery_attempted_at = None
    invitation.delivered_at = None
    invitation.updated_at = now
    invitation.expires_at = min(now + timedelta(hours=72), request.expires_at)
    db.flush()
    _event(db, invitation, actor_id, event, now)
    return IssuedInvitation(invitation.id, invitation.generation, raw)


def record_delivery(db: Session, *, invitation_id: int, generation: int,
                    actor_id: int, provider: str, message_id: str | None,
                    succeeded: bool):
    """Record a delivery result for exactly the generation that was attempted."""
    invitation = db.get(WorkspaceInvitation, invitation_id)
    if invitation is None:
        raise InvitationUnavailable()
    now = utc_now()
    values = {
        "delivery_provider": provider,
        "delivery_message_id": message_id,
        "delivery_attempted_at": now,
        "delivered_at": now if succeeded else None,
        "updated_at": now,
    }
    if not succeeded:
        values.update(status="delivery_failed", token_hash=None)
    result = db.execute(update(WorkspaceInvitation).where(
        WorkspaceInvitation.id == invitation_id,
        WorkspaceInvitation.generation == generation,
        WorkspaceInvitation.status == "pending",
    ).values(**values))
    if result.rowcount != 1:
        raise InvitationUnavailable()
    db.refresh(invitation)
    _event(db, invitation, actor_id, "delivered" if succeeded else "delivery_failed", now)


def revoke_invitation(db: Session, *, actor_id: int, invitation_id: int,
                      expected_generation: int):
    """Revocation invalidates the digest; it cannot undo an accepted membership."""
    invitation = db.get(WorkspaceInvitation, invitation_id)
    if invitation is None:
        raise InvitationUnavailable()
    _authorize(db, actor_id)
    now = utc_now()
    result = db.execute(update(WorkspaceInvitation).where(
        WorkspaceInvitation.id == invitation_id,
        WorkspaceInvitation.generation == expected_generation,
        WorkspaceInvitation.status.in_(["pending", "delivery_failed"]),
    ).values(status="revoked", token_hash=None, updated_at=now))
    if result.rowcount != 1:
        raise InvitationUnavailable()
    db.refresh(invitation)
    _event(db, invitation, actor_id, "revoked", now)


def invitation_from_token(db: Session, token: str, *, lock=False) -> WorkspaceInvitation:
    """Resolve only a live token; every invalid lifecycle state looks identical."""
    query = select(WorkspaceInvitation).join(
        AccessRequest, AccessRequest.id == WorkspaceInvitation.request_id
    ).where(
        WorkspaceInvitation.token_hash == digest_invitation_token(token),
        WorkspaceInvitation.status == "pending",
        WorkspaceInvitation.expires_at > utc_now(),
        AccessRequest.status == "approved",
        AccessRequest.expires_at > utc_now(),
    )
    invitation = db.scalar(query.with_for_update() if lock else query)
    if invitation is None:
        raise InvitationUnavailable()
    return invitation


def _consume(db: Session, invitation: WorkspaceInvitation, *, actor_id: int):
    now = utc_now()
    result = db.execute(update(WorkspaceInvitation).where(
        WorkspaceInvitation.id == invitation.id,
        WorkspaceInvitation.generation == invitation.generation,
        WorkspaceInvitation.status == "pending",
        WorkspaceInvitation.token_hash == invitation.token_hash,
        WorkspaceInvitation.expires_at > now,
    ).values(status="accepted", token_hash=None, updated_at=now))
    if result.rowcount != 1:
        raise InvitationUnavailable()
    db.refresh(invitation)
    _event(db, invitation, actor_id, "accepted", now)


def accept_new_account(db: Session, *, token: str, password: str, password_confirmation: str) -> User:
    """Create identity, membership, and consumption in the caller's transaction."""
    if password != password_confirmation or len(password) < 12 or len(password) > 1024:
        raise InvitationUnavailable()
    invitation = invitation_from_token(db, token, lock=True)
    request = db.get(AccessRequest, invitation.request_id)
    if request is None or request.expires_at <= utc_now():
        raise InvitationUnavailable()
    email = invitation.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise InvitationUnavailable()
    user = User(email=email, display_name=f"{request.first_name} {request.last_name}".strip(),
                password_hash=hash_password(password))
    db.add(user)
    db.flush()
    workspace = Workspace(name=f"{request.first_name.strip()}'s Workspace",
                          created_by_user_id=user.id)
    db.add(workspace)
    db.flush()
    invitation.workspace_id = workspace.id
    db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    _consume(db, invitation, actor_id=user.id)
    return user


def accept_existing_account(db: Session, *, token: str, user: User) -> User:
    """Consume for the matching existing identity without changing its access."""
    invitation = invitation_from_token(db, token, lock=True)
    if user.account_status != "active" or user.email.strip().lower() != invitation.email.strip().lower():
        raise InvitationUnavailable()
    _consume(db, invitation, actor_id=user.id)
    return user
