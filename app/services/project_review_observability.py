"""Emit privacy-safe, correlated lifecycle events for Project Review.

Project Review keeps its PRV workflow reference while routing events through the
shared Telaryn diagnostic boundary. Only bounded operational identifiers belong
here; project content, provider output, credentials, and exception messages do
not.
"""

import logging
import secrets

from app.core.diagnostics import log_diagnostic_event, safe_failure_location


def new_project_review_reference() -> str:
    """Return a short workflow reference that correlates a review and its logs."""
    return f"PRV-{secrets.token_hex(3).upper()}"


def log_project_review_event(
    event: str,
    *,
    reference_id: str,
    attempt_id: int | None = None,
    project_id: int | None = None,
    workspace_id: int | None = None,
    requester_id: int | None = None,
    provider: str | None = None,
    model: str | None = None,
    snapshot_prefix: str | None = None,
    duration_ms: int | None = None,
    safe_category: str | None = None,
    selected_ticket_count: int | None = None,
    exception_type: str | None = None,
    failure_location: str | None = None,
    level: int = logging.INFO,
) -> None:
    """Emit one review lifecycle event through the closed shared field set."""
    log_diagnostic_event(
        f"project_review_{event}",
        level=level,
        review_reference=reference_id,
        attempt_id=attempt_id,
        project_id=project_id,
        workspace_id=workspace_id,
        requester_id=requester_id,
        provider=provider,
        model=model,
        operation="project_review",
        outcome=event,
        snapshot_prefix=snapshot_prefix,
        duration_ms=duration_ms,
        safe_category=safe_category,
        selected_ticket_count=selected_ticket_count,
        exception_type=exception_type,
        failure_location=failure_location,
    )

