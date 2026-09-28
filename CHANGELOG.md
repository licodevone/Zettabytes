# Changelog

Todas as mudanças relevantes do Zettabytes são registradas aqui.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adota o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Corrigido

- CI: o passo de cache do `setup-uv` não falha mais quando não há dependências para salvar.

## [1.0.0] - 2026-09-28

Primeira versão pública, sob licença MIT. Entrega a fundação do sistema (Prompt 1 de [`docs/prompts`](docs/prompts)).

### Adicionado

- Monorepo Turborepo + pnpm com `apps/api`, `apps/web`, `packages/api-client` e `packages/typescript-config`.
- Backend FastAPI com SQLAlchemy 2.0 async, Alembic e Pydantic v2.
- Modelagem multi-tenant completa: usuários, empresas, memberships, planos, assinaturas, uso de IA, conexões WhatsApp, contatos, fluxos, agentes de IA, base de conhecimento (pgvector/HNSW), sessões de chat e mensagens.
- Autenticação OAuth2 com JWT (access + refresh com rotação e detecção de reuso), hash Argon2 e logout.
- Isolamento por tenant via header `X-Company-ID` e RBAC (`owner`, `admin`, `agent`, `viewer`).
- Tokens da Meta criptografados em repouso (Fernet).
- Controle atômico de cota de IA por mês (`usage_counters`).
- Endpoints `health`, `auth`, `users/me` e `companies` (dados, membros e uso).
- Documentação interativa em Swagger (`/docs`) e Scalar (`/scalar`).
- Client TypeScript tipado gerado a partir do OpenAPI (`openapi-typescript` + `openapi-fetch`).
- Frontend Next.js 16 / React 19 inicial, consumindo o client tipado.
- Docker Compose com PostgreSQL 17 + pgvector e Redis 7.
- Suíte de testes de integração com Postgres real.
- Licença MIT, guia de contribuição, código de conduta, política de segurança e templates de issue/PR.

[Não lançado]: https://github.com/licodevone/Zettabytes/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/licodevone/Zettabytes/releases/tag/v1.0.0
