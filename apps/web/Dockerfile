# syntax=docker/dockerfile:1.7
# Web do Zettabytes — Next.js 16 (standalone) em monorepo pnpm, Node 24.
# Modelo: acmebr-infra/dockerfiles/node-next.Dockerfile
# Contexto = RAIZ do monorepo:
#   docker build -f apps/web/Dockerfile --build-arg NEXT_PUBLIC_API_URL=http://localhost:8100 -t acmebr/zettabytes-web .

ARG NODE_VERSION=24
# Mesma versão do `packageManager` do package.json da raiz.
ARG PNPM_VERSION=12.11.2

############################ base ############################
FROM node:${NODE_VERSION}-bookworm-slim AS base
ARG PNPM_VERSION
RUN npm install -g pnpm@${PNPM_VERSION}
WORKDIR /repo
ENV CI=true NEXT_TELEMETRY_DISABLED=1

############################ build ############################
FROM base AS build
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web/package.json apps/web/
COPY apps/api/package.json apps/api/
COPY packages/api-client/package.json packages/api-client/
COPY packages/typescript-config/package.json packages/typescript-config/
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --store-dir /pnpm/store --filter "@zettabytes/web..."

COPY apps/web apps/web
COPY packages/api-client packages/api-client
COPY packages/typescript-config packages/typescript-config

# Públicas = resolvidas no build (uma imagem por ambiente).
ARG NEXT_PUBLIC_API_URL=http://localhost:8100
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm --filter @zettabytes/web build

############################ runtime ############################
FROM node:${NODE_VERSION}-bookworm-slim AS runtime
LABEL org.opencontainers.image.title="acmebr-zettabytes-web"
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3100 HOSTNAME=0.0.0.0

RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --home /app --shell /usr/sbin/nologin app
WORKDIR /app

# O app ainda não tem pasta public/; quando tiver, copie também
# /repo/apps/web/public para ./apps/web/public.
COPY --from=build --chown=app:app /repo/apps/web/.next/standalone ./
COPY --from=build --chown=app:app /repo/apps/web/.next/static ./apps/web/.next/static

USER app
EXPOSE 3100
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3100/').then(r=>process.exit(r.status<500?0:1)).catch(()=>process.exit(1))"

CMD ["node", "apps/web/server.js"]
