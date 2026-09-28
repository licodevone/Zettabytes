from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.contact import Contact
from app.models.enums import (
    MessageDirection,
    MessageStatus,
    MessageType,
    SenderType,
    SessionMode,
    SessionStatus,
)
from app.models.mixins import TenantMixin


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Conversa ativa entre um contato e um número conectado.

    Guarda o estado de execução (fluxo/nó atual, modo IA/humano) e a memória de curto prazo.
    """

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_inbox", "company_id", "status", "last_message_at"),
        # No máximo UMA sessão aberta por contato+número.
        Index(
            "uq_chat_sessions_open_per_contact",
            "contact_id",
            "whatsapp_connection_id",
            unique=True,
            postgresql_where=text("status <> 'closed'"),
        ),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), index=True
    )
    whatsapp_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("whatsapp_connections.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[SessionStatus] = mapped_column(default=SessionStatus.OPEN)
    mode: Mapped[SessionMode] = mapped_column(default=SessionMode.FLOW)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    current_flow_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("flows.id", ondelete="SET NULL")
    )
    current_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL")
    )
    ai_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_agents.id", ondelete="SET NULL")
    )
    # Memória de curto prazo: variáveis do fluxo, slots coletados, estado do agente.
    context: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    # Resumo incremental da conversa (compressão da janela de contexto da IA).
    summary: Mapped[str | None]
    handoff_reason: Mapped[str | None] = mapped_column(String(255))
    ai_paused_until: Mapped[datetime | None]

    # Janela de 24h da Meta: fora dela, só templates aprovados podem ser enviados.
    last_inbound_at: Mapped[datetime | None]
    last_message_at: Mapped[datetime | None]
    unread_count: Mapped[int] = mapped_column(default=0, server_default="0")
    closed_at: Mapped[datetime | None]

    contact: Mapped[Contact] = relationship(lazy="joined")
    messages: Mapped[list[Message]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_session_created", "session_id", "created_at"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE")
    )
    direction: Mapped[MessageDirection]
    sender_type: Mapped[SenderType]
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    type: Mapped[MessageType] = mapped_column(default=MessageType.TEXT)
    # Texto plano extraído (busca, contexto da IA, preview no inbox).
    text: Mapped[str | None]
    # Payload bruto/estruturado (mídia, botões, template, localização...).
    content: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    # `wamid` da Meta — único, garante idempotência no reprocessamento de webhooks.
    wa_message_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    reply_to_wa_message_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[MessageStatus] = mapped_column(default=MessageStatus.QUEUED)
    error: Mapped[dict[str, Any] | None]
    ai_input_tokens: Mapped[int | None]
    ai_output_tokens: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, index=True
    )
    status_updated_at: Mapped[datetime | None]

    session: Mapped[ChatSession] = relationship(back_populates="messages")
