from __future__ import annotations

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AgentKind, DocumentSourceType, DocumentStatus
from app.models.mixins import TenantMixin

EMBEDDING_DIMENSIONS = 1536


class AIAgent(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Persona de IA configurável pelo cliente (Comercial, Suporte, Agendamento...)."""

    __tablename__ = "ai_agents"

    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[AgentKind] = mapped_column(default=AgentKind.CUSTOM)
    model: Mapped[str] = mapped_column(String(64), default="claude-sonnet-5")
    system_prompt: Mapped[str]
    temperature: Mapped[float] = mapped_column(default=0.3)
    max_output_tokens: Mapped[int] = mapped_column(default=1024)
    # Skills habilitadas (nomes das tools do registry), ex.: ["rag.search", "calendar.book"].
    tools: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    # Regras de transbordo para humano: palavras-chave, sentimento, confiança mínima, max turnos.
    handoff_rules: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")

    knowledge_base: Mapped[KnowledgeBase | None] = relationship()


class KnowledgeBase(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None]
    embedding_model: Mapped[str] = mapped_column(String(64), default="voyage-3")

    documents: Mapped[list[KnowledgeDocument]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan", passive_deletes=True
    )


class KnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "knowledge_documents"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[DocumentSourceType]
    source_uri: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[DocumentStatus] = mapped_column(default=DocumentStatus.PENDING)
    checksum: Mapped[str | None] = mapped_column(String(64))  # evita reindexar conteúdo igual
    chunk_count: Mapped[int] = mapped_column(default=0, server_default="0")
    error: Mapped[str | None]

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")
    chunks: Mapped[list[KnowledgeChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Trecho vetorizado para RAG. Busca híbrida: pgvector (cosine) + full-text (tsvector)."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index(
            "ix_knowledge_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    content: Mapped[str]
    token_count: Mapped[int] = mapped_column(default=0)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
