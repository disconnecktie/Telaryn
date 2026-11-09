"""Construct the configured AI provider without leaking vendor choices into routes."""

from app.ai.base import AIProvider
from app.ai.mock import MockAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.core.config import settings


class AIProviderUnavailableError(RuntimeError):
    """Report deployment configuration gaps without exposing provider details."""


def get_ai_provider() -> AIProvider:
    """Build the configured provider so API routes remain provider-agnostic."""
    provider = settings.ai_provider.lower().strip()

    if provider == "mock":
        return MockAIProvider()

    if provider == "openai":
        if not settings.openai_api_key:
            raise AIProviderUnavailableError(
                "Telaryn AI is not configured for this deployment."
            )

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.ai_request_timeout_seconds,
            max_output_tokens=settings.ai_review_max_output_tokens,
            reasoning_effort=settings.ai_review_reasoning_effort,
        )

    raise AIProviderUnavailableError(
        "Telaryn AI is not configured for this deployment."
    )
