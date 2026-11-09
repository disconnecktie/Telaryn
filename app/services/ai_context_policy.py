"""Enforce project AI-context policy before any provider-visible work begins."""

from fastapi import HTTPException

from app.models.project import Project
from app.models.ticket import Ticket


PRIVATE_TICKET_AI_MESSAGE = (
    "Telaryn AI is unavailable for this Private ticket. Ticket privacy controls "
    "AI processing only; workspace access is unchanged."
)

PRIVATE_PROJECT_AI_MESSAGE = (
    "Telaryn AI is unavailable for this Private project. Project privacy controls "
    "AI processing only; workspace access is unchanged."
)


def require_project_ai_context(project: Project | None) -> None:
    """Reject provider work for a Private project before any context is assembled."""
    if project is not None and not project.ai_context_enabled:
        raise HTTPException(status_code=409, detail=PRIVATE_PROJECT_AI_MESSAGE)


def require_ticket_ai_context(ticket: Ticket) -> None:
    """Reject provider work for a Private Ticket before its context is assembled."""
    require_ticket_ai_context_enabled(ticket.ai_context_enabled)


def require_ticket_ai_context_enabled(ai_context_enabled: bool) -> None:
    """Reject a transient Private Ticket draft before provider selection."""
    if not ai_context_enabled:
        raise HTTPException(status_code=409, detail=PRIVATE_TICKET_AI_MESSAGE)

