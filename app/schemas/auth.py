"""Validate local login input and expose only safe authenticated identity data."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=1024)


class AuthenticatedUserRead(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    workspace_id: int
    workspace_name: str
