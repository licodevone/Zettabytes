from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def build_engine(url: str | None = None) -> AsyncEngine:
    return create_async_engine(
        url or settings.database_url,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        pool_pre_ping=True,
        connect_args={
            "server_settings": {"application_name": "zettabytes-api", "timezone": "UTC"},
        },
    )


engine = build_engine()

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # Evita lazy-loads implícitos (proibidos em async) após o commit.
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependência FastAPI: uma sessão por request.

    O commit é explícito nos services: o código após o `yield` de uma dependência roda depois
    que a resposta já foi enviada, então um commit aqui poderia falhar sem o cliente saber.
    """
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
