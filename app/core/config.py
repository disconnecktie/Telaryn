"""Environment-backed settings for persistence and optional AI providers."""

from typing import Literal

from pydantic import AliasChoices, Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Telaryn"
    app_version: str = "0.1.0"

    database_url: str = "sqlite:///./atlas.db"

    # Bootstrap identity is migration and private administration data, not request authority.
    bootstrap_user_email: str = Field(
        default="atlas.local@example.com",
        validation_alias=AliasChoices(
            "ATLAS_BOOTSTRAP_USER_EMAIL", "BOOTSTRAP_USER_EMAIL"
        ),
    )
    bootstrap_user_display_name: str = Field(
        default="Local user",
        validation_alias=AliasChoices(
            "ATLAS_BOOTSTRAP_USER_DISPLAY_NAME", "BOOTSTRAP_USER_DISPLAY_NAME"
        ),
    )
    bootstrap_workspace_name: str = Field(
        default="Telaryn Workspace",
        validation_alias=AliasChoices(
            "ATLAS_BOOTSTRAP_WORKSPACE_NAME", "BOOTSTRAP_WORKSPACE_NAME"
        ),
    )
    environment: str = "development"
    # Deployment intake is not owned by any individual workspace.
    access_request_reviewer_ids: list[PositiveInt] = Field(
        default_factory=list, validation_alias="ATLAS_ACCESS_REQUEST_REVIEWER_IDS"
    )
    # Deployment administrators govern Telaryn identities and account lifecycle.
    # This is deliberately separate from workspace ownership and intake review.
    deployment_administrator_ids: list[PositiveInt] = Field(
        default_factory=list, validation_alias="ATLAS_DEPLOYMENT_ADMINISTRATOR_IDS"
    )
    # Feedback reviewers may inspect private submissions, but receive no account-
    # lifecycle or access-request authority from this setting.
    feedback_reviewer_ids: list[PositiveInt] = Field(
        default_factory=list, validation_alias="ATLAS_FEEDBACK_REVIEWER_IDS"
    )
    access_request_intake_enabled: bool = Field(default=False, validation_alias="ATLAS_ACCESS_REQUEST_INTAKE_ENABLED")
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("ATLAS_LOG_LEVEL", "LOG_LEVEL"),
    )
    log_format: Literal["auto", "human", "json"] = Field(
        default="auto",
        validation_alias=AliasChoices("ATLAS_LOG_FORMAT", "LOG_FORMAT"),
    )
    session_cookie_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ATLAS_SESSION_COOKIE_SECURE", "SESSION_COOKIE_SECURE"
        ),
    )
    session_cookie_name: str = Field(
        default="atlas_session",
        validation_alias=AliasChoices(
            "ATLAS_SESSION_COOKIE_NAME", "SESSION_COOKIE_NAME"
        ),
    )
    session_lifetime_days: int = Field(default=7, ge=1, le=90)
    frontend_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias=AliasChoices("ATLAS_FRONTEND_ORIGINS", "FRONTEND_ORIGINS"),
    )
    public_app_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ATLAS_PUBLIC_APP_URL", "PUBLIC_APP_URL"),
    )
    invitation_delivery_provider: Literal["manual", "azure"] = Field(
        default="manual", validation_alias="ATLAS_INVITATION_DELIVERY_PROVIDER"
    )
    azure_communication_email_endpoint: str | None = Field(
        default=None, validation_alias="ATLAS_AZURE_COMMUNICATION_EMAIL_ENDPOINT"
    )
    azure_communication_email_sender: str | None = Field(
        default=None, validation_alias="ATLAS_AZURE_COMMUNICATION_EMAIL_SENDER"
    )
    azure_managed_identity_client_id: str | None = Field(
        default=None, validation_alias="AZURE_CLIENT_ID"
    )
    invitation_delivery_timeout_seconds: float = Field(
        default=30.0, gt=0, le=120,
        validation_alias="ATLAS_INVITATION_DELIVERY_TIMEOUT_SECONDS",
    )

    workspace_mode: str = "personal"
    ai_provider: str = "none"
    auth_provider: str = "local"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    ai_request_timeout_seconds: float = Field(default=45.0, gt=0)
    project_review_worker_poll_seconds: float = Field(default=1.0, gt=0, le=30)
    project_review_running_lease_seconds: float = Field(default=180.0, gt=45, le=3600)
    ai_review_max_output_tokens: int = Field(default=3500, ge=1000)
    ai_review_reasoning_effort: Literal[
        "none", "low", "medium", "high", "xhigh"
    ] = "low"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
