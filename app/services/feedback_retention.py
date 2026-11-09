"""Apply the owner-approved production retention policy to closed feedback."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.feedback import FeedbackAdminEvent, FeedbackSubmission


SCREENSHOT_RETENTION_DAYS = 90
FEEDBACK_RETENTION_DAYS = 365


@dataclass(frozen=True)
class FeedbackRetentionResult:
    screenshots_purged: int
    feedback_records_purged: int


def purge_closed_feedback(db: Session, *, now=None) -> FeedbackRetentionResult:
    """Purge screenshot bytes at 90 days and complete feedback at 365 days."""
    cutoff = now or utc_now()
    screenshot_deadline = cutoff - timedelta(days=SCREENSHOT_RETENTION_DAYS)
    feedback_deadline = cutoff - timedelta(days=FEEDBACK_RETENTION_DAYS)

    screenshot_result = db.execute(
        update(FeedbackSubmission)
        .where(
            FeedbackSubmission.closed_at.is_not(None),
            FeedbackSubmission.closed_at <= screenshot_deadline,
            FeedbackSubmission.screenshot_data.is_not(None),
        )
        .values(
            screenshot_data=None,
            screenshot_content_type=None,
            screenshot_filename=None,
            screenshot_size_bytes=None,
        )
    )

    expired_feedback = select(FeedbackSubmission.id).where(
        FeedbackSubmission.closed_at.is_not(None),
        FeedbackSubmission.closed_at <= feedback_deadline,
    )
    db.execute(
        delete(FeedbackAdminEvent).where(
            FeedbackAdminEvent.feedback_id.in_(expired_feedback)
        )
    )
    feedback_result = db.execute(
        delete(FeedbackSubmission).where(
            FeedbackSubmission.closed_at.is_not(None),
            FeedbackSubmission.closed_at <= feedback_deadline,
        )
    )
    return FeedbackRetentionResult(
        screenshots_purged=screenshot_result.rowcount,
        feedback_records_purged=feedback_result.rowcount,
    )
