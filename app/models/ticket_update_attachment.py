"""Reserve attachment provenance without authorizing attachment AI processing."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class TicketUpdateAttachment(Base):
    """Attachment metadata; file storage and ingestion are separate concerns."""

    __tablename__ = "ticket_update_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    update_entry_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_update_entries.id"),
        index=True,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )

    update_entry: Mapped["TicketUpdateEntry"] = relationship(
        "TicketUpdateEntry",
        back_populates="attachments",
    )
