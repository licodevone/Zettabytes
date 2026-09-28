# Prompt 2: Webhooks e integração com a WhatsApp Cloud API (Tech Provider)

```text
Atue como Engenheiro Backend Sênior especialista na Meta WhatsApp Cloud API (Graph API v23+).
Com base em docs/ARCHITECTURE.md e no código existente em apps/api, implemente:

1. EMBEDDED SIGNUP (Tech Provider)
   - Settings: META_APP_ID, META_APP_SECRET, META_CONFIG_ID, META_GRAPH_VERSION,
     META_WEBHOOK_VERIFY_TOKEN.
   - GET /api/v1/whatsapp/signup-config: devolve app_id/config_id para o SDK JS do frontend.
   - POST /api/v1/whatsapp/connections/exchange {code, waba_id, phone_number_id} (TenantAdmin):
     troca o code por Business Integration System User Token, busca os dados do número
     (display_phone_number, verified_name, quality_rating), assina o app na WABA
     (POST /{waba_id}/subscribed_apps), registra o número (POST /{phone_number_id}/register)
     e persiste em whatsapp_connections (token criptografado).
     Respeita plan.max_whatsapp_connections.
   - CRUD: listar, detalhes/health, desconectar (unsubscribe + DISCONNECTED), definir padrão.

2. CLIENTE DA META (app/integrations/meta/)
   - MetaGraphClient assíncrono (httpx.AsyncClient compartilhado, timeouts, retry exponencial com
     jitter em 429/5xx, erros tipados da Graph API -> MetaAPIError com code/subcode).
   - Envio: texto, mídia (upload + id), interativo (botões <=3, lista), template com componentes,
     reação, mark_as_read e typing indicator. Pydantic models para cada payload.
   - Janela de 24h: bloqueia mensagem livre se last_inbound_at > 24h (exige template).

3. WEBHOOKS
   - GET /api/v1/webhooks/meta: handshake (hub.mode, hub.verify_token, hub.challenge).
   - POST /api/v1/webhooks/meta: valida X-Hub-Signature-256 (HMAC-SHA256 do corpo bruto com o
     app secret, compare_digest), responde 200 rapidamente e enfileira no Redis (arq/Streams).
     Nunca processa inline.
   - Worker: roteia por metadata.phone_number_id -> tenant;
     messages: upsert Contact, obtém/cria ChatSession aberta (respeitando o índice único parcial),
     grava Message INBOUND idempotente por wa_message_id, atualiza last_inbound_at/unread_count;
     statuses: atualiza MessageStatus sem regredir estado (sent -> delivered -> read; failed + error);
     account_update / phone_number_quality_update: atualiza a conexão.
     Publica "message.received" para o dispatcher de conversa (Prompt 3).
   - Mídia recebida: baixa via Graph API para storage S3-compatible (interface abstrata).

4. SAÍDA
   - POST /api/v1/sessions/{id}/messages (atendente) -> OUTBOUND QUEUED -> worker envia ->
     wa_message_id/status. Header Idempotency-Key opcional.
   - Eventos em tempo real (Redis pub/sub) "message.created"/"message.status" para o Live Chat.

5. TESTES: payloads reais da Meta como fixtures, HMAC válido/inválido, idempotência (mesmo
   webhook 2x = 1 mensagem), roteamento multi-tenant, janela de 24h. Mock do Graph com respx.
Gere a migration Alembic se o schema mudar e mantenha ruff/mypy strict limpos.
```
