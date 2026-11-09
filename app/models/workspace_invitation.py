"""Store invitation digests, never reusable activation credentials."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"
    __table_args__ = (
        # "member" remains readable for accepted legacy collaborator records.
        CheckConstraint("role IN ('member', 'owner')", name="ck_invitation_role"),
        CheckConstraint("status IN ('pending', 'accepted', 'revoked', 'delivery_failed')", name="ck_invitation_status"),
        CheckConstraint("generation > 0", name="ck_invitation_generation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("access_requests.id", ondelete="CASCADE"), unique=True)
    # Assigned atomically when a new account's private workspace is created.
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Snapshot the verified intake address. Never accept a client-selected recipient.
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[str] = mapped_column(String(30))
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    generation: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    delivery_provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    delivery_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_attempted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class WorkspaceInvitationEvent(Base):
    __tablename__ = "workspace_invitation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    invitation_id: Mapped[int] = mapped_column(ForeignKey("workspace_invitations.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int] = mapped_column()
    workspace_id: Mapped[int | None] = mapped_column(nullable=True)
    generation: Mapped[int] = mapped_column()
    event: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
