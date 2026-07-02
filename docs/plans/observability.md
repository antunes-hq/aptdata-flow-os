# Plano: Observabilidade Full-Stack e Resiliente para o aptdata

> Status: PARCIALMENTE IMPLEMENTADO — Observer no-throw + ObservabilityStore
> (SQLite) + correlação run_id + instrumentação de Router/dispatch/MCP + CLI
> `aptdata obs` já existem (ver docs/observability.md). Restante: proposta.
> Escopo: `aptdata` 0.1.0 — modelo System/Flow/Component, núcleo multi-agente,
> MCP server, CLI Typer, TUI Textual.

---

## 1. Diagnóstico — o que já existe

Antes de propor, o que o código já entrega hoje (confirmado lendo os módulos):

| Peça | Arquivo:símbolo | O que faz | Lacuna |
|---|---|---|---|
| Bootstrap OTel | `aptdata/telemetry/instrumentation.py:configure_telemetry` | Cria `TracerProvider`/`MeterProvider` com `Resource(service.name)`; helpers `get_tracer`/`get_meter` | Só configura se chamado; default via `TelemetryProvider.get_instance()` usa console-less scaffold. Sem OTLP por padrão. |
| Máscara de segredos | `instrumentation.py:mask_telemetry_value` / `register_secret` | Redige `password/secret/token/...` e valores registrados | Bom — reaproveitar em todos os sinais. |
| Métricas de ingestão (in-memory) | `instrumentation.py:IngestionMetrics` + `get_ingestion_metrics` | Singleton com counters de docs/chunks/tokens, throughput, progresso; counter OTel `llm.tokens.used` | Estado global mutável; só cobre ingestão. Não há counter/gauge/histogram genéricos. |
| Provider injetável | `aptdata/telemetry/provider.py:TelemetryProvider` | Singleton exposto em `IContext.telemetry` | Só expõe tracer/meter; sem logs nem métricas de negócio. |
| Observador de LLM | `aptdata/observability/llm_observer.py` | Custo/latência/tokens por chamada; persiste via `store.log_event(...)` (SQLite `events`, kind=`llm_call`); agrega em `get_observability_summary` | **O `store` é externo (mindflow), não faz parte do aptdata.** aptdata não tem event store próprio. |
| Event Bus | `aptdata/core/events.py:EventBus` | Async, thread de fundo + fila, **captura exceptions de listeners e loga warning** | Já resiliente. É o backbone ideal para logs/eventos. Sem persistência. |
| Instrumentação de Component | `aptdata/core/system.py:BaseComponent.__init_subclass__` (linha ~247) | Envolve `execute()` em span OTel + dispatch de `ComponentExecutionEvent` (pre/success/failure/post) | Criação de span e leitura de `self.meta` **não** estão em try/except — falha de telemetria pode vazar. Sem `run_id` correlacionando System→Flow→Component. |
| Instrumentação de Workflow (funcional) | `aptdata/core/workflow.py:Workflow._run`/`_run_step` | Spans por run/step, `record_exception`, retry/backoff, `run_id` (`name_timens_uuid`) e `trace_id` propagados nos records | Só o `Workflow` funcional; o par `BaseSystem`/`BaseWorkflow`/`BaseComponent` não compartilha `run_id`. |
| Hooks de ciclo de vida | `workflow.py:BaseWorkflow.before_run`/`after_run` (150–156) | Setam chaves no context | Ponto de injeção livre — hoje subutilizado. |
| System | `system.py:BaseSystem.run` (635) | Injeta context/EventBus, roda flows, `event_bus.shutdown()` no fim | Sem span raiz, sem `run_id`, sem health/erros agregados. |
| Router/Agents | `aptdata/agents/router.py:Router.route`, `agents/project.py:ProjectRunner.run`, `agents/cli_agents.py:CLIAgent.send` | Routing prefix/skill/llm/default; `send` via subprocess com `timeout`; LLM router em try/except | **Zero telemetria.** Sem spans, sem métricas de decisão/latência/erro por agente. |
| MCP server | `aptdata/mcp/server.py` | Cada tool em try/except retorna dict de erro; `_mark_request()` counter thread-safe; `get_mcp_status()` | Só conta requests. Sem latência/erro por tool, sem correlação. |
| CLI | `aptdata/cli/app.py:_emit` | Emite 1 JSON line por evento com `trace_id` do span corrente | Bom padrão — estender para `run_id`. |
| CLI telemetry | `aptdata/cli/commands/telemetry_cmd.py` | `status`/`export` finos (só tipo do provider) | Sem `observability` (custo/erros/latência agregados). |
| TUI | `aptdata/tui/monitor.py` | Abas DAG/Metrics/AgentTrace/MCP; painéis com **dados placeholder** | Não plugado em sinais reais nem no EventBus. |

**Conclusões-chave:**
1. OpenTelemetry **já é dependência declarada** (`pyproject.toml`: `opentelemetry-api/sdk ^1.40`) e já é a base da instrumentação existente. Reinventar traces/métricas seria retrabalho.
2. O `EventBus` já é async, isolado e à prova de exceptions — é a espinha dorsal natural para logs estruturados e eventos de domínio.
3. Falta: (a) um **façade único** de observabilidade, (b) **correlação por `run_id`** ponta-a-ponta (System→Flow→Component e Router→Agent→Task), (c) **persistência própria** (o `events` SQLite é externo), (d) instrumentação de **agents e MCP**, (e) **alertas**, (f) **garantias formais de resiliência** (best-effort universal), (g) exposição real na CLI/TUI.

---

## 2. Decisão de arquitetura — OpenTelemetry vs. solução própria

**Recomendação: híbrido — OpenTelemetry como backbone de traces + métricas; camada aptdata-nativa fina por cima para logs estruturados, eventos de domínio, persistência local e alertas.**

Justificativa:

- **Usar OTel para traces e métricas** (não reinventar):
  - Já é dependência e já instrumenta `BaseComponent`/`Workflow`. Migrar para solução própria quebraria o que funciona.
  - Ganha de graça: propagação de contexto de span, exporters OTLP (Jaeger/Tempo/Honeycomb/Datadog — já documentado em `docs/telemetry.md`), `OTEL_SDK_DISABLED`, semantic conventions.
  - `SpanExporter`/`MetricReader` in-memory tornam os testes triviais.
- **Camada própria fina (`aptdata/observability/`) para o que OTel não cobre bem no nosso caso**:
  - **Logs estruturados** correlacionados: OTel logs SDK ainda é imaturo em Python; usamos `logging` + injeção de `run_id`/`trace_id` e roteamos pelo EventBus.
  - **Eventos de domínio** (routing decision, agent dispatch, quality fail, cost): modelados como `EventPayload` (Pydantic) — já existe o padrão.
  - **Persistência local opcional** (SQLite): um sink próprio, porque não queremos exigir um collector OTLP rodando para o dev ver custo/erros. Reaproveita o esquema `events` do llm_observer, mas **dentro** do aptdata.
  - **Alertas**: regras simples + canal Telegram (fire-and-forget do ecossistema) — fora do escopo do OTel.
- **Não** adotar backend pesado (Prometheus server, Grafana) como requisito: exportação Prometheus fica como *exporter opcional* plugável, não obrigatório.

Ou seja: **OTel por baixo, façade `aptdata.observability` por cima**. O código de negócio nunca fala com OTel diretamente — fala com o façade, que é best-effort e nunca levanta exceção.

---

## 3. Arquitetura-alvo

```
                    aptdata.observability (façade — API estável, best-effort)
                    ┌───────────────────────────────────────────────────────┐
 código de negócio → │  Observer (singleton fino, no-throw)                   │
 (Component/Agent/   │   ├── metrics: counter/gauge/histogram  → OTel Meter   │
  MCP/CLI)           │   ├── span(name, attrs)  (context mgr)  → OTel Tracer  │
                    │   ├── log(level, msg, **fields)         → EventBus     │
                    │   ├── event(EventPayload)               → EventBus     │
                    │   ├── error(exc, context)               → span+event   │
                    │   └── health()                          → HealthRegistry│
                    └──────────────┬──────────────────┬─────────────────────┘
                                   │                  │
                      ┌────────────▼───┐     ┌────────▼─────────┐
                      │ OTel providers │     │ EventBus (async) │
                      │ traces+metrics │     │  listeners:      │
                      └───────┬────────┘     │  - SqliteSink    │
                              │              │  - AlertEngine   │
                   exporters (opt):          │  - TUI bridge    │
                   OTLP / Prometheus /       │  - stdout JSONL  │
                   InMemory(testes)          └──────────────────┘
                                                      │
                                             ┌────────▼────────┐
                                             │ ObservabilityStore
                                             │  (SQLite, retenção)
                                             └─────────────────┘
```

### Correlação (`run_id`)
- Um `run_id` é gerado no topo (`BaseSystem.run` / CLI `run` / `ProjectRunner.run` / MCP tool) e propagado via `ExecutionContext` (`context.set("run.id", run_id)`) e como atributo de span (`aptdata.run_id`).
- `RunContext` (dataclass leve) carrega `run_id`, `span` raiz, `started_at`. Fica no `IContext` para que Flow e Component herdem sem parâmetros novos na assinatura pública.
- Router→Agent→Task: `ProjectRunner` cria `run_id` do projeto; cada `Task` vira um child span `aptdata.agent.dispatch` com `aptdata.agent_id`, `aptdata.route_mode`, `aptdata.task_id`.

---

## 4. Módulos e interfaces propostos

Novo pacote consolida o que hoje está espalhado entre `telemetry/` e `observability/` (mantém retrocompat reexportando).

```
aptdata/observability/
  __init__.py            # reexporta observer, get_observer, decorators
  observer.py            # Observer + get_observer() (singleton no-throw)   [NOVO]
  signals.py             # Metric/Span/Log/Event value objects + tipos      [NOVO]
  safe.py                # @suppress / safe_call / SafeTimeout — resiliência [NOVO]
  correlation.py         # RunContext, new_run_id, current_run_id            [NOVO]
  sinks/
    __init__.py
    sqlite_sink.py       # ObservabilityStore (SQLite) + retenção           [NOVO]
    stdout_sink.py       # JSON lines (reaproveita padrão do cli/app _emit)  [NOVO]
  health.py              # HealthRegistry + HealthCheck                      [NOVO]
  alerts.py              # AlertRule, AlertEngine, TelegramChannel           [NOVO]
  llm_observer.py        # EXISTENTE — refatorado p/ usar ObservabilityStore
  instrumentation.py     # (movido de telemetry/) — mantém OTel bootstrap
```

`aptdata/telemetry/` permanece como **camada OTel de baixo nível** (bootstrap, máscara, providers). O façade `observability.observer` a consome.

### 4.1 `Observer` (façade — `observability/observer.py`)

```python
class IObserver(ABC):
    def counter(self, name: str, value: int = 1, **attrs) -> None: ...
    def gauge(self, name: str, value: float, **attrs) -> None: ...
    def histogram(self, name: str, value: float, **attrs) -> None: ...
    def span(self, name: str, **attrs) -> ContextManager["Span"]: ...   # no-throw
    def log(self, level: str, msg: str, **fields) -> None: ...
    def event(self, event: EventPayload) -> None: ...
    def error(self, exc: BaseException, *, where: str, **ctx) -> None: ...
    def health(self) -> dict[str, "HealthStatus"]: ...

class Observer(IObserver):
    """Implementação real: OTel meter/tracer + EventBus. TODOS os métodos
    são best-effort — encapsulados em safe.suppress. Nunca levantam."""
```

`get_observer()` retorna um singleton lazy. Se OTel não estiver configurado, cai num `NoOpObserver` (também no-throw). O código de negócio SEMPRE chama `get_observer()` — nunca `get_tracer()`/`get_meter()` direto.

### 4.2 Resiliência (`observability/safe.py`) — requisito central

Contrato: **nenhuma chamada de observabilidade pode alterar o resultado nem propagar exceção do código de negócio.**

```python
def suppress(where: str):
    """Decorator/context manager: engole QUALQUER exceção, loga 1x
    (rate-limited) via logging.getLogger('aptdata.observability').debug,
    e retorna None. Nunca re-levanta."""

def safe_call(fn, *a, default=None, where="", **kw):
    """Chama fn, engole exceção, devolve default."""

class SafeTimeout:
    """Context manager: aborta operação de observabilidade que exceda
    N ms (default 200ms) sem travar o run — via deadline check ou
    thread watchdog para sinks bloqueantes."""
```

Regras de resiliência aplicadas em todo o módulo:
1. **Todo método público do `Observer`** é decorado com `@suppress`.
2. **Sinks rodam no EventBus** (thread de fundo já isolada) — I/O de persistência nunca no caminho quente.
3. **Fila com backpressure limitada**: `EventBus._queue` ganha `maxsize`; em overflow, **descarta o evento mais antigo** (drop-oldest) e incrementa um counter `observability.dropped` — degradação graciosa, nunca bloqueio.
4. **Timeouts** em toda I/O externa (SQLite `busy_timeout`, alert channel HTTP com timeout, health checks com deadline).
5. **Import guards**: dependências opcionais (OTel exporters, httpx p/ Telegram) em try/except → feature desliga sozinha se ausente.
6. **Circuit breaker** por sink: após N falhas consecutivas, o sink entra em `cooldown` e para de tentar por T segundos (evita tempestade de erros de disco/rede).
7. **Kill switch**: `APTDATA_OBS_DISABLED=1` → `NoOpObserver` global (além do `OTEL_SDK_DISABLED` já suportado).

### 4.3 Persistência (`observability/sinks/sqlite_sink.py`)

```python
class ObservabilityStore:
    """SQLite local (default ~/.aptdata/observability.db, configurável).
    Reaproveita e formaliza o esquema `events` usado pelo llm_observer."""
    # Tabelas:
    #   events(id, run_id, ts, kind, level, source, payload_json)
    #   metrics(id, run_id, ts, name, kind, value, attrs_json)   -- opcional/rollup
    #   runs(run_id, started_at, ended_at, status, error_count)
    def log_event(self, source, kind, payload, *, run_id=None, level="info"): ...
    def query(self, *, kind=None, run_id=None, since=None, limit=100): ...
    def summary(self, *, days=7) -> dict: ...        # move get_observability_summary p/ cá
    def prune(self, *, keep_days=30) -> int: ...     # retenção
```

- **PRAGMA**: `journal_mode=WAL`, `busy_timeout=2000`, `synchronous=NORMAL` — writes não bloqueiam reads e não travam.
- **Retenção**: `prune(keep_days)` chamada no fim do run (`BaseSystem.on_complete`) e via `aptdata observability prune`. Default 30 dias.
- **Compatibilidade**: `llm_observer.log_llm_call` passa a aceitar tanto o `store` externo (mindflow) quanto o `ObservabilityStore` (mesma assinatura `log_event`). Mantém o comportamento silencioso atual.

### 4.4 Health (`observability/health.py`)

```python
class HealthStatus(str, Enum): UP; DEGRADED; DOWN; UNKNOWN

@dataclass
class HealthCheck:
    name: str
    check: Callable[[], HealthStatus]   # deve ser rápido; roda sob SafeTimeout

class HealthRegistry:
    def register(self, hc: HealthCheck) -> None: ...
    def snapshot(self) -> dict[str, HealthStatus]: ...   # cada check em @suppress
```

Checks embutidos: OTel provider configurado; `ObservabilityStore` gravável; MCP ativo (`get_mcp_status`); por-agente via `IAgent.health()` (já existe em `agents/base.py`); EventBus worker vivo.

### 4.5 Alertas (`observability/alerts.py`)

```python
@dataclass
class AlertRule:
    name: str
    predicate: Callable[[EventPayload], bool]   # ex.: erro, latência>X, custo>Y
    channel: str = "telegram"
    cooldown_s: int = 300          # anti-flood por regra
    severity: str = "warning"

class AlertEngine:
    """Listener no EventBus. Avalia regras contra cada evento; dispara
    canal com dedup/cooldown. Disparo é fire-and-forget e best-effort."""

class TelegramChannel:
    """Envia via mecanismo fire-and-forget já existente no ecossistema
    (bot/worker). Timeout curto, nunca bloqueia. Sem httpx? desliga sozinho."""
```

Regras iniciais: (a) qualquer `on_failure`/`error`; (b) `execution_time > limiar` por componente; (c) `cost_usd` acumulado do run acima do budget; (d) agente `DOWN` num dispatch.

---

## 5. Pontos de integração concretos (arquivo:símbolo)

| Onde | Mudança | Sinal |
|---|---|---|
| `core/system.py:BaseSystem.run` | Abrir span raiz `aptdata.system.run`, gerar `run_id`, guardar em `context`; `on_complete` → `prune()` + flush | trace raiz, `run_id`, counter `system.runs` |
| `core/system.py:BaseComponent.__init_subclass__` | **Envolver o bloco de span/meta em `@suppress`**; trocar `get_tracer()` direto por `observer.span()`; adicionar `aptdata.run_id`; emitir histogram `component.duration_ms` e counter `component.errors` | span/métrica/erro por componente |
| `core/workflow.py:BaseWorkflow.before_run/after_run` | Registrar início/fim no `observer` (gauge de inputs/outputs, span de flow filho do system) | span de flow, gauge io |
| `core/workflow.py:Workflow._run_step` | Reaproveitar spans existentes; adicionar histogram de retry e counter de step failures via observer | métricas de retry |
| `core/events.py:EventBus` | Adicionar `maxsize` + drop-oldest + counter `observability.dropped`; permitir registrar sinks (`SqliteSink`, `AlertEngine`) | resiliência de fila |
| `agents/router.py:Router.route` | Span `aptdata.route`; event `RouteDecisionEvent`; counter por `mode` | decisão de routing |
| `agents/project.py:ProjectRunner.run` | `run_id` do projeto; span por task `aptdata.agent.dispatch`; event de resultado; histogram latência por agente | traces multi-agente |
| `agents/cli_agents.py:CLIAgent.send` / `base.py:BaseAgent.send` | Envolver em span; counter `agent.calls{agent,ok}`; histogram `agent.latency_ms`; `observer.error` em timeout/OSError | métricas por agente |
| `mcp/server.py` (cada `@mcp.tool`) | Decorator `@observed_tool` que abre span, mede latência, conta erros, propaga `run_id` — sem tocar a lógica de cada tool | métricas MCP por tool |
| `mcp/server.py:get_mcp_status` | Estender com latência média e error_count (lidos do observer) | health MCP |
| `cli/app.py:_emit` | Incluir `run_id` além do `trace_id` já presente | correlação CLI |
| `cli/commands/` | Novo `observability_cmd.py` (ver §6); registrar no `app` | exposição |
| `tui/monitor.py` | Trocar placeholders por leitura real: `_IngestionMetricsPanel` (já usa métricas reais), `_AgentTraceLog` assina EventBus, novo painel de custo/erros do `ObservabilityStore` | TUI viva |
| `core/context.py:ExecutionContext` | Expor `observer` além de `telemetry`/`event_bus`; carregar `RunContext` | injeção |

---

## 6. Exposição

### CLI — `aptdata observability ...` (`cli/commands/observability_cmd.py`)
Mesmo contrato JSON-lines do resto da CLI (`--json`), tabelas Rich no modo humano.
- `observability status` — providers OTel, sinks ativos, health snapshot.
- `observability summary [--days 7]` — custo/tokens/latência/erros (reusa `ObservabilityStore.summary`, hoje `get_observability_summary`).
- `observability events [--kind --run-id --since --limit]` — consulta o store.
- `observability health` — snapshot do `HealthRegistry`.
- `observability alerts [list|test]` — regras e disparo de teste.
- `observability prune [--keep-days 30]` — retenção manual.
- `observability export [--format otlp|prometheus|json]` — flush/export.

O comando `telemetry` atual permanece (retrocompat), delegando ao novo.

### TUI
- Painel de custo/erros/latência lendo `ObservabilityStore` (poll no `set_interval` já existente).
- `_AgentTraceLog` vira listener do EventBus (routing/dispatch em tempo real).

### Endpoint / export
- **Padrão**: sink SQLite local (zero infra). Dev vê tudo via CLI/TUI.
- **Opcional**: `configure_telemetry(span_exporter=OTLP, metric_reader=Prometheus/OTLP)` via env (`OTEL_EXPORTER_OTLP_ENDPOINT` já documentado). Export Prometheus como `MetricReader` plugável — não obrigatório.
- **Não** subir um servidor HTTP próprio na v1 (superfície de ataque/erro). Se necessário, o MCP server pode ganhar uma tool `get_observability_summary` (fecha o loop pros agentes).

---

## 7. Fases incrementais (cada uma entregável e testável)

### Fase 0 — Fundação de resiliência (bloqueante das demais)
- `observability/safe.py` (`suppress`, `safe_call`, `SafeTimeout`, circuit breaker).
- `observability/correlation.py` (`RunContext`, `new_run_id`, `current_run_id`).
- `EventBus`: `maxsize` + drop-oldest + counter `observability.dropped`.
- Kill switch `APTDATA_OBS_DISABLED`.
- **Entrega**: primitivas no-throw. **Testes**: injeção de falha (sink que sempre levanta) não afeta resultado; overflow dropa sem travar; timeout aborta.

### Fase 1 — Façade Observer + reaproveitar OTel
- `observability/observer.py` (`Observer`, `NoOpObserver`, `get_observer`), `signals.py`.
- Refatorar `BaseComponent.__init_subclass__` para usar `observer.span()` sob `@suppress` (sem mudar comportamento observável de negócio).
- Expor `observer` no `ExecutionContext`.
- **Entrega**: API única de sinais. **Testes**: `InMemorySpanExporter` confirma spans; observer com OTel quebrado ainda roda component.

### Fase 2 — Persistência própria + retenção
- `sinks/sqlite_sink.py` (`ObservabilityStore`, WAL, `prune`), `sinks/stdout_sink.py`.
- Migrar `get_observability_summary` → `ObservabilityStore.summary`; `llm_observer` aceita o store nativo.
- Registrar `SqliteSink` como listener do EventBus.
- **Entrega**: eventos persistidos localmente sem mindflow. **Testes**: round-trip write/query; prune; DB read-only não derruba (circuit breaker).

### Fase 3 — Correlação System→Flow→Component
- `run_id` em `BaseSystem.run`, propagado a Flow/Component; span raiz; `_emit`/CLI incluem `run_id`.
- Métricas `component.duration_ms`, `component.errors`, `system.runs`.
- **Entrega**: um trace/`run_id` conecta o pipeline inteiro. **Testes**: spans compartilham `run_id`; falha em component gera event `on_failure` correlacionado.

### Fase 4 — Instrumentação de Agents e MCP
- Spans/métricas em `Router.route`, `ProjectRunner.run`, `*.send`; decorator `@observed_tool` no MCP.
- `run_id` de projeto; latência/erro por agente.
- **Entrega**: observabilidade do núcleo multi-agente e do MCP. **Testes**: dispatch com agente `DOWN`/timeout vira métrica+event, `send` continua retornando `AgentResponse` (nunca levanta).

### Fase 5 — Health + Alertas
- `health.py` (`HealthRegistry` + checks embutidos).
- `alerts.py` (`AlertEngine`, `AlertRule`, `TelegramChannel` fire-and-forget) como listener.
- **Entrega**: erro/latência/custo disparam Telegram; `health` snapshot. **Testes**: regra dispara canal fake com cooldown; canal quebrado não afeta run.

### Fase 6 — Exposição (CLI + TUI)
- `observability_cmd.py` (status/summary/events/health/alerts/prune/export).
- TUI: painel de custo/erros + `_AgentTraceLog` plugado no EventBus.
- Docs: atualizar `docs/telemetry.md` / novo `docs/observability.md`.
- **Entrega**: Lucas vê tudo por CLI/TUI. **Testes**: CLI JSON-lines por comando; TUI renderiza dados reais (snapshot test).

Dependências entre fases: 0 → 1 → {2, 3} → 4 → 5 → 6. Fases 2 e 3 são paralelizáveis após a 1.

---

## 8. Estratégia de testes da própria observabilidade

- **Exporters in-memory** (`InMemorySpanExporter`, `InMemoryMetricReader`) via `configure_telemetry(span_exporter=..., metric_reader=...)` — asserção direta de spans/métricas. Padrão já viável (ver `tests/test_telemetry_instrumentation.py`).
- **Testes de resiliência (os mais importantes)**:
  - *Fault injection*: sink/exporter/canal que sempre levanta → o run de negócio produz o **mesmo** resultado (asserção de igualdade de output com e sem falha).
  - *Property/fuzz* no `mask_telemetry_value` e no `suppress` (qualquer input → nunca propaga).
  - *Overflow*: floodar o EventBus além do `maxsize` → nenhum bloqueio, counter `observability.dropped` sobe.
  - *Timeout*: sink lento além do deadline → run não trava (mede wall-clock).
  - *Circuit breaker*: N falhas → sink entra em cooldown; conta tentativas.
- **Correlação**: asserção de que `run_id`/`trace_id` são iguais ao longo de System→Flow→Component e Router→Task.
- **Contrato no-throw**: teste parametrizado que chama **todo** método público do `Observer` com OTel desconfigurado, DB read-only e EventBus parado — nenhum levanta.
- **CLI**: subprocess/`CliRunner`, valida 1 JSON line válido por comando e exit codes.
- **Retenção**: `prune` remove só o que passou de `keep_days`.
- **Kill switch**: `APTDATA_OBS_DISABLED=1` → `NoOpObserver`, zero I/O.
- Manter `fail_under = 80` (pyproject). `mcp/server.py` está no `omit` de coverage — cobrir a lógica do decorator `@observed_tool` em teste unitário separado do server.

---

## 9. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Observabilidade derrubar o app | `@suppress` universal, sinks fora do caminho quente, circuit breaker, kill switch, testes de fault injection dedicados. |
| Overhead de span por component | Span é barato; métricas agregadas; `OTEL_SDK_DISABLED`/`NoOpObserver` para hot paths; histogram em vez de log por item. |
| Estado global (singletons `IngestionMetrics`, `_TOKEN_COUNTER`) | Manter locks já existentes; `Observer` singleton lazy e substituível por `NoOp`; evitar novo estado global mutável fora dos sinks. |
| Vazamento de segredos nos sinais | Reusar `mask_telemetry_value` em TODO payload de event/log/span antes de persistir/exportar. |
| Crescimento do SQLite | WAL + `prune` automático no fim do run + comando manual. |
| Divergência com telemetria existente | `telemetry/` vira camada baixa; `observability/` reexporta; nada quebra import público. |

---

## 10. Resumo de entregáveis por arquivo (novos)

- `aptdata/observability/observer.py`, `signals.py`, `safe.py`, `correlation.py`, `health.py`, `alerts.py`
- `aptdata/observability/sinks/{sqlite_sink,stdout_sink}.py`
- `aptdata/cli/commands/observability_cmd.py`
- Edições: `core/system.py`, `core/workflow.py`, `core/events.py`, `core/context.py`, `agents/{router,project,cli_agents,base}.py`, `mcp/server.py`, `cli/app.py`, `tui/monitor.py`
- Testes: `tests/test_observability_{safe,observer,sqlite_sink,correlation,agents,mcp,alerts,health,cli}.py`
- Docs: atualizar `docs/telemetry.md` + novo `docs/observability.md`
