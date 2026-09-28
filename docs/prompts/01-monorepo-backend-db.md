# Prompt 1: Monorepo, backend FastAPI e PostgreSQL ✅ EXECUTADO

> Status: implementado neste repositório. Resultado: 13 testes de integração passando, ruff e mypy strict limpos, `alembic check` sem drift e `pnpm dev` sobe API + Web.

```text
Atue como Arquiteto de Software Sênior. Leia docs/ARCHITECTURE.md e implemente a fundação do Zettachat:

1. MONOREPO: Turborepo + pnpm workspaces (apps/api, apps/web, packages/api-client,
   packages/typescript-config). turbo.json com pipeline openapi -> generate -> typecheck/build/dev.
   O apps/api (Python/uv) participa do Turbo via package.json cujos scripts delegam ao uv.
   docker-compose com Postgres 17 + pgvector e Redis. Portas configuráveis.

2. BACKEND: FastAPI com layout core/ db/ models/ schemas/ services/ api/.
   - pydantic-settings lendo o .env da raiz; validação que falha no boot em produção insegura.
   - SQLAlchemy 2.0 async (asyncpg): engine com pool_pre_ping, async_sessionmaker
     (expire_on_commit=False) e dependência get_db. Commit explícito nos services.
   - DeclarativeBase com naming_convention, type_annotation_map (UUID, timestamptz, JSONB, Enum)
     e mixins UUIDPrimaryKey/Timestamp/Tenant.

3. MODELOS (Mapped/mapped_column) de TODAS as tabelas da seção 4 da arquitetura, com FKs,
   ondelete, índices compostos, índice único parcial (1 sessão aberta por contato), HNSW no
   pgvector e tokens da Meta criptografados (TypeDecorator + Fernet).
   Alembic async + migration inicial (extensões citext e vector).

4. AUTH com fastapi.security: OAuth2PasswordBearer + OAuth2PasswordRequestForm, JWT (PyJWT)
   access/refresh, Argon2 (pwdlib) com proteção contra timing attack, refresh token persistido
   com rotação e detecção de reuso, logout, troca de senha. Multi-tenant pelo header
   X-Company-ID validado contra memberships (404 para tenant alheio) + RBAC require_roles().
   Registro cria User + Company + Membership OWNER + Subscription em trial.

5. DOCS: Swagger em /docs (persistAuthorization) e Scalar em /scalar (dark mode);
   operationIds limpos para o client TS gerado.

6. QUALIDADE: pytest com Postgres real (banco *_test), ruff, mypy strict, seed de planos.
```
