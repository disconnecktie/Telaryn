"""Record non-sensitive deployment-administration actions for identity lifecycle."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class AccountAdminEvent(Base):
    """An auditable outcome without workspace content, credentials, or tokens."""

    __tablename__ = "account_admin_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    affected_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
