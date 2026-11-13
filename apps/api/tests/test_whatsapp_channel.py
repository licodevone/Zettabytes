"""Integração real com PostgreSQL de testes; a Cloud API é sempre simulada."""

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import select, text

from app.core.config import settings
from app.models.site_chat import SiteConversation, SiteMessage
from app.services import whatsapp_channel

PATH = "/api/v1/webhooks/meta"
INBOX = "/api/v1/site/chat/inbox"
HEADERS = {"X-Site-Key": "site-test-key"}
SENDER = "5511999990000"
SEND_TEXT = whatsapp_channel.send_text


@pytest.fixture(autouse=True)
def channel(monkeypatch):
    for name, value in {
        "WHATSAPP_PHONE_NUMBER_ID": "phone-test",
        "WHATSAPP_WABA_ID": "waba-test",
        "WHATSAPP_API_VERSION": "v99.0",
        "WHATSAPP_ACCESS_TOKEN": SecretStr("not-a-real-token"),
        "WHATSAPP_NUMBER": SENDER,
        "META_APP_SECRET": SecretStr("app-test-secret"),
        "META_WEBHOOK_VERIFY_TOKEN": SecretStr("verify-test-token"),
        "SITE_CHAT_KEY": SecretStr("site-test-key"),
        "ENCRYPTION_KEY": SecretStr(Fernet.generate_key().decode()),
    }.items():
        monkeypatch.setattr(settings, name, value)
    sender = AsyncMock(side_effect=lambda *_: f"wamid.out.{uuid.uuid4()}")
    monkeypatch.setattr(whatsapp_channel, "send_text", sender)
    return sender


def event(message="Tenho um restaurante", *, message_id="wamid.in.1", age=0, phone="phone-test"):
    value = {
        "metadata": {"phone_number_id": phone},
        "messages": [
            {
                "id": message_id,
                "from": SENDER,
                "timestamp": str(int((datetime.now(UTC) - timedelta(hours=age)).timestamp())),
                "type": "text",
                "text": {"body": message},
            }
        ],
    }
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-test",
                "changes": [{"field": "messages", "value": value}],
            }
        ],
    }


async def post(client, payload, *, signature=None):
    body = json.dumps(payload, ensure_ascii=False).encode()
    digest = "sha256=" + hmac.new(b"app-test-secret", body, hashlib.sha256).hexdigest()
    return await client.post(
        PATH,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature or digest,
        },
    )


async def test_subscription_challenge_and_secret_required(client, monkeypatch):
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "verify-test-token",
        "hub.challenge": "123",
    }
    response = await client.get(PATH, params=params)
    assert response.status_code == 200 and response.text == "123"
    params["hub.verify_token"] = "wrong"
    assert (await client.get(PATH, params=params)).status_code == 403
    monkeypatch.setattr(settings, "META_WEBHOOK_VERIFY_TOKEN", None)
    assert (await client.get(PATH, params=params)).status_code == 503


async def test_signature_routing_size_and_stale_events(client, channel):
    assert (await post(client, event(), signature="sha256=wrong")).status_code == 401
    assert (await post(client, event(phone="someone-elses-number"))).status_code == 200
    assert (await post(client, event(age=25))).status_code == 200
    assert (await post(client, event(age=-1))).status_code == 200
    assert (
        await post(client, {"object": "whatsapp_business_account", "entry": "invalid"})
    ).status_code == 400
    response = await client.post(PATH, content=b"x" * (256 * 1024 + 1))
    assert response.status_code == 413
    channel.assert_not_awaited()


async def test_idempotency_history_and_encryption(client, db, channel):
    payload = event()
    assert (await post(client, payload)).status_code == 200
    assert (await post(client, payload)).status_code == 200
    channel.assert_awaited_once()
    inbox = (await client.get(INBOX, headers=HEADERS)).json()
    assert len(inbox) == 1 and inbox[0]["channel"] == "whatsapp"
    response = await client.get(f"{INBOX}/{inbox[0]['id']}", headers=HEADERS)
    messages = response.json()["messages"]
    assert len(messages) == 2
    assert "Comanda" in messages[-1]["text"] and messages[-1]["delivery"] == "sent"
    encrypted = await db.scalar(text("SELECT whatsapp_recipient FROM site_conversations LIMIT 1"))
    assert SENDER not in encrypted
    assert (await client.get(INBOX)).status_code == 401
    # A sessão web não pode usar a conversa WhatsApp, mesmo conhecendo o UUID.
    response = await client.get(
        f"/api/v1/site/chat/sessions/{inbox[0]['id']}", headers={**HEADERS, "X-Chat-Token": "wrong"}
    )
    assert response.status_code == 404


async def test_handoff_and_staff_reply(client, channel):
    await post(client, event("Quero um atendente"))
    await post(client, event("Mais detalhes", message_id="wamid.in.2"))
    channel.assert_awaited_once()
    inbox = (await client.get(INBOX, headers=HEADERS)).json()
    assert inbox[0]["mode"] == "human"
    conversation_id = inbox[0]["id"]
    data = {"text": "Olá! Sou da equipe.", "author": "Equipe", "client_id": str(uuid.uuid4())}
    response = await client.post(f"{INBOX}/{conversation_id}/messages", json=data, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["messages"][-1]["delivery"] == "sent"
    await client.post(f"{INBOX}/{conversation_id}/messages", json=data, headers=HEADERS)
    assert channel.await_count == 2


async def test_expired_window_prevents_staff_send(client, db, channel):
    await post(client, event())
    conversation = await db.scalar(select(SiteConversation))
    conversation.last_inbound_at = datetime.now(UTC) - timedelta(hours=25)
    await db.commit()
    response = await client.post(
        f"{INBOX}/{conversation.id}/messages",
        headers=HEADERS,
        json={"text": "Resposta", "author": "Equipe", "client_id": str(uuid.uuid4())},
    )
    assert response.status_code == 409
    assert channel.await_count == 1


async def test_timeout_is_visible_and_replay_does_not_duplicate(client, channel):
    channel.side_effect = httpx.ReadTimeout("simulated timeout")
    await post(client, event())
    await post(client, event())
    channel.assert_awaited_once()
    inbox = (await client.get(INBOX, headers=HEADERS)).json()
    response = await client.get(f"{INBOX}/{inbox[0]['id']}", headers=HEADERS)
    assert response.json()["messages"][-1]["delivery"] == "unknown"


async def test_delivery_events_do_not_reply_or_regress(client, db, channel):
    await post(client, event())
    outgoing = await db.scalar(select(SiteMessage).where(SiteMessage.role == "assistant"))
    for status in ("read", "delivered", "sent", "failed"):
        payload = event()
        value = payload["entry"][0]["changes"][0]["value"]
        value.pop("messages")
        value["statuses"] = [{"id": outgoing.provider_id, "status": status}]
        assert (await post(client, payload)).status_code == 200
    await db.refresh(outgoing)
    assert outgoing.delivery == "read"
    channel.assert_awaited_once()


async def test_concurrent_replay_delivers_once(client, channel):
    responses = await asyncio.gather(post(client, event()), post(client, event()))
    assert all(response.status_code == 200 for response in responses)
    channel.assert_awaited_once()


async def test_web_chat_remains_independent(client, channel):
    response = await client.post("/api/v1/site/chat/sessions", headers=HEADERS)
    assert response.status_code == 201
    session = response.json()
    response = await client.post(
        f"/api/v1/site/chat/sessions/{session['id']}/messages",
        headers={**HEADERS, "X-Chat-Token": session["token"]},
        json={"text": "Quero um orçamento", "client_id": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    assert response.json()["channel"] == "web"
    channel.assert_not_awaited()


async def test_unknown_media_hands_off_without_inventing_content(client, channel):
    payload = event()
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message["type"] = "audio"
    message.pop("text")
    assert (await post(client, payload)).status_code == 200
    inbox = (await client.get(INBOX, headers=HEADERS)).json()
    assert inbox[0]["mode"] == "human"
    assert "Por enquanto consigo responder a textos" in channel.call_args.args[1]


async def test_burst_stops_automation_but_keeps_history(client, channel):
    for i in range(12):
        assert (await post(client, event(message_id=f"wamid.in.{i}"))).status_code == 200
    assert channel.await_count == 10
    inbox = (await client.get(INBOX, headers=HEADERS)).json()
    assert inbox[0]["mode"] == "human"
    response = await client.get(f"{INBOX}/{inbox[0]['id']}", headers=HEADERS)
    assert len([m for m in response.json()["messages"] if m["role"] == "visitor"]) == 12


async def test_cloud_api_request_uses_configured_number_and_token(monkeypatch):
    # Implementação real com HTTP de saída interceptado.
    client_class = httpx.AsyncClient
    requests = []

    def handle(request):
        requests.append(request)
        assert str(request.url) == "https://graph.facebook.com/v99.0/phone-test/messages"
        assert request.headers["Authorization"] == "Bearer not-a-real-token"
        body = json.loads(request.content)
        assert body["to"] == SENDER and body["messaging_product"] == "whatsapp"
        assert body["text"] == {"body": "Resposta de teste", "preview_url": False}
        return httpx.Response(200, json={"messages": [{"id": "wamid.mock.response"}]})

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handle), **kwargs),
    )
    assert await SEND_TEXT(SENDER, "Resposta de teste") == "wamid.mock.response"
    assert len(requests) == 1


@pytest.mark.parametrize("code,state", [(400, "failed"), (500, "unknown")])
async def test_provider_failure_is_saved_without_replay(client, channel, code, state):
    response = httpx.Response(
        code, request=httpx.Request("POST", "https://graph.facebook.com/mock")
    )
    channel.side_effect = httpx.HTTPStatusError(
        "simulated rejection", request=response.request, response=response
    )
    await post(client, event())
    await post(client, event())
    channel.assert_awaited_once()
    inbox = (await client.get(INBOX, headers=HEADERS)).json()
    result = await client.get(f"{INBOX}/{inbox[0]['id']}", headers=HEADERS)
    assert result.json()["messages"][-1]["delivery"] == state
