# Política de segurança

## Versões com suporte

| Versão | Suporte |
|---|---|
| 1.x | ✅ correções de segurança |
| < 1.0 | ❌ |

## Como reportar uma vulnerabilidade

**Não abra uma issue pública** para falhas de segurança.

Use o [reporte privado de vulnerabilidades do GitHub](https://github.com/licodevone/Zettabytes/security/advisories/new) e inclua:

- descrição do problema e impacto esperado;
- passos para reproduzir (ou uma prova de conceito);
- versão, branch ou commit afetado;
- sugestão de correção, se tiver.

Você deve receber uma confirmação em até 7 dias. Depois que a correção for publicada, o reporte é divulgado com os créditos a quem o encontrou (se desejar).

## Escopo que merece atenção especial

- Isolamento entre tenants (`X-Company-ID`, `memberships`, filtros por `company_id`).
- Autenticação, rotação de refresh tokens e RBAC.
- Criptografia de segredos em repouso (`ENCRYPTION_KEY`, tokens da Meta).
- Validação de assinatura de webhooks (Meta, Stripe, Asaas).
- Prompt injection e execução de tools pelos agentes de IA.
