import re
import secrets
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Company, Membership, Plan, RefreshToken, Subscription, User
from app.models.enums import MemberRole, SubscriptionStatus
from app.schemas.auth import RegisterRequest, TokenPair

TRIAL_DAYS = 14
DEFAULT_PLAN_CODE = "starter"


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:48] or "empresa"


async def _unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while await db.scalar(select(Company.id).where(Company.slug == slug)):
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def register(db: AsyncSession, data: RegisterRequest) -> User:
    """Cria User + Company (tenant) + Membership OWNER + Subscription em trial, atomicamente."""
    if await get_user_by_email(db, data.email):
        raise ConflictError("E-mail já cadastrado")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    company = Company(name=data.company_name, slug=await _unique_slug(db, data.company_name))
    db.add_all([user, company])
    db.add(Membership(user=user, company=company, role=MemberRole.OWNER))

    plan_id = await db.scalar(select(Plan.id).where(Plan.code == DEFAULT_PLAN_CODE))
    if plan_id is not None:
        now = datetime.now(UTC)
        db.add(
            Subscription(
                company=company,
                plan_id=plan_id,
                provider=None,
                status=SubscriptionStatus.TRIALING,
                current_period_start=now,
                current_period_end=now + timedelta(days=TRIAL_DAYS),
                trial_ends_at=now + timedelta(days=TRIAL_DAYS),
            )
        )

    await db.flush()
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    valid, new_hash = verify_password(password, user.hashed_password if user else None)
    if user is None or not valid:
        raise AuthenticationError("E-mail ou senha incorretos")
    if not user.is_active:
        raise AuthenticationError("Usuário desativado")
    if new_hash:
        user.hashed_password = new_hash
    user.last_login_at = datetime.now(UTC)
    return user


async def issue_tokens(
    db: AsyncSession,
    user: User,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            jti=refresh.jti,
            user_id=user.id,
            expires_at=refresh.expires_at,
            user_agent=(user_agent or "")[:512] or None,
            ip_address=ip_address,
        )
    )
    await db.flush()
    return TokenPair(
        access_token=access.token,
        refresh_token=refresh.token,
        expires_at=access.expires_at,
        refresh_expires_at=refresh.expires_at,
    )


async def _revoke_all(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def rotate_refresh_token(
    db: AsyncSession,
    raw_token: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    """Troca um refresh token válido por um novo par (rotação). Reuso => revoga tudo."""
    try:
        payload = decode_token(raw_token, TokenType.REFRESH)
    except InvalidTokenError as exc:
        raise AuthenticationError("Refresh token inválido") from exc

    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.jti == payload.jti).with_for_update()
    )
    if stored is None or stored.user_id != payload.sub:
        raise AuthenticationError("Refresh token inválido")

    if stored.revoked_at is not None:
        # Token já usado/revogado sendo reapresentado: provável vazamento.
        await _revoke_all(db, stored.user_id)
        await db.commit()
        raise AuthenticationError("Refresh token reutilizado; sessões encerradas")

    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Usuário inválido")

    tokens = await issue_tokens(db, user, user_agent=user_agent, ip_address=ip_address)
    new_jti = decode_token(tokens.refresh_token, TokenType.REFRESH).jti
    stored.revoked_at = datetime.now(UTC)
    stored.replaced_by_jti = new_jti
    return tokens


async def revoke_refresh_token(db: AsyncSession, raw_token: str, user_id: uuid.UUID) -> None:
    try:
        payload = decode_token(raw_token, TokenType.REFRESH)
    except InvalidTokenError:
        return  # logout é idempotente
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.jti == payload.jti,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )


async def change_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    valid, _ = verify_password(current_password, user.hashed_password)
    if not valid:
        raise AuthenticationError("Senha atual incorreta")
    user.hashed_password = hash_password(new_password)
    await _revoke_all(db, user.id)
