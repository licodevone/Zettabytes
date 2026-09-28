import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import MemberRole, SubscriptionStatus
from app.schemas.common import APIModel


class CompanyRead(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    timezone: str
    locale: str
    logo_url: str | None
    settings: dict[str, Any]
    created_at: datetime


class CompanyUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=16)
    logo_url: str | None = Field(default=None, max_length=512)
    settings: dict[str, Any] | None = None


class MemberRead(APIModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: MemberRole
    is_online: bool
    full_name: str
    email: str


class UsageRead(APIModel):
    period: str
    plan_code: str | None
    subscription_status: SubscriptionStatus | None
    ai_requests_used: int
    ai_requests_limit: int
    ai_tokens_used: int
    ai_tokens_limit: int
