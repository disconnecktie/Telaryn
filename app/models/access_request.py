"""Store public interest separately from accounts, workspaces, and private work."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class AccessRequest(Base):
    __tablename__ = "access_requests"
    __table_args__ = (
        CheckConstraint("status IN ('new', 'reviewed', 'approved', 'declined', 'closed')", name="ck_access_request_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(40), default="")
    biography: Mapped[str] = mapped_column(Text, default="")
    referral_source: Mapped[str] = mapped_column(String(20))
    referral_detail: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
    # An explicit deadline avoids treating repeated reads as an active follow-up.
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)


class AccessRequestEvent(Base):
    __tablename__ = "access_request_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("access_requests.id", ondelete="CASCADE"), index=True
    )
    # No free-form PII is duplicated into history; purge removes history too.
    reviewer_id: Mapped[int] = mapped_column()
    previous_status: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class AccessRequestLimit(Base):
    __tablename__ = "access_request_limit"
    id: Mapped[int] = mapped_column(primary_key=True)
    window_start: Mapped[datetime] = mapped_column(UTCDateTime())
    accepted: Mapped[int] = mapped_column()
