"""Webhook da Meta para o número próprio da ACMEbr (não é Embedded Signup)."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ValidationError

from app.api.deps import DBSession
from app.core.config import settings
from app.services.whatsapp_channel import receive_message, require_channel, update_status

router = APIRouter(prefix="/webhooks/meta", tags=["WhatsApp"])
MAX_BODY_BYTES = 256 * 1024


class IncomingMessage(BaseModel):
    id: str = Field(min_length=1, max_length=192)
    sender: str = Field(alias="from", pattern=r"^[1-9]\d{7,14}$")
    timestamp: str = Field(pattern=r"^\d{1,12}$")
    type: str = Field(max_length=32)
    text: dict[str, Any] = Field(default_factory=dict)
    interactive: dict[str, Any] = Field(default_factory=dict)
    button: dict[str, Any] = Field(default_factory=dict)

    def content(self) -> tuple[str, bool]:
        value = None
        if self.type == "text":
            value = self.text.get("body")
        elif self.type == "button":
            value = self.button.get("text")
        elif self.type == "interactive":
            selected = self.interactive.get("button_reply") or self.interactive.get("list_reply")
            if isinstance(selected, dict):
                value = selected.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()[:4096], True
        return f"[Mensagem do tipo {self.type}; conteúdo não processado]", False


class MessageStatus(BaseModel):
    id: str = Field(max_length=192)
    status: Literal["sent", "delivered", "read", "failed"]


class Notification(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
    messages: list[IncomingMessage] = Field(default_factory=list, max_length=100)
    statuses: list[MessageStatus] = Field(default_factory=list, max_length=100)


class Change(BaseModel):
    field: str
    value: Notification


class Entry(BaseModel):
    id: str
    changes: list[Change] = Field(default_factory=list, max_length=100)


class Webhook(BaseModel):
    object: str
    entry: list[Entry] = Field(default_factory=list, max_length=100)


def verify_signature(body: bytes, signature: str) -> None:
    if not settings.META_APP_SECRET:
        raise HTTPException(503, "Webhook não configurado")
    expected = (
        "sha256="
        + hmac.new(
            settings.META_APP_SECRET.get_secret_value().encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
    )
    if not hmac.compare_digest(expected.encode(), signature.encode()):
        raise HTTPException(401, "Assinatura inválida")


@router.get("", response_class=PlainTextResponse)
async def verify_webhook(
    mode: Annotated[str, Query(alias="hub.mode")] = "",
    token: Annotated[str, Query(alias="hub.verify_token")] = "",
    challenge: Annotated[str, Query(alias="hub.challenge", max_length=256)] = "",
) -> str:
    expected = settings.META_WEBHOOK_VERIFY_TOKEN
    if not expected:
        raise HTTPException(503, "Webhook não configurado")
    if (
        mode != "subscribe"
        or not challenge
        or not secrets.compare_digest(
            token.encode(),
            expected.get_secret_value().encode(),
        )
    ):
        raise HTTPException(403, "Verificação inválida")
    return challenge


@router.post("")
async def receive_webhook(request: Request, db: DBSession) -> dict[str, bool]:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(413, "Evento muito grande")
    verify_signature(bytes(body), request.headers.get("x-hub-signature-256", ""))
    try:
        event = Webhook.model_validate_json(bytes(body))
    except ValidationError:
        raise HTTPException(400, "Evento inválido") from None
    if event.object != "whatsapp_business_account":
        return {"ok": True}
    require_channel()
    for entry in event.entry:
        if entry.id != settings.WHATSAPP_WABA_ID:
            continue
        for change in entry.changes:
            if change.field != "messages":
                continue
            value = change.value
            if str(value.metadata.get("phone_number_id", "")) != settings.WHATSAPP_PHONE_NUMBER_ID:
                continue
            for message in value.messages:
                try:
                    timestamp = datetime.fromtimestamp(int(message.timestamp), UTC)
                except (ValueError, OSError, OverflowError):
                    raise HTTPException(400, "Data de mensagem inválida") from None
                content, supported = message.content()
                await receive_message(
                    db,
                    provider_id=message.id,
                    sender=message.sender,
                    text=content,
                    timestamp=timestamp,
                    supported=supported,
                )
            for status in value.statuses:
                await update_status(db, status.id, status.status)
    return {"ok": True}
