from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.billing import Subscription, UsageCounter
    from app.models.user import Membership
    from app.models.whatsapp import WhatsAppConnection


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant. Todos os dados de negócio são isolados por `company_id`."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    locale: Mapped[str] = mapped_column(String(16), default="pt-BR")
    logo_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    # Horário comercial, mensagens de ausência, preferências do Live Chat etc.
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="company", cascade="all, delete-orphan", passive_deletes=True
    )
    subscription: Mapped[Subscription | None] = relationship(
        back_populates="company", uselist=False, passive_deletes=True
    )
    usage_counters: Mapped[list[UsageCounter]] = relationship(
        back_populates="company", passive_deletes=True
    )
    whatsapp_connections: Mapped[list[WhatsAppConnection]] = relationship(
        back_populates="company", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Company {self.slug}>"
