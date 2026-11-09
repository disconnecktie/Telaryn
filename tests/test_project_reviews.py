"""Verify durable asynchronous Project Review queue behavior."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.ai.base import (
    AIProvider,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIReviewResult,
)
from app.ai.project_review import ProjectReviewOutcome, ProjectReviewResult
from app.core.time import utc_now
from app.db.base import Base
from app.models.project import Project
from app.models.project_review_attempt import (
    ProjectReviewAttempt,
    ProjectReviewAttemptStatus,
)
from app.models.ticket import Ticket
from app.services.project_reviews import ProjectReviewService
from app.services.workspaces import get_or_create_bootstrap_workspace


class FakeProjectProvider(AIProvider):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.snapshots = []

    @property
    def name(self):
        return "fake"

    @property
    def model_name(self):
        return "fake-project-v1"

    def review_ticket(self, context):
        return AIReviewResult()

    def review_project(self, snapshot):
        self.snapshots.append(snapshot)
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


def no_concerns(summary="No material concerns."):
    return ProjectReviewResult(
        outcome=ProjectReviewOutcome.NO_MATERIAL_CONCERNS,
        summary=summary,
        findings=[],
        risks=[],
        planning_guidance=[],
        proposals=[],
        recommended_focus=None,
    )


class ProjectReviewServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.workspace = get_or_create_bootstrap_workspace(self.db)
        self.project = Project(workspace_id=self.workspace.id, name="Telaryn")
        self.db.add(self.project)
        self.db.flush()
        self.ticket = Ticket(
            workspace_id=self.workspace.id,
            project_id=self.project.id,
            title="Build Project Review",
        )
        self.db.add(self.ticket)
        self.db.commit()
        self.user_id = self.workspace.created_by_user_id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def queue_review(self, provider, *, force_fresh=False):
        return ProjectReviewService(provider).queue_project_review(
            self.project,
            workspace_id=self.workspace.id,
            user_id=self.user_id,
            db=self.db,
            reference_id="PRV-TEST01",
            force_fresh=force_fresh,
        )

    def execute(self, provider, attempt):
        attempt.status = ProjectReviewAttemptStatus.RUNNING
        attempt.started_at = utc_now()
        self.db.commit()
        return ProjectReviewService(provider).execute_queued_review(attempt, db=self.db)

    def test_queue_returns_without_provider_invocation(self):
        provider = FakeProjectProvider([no_concerns()])

        attempt = self.queue_review(provider)

        self.assertEqual(attempt.status, ProjectReviewAttemptStatus.PENDING)
        self.assertEqual(provider.calls, 0)
        self.assertIsNotNone(attempt.snapshot)
        self.assertEqual(attempt.review_reference, "PRV-TEST01")

    def test_worker_completes_full_snapshot_and_reuses_success(self):
        provider = FakeProjectProvider([no_concerns("Completed asynchronously.")])

        queued = self.queue_review(provider)
        completed = self.execute(provider, queued)
        reused = self.queue_review(provider)

        self.assertEqual(completed.status, ProjectReviewAttemptStatus.COMPLETED)
        self.assertEqual(completed.result["summary"], "Completed asynchronously.")
        self.assertEqual(provider.calls, 1)
        self.assertEqual(reused.id, completed.id)

    def test_failed_attempt_is_requeued_without_duplicate_provider_work(self):
        provider = FakeProjectProvider([
            AIProviderError("safe provider failure"),
            no_concerns("Retry succeeded."),
        ])

        failed = self.execute(provider, self.queue_review(provider))
        self.assertEqual(failed.status, ProjectReviewAttemptStatus.FAILED)
        self.assertEqual(failed.safe_error_category, "provider_error")

        requeued = self.queue_review(provider)
        self.assertEqual(requeued.id, failed.id)
        self.assertEqual(requeued.status, ProjectReviewAttemptStatus.PENDING)
        completed = self.execute(provider, requeued)

        self.assertEqual(completed.status, ProjectReviewAttemptStatus.COMPLETED)
        self.assertEqual(provider.calls, 2)

    def test_invalid_provider_output_is_retained_without_raw_output(self):
        provider = FakeProjectProvider([
            AIProviderInvalidResponseError("malformed structured output")
        ])

        attempt = self.execute(provider, self.queue_review(provider))

        self.assertEqual(attempt.status, ProjectReviewAttemptStatus.INVALID)
        self.assertEqual(attempt.safe_error_category, "invalid_schema")
        self.assertIsNone(attempt.result)

    def test_unsupported_evidence_is_recorded_as_invalid(self):
        provider = FakeProjectProvider([
            {
                "outcome": "findings_only",
                "summary": "Invented evidence must fail.",
                "findings": [{
                    "summary": "Unsupported claim",
                    "basis": "supported",
                    "significance": "important",
                    "evidence": [{
                        "source_type": "ticket",
                        "source_id": 999999,
                        "field_name": "title",
                        "summary": "Invented ticket",
                    }],
                }],
                "risks": [],
                "planning_guidance": [],
                "proposals": [],
                "recommended_focus": None,
            }
        ])

        attempt = self.execute(provider, self.queue_review(provider))

        self.assertEqual(attempt.status, ProjectReviewAttemptStatus.INVALID)
        self.assertEqual(attempt.safe_error_category, "invalid_evidence")

    def test_large_snapshot_is_queued_without_an_invented_preflight_limit(self):
        self.project.description = "x" * 121_000
        self.db.commit()
        provider = FakeProjectProvider([no_concerns()])

        attempt = self.queue_review(provider)

        self.assertEqual(attempt.status, ProjectReviewAttemptStatus.PENDING)
        self.assertEqual(provider.calls, 0)

    def test_private_ticket_is_excluded_before_provider_review(self):
        self.ticket.ai_context_enabled = False
        self.ticket.title = "Private compensation discussion"
        self.ticket.description = "This must never reach the provider."
        self.db.commit()
        provider = FakeProjectProvider([no_concerns()])

        queued = self.queue_review(provider)
        completed = self.execute(provider, queued)

        self.assertEqual(completed.status, ProjectReviewAttemptStatus.COMPLETED)
        self.assertEqual(
            completed.excluded_private_tickets,
            [{"id": self.ticket.id, "title": "Private compensation discussion"}],
        )
        self.assertNotIn(self.ticket.id, [item.id for item in provider.snapshots[0].tickets])
        rendered_snapshot = provider.snapshots[0].model_dump_json()
        self.assertNotIn("Private compensation discussion", rendered_snapshot)
        self.assertNotIn("This must never reach the provider.", rendered_snapshot)

    def test_confirmed_fresh_review_bypasses_success_reuse(self):
        provider = FakeProjectProvider([
            no_concerns("Original review."),
            no_concerns("Fresh review."),
        ])

        original = self.execute(provider, self.queue_review(provider))
        fresh = self.queue_review(provider, force_fresh=True)
        completed_fresh = self.execute(provider, fresh)

        self.assertNotEqual(fresh.id, original.id)
        self.assertEqual(completed_fresh.status, ProjectReviewAttemptStatus.COMPLETED)
        self.assertEqual(completed_fresh.result["summary"], "Fresh review.")
        self.assertEqual(provider.calls, 2)


if __name__ == "__main__":
    unittest.main()

