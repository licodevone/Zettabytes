"""Canal WhatsApp da ACMEbr: histórico, deduplicação e entrega pela Cloud API."""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.site_chat import SiteConversation, SiteMessage
from app.services.site_assistant import reply_to

logger = logging.getLogger(__name__)
DeliveryStatus = Literal["sent", "delivered", "read", "failed"]


def can_reply(conversation: SiteConversation) -> bool:
    return conversation.channel == "web" or (
        conversation.last_inbound_at is not None
        and conversation.last_inbound_at > datetime.now(UTC) - timedelta(hours=24)
    )


def require_channel() -> None:
    if not all(
        (
            settings.WHATSAPP_PHONE_NUMBER_ID,
            settings.WHATSAPP_WABA_ID,
            settings.WHATSAPP_API_VERSION,
            settings.WHATSAPP_ACCESS_TOKEN,
            settings.ENCRYPTION_KEY,
        )
    ):
        raise HTTPException(503, "Canal WhatsApp não configurado")


async def send_text(recipient: str, text: str) -> str:
    require_channel()
    assert settings.WHATSAPP_ACCESS_TOKEN is not None
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN.get_secret_value()}"
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "text",
                "text": {"body": text, "preview_url": False},
            },
        )
    response.raise_for_status()
    provider_id: str = response.json()["messages"][0]["id"]
    return provider_id


async def deliver(db: AsyncSession, message_id: uuid.UUID) -> bool:
    """Claim persistido antes do envio: timeout/replay nunca reenvia algo incerto."""
    message = await db.scalar(
        select(SiteMessage).where(SiteMessage.id == message_id).with_for_update()
    )
    assert message is not None
    if message.delivery != "queued":
        return message.delivery in ("sent", "delivered", "read")
    conversation = await db.get(SiteConversation, message.conversation_id)
    assert conversation is not None
    if not can_reply(conversation):
        message.delivery = "expired"
        await db.commit()
        return False
    recipient = conversation.whatsapp_recipient
    assert recipient is not None
    require_channel()
    message.delivery = "sending"
    await db.commit()
    try:
        provider_id = await send_text(recipient, message.text)
    except httpx.HTTPStatusError as error:
        # Só 4xx confirma rejeição. Em 5xx/timeout o resultado pode ser ambíguo.
        message.delivery = "failed" if 400 <= error.response.status_code < 500 else "unknown"
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        message.delivery = "unknown"
    else:
        message.provider_id = provider_id
        message.delivery = "sent"
    await db.commit()
    if message.delivery != "sent":
        logger.warning(
            "WhatsApp delivery requires review: message=%s state=%s", message.id, message.delivery
        )
    return message.delivery == "sent"


async def receive_message(
    db: AsyncSession,
    *,
    provider_id: str,
    sender: str,
    text: str,
    timestamp: datetime,
    supported: bool = True,
) -> None:
    now = datetime.now(UTC)
    if timestamp > now + timedelta(minutes=5) or timestamp < now - timedelta(hours=24):
        return  # Não reabre a janela com eventos antigos ou um relógio inválido.
    conversation_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"acmebr:{settings.SITE_SLUG}:{settings.WHATSAPP_PHONE_NUMBER_ID}:{sender}",
    )
    # Conflito entre workers serializa no mesmo registro, inclusive no primeiro evento.
    await db.execute(
        insert(SiteConversation)
        .values(
            id=conversation_id,
            site_slug=settings.SITE_SLUG,
            token_hash=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
            channel="whatsapp",
            whatsapp_recipient=sender,
            expires_at=now + timedelta(days=30),
        )
        .on_conflict_do_nothing(index_elements=[SiteConversation.id])
    )
    conversation = await db.scalar(
        select(SiteConversation)
        .where(
            SiteConversation.id == conversation_id,
            SiteConversation.site_slug == settings.SITE_SLUG,
            SiteConversation.channel == "whatsapp",
        )
        .with_for_update()
    )
    assert conversation is not None
    previous = await db.scalar(select(SiteMessage.id).where(SiteMessage.provider_id == provider_id))
    reply_id = f"wa-auto:{hashlib.sha256(provider_id.encode()).hexdigest()[:48]}"
    if previous:
        previous_outgoing_id = await db.scalar(
            select(SiteMessage.id).where(
                SiteMessage.conversation_id == conversation.id,
                SiteMessage.client_id == reply_id,
            )
        )
        await db.commit()
        if previous_outgoing_id:
            await deliver(db, previous_outgoing_id)
        return
    conversation.last_inbound_at = max(conversation.last_inbound_at or timestamp, timestamp)
    conversation.updated_at = now
    conversation.expires_at = now + timedelta(days=30)
    db.add(
        SiteMessage(
            conversation_id=conversation.id,
            role="visitor",
            text=text,
            provider_id=provider_id,
            created_at=timestamp,
        )
    )
    recent = await db.scalar(
        select(func.count())
        .select_from(SiteMessage)
        .where(
            SiteMessage.conversation_id == conversation.id,
            SiteMessage.role == "visitor",
            SiteMessage.created_at > now - timedelta(minutes=1),
        )
    )
    # Evita respostas automáticas ilimitadas; preserva as mensagens para a equipe.
    if (recent or 0) >= 10:
        conversation.mode = "human"
    outgoing_id = None
    if conversation.mode == "automatic":
        answer, human = (
            reply_to(text, channel="whatsapp")
            if supported
            else (
                "Recebi sua mensagem. Por enquanto consigo responder a textos. "
                "Vou deixar este atendimento com a equipe, "
                "que responderá quando estiver disponível.",
                True,
            )
        )
        outgoing = SiteMessage(
            conversation_id=conversation.id,
            role="assistant",
            text=answer,
            client_id=reply_id,
            delivery="queued",
        )
        db.add(outgoing)
        await db.flush()
        outgoing_id = outgoing.id
        if human:
            conversation.mode = "human"
    await db.commit()
    if outgoing_id:
        await deliver(db, outgoing_id)


async def update_status(db: AsyncSession, provider_id: str, status: DeliveryStatus) -> None:
    message = await db.scalar(
        select(SiteMessage)
        .join(SiteConversation)
        .where(
            SiteMessage.provider_id == provider_id,
            SiteMessage.role != "visitor",
            SiteConversation.site_slug == settings.SITE_SLUG,
            SiteConversation.channel == "whatsapp",
        )
        .with_for_update()
    )
    if message:
        order = {"sent": 1, "delivered": 2, "read": 3}
        current = message.delivery or "sent"
        if (status == "failed" and current not in ("delivered", "read")) or (
            status != "failed" and order.get(status, 0) > order.get(current, 0)
        ):
            message.delivery = status
        await db.commit()
