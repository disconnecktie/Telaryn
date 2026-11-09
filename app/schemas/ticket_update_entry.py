"""Validate append-only Ticket Updates and attachment metadata reads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class TicketUpdateEntryCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("An update cannot be empty.")

        if len(value) > 5000:
            raise ValueError("An update must be 5,000 characters or fewer.")

        return value


class TicketUpdateEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    content: str
    created_at: datetime
    attachment_count: int = 0
