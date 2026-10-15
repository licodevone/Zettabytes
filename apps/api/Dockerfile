# syntax=docker/dockerfile:1.7
# API do Zettabytes — FastAPI + uvicorn, SQLAlchemy async + Alembic, uv, Python 3.12.
# Modelo: acmebr-infra/dockerfiles/python-fastapi.Dockerfile
# Contexto = RAIZ do monorepo (para valer o .dockerignore da raiz, que tira .venv):
#   docker build -f apps/api/Dockerfile -t acmebr/zettabytes-api .
# Config por ambiente: DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, ENCRYPTION_KEY,
# CORS_ORIGINS, ENVIRONMENT (ver .env.example).

ARG PYTHON_VERSION=3.12

############################ build ############################
FROM ghcr.io/astral-sh/uv:0.9 AS uv
FROM python:${PYTHON_VERSION}-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
# Mesmo layout do repo: app/core/config.py acha a raiz subindo de apps/api
# (API_DIR.parents[1]); em /app não há dois níveis acima e o import quebra.
WORKDIR /repo/apps/api
ENV UV_PROJECT_ENVIRONMENT=/repo/apps/api/.venv UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY apps/api/app app
COPY apps/api/alembic alembic
COPY apps/api/alembic.ini ./

############################ runtime ############################
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
LABEL org.opencontainers.image.title="acmebr-zettabytes-api"
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --home /repo --shell /usr/sbin/nologin app
WORKDIR /repo/apps/api
COPY --from=build --chown=app:app /repo/apps/api /repo/apps/api
ENV PATH="/repo/apps/api/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PORT=8100
USER app
EXPOSE 8100

# /api/v1/health = liveness + banco (503 se o Postgres cair).
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,os,sys; r=urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/v1/health', timeout=2); sys.exit(0 if r.status<500 else 1)" || exit 1

# `alembic upgrade head` roda como serviço one-shot no compose, antes da API.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
