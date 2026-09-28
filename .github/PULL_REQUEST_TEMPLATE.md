## O que muda

<!-- Resumo da mudança e motivação. Referencie a issue: "Closes #123". -->

## Tipo

- [ ] feat: nova funcionalidade
- [ ] fix: correção de bug
- [ ] docs / refactor / test / chore
- [ ] **Breaking change** (quebra contrato da API ou exige ação manual)

## Como testar

<!-- Passos para validar localmente. -->

## Checklist

- [ ] O PR aponta para a branch `release/vX.Y` ativa (não para a `master`).
- [ ] Testes adicionados ou ajustados.
- [ ] `pnpm lint`, `pnpm typecheck` e `pnpm test` passam.
- [ ] Migration do Alembic criada e revisada (se o schema mudou).
- [ ] `pnpm codegen` executado e `openapi.json`/`schema.d.ts` commitados (se a API mudou).
- [ ] Consultas a tabelas de domínio filtram por `company_id`.
- [ ] `CHANGELOG.md` atualizado na seção [Não lançado].
