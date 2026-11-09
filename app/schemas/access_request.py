"""Validate minimal public-interest data without accepting identity or access grants."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Context = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
RequestStatus = Literal["new", "reviewed", "approved", "declined", "closed"]


class AccessRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Name
    last_name: Name
    email: EmailStr = Field(max_length=254)
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] = ""
    biography: Context = ""
    referral_source: Literal["linkedin", "friend", "search", "github", "other"]
    referral_detail: ShortText = ""
    notes: Context = ""


class AccessRequestReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RequestStatus

