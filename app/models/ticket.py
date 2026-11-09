"""Define the authoritative ticket record and its aggregate relationships."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Integer, String, Text, UniqueConstraint, event, update
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.identifiers import generate_public_id


class TicketStatus(str, Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketType(str, Enum):
    TASK = "task"
    PROBLEM = "problem"
    REQUEST = "request"
    RESEARCH = "research"
    DEVELOPMENT = "development"


def generate_ticket_public_id() -> str:
    """Return a compact opaque identifier suitable for cross-workspace references."""
    return generate_public_id("TKT")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_tickets_public_id"),
        UniqueConstraint("workspace_id", "workspace_ticket_number", name="uq_tickets_workspace_ticket_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # The opaque public identifier never changes and does not reveal row counts.
    public_id: Mapped[str] = mapped_column(String(18), default=generate_ticket_public_id, nullable=False)
    # Users see this familiar local number only inside the owning workspace.
    workspace_ticket_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Atomic allocators for immutable AC-001 and ST-001 references within this Ticket.
    next_acceptance_criterion_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    next_subtask_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Tickets carry the workspace directly so unprojected work remains private.
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(SQLEnum(TicketStatus), default=TicketStatus.READY, nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(SQLEnum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    ticket_type: Mapped[TicketType] = mapped_column(SQLEnum(TicketType), default=TicketType.TASK, nullable=False)

    # Private Tickets remain visible to the workspace but never enter AI context.
    ai_context_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False)

    project: Mapped["Project | None"] = relationship("Project", back_populates="tickets")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="tickets")
    subtasks: Mapped[list["Subtask"]] = relationship("Subtask", back_populates="ticket", cascade="all, delete-orphan")
    acceptance_criteria: Mapped[list["AcceptanceCriterion"]] = relationship("AcceptanceCriterion", back_populates="ticket", cascade="all, delete-orphan")
    ai_reviews: Mapped[list["AIReview"]] = relationship("AIReview", back_populates="ticket", cascade="all, delete-orphan")
    status_events: Mapped[list["TicketStatusEvent"]] = relationship("TicketStatusEvent", back_populates="ticket", cascade="all, delete-orphan")
    activity_events: Mapped[list["TicketActivityEvent"]] = relationship("TicketActivityEvent", back_populates="ticket", cascade="all, delete-orphan")
    update_entries: Mapped[list["TicketUpdateEntry"]] = relationship("TicketUpdateEntry", back_populates="ticket", cascade="all, delete-orphan")


@event.listens_for(Ticket, "before_insert")
def assign_ticket_identifiers(_mapper, connection, ticket: Ticket) -> None:
    """Assign durable Ticket references on every creation path."""
    if not ticket.public_id:
        ticket.public_id = generate_ticket_public_id()
    if ticket.workspace_ticket_number is not None:
        return

    from app.models.workspace import Workspace

    next_number = connection.execute(
        update(Workspace.__table__)
        .where(Workspace.id == ticket.workspace_id)
        .values(next_ticket_number=Workspace.next_ticket_number + 1)
        .returning(Workspace.next_ticket_number)
    ).scalar_one()
    ticket.workspace_ticket_number = next_number - 1
