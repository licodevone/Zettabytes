"""Controle de limites de IA por tenant (licença do software; custos da Meta ficam fora)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QuotaExceededError
from app.models import Subscription, UsageCounter
from app.models.enums import SubscriptionStatus

# Status que liberam o uso do produto. PAST_DUE só é aceito dentro do período de carência.
_USABLE_STATUSES = {SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE}


def current_period(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m")


@dataclass(frozen=True, slots=True)
class UsageSnapshot:
    period: str
    subscription: Subscription | None
    ai_requests_used: int
    ai_requests_limit: int
    ai_tokens_used: int
    ai_tokens_limit: int

    @property
    def has_ai_quota(self) -> bool:
        return (
            self.ai_requests_used < self.ai_requests_limit
            and self.ai_tokens_used < self.ai_tokens_limit
        )


async def get_usage(db: AsyncSession, company_id: uuid.UUID) -> UsageSnapshot:
    period = current_period()
    subscription = await db.scalar(
        select(Subscription).where(Subscription.company_id == company_id)
    )
    counter = await db.scalar(
        select(UsageCounter).where(
            UsageCounter.company_id == company_id, UsageCounter.period == period
        )
    )
    plan = subscription.plan if subscription else None
    bonus = counter.bonus_ai_requests if counter else 0
    return UsageSnapshot(
        period=period,
        subscription=subscription,
        ai_requests_used=counter.ai_requests if counter else 0,
        ai_requests_limit=(plan.ai_requests_per_month if plan else 0) + bonus,
        ai_tokens_used=(counter.ai_input_tokens + counter.ai_output_tokens) if counter else 0,
        ai_tokens_limit=plan.ai_tokens_per_month if plan else 0,
    )


def subscription_is_usable(subscription: Subscription | None) -> bool:
    if subscription is None:
        return False
    if subscription.status in _USABLE_STATUSES:
        return True
    grace = subscription.grace_period_ends_at
    return subscription.status == SubscriptionStatus.PAST_DUE and bool(
        grace and grace > datetime.now(UTC)
    )


async def ensure_ai_quota(db: AsyncSession, company_id: uuid.UUID) -> UsageSnapshot:
    """Guard chamado pelo Agent Engine antes de cada chamada ao LLM."""
    usage = await get_usage(db, company_id)
    if not subscription_is_usable(usage.subscription):
        raise QuotaExceededError("Assinatura inativa")
    if not usage.has_ai_quota:
        raise QuotaExceededError("Limite mensal de IA atingido")
    return usage


async def record_ai_usage(
    db: AsyncSession,
    company_id: uuid.UUID,
    *,
    input_tokens: int,
    output_tokens: int,
    requests: int = 1,
) -> None:
    """Incremento atômico via UPSERT (seguro sob concorrência entre workers)."""
    stmt = insert(UsageCounter).values(
        id=uuid.uuid4(),
        company_id=company_id,
        period=current_period(),
        ai_requests=requests,
        ai_input_tokens=input_tokens,
        ai_output_tokens=output_tokens,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[UsageCounter.company_id, UsageCounter.period],
        set_={
            "ai_requests": UsageCounter.ai_requests + stmt.excluded.ai_requests,
            "ai_input_tokens": UsageCounter.ai_input_tokens + stmt.excluded.ai_input_tokens,
            "ai_output_tokens": UsageCounter.ai_output_tokens + stmt.excluded.ai_output_tokens,
            "updated_at": datetime.now(UTC),
        },
    )
    await db.execute(stmt)
