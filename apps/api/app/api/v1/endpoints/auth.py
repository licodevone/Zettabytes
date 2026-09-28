from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import ChangePasswordRequest, RefreshRequest, RegisterRequest, TokenPair
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def _client_meta(request: Request) -> dict[str, str | None]:
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None,
    }


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Cria conta, empresa (tenant) e inicia o trial",
)
async def register(payload: RegisterRequest, request: Request, db: DBSession) -> TokenPair:
    user = await auth_service.register(db, payload)
    tokens = await auth_service.issue_tokens(db, user, **_client_meta(request))
    await db.commit()
    return tokens


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login OAuth2 (password flow) — `username` = e-mail",
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: DBSession,
) -> TokenPair:
    user = await auth_service.authenticate(db, form.username, form.password)
    tokens = await auth_service.issue_tokens(db, user, **_client_meta(request))
    await db.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair, summary="Rotaciona o refresh token")
async def refresh(payload: RefreshRequest, request: Request, db: DBSession) -> TokenPair:
    tokens = await auth_service.rotate_refresh_token(
        db, payload.refresh_token, **_client_meta(request)
    )
    await db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoga o refresh token")
async def logout(payload: RefreshRequest, user: CurrentUser, db: DBSession) -> None:
    await auth_service.revoke_refresh_token(db, payload.refresh_token, user.id)
    await db.commit()


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Altera a senha e encerra todas as sessões",
)
async def change_password(payload: ChangePasswordRequest, user: CurrentUser, db: DBSession) -> None:
    await auth_service.change_password(db, user, payload.current_password, payload.new_password)
    await db.commit()
