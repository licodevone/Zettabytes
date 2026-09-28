from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DBSession, Tenant, TenantAdmin
from app.models import Company, Membership, User
from app.schemas.company import CompanyRead, CompanyUpdate, MemberRead, UsageRead
from app.services import usage_service

router = APIRouter(prefix="/companies/current", tags=["Companies"])


@router.get("", response_model=CompanyRead, summary="Empresa (tenant) ativa")
async def read_company(ctx: Tenant) -> Company:
    return ctx.company


@router.patch("", response_model=CompanyRead, summary="Atualiza a empresa (owner/admin)")
async def update_company(payload: CompanyUpdate, ctx: TenantAdmin, db: DBSession) -> Company:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ctx.company, field, value)
    await db.commit()
    return ctx.company


@router.get("/members", response_model=list[MemberRead], summary="Membros da equipe")
async def list_members(ctx: Tenant, db: DBSession) -> list[MemberRead]:
    rows = await db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.company_id == ctx.company_id)
        .order_by(User.full_name)
    )
    return [
        MemberRead(
            id=m.id,
            user_id=u.id,
            role=m.role,
            is_online=m.is_online,
            full_name=u.full_name,
            email=u.email,
        )
        for m, u in rows
    ]


@router.get("/usage", response_model=UsageRead, summary="Consumo de IA no período e limites")
async def read_usage(ctx: Tenant, db: DBSession) -> UsageRead:
    usage = await usage_service.get_usage(db, ctx.company_id)
    sub = usage.subscription
    return UsageRead(
        period=usage.period,
        plan_code=sub.plan.code if sub else None,
        subscription_status=sub.status if sub else None,
        ai_requests_used=usage.ai_requests_used,
        ai_requests_limit=usage.ai_requests_limit,
        ai_tokens_used=usage.ai_tokens_used,
        ai_tokens_limit=usage.ai_tokens_limit,
    )
