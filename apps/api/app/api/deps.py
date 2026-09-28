"""Dependências de injeção: sessão do banco, usuário autenticado, tenant ativo e RBAC."""

import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.db.session import get_db
from app.models import Company, Membership, User
from app.models.enums import MemberRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    description="Faça login com e-mail (campo `username`) e senha para obter o JWT.",
)

DBSession = Annotated[AsyncSession, Depends(get_db)]

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não foi possível validar as credenciais",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(db: DBSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        payload = decode_token(token, TokenType.ACCESS)
    except InvalidTokenError:
        raise _CREDENTIALS_EXCEPTION from None

    user = await db.get(User, payload.sub)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Contexto multi-tenant resolvido a partir do header `X-Company-ID`."""

    user: User
    company: Company
    membership: Membership

    @property
    def company_id(self) -> uuid.UUID:
        return self.company.id

    @property
    def role(self) -> MemberRole:
        return self.membership.role


async def get_tenant(
    db: DBSession,
    user: CurrentUser,
    x_company_id: Annotated[
        uuid.UUID,
        Header(description="ID da empresa (tenant) em que a operação será executada."),
    ],
) -> TenantContext:
    membership = await db.scalar(
        select(Membership)
        .options(joinedload(Membership.company))
        .where(Membership.user_id == user.id, Membership.company_id == x_company_id)
    )
    # 404 (e não 403) para não revelar a existência de tenants alheios.
    if membership is None or not membership.company.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")
    return TenantContext(user=user, company=membership.company, membership=membership)


Tenant = Annotated[TenantContext, Depends(get_tenant)]


def require_roles(
    *roles: MemberRole,
) -> Callable[[TenantContext], Coroutine[Any, Any, TenantContext]]:
    """Uso: `ctx: Annotated[TenantContext, Depends(require_roles(MemberRole.OWNER))]`."""
    allowed = set(roles)

    async def checker(ctx: Tenant) -> TenantContext:
        if ctx.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")
        return ctx

    return checker


TenantAdmin = Annotated[TenantContext, Depends(require_roles(MemberRole.OWNER, MemberRole.ADMIN))]
TenantOwner = Annotated[TenantContext, Depends(require_roles(MemberRole.OWNER))]
