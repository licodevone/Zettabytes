# Zettabytes

Automação de WhatsApp com fluxos visuais e agentes de IA generativa, no modelo **Meta Tech Provider**.

- Arquitetura: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Prompts de desenvolvimento: [`docs/prompts/`](docs/prompts)

## Requisitos

Node 22+, pnpm 10+, Python 3.12+ com [uv](https://docs.astral.sh/uv/) e Docker.

## Primeiros passos

```bash
cp .env.example .env        # gere JWT_SECRET_KEY e ENCRYPTION_KEY (comandos no arquivo)
pnpm install
pnpm db:up                  # Postgres 17 + pgvector (porta 5442) e Redis
pnpm bootstrap              # uv sync do backend (obs.: `pnpm setup` é comando nativo do pnpm)
pnpm db:seed                # aplica as migrations e cria os planos
pnpm dev                    # API + Web juntos
```

| Serviço | URL |
|---|---|
| Web (Next.js) | http://localhost:3100 |
| API | http://localhost:8100 |
| Swagger | http://localhost:8100/docs |
| Scalar | http://localhost:8100/scalar |

As portas 3100, 8100 e 5442 fogem das padrões para não colidir com outros projetos locais.

## Comandos

| Comando | O que faz |
|---|---|
| `pnpm dev` | exporta o OpenAPI, gera o client TS e sobe API + Web |
| `pnpm test` | pytest (Postgres real, banco `zettabytes_test`) |
| `pnpm typecheck` | mypy strict (API) + tsc (Web e pacotes) |
| `pnpm lint` | ruff |
| `pnpm codegen` | regenera `packages/api-client` a partir do FastAPI |
| `pnpm db:migrate` | `alembic upgrade head` |
| `pnpm --filter @zettabytes/api db:revision "mensagem"` | nova migration (autogenerate) |

## Estrutura

```
apps/api      FastAPI · SQLAlchemy 2.0 async · Alembic · JWT (OAuth2)
apps/web      Next.js 16 · React 19 (Tailwind + shadcn/ui no Prompt 4)
packages/api-client          tipos gerados do OpenAPI + openapi-fetch
packages/typescript-config   tsconfigs compartilhados
```
