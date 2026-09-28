from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EncryptedString, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConnectionStatus
from app.models.mixins import TenantMixin

if TYPE_CHECKING:
    from app.models.company import Company


class WhatsAppConnection(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Número de WhatsApp conectado pelo cliente via Embedded Signup (Meta Tech Provider).

    A cobrança das conversas é feita pela Meta diretamente na WABA do cliente;
    guardamos apenas o necessário para operar a Cloud API em nome dele.
    """

    __tablename__ = "whatsapp_connections"
    __table_args__ = (UniqueConstraint("phone_number_id"),)

    # `phone_number_id` é a chave de roteamento dos webhooks da Meta -> tenant.
    phone_number_id: Mapped[str] = mapped_column(String(64))
    waba_id: Mapped[str] = mapped_column(String(64), index=True)
    business_id: Mapped[str | None] = mapped_column(String(64))
    display_phone_number: Mapped[str] = mapped_column(String(32))
    verified_name: Mapped[str | None] = mapped_column(String(255))

    # Business Integration System User Token — criptografado em repouso (Fernet).
    access_token: Mapped[str] = mapped_column(EncryptedString())
    token_expires_at: Mapped[datetime | None]

    status: Mapped[ConnectionStatus] = mapped_column(default=ConnectionStatus.PENDING)
    quality_rating: Mapped[str | None] = mapped_column(String(16))  # GREEN / YELLOW / RED
    messaging_limit_tier: Mapped[str | None] = mapped_column(String(32))
    webhook_subscribed: Mapped[bool] = mapped_column(default=False, server_default="false")
    is_default: Mapped[bool] = mapped_column(default=False, server_default="false")
    last_error: Mapped[dict[str, Any] | None]
    connected_at: Mapped[datetime | None]

    company: Mapped[Company] = relationship(back_populates="whatsapp_connections")
