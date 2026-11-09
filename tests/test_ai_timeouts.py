"""Verify provider failures stay bounded, safe, and isolated from unrelated APIs."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.ai.base import AIProvider, AIProviderError, AIProviderTimeoutError
from app.ai.context import WorkContext
from app.api import ai_drafts
from app.main import app
from app.services.auth import require_auth_context


@pytest.fixture(autouse=True)
def authenticated_provider_test():
    """Keep provider tests focused while restoring application dependencies afterward."""
    app.dependency_overrides[require_auth_context] = lambda: object()
    yield
    app.dependency_overrides.pop(require_auth_context, None)


class TimeoutProvider(AIProvider):
    """Deterministic provider used to verify Telaryn's timeout translation."""

    @property
    def name(self) -> str:
        return "timeout-test"

    @property
    def model_name(self) -> str:
        return "never-responds"

    def review_ticket(self, context: WorkContext):
        raise AIProviderTimeoutError("provider deadline reached")


class FailedProvider(TimeoutProvider):
    def review_ticket(self, context: WorkContext):
        raise AIProviderError("secret provider detail")


class StalledProvider(TimeoutProvider):
    """Hold one provider thread open so unrelated API work can be exercised."""

    def __init__(self, started: Event, release: Event):
        self.started = started
        self.release = release

    def review_ticket(self, context: WorkContext):
        self.started.set()
        self.release.wait(timeout=2)
        raise AIProviderTimeoutError("provider deadline reached")


def test_draft_review_timeout_returns_504_and_api_remains_healthy(monkeypatch):
    monkeypatch.setattr(ai_drafts, "get_ai_provider", lambda: TimeoutProvider())
    client = TestClient(app)

    response = client.post(
        "/ai-reviews/draft",
        json={"title": "Timeout test", "description": "Keep this draft safe."},
    )

    assert response.status_code == 504
    assert "draft was not changed" in response.json()["detail"]
    assert client.get("/health").json() == {"status": "healthy"}


def test_stalled_review_does_not_block_unrelated_api_requests(monkeypatch):
    started = Event()
    release = Event()
    provider = StalledProvider(started, release)
    monkeypatch.setattr(ai_drafts, "get_ai_provider", lambda: provider)

    def request_review():
        return TestClient(app).post(
            "/ai-reviews/draft",
            json={"title": "Concurrent availability test"},
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        review_request = executor.submit(request_review)
        assert started.wait(timeout=1), "The simulated provider never started."

        try:
            health_response = TestClient(app).get("/health")
            assert health_response.status_code == 200
            assert health_response.json() == {"status": "healthy"}
        finally:
            release.set()

        assert review_request.result(timeout=2).status_code == 504


def test_provider_failure_returns_safe_retryable_message(monkeypatch):
    monkeypatch.setattr(ai_drafts, "get_ai_provider", lambda: FailedProvider())
    with patch("app.core.diagnostics.logger.log") as log:
        response = TestClient(app).post(
            "/ai-reviews/draft",
            json={"title": "Private provider failure test"},
        )

    assert response.status_code == 502
    assert "temporarily unavailable" in response.json()["detail"]
    rendered = response.text + repr(log.call_args_list)
    assert "secret provider detail" not in rendered
    assert "Private provider failure test" not in rendered
    events = [call.kwargs["extra"] for call in log.call_args_list if "extra" in call.kwargs]
    assert any(
        event.get("atlas_operation") == "draft_ticket_review"
        and event.get("atlas_outcome") == "provider_failure"
        and event.get("atlas_provider") == "timeout-test"
        for event in events
    )

