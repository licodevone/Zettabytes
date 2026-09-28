# Prompt 4: Frontend Next.js (Dashboard, Flow Builder, Live Chat)

```text
Atue como Engenheiro Frontend Sênior e Product Designer. Em apps/web (Next.js 16 App Router,
React 19, TypeScript strict), construa a interface do Zettachat seguindo docs/ARCHITECTURE.md §5:

1. FUNDAÇÃO
   - Tailwind CSS v4 + shadcn/ui (componentes base em packages/ui).
   - Design tokens em OKLCH com dark mode elegante como padrão (next-themes, sem flash); Geist Sans/Mono.
   - Estética Vercel/Linear: bordas 1px, sem sombras pesadas, raio 8px, densidade alta, foco
     visível, motion sutil (respeitando prefers-reduced-motion).
   - Dados: @zettachat/api-client (openapi-fetch tipado) + TanStack Query. Access token em memória
     e refresh token em cookie httpOnly via Route Handler (BFF); middleware protegendo /app/*;
     tenant ativo enviado no header X-Company-ID.
   - Shell: sidebar colapsável, seletor de empresa, breadcrumbs, Command Palette (cmdk, Cmd+K), toasts (sonner).
   - Auth: login, registro (cria empresa), esqueci a senha.

2. DASHBOARD (/app)
   - KPI cards (conversas, % resolvidas pela IA, tempo de 1ª resposta, handoffs, uso de IA vs.
     limite), seletor de período.
   - Recharts: área (volume diário inbound/outbound), barras (por agente/fluxo), funil do fluxo;
     paleta consistente em light/dark; skeletons e estados vazios.
   - Tabela de conversas recentes (TanStack Table).

3. FLOW BUILDER (/app/flows/[id])
   - @xyflow/react: grid de pontos, minimapa, controles, snap, handles com múltiplas saídas
     (buttons/condition), edges customizadas com botão de excluir.
   - Um nó customizado por NodeType (start, send_message, ask_question, buttons, list, condition,
     ai_agent, action, delay, handoff, end), com ícone, acento sutil e preview do conteúdo.
   - Paleta lateral com drag-and-drop; shadcn Sheet à direita para editar o nó selecionado
     (react-hook-form + zod por tipo; variáveis {{contact.name}} com autocomplete).
   - zustand + undo/redo; autosave com debounce; validação (nós órfãos, saídas sem destino);
     botão Publicar; atalhos (Del, Cmd+Z, Cmd+D).

4. LIVE CHAT (/app/inbox): 3 colunas redimensionáveis (shadcn Resizable)
   - Coluna 1: filtros (Minhas, Não atribuídas, IA, Fechadas), busca, lista virtualizada com
     avatar, preview, horário relativo e badge de não lidas.
   - Coluna 2: header com contato e ações (atribuir, fechar, retomar IA); mensagens agrupadas por
     dia; bolhas inbound/outbound/IA/sistema; ticks de status; mídia; fontes do RAG; banner
     "IA pausada"; aviso da janela de 24h (fora dela, seletor de template); composer com respostas
     rápidas (/), anexos e Enter/Shift+Enter.
   - Coluna 3: perfil do contato (atributos editáveis, tags, resumo da IA, sessões anteriores).
   - Tempo real via WebSocket (reconexão com backoff) + atualização otimista.

5. CONFIGURAÇÕES: WhatsApp (Embedded Signup com o SDK da Meta -> POST exchange; status e qualidade
   do número), Agentes de IA (+ playground com streaming), Base de conhecimento (upload e status),
   Equipe, Plano e uso (checkout).

Responsivo (em telas pequenas o inbox vira navegação em pilha), acessibilidade AA, sem `any`,
componentes em /components/<domínio>. `pnpm typecheck` e `pnpm build` devem passar.
```
