"""Transactional persistence for a ticket drawer working session.

The drawer sends its final intended state only after the user reviews it.
This service is the boundary that keeps temporary UI interactions out of
the permanent ticket record and Activity timeline.
"""

from typing import Any

from sqlalchemy.orm import Session


def drawer_change_summary(
    *,
    ticket_before: dict[str, Any],
    ticket_after: dict[str, Any],
    criteria_before: list[dict[str, Any]],
    criteria_after: list[dict[str, Any]],
    subtasks_before: list[dict[str, Any]],
    subtasks_after: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the reviewable before/after payload for one drawer commit."""
    return {
        "ticket": {
            "previous": ticket_before,
            "new": ticket_after,
        },
        "acceptance_criteria": {
            "previous": criteria_before,
            "new": criteria_after,
        },
        "subtasks": {
            "previous": subtasks_before,
            "new": subtasks_after,
        },
    }


def commit_drawer_changes(db: Session, **_changes: Any) -> None:
    """Placeholder for the atomic drawer-save workflow.

    The API endpoint and validation schemas are introduced with the next
    incremental commit so this service can remain the single transaction owner.
    """
    raise NotImplementedError("Drawer commit wiring is not implemented yet.")
