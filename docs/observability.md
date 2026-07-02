# Observability — o traço do ecossistema

O aptdata grava um **traço de eventos** de tudo que acontece na orquestração
multi-agente: por que o Router escolheu um agente, quando um prompt saiu,
quanto demorou a resposta, quando um app subiu. O traço é a **fonte única**
que todas as superfícies leem — CLI (`aptdata obs`), viz e TUI — seguindo a
north star de sincronização (`docs/plans/sync-architecture.md`).

## Como funciona

- **`Observer`** (`aptdata.observability.Observer`) é a façade de emissão:
  **best-effort e no-throw** — uma falha de telemetria nunca derruba o fluxo
  de negócio.
- **`ObservabilityStore`** persiste os eventos em **SQLite local**
  (`~/.aptdata/events.db` por padrão) — nenhum collector externo é
  necessário.
- Cada evento carrega `ts`, `kind`, `agent_id`, `payload`, o `trace_id`
  OpenTelemetry corrente (quando houver) e o **`run_id`** de correlação.

## Correlação por `run_id`

Um comando como `aptdata agents dispatch` abre um *run context*; tudo que
acontece dentro dele — decisão do Router, dispatch, resposta — compartilha o
mesmo `run_id`:

```bash
$ aptdata agents dispatch "mexer no frontend" --json
$ aptdata obs tail --json | jq '.events[] | {kind, run_id}'
{"kind": "routing.decision", "run_id": "run_20260702..."}
{"kind": "agent.dispatch",  "run_id": "run_20260702..."}
{"kind": "agent.response",  "run_id": "run_20260702..."}
```

Programaticamente:

```python
from aptdata.observability import Observer

obs = Observer.get()
with obs.run_context() as run_id:
    ...  # tudo emitido aqui herda o run_id
```

## Taxonomia de eventos

| Kind | Emitido por | Payload |
|------|-------------|---------|
| `app.started` | viz (e demais apps ao subir) | `{app, host, port}` |
| `routing.decision` | `Router.route()` — toda superfície (CLI, viz, MCP, projects) | `RouteDecision` completo: `{agent_id, mode, confidence, skill, matched_keyword, text}` |
| `agent.dispatch` | `observed_send()` (CLI `agents send/dispatch`, `project run`, MCP `dispatch`) | `{prompt_chars}` |
| `agent.response` | idem | `{ok, error, latency_ms, text_chars}` |
| `permission.requested` / `permission.resolved` | loop de confirmação do ConversationEngine (planejado) | decisão pendente / escolha |

## CLI

```bash
aptdata obs summary [--json]   # totais por kind, decisões por modo, saúde dos dispatches
aptdata obs tail [--limit N] [--kind KIND] [--run-id ID] [--json]
```

## Configuração

| Variável | Efeito |
|----------|--------|
| `APTDATA_OBS_DB` | Caminho do SQLite (default `~/.aptdata/events.db`) |
| `APTDATA_OBS_DISABLED=1` | Kill-switch: desliga toda a emissão |

## Garantias

- **No-throw**: `Observer.emit()` engole qualquer erro (payload não
  serializável, disco cheio, store quebrado) e loga em `DEBUG`.
- **Thread-safe**: o store serializa escritas/leituras com lock (o viz é
  thread-per-request).
- **Isolado em testes**: a suite aponta `APTDATA_OBS_DB` para um banco
  temporário (fixture autouse em `tests/conftest.py`).

## Relação com OpenTelemetry

OTel continua sendo o backbone de **traces/métricas** (ver
[Telemetry](telemetry.md)); o traço de eventos é a camada aptdata-nativa para
**eventos de domínio** com persistência local — os dois se correlacionam pelo
`trace_id` embutido em cada evento. Roadmap completo em
`docs/plans/observability.md`.
