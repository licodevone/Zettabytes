"""Hash de senhas (Argon2 via pwdlib), emissão/validação de JWT e criptografia simétrica."""

import base64
import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import lru_cache
from typing import Any

import jwt
from cryptography.fernet import Fernet
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()

# Hash "fantasma" usado quando o usuário não existe, para que o tempo de resposta do login
# seja o mesmo com e sem usuário válido (mitiga enumeração de e-mails por timing).
_DUMMY_HASH = password_hash.hash("zettachat-timing-attack-dummy-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str | None) -> tuple[bool, str | None]:
    """Retorna (válida, novo_hash). `novo_hash` vem preenchido quando os parâmetros do
    algoritmo evoluíram e o hash armazenado deve ser atualizado."""
    if hashed is None:
        password_hash.verify(password, _DUMMY_HASH)
        return False, None
    return password_hash.verify_and_update(password, hashed)


# ─── JWT ─────────────────────────────────────────────────────────────────────


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: uuid.UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenPayload:
    sub: uuid.UUID
    jti: uuid.UUID
    type: TokenType
    exp: datetime


class InvalidTokenError(Exception):
    pass


def _encode(subject: uuid.UUID, token_type: TokenType, ttl: timedelta, **extra: Any) -> IssuedToken:
    now = datetime.now(UTC)
    jti = uuid.uuid4()
    expires_at = now + ttl
    payload = {
        "sub": str(subject),
        "jti": str(jti),
        "type": token_type.value,
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        **extra,
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM
    )
    return IssuedToken(token=token, jti=jti, expires_at=expires_at)


def create_access_token(user_id: uuid.UUID) -> IssuedToken:
    return _encode(
        user_id, TokenType.ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: uuid.UUID) -> IssuedToken:
    return _encode(user_id, TokenType.REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    try:
        data = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["sub", "jti", "type", "exp", "iat"]},
        )
        payload = TokenPayload(
            sub=uuid.UUID(data["sub"]),
            jti=uuid.UUID(data["jti"]),
            type=TokenType(data["type"]),
            exp=datetime.fromtimestamp(data["exp"], tz=UTC),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload.type is not expected_type:
        raise InvalidTokenError("Tipo de token inválido")
    return payload


# ─── Criptografia de segredos em repouso ─────────────────────────────────────


@lru_cache
def _fernet() -> Fernet:
    if settings.ENCRYPTION_KEY is not None:
        return Fernet(settings.ENCRYPTION_KEY.get_secret_value().encode())
    # Fora de produção, deriva uma chave estável do segredo JWT para facilitar o dev local.
    digest = hashlib.sha256(settings.JWT_SECRET_KEY.get_secret_value().encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
