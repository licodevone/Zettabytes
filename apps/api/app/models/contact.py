from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.mixins import TenantMixin


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Lead/cliente final que conversa com a empresa pelo WhatsApp."""

    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("company_id", "wa_id"),)

    wa_id: Mapped[str] = mapped_column(String(32))  # identificador do WhatsApp (E.164 sem '+')
    name: Mapped[str | None] = mapped_column(String(255))
    profile_name: Mapped[str | None] = mapped_column(String(255))  # nome do perfil no WhatsApp
    email: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, server_default="{}")
    # Campos personalizados capturados pelos fluxos / agentes (ex.: cpf, interesse, orçamento).
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    opted_in: Mapped[bool] = mapped_column(default=True, server_default="true")
    is_blocked: Mapped[bool] = mapped_column(default=False, server_default="false")
    # Memória de longo prazo do contato, consolidada pelo agente de IA ao fim das sessões.
    ai_profile_summary: Mapped[str | None]
    last_seen_at: Mapped[datetime | None]
