# Telegram → Orquestração de Agentes (via aptdata)

> Plano de arquitetura + UX · 01/07/2026
> Status: Fases 0-1 IMPLEMENTADAS (ConversationEngine headless + DecisionPolicy
> via bloco `routing:` + SessionStore + CLI `aptdata converse` + MCP
> `converse`/`confirm`, com eventos permission.* no traço). Fases 2+ pendentes.

---

## 0. Objetivo em uma frase

Transformar uma mensagem solta no Telegram numa **decisão de roteamento transparente**,
com **confirmação quando faz sentido**, **contexto multi-turno**, e **entrega/resposta
rastreável** — reusando o `Router`/`dispatch` que o aptdata **já tem**, sem duplicar lógica.

---

## 1. Estado atual (confirmado no código)

### O que o aptdata já entrega (a fundação está pronta)
- `aptdata/agents/router.py` — `Router.route(text) -> RouteDecision` com 4 modos
  (`prefix` 1.0 · `skill` 0.5–1.0 · `llm` 0.5 · `default` 0.3 · `none`). O `RouteDecision`
  **já carrega `mode`, `confidence`, `skill`, `matched_keyword`** — matéria-prima pronta
  para a transparência da decisão.
- `aptdata/agents/registry.py` — `AgentRegistry.from_yaml("agents.yaml")`, fonte única.
- `aptdata/agents/base.py` — `IAgent.send(prompt) -> AgentResponse(ok/text/error)`.
- Adapters: `OpenClawAgent` (HTTP `/api/chat`), `ClaudeCodeAgent`/`OpenCodeAgent` (CLI
  one-shot, **já síncronos**), `_PlaceholderAgent` (ex.: `docker_compose`/Boleiro).
- `aptdata/agents/project.py` — `Project`/`ProjectRunner` (Flow de tarefas → agents).
- `aptdata/mcp/server.py` — MCP tools `dispatch(prompt, hint)`, `list_agents`, `run_flow`.

### O que o plugin TS já tem (a herdar / aposentar)
`opencode-telegram-plugin/plugin/src/`: grammy `bot.ts`, `dispatcher.ts` (lógica **duplicada**
do Router — a aposentar), `task-queue.ts` (fila persistida pending/running/done/failed com
correlação por `id`), `pending-questions.ts`/`pending-permissions.ts` (loop de botões inline),
`learning-loop.ts` (feedback de overrides), `failure-notifier.ts`, `claim.ts`/`lock.ts`.

### A restrição crítica de transporte
- **Envio SÍNCRONO ao worker OpenClaw está TRAVADO.** Gateway é WebSocket (protocol 4,
  `sessions.send`), exige device operator com scope `operator.write` — **não provisionado**
  (só há `operator.pairing`). Passo 2 = provisionar via `openclaw qr`.
- Hoje só dá pra alcançar worker **fire-and-forget** (a resposta volta no canal Telegram do
  próprio worker, não inline). O `OpenClawAgent.send()` via HTTP `/api/chat` **não é entrega
  confiável hoje** — tratar como best-effort/enfileirar.
- CLI agents (Gandalf/Claude Code, Darwin/OpenCode) **já respondem síncrono** — bom pra
  provar o fluxo ponta-a-ponta antes do WS.

**Consequência de design:** o loop de decisão precisa separar **"despachado" (receipt)** de
**"respondeu" (result)**, e lidar com resposta assíncrona/correlacionada.

---

## 2. Decisão de arquitetura

### Escolha: **cérebro no aptdata + transporte fino (cliente-MCP)**

Alinhado com a visão do cerne (Fase 4 do `planejamento-aptdata-cerne.md`: "plugin vira
transporte fino, deleta lógica duplicada"). Rejeitamos "plugin-no-aptdata" no sentido de um
plugin gordo com sua própria lógica de roteamento — isso recria a divergência dos 3 registros.

```
  Telegram (Lucas)
        │  texto / clique em botão
        ▼
  ┌──────────────────────────────┐     transporte FINO:
  │  Transporte Telegram (thin)  │     só renderiza cards + botões,
  │  - relay texto  → converse   │     relê MCP, nunca decide rota
  │  - clique       → confirm     │
  │  - result ready → notify      │
  └───────────────┬──────────────┘
                  │ MCP (ou import in-process p/ o bot Python)
                  ▼
  ┌──────────────────────────────────────────────────────────┐
  │  APTDATA — CÉREBRO DE CONVERSA/ORQUESTRAÇÃO (novo)        │
  │  aptdata/agents/conversation.py  ConversationEngine       │
  │    · handle(session, text) -> Turn                        │
  │    · usa Router (já existe) p/ decidir                    │
  │    · SessionStore (multi-turno, via state)                │
  │  aptdata/agents/delivery.py      DeliveryTracker          │
  │    · correlação + fila async (porta do task-queue TS)     │
  │  Router · AgentRegistry · adapters  (JÁ EXISTEM)          │
  └──────────────────────────────────────────────────────────┘
```

**Por que MCP como costura:** o mesmo cérebro serve Telegram, TUI, painel web e agentes-IA.
Para o **bot Python** (co-localizado), a opção mais barata é `import` in-process do
`ConversationEngine` (sem hop MCP); MCP fica para transportes remotos/heterogêneos. As MCP
tools novas são um wrapper fino sobre o mesmo engine — não há segunda implementação.

**Onde o transporte vive (recomendação):** aparar o plugin TS existente OU escrever um bot
Python fino. Recomendo **bot Python fino** que importa o engine in-process (latência mínima,
tudo Python, sem ponte TS↔Python), reaproveitando as *ideias* do TS (task-queue, botões,
failure-notifier) já portadas pra dentro do aptdata. O TS vira legado a aposentar.

### Regra de ouro
> Nenhuma decisão de rota, nenhum threshold, nenhum estado de conversa vive no transporte.
> Transporte = I/O do Telegram. Cérebro = aptdata.

---

## 3. Fluxo conversa → decisão → confirmação → dispatch → resposta

### Diagrama (ASCII)

```
 Lucas ──"arruma o css do header"──► Transporte ──converse(sess, txt)──► ConversationEngine
                                                                              │
                                                            carrega SessionStore[sess]
                                                            (histórico, decisão pendente,
                                                             correlações ativas, overrides)
                                                                              │
                                                                     Router.route(txt)
                                                                              │
                                                                 RouteDecision{agent, mode,
                                                                   confidence, skill, kw}
                                                                              │
                                        ┌─────────────────────────────────────┼───────────────┐
                                        ▼                     ▼                ▼               ▼
                                   POLÍTICA DE DECISÃO (confidence + capability + guardrails)
                                        │                     │                │               │
                              prefix / skill-alto        skill-médio        default/none    capability
                                   (>= 0.75)              ou llm            (sem sinal)      destrutiva
                                        │                     │                │           (deploy/ssh/
                                        ▼                     ▼                ▼            docker) → SEMPRE
                                  DISPATCH DIRETO      NEEDS_CONFIRM      NEEDS_CLARIFY      NEEDS_CONFIRM
                                  (+ card "por quê"    (card + botões:    (pergunta:            │
                                   + botão desfazer)    Confirmar/Trocar/  "qual área?          │
                                        │               Editar)            o quê?")             │
                                        │                     │                │               │
                                        │        Lucas clica  │   Lucas responde texto         │
                                        │        confirm(...) │   → volta pro Engine (merge)   │
                                        │                     └────────┬───────────────────────┘
                                        ▼                              ▼
                                 ┌───────────── DISPATCH via AgentRegistry.get(id).send / async ─────────┐
                                 │                                                                        │
                        agente SÍNCRONO (CLI:                            agente FIRE-AND-FORGET
                        Gandalf/Darwin)  OU  WS-sync                     (OpenClaw hoje)
                                 │                                                │
                        AgentResponse inline                       DeliveryTracker.create(corr_id)
                                 │                                  envia prompt + tag [apt:req:xxxx]
                                 ▼                                  status=pending → devolve RECEIPT
                        "✅ Ondina respondeu: …"                            │
                                                                    "📨 Despachei pro Ondina
                                                                     (req xxxx). Aviso quando responder."
                                                                            │
                                                          resposta do worker chega (webhook/dropfile/
                                                          canal do worker) → match por corr_id
                                                                            │
                                                          DeliveryTracker.answer(corr_id, text)
                                                                            │
                                                          Transporte.notify(chat) ► nova msg (com ping):
                                                          "✅ Resposta do Ondina (req xxxx): …"
```

### Política de decisão (quando dispatch direto × confirmar × esclarecer)

| Situação (do `RouteDecision`)        | Ação            | UX no Telegram                                   |
|--------------------------------------|-----------------|--------------------------------------------------|
| `mode=prefix` (`/ondina ...`)        | Dispatch direto | card curto "por quê" + botão *Desfazer*          |
| `mode=skill`, `confidence >= 0.75`   | Dispatch direto | card "por quê" + *Desfazer/Trocar*               |
| `mode=skill`, `0.5 ≤ conf < 0.75`    | **Confirmar**   | card + botões *Confirmar · Trocar agente · Editar* |
| `mode=llm` (0.5)                     | **Confirmar**   | mostra 1º + alternativa; botões idem             |
| `mode=default` (0.3) / `none`        | **Esclarecer**  | pergunta ("qual área? o que quer fazer?")        |
| capability destrutiva (deploy/ssh/docker/ops) | **Confirmar sempre** | guardrail, ignora confiança |

- Thresholds e a lista de capabilities-guardrail ficam em `agents.yaml` (bloco `routing:`),
  não hard-coded — Lucas ajusta sem recompilar.
- **Follow-up multi-turno:** "continua", "e agora?", "manda de novo pro mesmo" reusam
  `session.last_agent` sem re-rotear. Uma resposta a um *clarify* é mesclada na decisão pendente.

### Transparência da decisão (reusa o que já existe)
- Card renderiza direto de `RouteDecision.to_dict()`:
  `🧭 Ondina · skill:frontend · kw:'css' · conf 0.82`.
- Botão **Trocar agente** → lista `list_agents()` (enabled) → `reroute(sess, agent_id)` força
  `mode=override`, dispatch, e **grava o override** (alimenta learning-loop → ajusta skill table).
- Botão **Editar** → reabre o texto pra refinar antes de despachar.

---

## 4. Loop de confirmação e entrega assíncrona

O ponto mais sensível dado o transporte travado. Modelo de **dois acks**:

1. **Receipt (imediato):** ao despachar fire-and-forget, `DeliveryTracker.create(corr_id, agent,
   prompt)` marca `pending` e o transporte responde na hora: *"📨 despachei pro X, req `xxxx`"*.
2. **Result (eventual):** quando a resposta do worker chega, casa por `corr_id` e o transporte
   manda **mensagem nova** (com push) no chat original: *"✅ resposta do X (req xxxx): …"*.

### Correlação (como casar resposta com pedido)
- Injeta uma tag curta no prompt de saída: `[apt:req:xxxx]` (ou header, se o canal permitir).
- Coletor de resultado (uma das vias, por ordem de robustez):
  - **(a) Dropfile compartilhado** — worker escreve resposta em `/workspace/.aptdata/replies/<corr>.json`
    (bind mount já existe); `DeliveryTracker` faz poll/`watch`. Mais confiável hoje.
  - **(b) Webhook** — reaproveitar o padrão do `holt-webhook.py`: worker/gateway faz POST de volta.
  - **(c) Canal do worker** — se controlarmos o bot do worker, lê a resposta e casa por tag.
- **Timeout/retry:** `DeliveryTracker` herda os estados do task-queue TS (`pending/running/done/
  failed` + `retryCount`), persistido via o módulo `state` do aptdata. Timeout → *"⏳ X não
  respondeu em Ns"* + botão *Reenviar*.

### Interface do adapter (para o swap do passo 2 ser local)
Estender `IAgent` para expor os dois modos, isolando a mudança de transporte num só lugar:
- `send(prompt) -> AgentResponse` — síncrono; hoje só CLI agents cumprem; OpenClaw levanta
  `NotDeliverable` até o WS.
- `dispatch_async(prompt, corr_id) -> Receipt` — fire-and-forget; devolve receipt na hora.

O `ConversationEngine` escolhe `send` vs `dispatch_async` por capacidade do agente (flag no spec),
então **nada acima do adapter muda** quando o WS ligar.

---

## 5. O que muda quando o passo 2 (operator.write / `sessions.send` síncrono) ficar pronto

- **Só o transporte do `OpenClawAgent` troca:** HTTP/fire-and-forget → WS protocol 4
  `sessions.send {key,message}`, correlação por `id` da resposta. `send()` passa a devolver
  `AgentResponse` inline.
- **Loop de confirmação colapsa** para OpenClaw: dispatch vira síncrono como os CLI agents; os
  dois acks viram um só ("✅ respondeu: …").
- **DeliveryTracker** deixa de ser obrigatório para OpenClaw — fica reservado a jobs longos
  (quando a resposta demora além do timeout do WS) e a projetos multi-tarefa.
- **Zero mudança** no `ConversationEngine`, na política de decisão, no transporte Telegram ou
  nas MCP tools. É por isso que a interface `send`/`dispatch_async` do §4 vale a pena agora.

---

## 6. Arquitetura do plugin — interfaces

### Novos módulos no aptdata (o cérebro)
- `aptdata/agents/conversation.py`
  - `ConversationEngine(router, registry, delivery, store, policy)`
  - `handle(session_id, text) -> Turn`
  - `Turn` = união: `Dispatched(agent, response)` · `NeedsConfirmation(decision, candidates)` ·
    `NeedsClarification(question)` · `Reply(text)` · `Receipt(corr_id, agent)`
  - `confirm(session_id, decision_id, choice)`, `reroute(session_id, agent_id)`
  - `SessionStore` — persiste histórico/decisão-pendente/correlações via `aptdata` state.
  - `DecisionPolicy` — lê thresholds/guardrails de `agents.yaml`.
- `aptdata/agents/delivery.py`
  - `DeliveryTracker` — porta do `task-queue.ts` (create/start/answer/fail/retry/list/stats),
    persistido em JSON/state; correlação por `corr_id`.

### MCP tools novas (wrapper fino sobre o engine)
- `converse(session_id, text) -> Turn(json)`
- `confirm(session_id, decision_id, choice) -> Turn(json)`
- `reroute(session_id, agent_id) -> Turn(json)`
- `poll(corr_id) -> DeliveryStatus` (ou push via webhook do transporte)
- reusa `dispatch`, `list_agents` já existentes.

### Transporte Telegram (fino — o que ele PODE fazer)
- Relay de texto → `converse`; clique de botão → `confirm`/`reroute`.
- Render de card a partir do `Turn`/`RouteDecision` (botões inline).
- Receber/pollar result e emitir mensagem nova (push) no chat.
- **Não** contém: skill-matcher, llm-router, prefix-router, thresholds, estado de decisão.

---

## 7. Fases incrementais (cada uma entrega valor sozinha)

**Fase 0 — Contratos (sem comportamento novo)**
- Definir `Turn`, `DecisionPolicy`, `DeliveryStatus`, assinaturas MCP.
- Bloco `routing:` em `agents.yaml` (thresholds + capabilities-guardrail).
- Entrega: contratos revisáveis, nada quebra.

**Fase 1 — ConversationEngine no aptdata (headless)**
- `ConversationEngine` + `SessionStore` + `DecisionPolicy`, reusando `Router`.
- Política: dispatch-direto / confirm / clarify / guardrail.
- Expor `aptdata converse` (CLI) + MCP `converse`/`confirm`.
- Entrega: dá pra conversar e ver a decisão + "por quê" **sem Telegram** (CLI/MCP/testes).

**Fase 2 — Telegram fino + fluxo síncrono (CLI agents)**
- Bot Python fino → engine in-process; cards + botões (confirm/reroute/editar).
- Sessão multi-turno persistida; captura de override → learning.
- Entrega: chat → card → confirma → dispatch → resposta **inline** para Gandalf/Darwin
  (que já são síncronos). Prova o loop ponta-a-ponta.

**Fase 3 — Entrega assíncrona + correlação (OpenClaw fire-and-forget)**
- `DeliveryTracker` + tag `[apt:req]` + coletor (dropfile/webhook) + notificação de result.
- Modelo dos dois acks (receipt + result), timeout/retry.
- Entrega: despacho pra Ondina/Maresia com receipt e resposta eventual reportada no canal.

**Fase 4 — WS síncrono (quando operator.write existir)**
- Trocar transporte do `OpenClawAgent` p/ WS `sessions.send` (§5). Loop colapsa. Zero mudança acima.
- Entrega: experiência síncrona unificada em todos os agentes.

**Fase 5 — Aprendizado + painel**
- Learning-loop ajusta thresholds/skill table a partir dos overrides.
- Painel consome telemetry de decisão/entrega (aposenta lógica no painel estático).
- Aposentar o dispatcher/rota TS de vez.

---

## 8. Assunções e riscos

1. **Assumo** que o bot Python in-process é aceitável (tudo é Python/co-localizado); se um dia
   o transporte precisar ser remoto, o MCP já cobre — sem retrabalho.
2. **Assumo** que dá pra fazer o worker escrever um dropfile em `/workspace/.aptdata/replies/`
   (bind mount confirmado) — via de correlação mais robusta antes do WS.
3. **Risco:** o `OpenClawAgent.send()` HTTP atual dá falsa sensação de entrega síncrona.
   Mitigação: marcá-lo `NotDeliverable`/best-effort até o WS; roteá-lo por `dispatch_async`.
4. **Risco:** portar task-queue/learning-loop do TS tem custo. Mitigação: portar só o núcleo
   (estados + correlação) na Fase 3; o resto do TS morre.
5. **Decisão:** não forkar nada — estender o aptdata; transporte é cliente fino.
```
