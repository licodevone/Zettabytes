# Prompt 3: Engine de agentes de IA, RAG, memória e handoff

```text
Atue como Engenheiro de IA Sênior. Com base em docs/ARCHITECTURE.md (seções 2, 3 e 6) e no código
de apps/api, implemente o Agent Engine com o SDK oficial `anthropic` (async, tool use nativo),
modelo configurável por agente: claude-sonnet-5 para especialistas e claude-haiku-4-5 para o Router.

1. DISPATCHER DE CONVERSA (consome "message.received")
   - Lock distribuído por sessão (Redis) para processar mensagens em ordem; debounce de ~2 s
     para agrupar mensagens picadas.
   - mode=human ou ai_paused_until futuro -> só notifica o Live Chat;
     mode=flow -> FlowRuntime executa o published_graph (o nó ai_agent delega ao engine);
     sem fluxo ativo -> gatilhos (keyword/welcome/default) ou Router.

2. AGENT ENGINE (app/agents/)
   - ToolRegistry com decorator @skill(name, description); schema JSON gerado de Pydantic;
     company_id/session_id injetados pelo engine (NUNCA vindos do LLM); allowlist por ai_agent.tools.
   - Skills internas: rag.search, contact.get/update_attributes/add_tag, session.get_history,
     flow.trigger, handoff.request, wa.send_interactive.
   - MCP client (SDK `mcp`) para servidores externos por tenant (calendar, crm, payment);
     credenciais criptografadas, timeout, circuit breaker; tabela tool_calls para auditoria.
   - Loop agentic com limite de iterações e tokens; resultado de tool tratado como dado
     (defesa contra prompt injection); prompt caching no system prompt + tools.

3. MEMÓRIA
   - Curto prazo: últimas N mensagens + chat_sessions.context (slots/variáveis).
   - Compressão: acima do orçamento de tokens, atualiza chat_sessions.summary.
   - Longo prazo: ao fechar a sessão, consolida fatos em contacts.ai_profile_summary/attributes,
     injetados no system prompt da próxima conversa.

4. RAG
   - Ingestão assíncrona: PDF/DOCX/URL/texto/FAQ -> extração -> chunking semântico (~500 tokens,
     overlap 15%) -> embeddings em lote (provider plugável, 1536 dims) -> knowledge_chunks;
     checksum evita reindexar; status no documento.
   - Busca híbrida: pgvector cosine (HNSW) + full-text (tsvector 'portuguese') fundidos por
     Reciprocal Rank Fusion, sempre filtrados por company_id/knowledge_base_id; limiar de relevância.
     Abaixo dele, o agente admite não saber e pode acionar handoff.
   - Respostas guardam as fontes (ids dos chunks) para exibição no Live Chat.

5. HANDOFF INTELIGENTE
   - Gatilhos por turno (handoff_rules): pedido explícito, sentimento negativo em N mensagens,
     baixa confiança no RAG, turnos máximos, palavras sensíveis, cota esgotada.
   - Efeito: mode=human, status=pending, handoff_reason, ai_paused_until; atribuição round-robin
     entre memberships online respeitando max_concurrent_chats; evento ao Live Chat e mensagem de
     transição ao contato. POST /sessions/{id}/resume-ai devolve à IA.

6. LIMITES: usage_service.ensure_ai_quota() antes de cada chamada e record_ai_usage() depois
   (tokens de response.usage); eventos de alerta em 80% e 100%.

7. API: CRUD de ai_agents, knowledge_bases e documentos (upload); playground
   POST /agents/{id}/playground com streaming SSE (sem WhatsApp).

8. TESTES: cliente Anthropic mockado, escolha de tools, isolamento multi-tenant no RAG
   (tenant A nunca recupera chunk do B), gatilhos de handoff, quota esgotada.
```
