# Plano — aptdata studio (camada de visualização do aptdata)

> Status: Fases 1–2 entregues (API + view ecossistema); Fase 4 parcial
> (`/api/observability` real + `/api/events` SSE + feed ao vivo no painel
> + Agent Trace da TUI lendo o mesmo store). Fases 3/5/6 pendentes.

> Objetivo: uma camada de **visualização web** do aptdata — ver flows, runs, agentes,
> decisões de roteamento e observabilidade **ao vivo**, unificando o que hoje está
> espalhado (TUI monitor + painel multiverso) sobre uma única API de dados.

## Contexto (o que já existe — reusar, não recriar)
- **Painel multiverso** (`multiverso/`): FastAPI (`vps-api.py`) + `painel.html` (vanilla JS). Já lê `docker.sock` (status de container), `multiverso.json`/DEFAULT_CONFIG (bots VPS+locais: nome/modelo/handle/capabilities/tipo) e devlog/sessao. É o dashboard do ecossistema de bots.
- **aptdata/mcp/server.py**: expõe `list_agents`, `dispatch`, `run_flow` (+ ~5 tools).
- **aptdata/observability/llm_observer.py**: `get_observability_summary` → `total_calls, total_tokens, total_cost_usd, avg_latency_ms, by_routine[], recent[]`.
- **aptdata/tui/monitor.py**: `_DAGPanel` (grafo do flow), `_StatusTable` (status por step), barra de memória — já é uma "studio" no terminal.
- **Planos irmãos** (dependências): `observability.md` (Observer no-throw + event store SQLite + correlação `run_id` System→Flow→Component e Router→Agent→Task) e `telegram-orchestration.md` (ConversationEngine/decisões).

**Princípio:** aptdata studio é **consumidor**, não dono de lógica. Zero regra de negócio no studio — ele só lê a mesma fonte da observability e do registry e renderiza. Absorve o painel multiverso e espelha a TUI (paridade web).

## Views (o que visualizar)
1. **Ecossistema de agentes** (absorve o painel multiverso) — registry (`list_agents`/`agents.yaml`): agente, tipo, location, capabilities, **modelo**, health, e a **decisão de roteamento** do Router (mode/skill/confidence — por que caiu naquele agente). Valor imediato, não depende de observability completa.
2. **Flow/System DAG** — grafo System→Flow→Component com status por nó ao vivo durante um run (paridade web da TUI). Mermaid ou vis-network via CDN.
3. **Observabilidade** — custo/tokens/latência por routine/agente (de `get_observability_summary`), taxa de erro, health, alertas.
4. **Trace/timeline de run** — waterfall dos spans de um `run_id` ao longo de Flow→Component e Router→Agent→Task (depende da correlação `run_id` da observability.md).
5. **Console de dispatch** — dispara `dispatch`/`run_flow` pela UI e assiste o fluxo ao vivo (liga no ConversationEngine da telegram-orchestration).

## Arquitetura
- **Backend**: novo módulo `aptdata/studio/` — servidor (FastAPI, já usado no multiverso; ou stdlib pra manter leve) expondo API de LEITURA:
  - `GET /api/flows` (grafo), `GET /api/runs`, `GET /api/runs/{id}/trace`, `GET /api/agents`, `GET /api/observability`, `GET /api/events` (**SSE** ao vivo).
  - Fonte: o **event store da observability.md** (SQLite) + o registry do MCP. Ao vivo via **SSE** plugado no EventBus (backbone da observability).
  - CLI: `aptdata studio` sobe o servidor (paridade com `aptdata monitor` da TUI).
- **Frontend**: single-page **vanilla JS** (mesmo estilo leve do painel/Aconchego, sem build), DAG com **Mermaid** ou **vis-network** via CDN, live via **EventSource (SSE)**. Um studio, dois frontends (TUI no terminal + web no browser) sobre a MESMA API.
- **Deploy**: Docker na VPS atrás do Traefik (como o painel), domínio `aptdata-studio.srv1723096.hstgr.cloud` — **substitui** o multiverso painel a médio prazo.

## Fases (cada uma entregável)
0. **Contrato de dados** — definir as shapes da API de leitura (flows/runs/traces/agents/observability + evento SSE). Pré-req: observability.md Fase 1–3 (Observer + persistência + `run_id`).
1. **Backend read API** (`aptdata/studio`, FastAPI) sobre o event store + registry MCP. CLI `aptdata studio`. Deploy Docker/Traefik.
2. **View Ecossistema de agentes** (absorve o painel) — agentes/health/capabilities/modelo + decisão de roteamento. **Primeiro a entregar** (não depende de observability completa).
3. **View Flow DAG** ao vivo (status por nó) — paridade web da TUI.
4. **View Observabilidade** (custo/tokens/latência/erros por routine/agente + alertas).
5. **View Trace/timeline** (waterfall por `run_id`).
6. **Console de dispatch** (dispara + assiste ao vivo), ligado à telegram-orchestration.

## Decisões / riscos
- **Não forkar**: absorver o painel multiverso, reusar o event store da observability, espelhar a TUI. Uma fonte de dados só.
- **Dependência forte da observability.md**: as views 3/4/5 (DAG live, obs, trace) precisam do `run_id` e do event store. A view 2 (ecossistema) ship primeiro, standalone.
- **Stack leve** (vanilla JS + CDN) casa com o resto do ecossistema (painel/Aconchego são vanilla) e evita build.
- **Fable 5**: o studio é agnóstico de modelo, mas expõe o `modelo` por agente — útil pra ver quem está no `claude-fable-5` no teste de fluxo geral.

## Ordem recomendada
Fase 1 (API) + Fase 2 (ecossistema, valor imediato substituindo o painel) → depois plugar nas fases da observability.md conforme ela entrega `run_id`/event store (Fases 3–5) → Console (Fase 6).
