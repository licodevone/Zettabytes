from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BillingInterval, BillingProvider, SubscriptionStatus
from app.models.mixins import TenantMixin

if TYPE_CHECKING:
    from app.models.company import Company


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Catálogo de planos (global, não é tenant-scoped). Limites = licença do software.

    Custos de mensagens da Meta NÃO passam por aqui: o cliente paga direto à Meta
    (modelo Tech Provider). Nós limitamos apenas o uso de IA e recursos do produto.
    """

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), unique=True)  # ex.: starter, pro, scale
    name: Mapped[str] = mapped_column(String(64))
    price_cents: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    interval: Mapped[BillingInterval] = mapped_column(default=BillingInterval.MONTH)
    stripe_price_id: Mapped[str | None] = mapped_column(String(128))
    asaas_plan_ref: Mapped[str | None] = mapped_column(String(128))

    ai_requests_per_month: Mapped[int]
    ai_tokens_per_month: Mapped[int] = mapped_column(BigInteger)
    max_whatsapp_connections: Mapped[int] = mapped_column(default=1)
    max_members: Mapped[int] = mapped_column(default=3)
    max_flows: Mapped[int] = mapped_column(default=10)
    max_knowledge_documents: Mapped[int] = mapped_column(default=50)
    features: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    is_public: Mapped[bool] = mapped_column(default=True, server_default="true")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("company_id"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    provider: Mapped[BillingProvider | None]  # None durante o trial, antes do checkout
    status: Mapped[SubscriptionStatus] = mapped_column(default=SubscriptionStatus.TRIALING)
    external_customer_id: Mapped[str | None] = mapped_column(String(128), index=True)
    external_subscription_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True
    )
    current_period_start: Mapped[datetime | None]
    current_period_end: Mapped[datetime | None]
    trial_ends_at: Mapped[datetime | None]
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, server_default="false")
    canceled_at: Mapped[datetime | None]
    # Tolerância após falha de pagamento antes de bloquear o uso (dunning).
    grace_period_ends_at: Mapped[datetime | None]

    company: Mapped[Company] = relationship(back_populates="subscription")
    plan: Mapped[Plan] = relationship(lazy="joined")


class UsageCounter(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Contador mensal de consumo de IA por tenant. Incrementado atomicamente via UPSERT."""

    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("company_id", "period"),)

    period: Mapped[str] = mapped_column(String(7))  # "YYYY-MM"
    ai_requests: Mapped[int] = mapped_column(default=0, server_default="0")
    ai_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    ai_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    embedding_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    # Pacotes extras de IA comprados avulsos no período.
    bonus_ai_requests: Mapped[int] = mapped_column(default=0, server_default="0")

    company: Mapped[Company] = relationship(back_populates="usage_counters")


class BillingEvent(UUIDPrimaryKeyMixin, Base):
    """Log idempotente de webhooks do gateway. `(provider, external_event_id)` é único."""

    __tablename__ = "billing_events"
    __table_args__ = (UniqueConstraint("provider", "external_event_id"),)

    provider: Mapped[BillingProvider]
    external_event_id: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(96), index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    payload: Mapped[dict[str, Any]]
    processed_at: Mapped[datetime | None]
    error: Mapped[str | None]
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
