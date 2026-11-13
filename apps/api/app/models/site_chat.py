"""Canal web independente de números e sessões da Meta."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EncryptedString, TimestampMixin, UUIDPrimaryKeyMixin


class SiteConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "site_conversations"
    __table_args__ = (Index("ix_site_conversations_site_updated", "site_slug", "updated_at"),)

    site_slug: Mapped[str] = mapped_column(String(64))
    token_hash: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16), default="automatic")
    channel: Mapped[str] = mapped_column(String(16), default="web", server_default="web")
    whatsapp_recipient: Mapped[str | None] = mapped_column(EncryptedString())
    last_inbound_at: Mapped[datetime | None]
    expires_at: Mapped[datetime]


class SiteMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "site_messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "client_id", name="uq_site_message_client"),
        Index("ix_site_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("site_conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(16))
    text: Mapped[str]
    client_id: Mapped[str | None] = mapped_column(String(64))
    provider_id: Mapped[str | None] = mapped_column(String(192), unique=True)
    delivery: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), server_default=func.now()
    )
