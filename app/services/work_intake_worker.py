"""Run durable Work Intake operations outside browser request lifecycles."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.exc import OperationalError

from app.ai.factory import get_ai_provider
from app.core.config import settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.work_intake_attempt import (
    WorkIntakeAttempt,
    WorkIntakeAttemptStatus,
)
from app.services.work_intake import WorkIntakeService


def _claim_next_work_intake() -> bool:
    """Atomically claim one queued or abandoned operation across backend workers."""
    db = SessionLocal()
    try:
        lease_cutoff = utc_now() - timedelta(
            seconds=settings.project_review_running_lease_seconds
        )
        try:
            candidate_id = db.scalar(
                select(WorkIntakeAttempt.id)
                .where(
                    WorkIntakeAttempt.dismissed_at.is_(None),
                    or_(
                        WorkIntakeAttempt.status == WorkIntakeAttemptStatus.PENDING,
                        (
                            WorkIntakeAttempt.status == WorkIntakeAttemptStatus.RUNNING
                        )
                        & (WorkIntakeAttempt.started_at < lease_cutoff),
                    ),
                )
                .order_by(WorkIntakeAttempt.created_at, WorkIntakeAttempt.id)
                .limit(1)
            )
        except OperationalError:
            db.rollback()
            return False
        if candidate_id is None:
            return False

        claimed = db.execute(
            update(WorkIntakeAttempt)
            .where(
                WorkIntakeAttempt.id == candidate_id,
                WorkIntakeAttempt.dismissed_at.is_(None),
                or_(
                    WorkIntakeAttempt.status == WorkIntakeAttemptStatus.PENDING,
                    (
                        WorkIntakeAttempt.status == WorkIntakeAttemptStatus.RUNNING
                    )
                    & (WorkIntakeAttempt.started_at < lease_cutoff),
                ),
            )
            .values(
                status=WorkIntakeAttemptStatus.RUNNING,
                started_at=utc_now(),
                completed_at=None,
            )
        )
        if claimed.rowcount != 1:
            db.rollback()
            return False
        db.commit()

        attempt = db.get(WorkIntakeAttempt, candidate_id)
        if attempt is None:
            return False
        WorkIntakeService(get_ai_provider()).execute_queued_attempt(attempt, db=db)
        return True
    finally:
        db.close()


async def run_work_intake_worker(stop_event: asyncio.Event) -> None:
    """Process durable Work Intake operations until application shutdown."""
    while not stop_event.is_set():
        processed = await asyncio.to_thread(_claim_next_work_intake)
        if processed:
            continue
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.project_review_worker_poll_seconds,
            )
        except TimeoutError:
            pass
