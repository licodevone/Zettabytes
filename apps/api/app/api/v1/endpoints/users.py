from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models import Membership, User
from app.schemas.user import UserMe, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


async def _load_me(db: DBSession, user: User) -> User:
    result = await db.scalar(
        select(User)
        .options(selectinload(User.memberships).selectinload(Membership.company))
        .where(User.id == user.id)
        .execution_options(populate_existing=True)
    )
    assert result is not None
    return result


@router.get("/me", response_model=UserMe, summary="Usuário autenticado e suas empresas")
async def read_me(user: CurrentUser, db: DBSession) -> User:
    return await _load_me(db, user)


@router.patch("/me", response_model=UserMe, summary="Atualiza o perfil do usuário")
async def update_me(payload: UserUpdate, user: CurrentUser, db: DBSession) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    return await _load_me(db, user)
