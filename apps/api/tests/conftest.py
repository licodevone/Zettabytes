import os

# Precisa vir antes de qualquer import de `app`: faz o engine apontar para TEST_DATABASE_URL.
os.environ["ENVIRONMENT"] = "test"

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory, engine
from app.main import app
from app.models import Base
from app.scripts.seed import PLANS

PASSWORD = "S3nha-forte!"


@pytest.fixture(scope="session", autouse=True)
async def _schema() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


@pytest.fixture
async def plans(db: AsyncSession) -> None:
    from app.models import Plan

    db.add_all(Plan(**plan) for plan in PLANS)
    await db.commit()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register(
    client: AsyncClient, email: str = "ana@acme.com", company: str = "Acme Ltda"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ana Souza",
            "email": email,
            "password": PASSWORD,
            "company_name": company,
        },
    )
    assert response.status_code == 201, response.text
    tokens: dict[str, Any] = response.json()
    me = await client.get("/api/v1/users/me", headers=auth(tokens["access_token"]))
    tokens["company_id"] = me.json()["memberships"][0]["company"]["id"]
    return tokens


def auth(token: str, company_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if company_id:
        headers["X-Company-ID"] = company_id
    return headers
