import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession
from app.core.config import settings
from app.models.site_chat import SiteConversation, SiteMessage
from app.services.site_assistant import WELCOME, reply_to
from app.services.whatsapp_channel import can_reply, deliver, require_channel


def gateway(x_site_key: Annotated[str, Header()] = "") -> None:
    expected = settings.SITE_CHAT_KEY
    if expected is None:
        raise HTTPException(503, "Canal indisponível")
    if not secrets.compare_digest(x_site_key, expected.get_secret_value()):
        raise HTTPException(401, "Acesso não autorizado")


router = APIRouter(prefix="/site/chat", tags=["Site chat"], dependencies=[Depends(gateway)])


class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    client_id: uuid.UUID


class StaffInput(TextInput):
    author: str = Field(min_length=1, max_length=120)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, token: str | None = None
) -> SiteConversation:
    conversation = await db.scalar(
        select(SiteConversation)
        .where(
            SiteConversation.id == conversation_id,
            SiteConversation.site_slug == settings.SITE_SLUG,
            SiteConversation.expires_at > datetime.now(UTC),
        )
        .with_for_update()
    )
    if conversation is None or (
        token is not None
        and (
            conversation.channel != "web"
            or not secrets.compare_digest(conversation.token_hash, token_hash(token))
        )
    ):
        raise HTTPException(404, "Conversa não encontrada")
    return conversation


async def snapshot(db: AsyncSession, conversation: SiteConversation) -> dict[str, Any]:
    messages = (
        await db.scalars(
            select(SiteMessage)
            .where(SiteMessage.conversation_id == conversation.id)
            .order_by(SiteMessage.created_at.desc(), SiteMessage.id.desc())
            .limit(400)
        )
    ).all()
    return {
        "id": str(conversation.id),
        "mode": conversation.mode,
        "channel": conversation.channel,
        "can_reply": can_reply(conversation),
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "text": m.text,
                "created_at": m.created_at.isoformat(),
                "delivery": m.delivery,
            }
            for m in reversed(messages)
        ],
    }


@router.get("/configuration")
async def configuration() -> dict[str, str | None]:
    return {"whatsapp_number": settings.WHATSAPP_NUMBER}


@router.post("/sessions", status_code=201)
async def create_session(db: DBSession, response: Response) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    conversation = SiteConversation(
        site_slug=settings.SITE_SLUG,
        token_hash=token_hash(token),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(conversation)
    await db.flush()
    db.add(SiteMessage(conversation_id=conversation.id, role="assistant", text=WELCOME))
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {**await snapshot(db, conversation), "token": token}


@router.get("/sessions/{conversation_id}")
async def get_session(
    conversation_id: uuid.UUID, db: DBSession, x_chat_token: Annotated[str, Header()]
) -> dict[str, Any]:
    return await snapshot(db, await get_conversation(db, conversation_id, x_chat_token))


@router.post("/sessions/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: TextInput,
    db: DBSession,
    x_chat_token: Annotated[str, Header()],
) -> dict[str, Any]:
    conversation = await get_conversation(db, conversation_id, x_chat_token)
    if not body.text.strip():
        raise HTTPException(422, "Escreva uma mensagem")
    duplicate = await db.scalar(
        select(SiteMessage.id).where(
            SiteMessage.conversation_id == conversation.id,
            SiteMessage.client_id == str(body.client_id),
        )
    )
    if duplicate:
        return await snapshot(db, conversation)
    count = await db.scalar(
        select(func.count())
        .select_from(SiteMessage)
        .where(SiteMessage.conversation_id == conversation.id)
    )
    recent = await db.scalar(
        select(func.count())
        .select_from(SiteMessage)
        .where(
            SiteMessage.conversation_id == conversation.id,
            SiteMessage.role == "visitor",
            SiteMessage.created_at > datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    if (count or 0) >= 395 or (recent or 0) >= 10:
        raise HTTPException(
            429, "Aguarde um minuto antes de continuar ou use o formulário de contato."
        )
    db.add(
        SiteMessage(
            conversation_id=conversation.id,
            role="visitor",
            text=body.text.strip(),
            client_id=str(body.client_id),
        )
    )
    if conversation.mode == "automatic":
        answer, human = reply_to(body.text)
        await db.flush()
        db.add(SiteMessage(conversation_id=conversation.id, role="assistant", text=answer))
        if human:
            conversation.mode = "human"
    conversation.updated_at = datetime.now(UTC)
    await db.commit()
    return await snapshot(db, conversation)


@router.get("/inbox")
async def inbox(db: DBSession) -> list[dict[str, Any]]:
    conversations = (
        await db.scalars(
            select(SiteConversation)
            .where(
                SiteConversation.site_slug == settings.SITE_SLUG,
                SiteConversation.expires_at > datetime.now(UTC),
            )
            .order_by(SiteConversation.updated_at.desc())
            .limit(100)
        )
    ).all()
    return [
        {
            "id": str(c.id),
            "mode": c.mode,
            "channel": c.channel,
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/inbox/{conversation_id}")
async def inbox_conversation(conversation_id: uuid.UUID, db: DBSession) -> dict[str, Any]:
    return await snapshot(db, await get_conversation(db, conversation_id))


@router.post("/inbox/{conversation_id}/messages")
async def staff_message(
    conversation_id: uuid.UUID, body: StaffInput, db: DBSession
) -> dict[str, Any]:
    conversation = await get_conversation(db, conversation_id)
    if not body.text.strip():
        raise HTTPException(422, "Escreva uma mensagem")
    duplicate = await db.scalar(
        select(SiteMessage.id).where(
            SiteMessage.conversation_id == conversation.id,
            SiteMessage.client_id == str(body.client_id),
        )
    )
    if not duplicate:
        if not can_reply(conversation):
            raise HTTPException(409, "Janela de atendimento do WhatsApp encerrada")
        if conversation.channel == "whatsapp":
            require_channel()
        message = SiteMessage(
            conversation_id=conversation.id,
            role="team",
            text=f"{body.author}: {body.text.strip()}",
            client_id=str(body.client_id),
            delivery="queued" if conversation.channel == "whatsapp" else None,
        )
        db.add(message)
        conversation.mode = "human"
        conversation.updated_at = datetime.now(UTC)
        await db.commit()
        if conversation.channel == "whatsapp":
            await deliver(db, message.id)
    elif conversation.channel == "whatsapp":
        await deliver(db, duplicate)
    return await snapshot(db, conversation)
