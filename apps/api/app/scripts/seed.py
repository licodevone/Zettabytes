"""Seed idempotente do catálogo de planos."""

import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.db.session import SessionFactory, engine
from app.models import Plan

PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "price_cents": 9700,
        "ai_requests_per_month": 1_000,
        "ai_tokens_per_month": 2_000_000,
        "max_whatsapp_connections": 1,
        "max_members": 2,
        "max_flows": 10,
        "max_knowledge_documents": 20,
    },
    {
        "code": "pro",
        "name": "Pro",
        "price_cents": 29700,
        "ai_requests_per_month": 5_000,
        "ai_tokens_per_month": 10_000_000,
        "max_whatsapp_connections": 3,
        "max_members": 10,
        "max_flows": 100,
        "max_knowledge_documents": 200,
    },
    {
        "code": "scale",
        "name": "Scale",
        "price_cents": 89700,
        "ai_requests_per_month": 25_000,
        "ai_tokens_per_month": 50_000_000,
        "max_whatsapp_connections": 10,
        "max_members": 50,
        "max_flows": 1_000,
        "max_knowledge_documents": 2_000,
    },
]


async def main() -> None:
    async with SessionFactory() as db:
        for plan in PLANS:
            stmt = insert(Plan).values(**plan)
            await db.execute(
                stmt.on_conflict_do_update(
                    index_elements=[Plan.code],
                    set_={k: stmt.excluded[k] for k in plan if k != "code"},
                )
            )
        await db.commit()
    await engine.dispose()
    print(f"{len(PLANS)} planos sincronizados.")


if __name__ == "__main__":
    asyncio.run(main())
