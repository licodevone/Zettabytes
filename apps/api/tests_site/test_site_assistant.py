import uuid

import pytest
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError

from app.api.v1.endpoints.site_chat import TextInput, gateway, token_hash
from app.core.config import settings
from app.services.site_assistant import reply_to


@pytest.mark.parametrize("message", ["Quero um atendente", "preciso de um humano", "RECLAMAÇÃO"])
def test_handoff_is_explicit(message):
    answer, handoff = reply_to(message)
    assert handoff
    assert "quando estiver disponível" in answer


@pytest.mark.parametrize("message", ["preço", "qual o valor?", "quanto custa?"])
def test_no_unverified_price(message):
    answer, handoff = reply_to(message)
    assert "Não tenho um preço confirmado" in answer
    assert not handoff


def test_product_routing():
    answer, handoff = reply_to("Tenho um restaurante")
    assert "Comanda" in answer
    assert not handoff


def test_key_required_and_constant_comparison(monkeypatch):
    monkeypatch.setattr(settings, "SITE_CHAT_KEY", None)
    with pytest.raises(HTTPException) as error:
        gateway("")
    assert error.value.status_code == 503
    monkeypatch.setattr(settings, "SITE_CHAT_KEY", SecretStr("test-key"))
    with pytest.raises(HTTPException) as error:
        gateway("wrong")
    assert error.value.status_code == 401
    gateway("test-key")


def test_token_is_hashed_and_large_messages_rejected():
    assert token_hash("token-a") != token_hash("token-b")
    assert "token-a" not in token_hash("token-a")
    with pytest.raises(ValidationError):
        TextInput(text="x" * 2001, client_id=uuid.uuid4())
