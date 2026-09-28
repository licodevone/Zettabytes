import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import MemberRole
from app.schemas.common import APIModel


class CompanySummary(APIModel):
    id: uuid.UUID
    name: str
    slug: str


class MembershipRead(APIModel):
    id: uuid.UUID
    role: MemberRole
    company: CompanySummary


class UserRead(APIModel):
    id: uuid.UUID
    email: str
    full_name: str
    avatar_url: str | None
    is_active: bool
    email_verified_at: datetime | None
    created_at: datetime


class UserMe(UserRead):
    memberships: list[MembershipRead]


class UserUpdate(APIModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=512)
