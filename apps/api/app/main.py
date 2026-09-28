import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIRoute
from scalar_fastapi import get_scalar_api_reference

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.db.session import engine

logger = logging.getLogger("zettabytes")

OPENAPI_TAGS = [
    {"name": "Health", "description": "Verificações de liveness/readiness."},
    {"name": "Auth", "description": "Cadastro, login OAuth2 (JWT), refresh e logout."},
    {"name": "Users", "description": "Perfil do usuário autenticado."},
    {
        "name": "Companies",
        "description": "Tenant ativo (header `X-Company-ID`), equipe e consumo de IA.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.validate_for_production()
    logger.info("Zettabytes API iniciando (%s)", settings.ENVIRONMENT.value)
    yield
    await engine.dispose()


def _operation_id(route: APIRoute) -> str:
    """operationIds limpos (`auth-login`) => nomes legíveis no client TS gerado."""
    tag = str(route.tags[0]).lower() if route.tags else "default"
    return f"{tag}-{route.name}".replace("_", "-")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        summary="Automação de WhatsApp com fluxos e agentes de IA generativa.",
        openapi_tags=OPENAPI_TAGS,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True},
        generate_unique_id_function=_operation_id,
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - started) * 1000:.1f}"
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/scalar", include_in_schema=False)
    async def scalar_docs() -> HTMLResponse:
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=f"{settings.PROJECT_NAME} — Referência",
            dark_mode=True,
            persist_auth=True,
            telemetry=False,
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"name": settings.PROJECT_NAME, "docs": "/docs", "reference": "/scalar"}

    return app


app = create_app()
