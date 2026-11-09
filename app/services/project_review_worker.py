"""Run durable Project Review jobs outside browser request lifecycles."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.exc import OperationalError

from app.ai.factory import get_ai_provider
from app.core.config import settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.project_review_attempt import (
    ProjectReviewAttempt,
    ProjectReviewAttemptStatus,
)
from app.services.project_review_observability import log_project_review_event
from app.services.project_reviews import ProjectReviewService


def _claim_next_project_review() -> bool:
    """Atomically claim one queued or abandoned attempt across backend workers."""
    db = SessionLocal()
    try:
        lease_cutoff = utc_now() - timedelta(
            seconds=settings.project_review_running_lease_seconds
        )
        try:
            candidate_id = db.scalar(
                select(ProjectReviewAttempt.id)
                .where(
                    or_(
                        ProjectReviewAttempt.status == ProjectReviewAttemptStatus.PENDING,
                        (
                            ProjectReviewAttempt.status
                            == ProjectReviewAttemptStatus.RUNNING
                        )
                        & (ProjectReviewAttempt.started_at < lease_cutoff),
                    )
                )
                .order_by(ProjectReviewAttempt.created_at, ProjectReviewAttempt.id)
                .limit(1)
            )
        except OperationalError:
            # Tests and startup diagnostics may construct the app before migrations.
            db.rollback()
            return False
        if candidate_id is None:
            return False

        claimed = db.execute(
            update(ProjectReviewAttempt)
            .where(
                ProjectReviewAttempt.id == candidate_id,
                or_(
                    ProjectReviewAttempt.status
                    == ProjectReviewAttemptStatus.PENDING,
                    (
                        ProjectReviewAttempt.status
                        == ProjectReviewAttemptStatus.RUNNING
                    )
                    & (ProjectReviewAttempt.started_at < lease_cutoff),
                ),
            )
            .values(
                status=ProjectReviewAttemptStatus.RUNNING,
                started_at=utc_now(),
                completed_at=None,
            )
        )
        if claimed.rowcount != 1:
            db.rollback()
            return False
        db.commit()

        attempt = db.get(ProjectReviewAttempt, candidate_id)
        if attempt is None:
            return False
        log_project_review_event(
            "started",
            reference_id=attempt.review_reference or "PRV-UNKNOWN",
            attempt_id=attempt.id,
            project_id=attempt.project_id,
            workspace_id=attempt.workspace_id,
            requester_id=attempt.requested_by_user_id,
            provider=attempt.provider,
            model=attempt.model,
            snapshot_prefix=attempt.snapshot_version[:12],
        )
        ProjectReviewService(get_ai_provider()).execute_queued_review(attempt, db=db)
        return True
    finally:
        db.close()


async def run_project_review_worker(stop_event: asyncio.Event) -> None:
    """Process one durable Project Review at a time until application shutdown."""
    while not stop_event.is_set():
        processed = await asyncio.to_thread(_claim_next_project_review)
        if processed:
            continue
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.project_review_worker_poll_seconds,
            )
        except TimeoutError:
            pass
