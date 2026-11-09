"""Verify Project Review diagnostics remain useful without leaking user content."""

import re
import unittest
from unittest.mock import patch

from app.api.project_reviews import _unexpected_review_error
from app.services.project_review_observability import (
    log_project_review_event,
    new_project_review_reference,
    safe_failure_location,
)


SENSITIVE_VALUES = (
    "Install backyard fence for dog containment",
    "Boo will be upset",
    "sk-proj-secret",
    "session-cookie-secret",
    '{"raw_provider_output": "private"}',
)


class ProjectReviewObservabilityTests(unittest.TestCase):
    def test_reference_has_stable_support_format(self):
        self.assertRegex(new_project_review_reference(), r"^PRV-[0-9A-F]{6}$")

    def test_lifecycle_log_contains_only_explicit_safe_fields(self):
        with patch("app.core.diagnostics.logger.log") as log:
            log_project_review_event(
                "completed",
                reference_id="PRV-8F31C2",
                attempt_id=7,
                project_id=3,
                workspace_id=2,
                requester_id=4,
                provider="openai",
                model="gpt-test",
                snapshot_prefix="abc123",
                duration_ms=125,
            )

        log.assert_called_once()
        output = repr(log.call_args.args) + repr(log.call_args.kwargs)
        self.assertIn("'atlas_event': 'project_review_completed'", output)
        self.assertIn("'atlas_review_reference': 'PRV-8F31C2'", output)
        self.assertIn("'atlas_attempt_id': 7", output)
        for sensitive in SENSITIVE_VALUES:
            self.assertNotIn(sensitive, output)

    def test_unexpected_api_failure_returns_reference_without_exception_message(self):
        try:
            raise RuntimeError(" ".join(SENSITIVE_VALUES))
        except RuntimeError as error:
            location = safe_failure_location(error)
            with patch("app.core.diagnostics.logger.log") as log:
                response = _unexpected_review_error(
                    error,
                    operation="list",
                    reference_id="PRV-A1B2C3",
                    project_id=3,
                    workspace_id=2,
                    requester_id=4,
                )

        self.assertEqual(response.status_code, 500)
        self.assertIn("Reference: PRV-A1B2C3", response.detail)
        self.assertIsNotNone(location)
        log.assert_called_once()
        output = repr(log.call_args.args) + repr(log.call_args.kwargs)
        self.assertIn("'atlas_exception_type': 'RuntimeError'", output)
        self.assertIn("'atlas_safe_category': 'list'", output)
        for sensitive in SENSITIVE_VALUES:
            self.assertNotIn(sensitive, output)
            self.assertNotIn(sensitive, response.detail)

    def test_reference_is_not_credential_shaped(self):
        reference = new_project_review_reference()
        self.assertFalse(re.search(r"sk-|bearer|session", reference, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
