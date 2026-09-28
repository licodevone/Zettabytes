import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, Text, TypeDecorator, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Convenção de nomes determinística: o Alembic gera migrations estáveis
# e os nomes de constraints ficam previsíveis entre ambientes.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class EncryptedString(TypeDecorator[str]):
    """Coluna que criptografa o valor com Fernet antes de gravar (ex.: tokens da Meta)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        from app.core.security import encrypt_secret

        return None if value is None else encrypt_secret(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        from app.core.security import decrypt_secret

        return None if value is None else decrypt_secret(value)


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Mapeia anotações Python -> tipos SQL, permitindo `Mapped[...]` sem repetir o tipo.
    type_annotation_map = {  # noqa: RUF012 (atributo de classe do DeclarativeBase)
        uuid.UUID: PG_UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB(),
        list[Any]: JSONB(),
        str: Text(),
        # Enums são gravados como VARCHAR validado pela aplicação (sem ENUM nativo nem CHECK):
        # adicionar um valor novo não exige migration nem lock de tabela.
        enum.Enum: SAEnum(
            enum.Enum,
            native_enum=False,
            create_constraint=False,
            length=32,
            values_callable=lambda cls: [member.value for member in cls],
        ),
    }


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
