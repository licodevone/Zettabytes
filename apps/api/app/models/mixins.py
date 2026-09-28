import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TenantMixin:
    """Toda tabela de domínio pertence a uma Company (tenant).

    A coluna `company_id` é redundante em tabelas filhas (ex.: nodes -> flows -> companies)
    de propósito: permite filtrar por tenant sem JOIN e habilita Row-Level Security no Postgres.
    """

    @declared_attr
    def company_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
        )
