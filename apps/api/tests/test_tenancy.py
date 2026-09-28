import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Membership, User, WhatsAppConnection
from app.models.enums import MemberRole
from app.services import usage_service
from tests.conftest import auth, register

pytestmark = pytest.mark.usefixtures("plans")


async def test_tenant_header_is_required_and_scoped(client: AsyncClient) -> None:
    ana = await register(client)
    bob = await register(client, email="bob@globex.com", company="Globex")
    token = ana["access_token"]

    missing = await client.get("/api/v1/companies/current", headers=auth(token))
    assert missing.status_code == 422

    own = await client.get("/api/v1/companies/current", headers=auth(token, ana["company_id"]))
    assert own.status_code == 200
    assert own.json()["name"] == "Acme Ltda"

    # Ana não pode acessar o tenant do Bob — e não descobre que ele existe (404).
    foreign = await client.get("/api/v1/companies/current", headers=auth(token, bob["company_id"]))
    assert foreign.status_code == 404
    random = await client.get("/api/v1/companies/current", headers=auth(token, str(uuid.uuid4())))
    assert random.status_code == 404


async def test_rbac_agent_cannot_update_company(client: AsyncClient, db: AsyncSession) -> None:
    ana = await register(client)
    carl = await register(client, email="carl@acme.com", company="Carl Co")
    carl_id = await db.scalar(select(User.id).where(User.email == "carl@acme.com"))
    db.add(
        Membership(user_id=carl_id, company_id=uuid.UUID(ana["company_id"]), role=MemberRole.AGENT)
    )
    await db.commit()

    headers = auth(carl["access_token"], ana["company_id"])
    assert (await client.get("/api/v1/companies/current", headers=headers)).status_code == 200
    denied = await client.patch(
        "/api/v1/companies/current", json={"name": "Hacked"}, headers=headers
    )
    assert denied.status_code == 403

    owner = await client.patch(
        "/api/v1/companies/current",
        json={"name": "Acme S.A."},
        headers=auth(ana["access_token"], ana["company_id"]),
    )
    assert owner.status_code == 200
    assert owner.json()["name"] == "Acme S.A."

    members = await client.get("/api/v1/companies/current/members", headers=headers)
    assert {m["role"] for m in members.json()} == {"owner", "agent"}


async def test_usage_reports_trial_plan_and_counts_atomically(
    client: AsyncClient, db: AsyncSession
) -> None:
    ana = await register(client)
    company_id = uuid.UUID(ana["company_id"])
    headers = auth(ana["access_token"], ana["company_id"])

    usage = (await client.get("/api/v1/companies/current/usage", headers=headers)).json()
    assert usage["plan_code"] == "starter"
    assert usage["subscription_status"] == "trialing"
    assert usage["ai_requests_used"] == 0
    assert usage["ai_requests_limit"] == 1000

    for _ in range(3):
        await usage_service.record_ai_usage(db, company_id, input_tokens=100, output_tokens=50)
    await db.commit()
    snapshot = await usage_service.ensure_ai_quota(db, company_id)
    assert snapshot.ai_requests_used == 3
    assert snapshot.ai_tokens_used == 450


async def test_whatsapp_token_is_encrypted_at_rest(db: AsyncSession, client: AsyncClient) -> None:
    ana = await register(client)
    conn = WhatsAppConnection(
        company_id=uuid.UUID(ana["company_id"]),
        phone_number_id="1234567890",
        waba_id="waba-1",
        display_phone_number="+55 11 99999-0000",
        access_token="EAAG-super-secret-token",
    )
    db.add(conn)
    await db.commit()

    raw = await db.scalar(
        text("SELECT access_token FROM whatsapp_connections WHERE id = :id"), {"id": conn.id}
    )
    assert raw is not None and "super-secret" not in raw
    db.expunge_all()
    loaded = await db.get(WhatsAppConnection, conn.id)
    assert loaded is not None and loaded.access_token == "EAAG-super-secret-token"


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
