from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FlowStatus, FlowTriggerType, NodeType
from app.models.mixins import TenantMixin


class Flow(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Fluxo de automação desenhado no Flow Builder (React Flow / XYFlow)."""

    __tablename__ = "flows"
    __table_args__ = (Index("ix_flows_company_status", "company_id", "status"),)

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None]
    status: Mapped[FlowStatus] = mapped_column(default=FlowStatus.DRAFT)
    trigger_type: Mapped[FlowTriggerType] = mapped_column(default=FlowTriggerType.KEYWORD)
    # ex.: {"keywords": ["preço", "orçamento"], "match": "contains"} ou {"ad_ids": [...]}
    trigger_config: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    priority: Mapped[int] = mapped_column(default=0, server_default="0")
    whatsapp_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("whatsapp_connections.id", ondelete="SET NULL")
    )
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    # Snapshot imutável do grafo publicado: o runtime executa isto, não o rascunho.
    published_graph: Mapped[dict[str, Any] | None]
    published_at: Mapped[datetime | None]
    # Viewport do canvas (x, y, zoom) para reabrir o editor no mesmo ponto.
    viewport: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")

    nodes: Mapped[list[Node]] = relationship(
        back_populates="flow", cascade="all, delete-orphan", passive_deletes=True
    )
    edges: Mapped[list[Edge]] = relationship(
        back_populates="flow", cascade="all, delete-orphan", passive_deletes=True
    )


class Node(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "nodes"
    __table_args__ = (UniqueConstraint("flow_id", "client_id"),)

    flow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"), index=True
    )
    # ID gerado no frontend pelo React Flow; estável entre salvamentos do rascunho.
    client_id: Mapped[str] = mapped_column(String(64))
    type: Mapped[NodeType]
    label: Mapped[str | None] = mapped_column(String(120))
    position_x: Mapped[float] = mapped_column(default=0.0)
    position_y: Mapped[float] = mapped_column(default=0.0)
    # Configuração específica do tipo (texto, botões, condição, id do agente de IA...).
    data: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")

    flow: Mapped[Flow] = relationship(back_populates="nodes")


class Edge(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "edges"
    __table_args__ = (UniqueConstraint("flow_id", "client_id"),)

    flow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("flows.id", ondelete="CASCADE"), index=True
    )
    client_id: Mapped[str] = mapped_column(String(64))
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), index=True
    )
    # Handle de saída (ex.: id do botão clicado, "true"/"false" de uma condição).
    source_handle: Mapped[str | None] = mapped_column(String(64))
    label: Mapped[str | None] = mapped_column(String(120))

    flow: Mapped[Flow] = relationship(back_populates="edges")
