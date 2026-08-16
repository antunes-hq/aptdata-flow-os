# ADR 0006 — Telegram como canal de eventos e acesso temporário ao navegador

**Status:** Accepted  
**Data:** 2026-08-16  
**Decisão:** Telegram será o canal de notificações/aprovações da execução; o navegador usará uma sessão temporária emitida pelo Control Plane. Tokens de infraestrutura nunca serão enviados como credencial de navegador.

## Problema

Enquanto uma squad executa uma jornada, Lucas precisa:

```text
saber que começou
entender o que está acontecendo sem acompanhar logs
ver checkpoints e bloqueios
aprovar ações de risco
abrir o estado visual no navegador
retomar depois sem depender da conversa
```

O chat não pode virar o centro do estado. Ele apenas recebe eventos e oferece ações autorizadas.

## Estado atual verificado

A superfície Nuvem atual:

```text
GET /                         → HTTP 200
GET /cloud sem Authorization  → HTTP 401
```

O servidor atual usa `CAPTURE_TOKEN` como Bearer fixo e o PWA salva o token no `localStorage` para consultar/capturar. Esse mecanismo é legado/pessoal e **não é o desenho final para uma sessão cloud/licenciada**.

Arquivos de referência:

```text
/home/strondinha/lab/antunes-hq/nuvem/servidor/server.py
/home/strondinha/lab/antunes-hq/nuvem/app/src/views/Setup.svelte
```

## Modelo de superfícies

```text
Flow OS Control Plane
  = fonte de estado, runs, evidências, políticas e sessões

Telegram adapter
  = recebe eventos e apresenta comandos de consulta/aprovação

My Universe adapter
  = mostra o universo planetário e a retomada humana

Browser session
  = sessão curta para acessar Definition/Run/Control Views
```

Telegram e navegador consultam o mesmo `run_id`/`workspace_id`; nenhum mantém uma cópia concorrente do estado.

## Protocolo de notificações Telegram

Cada squad/run tem um `work_id` e `run_id`. Mensagens são curtas, orientadas a decisão, e sempre trazem próximo passo.

### Evento `run.started`

```text
🚀 Squad iniciada
Flow: <flow_definition>
Run: <run_id curto>
Objetivo: <uma linha>
Fases: PO → Tech/UX → QA → Judge → Integrator
Executor pool: <resumo>
Acompanhar: <link My Universe/Control View quando disponível>
Próximo: aguardando primeiro checkpoint
```

### Evento `stage.completed`

```text
✅ PO concluído
Run: <run_id curto>
Entregou: <artefato/decisão>
Evidência: <commit/arquivo/receipt>
Próximo: Tech Lead + UI/UX
Abrir: <link temporário, se emitido>
```

### Evento `checkpoint`

```text
📍 Checkpoint <n>/<total>
Run: <run_id curto>
Feito: <resumo curto>
Testes: <pass/fail + comando resumido>
Risco: <none/warning/high>
Próximo passo: <um passo>
```

### Evento `approval.required`

```text
🟡 Aprovação necessária
Ação: <deploy/restart/DNS/fechar PR/etc.>
Por quê: <motivo>
Escopo: <workspace/projeto/ambiente>
Risco: <nível>
Expira: <timestamp>
[aprovar] [recusar] [abrir evidência]
```

A ação só pode ser executada após a aprovação correspondente. Botões são referências a comandos autorizados, não bypass de policy.

### Evento `run.blocked`

```text
🛑 Squad bloqueada
Run: <run_id curto>
Bloqueio: <causa real>
O que falta: <input único>
Alternativa: <fallback, se existir>
Ação disponível: <responder/aprovar/replanejar>
```

### Evento `run.completed`

```text
🏁 Run encerrada
Run: <run_id curto>
Resultado: verified/integrated/blocked
Entregas: <lista curta>
Evidência: <links/commit/build/smoke>
Pendências: <0 ou lista>
Retomar: <link para My Universe/Run View>
```

### Regras de entrega

- evento importante chega imediatamente no Telegram;
- mensagens repetitivas são agregadas por `run_id`;
- heartbeat não vira spam: no máximo um resumo por janela configurada;
- falha, bloqueio e aprovação nunca são silenciosos;
- cada notificação aponta para o artefato/estado externo;
- o texto não contém segredo, token, transcript bruto ou payload privado desnecessário;
- se Telegram estiver fora, o evento permanece no ledger/outbox e não se perde.

## Acesso ao navegador

### O que Lucas receberá

Não será o `CAPTURE_TOKEN`, `FLOW_MCP_TOKEN`, token Vercel, SSH key ou OAuth secret.

O produto emitirá um **Browser Session Grant** curto:

```text
session_grant_id
workspace_id
scopes
created_at
expires_at
single_use=true
bound_to=telegram_user_id
```

Formato de UX possível:

```text
🔐 Acesso temporário pronto
Abrir: https://app.flow-os.../access/<opaque-grant>
Validade: 10 minutos
Uso: uma vez
Escopo: leitura do run <run_id>
```

Alternativa quando links não forem desejáveis:

```text
Código: FLOW-7KQ2-M9P4
Validade: 10 minutos
Abrir: https://app.flow-os.../access
```

O código é trocado no Control Plane por cookie de sessão `HttpOnly`, `Secure`, `SameSite` apropriado. O grant é consumido e revogado na troca.

### Scopes iniciais

```text
run:read
flow:read
artifact:read
approval:respond
```

Por padrão, o grant do acompanhamento é read-only. `deploy:production`, `connector:write` e `admin:workspace` não entram nele.

### Expiração e revogação

```text
TTL curto (ex.: 10 minutos)
single-use
revogável pelo Telegram
invalidado após logout
invalidado se o run/workspace for revogado
rate limit no endpoint de troca
não registrar o valor bruto do grant em logs
```

O TTL exato será uma policy configurável e testada; o exemplo de 10 minutos é o default inicial proposto, não uma promessa de implementação atual.

## Segurança

```text
Telegram não recebe segredo de provider
browser não recebe token de infraestrutura
grant não é reutilizado como upstream token
Control Plane valida workspace/user/scope no servidor
My Universe recebe somente projeções autorizadas
MCP recebe sessão/token destinado ao próprio MCP
runner resolve secrets somente no boundary de execução
logs registram hash/id do grant, nunca o valor
```

O link pode aparecer no histórico do Telegram; por isso ele precisa ser curto, one-shot, revogável e limitado por escopo. Para ambientes de maior risco, oferecer aprovação manual adicional ou exigir código digitado no navegador.

## Acompanhamento visual

O link temporário abre a superfície correspondente ao run:

```text
My Universe → estrela/planeta → detalhe → retomada
flow-viz    → Run View → stages → evidence
Control     → approvals → actions
```

A URL não deve abrir um dashboard genérico sem contexto. Ela deve apontar para:

```text
workspace + project + run_id
```

O servidor ainda revalida tudo; parâmetros da URL nunca concedem acesso por si só.

## Outbox e durabilidade

Eventos de squad são escritos primeiro no ledger/outbox:

```text
run event → outbox → Telegram delivery attempt
                    ↘ browser SSE/poll projection
```

Se Telegram falhar:

```text
status = delivery_pending
retry com backoff
não duplicar por event_id/idempotency_key
```

A squad não depende de o usuário estar lendo o chat naquele instante.

## Contrato de evento

```json
{
  "event_id": "evt_...",
  "event_type": "stage.completed",
  "workspace_id": "ws_...",
  "project_id": "project_...",
  "flow_definition_id": "flow_...",
  "run_id": "run_...",
  "stage_id": "stage_...",
  "severity": "info",
  "human_summary": "Tech Lead concluiu a arquitetura",
  "next_action": "aguardar QA",
  "evidence_refs": ["receipt_..."],
  "delivery": {
    "telegram": "pending|sent|failed",
    "browser": "available|unavailable"
  },
  "created_at": "..."
}
```

## Critério de aceitação

A implementação estará pronta quando:

1. uma squad gera `run.started`, checkpoints, bloqueios e encerramento;
2. Telegram recebe mensagens legíveis e não recebe segredos;
3. cada evento tem `event_id`/`run_id` e pode ser reprocessado sem duplicar;
4. o usuário recebe um link/código de sessão temporário;
5. a sessão abre o run correto no navegador;
6. o grant expira, é one-shot e pode ser revogado;
7. o navegador usa cookie de sessão e não precisa conhecer `CAPTURE_TOKEN`;
8. read-only e approval scopes são separados;
9. falha de Telegram não perde o evento nem para a squad;
10. a superfície My Universe e o flow-viz mostram o mesmo run por referências compartilhadas.

## Estado e próximos passos

Ainda não existe Browser Session Grant implementado na Nuvem atual. A implementação deve acontecer no Control Plane/adapter novo, mantendo o token legado da Nuvem funcionando durante a migração.

Ordem:

```text
1. event envelope + outbox no SDK/local ledger
2. notifier Telegram read-only
3. browser grant local/self-hosted
4. Run View deep link
5. approval callbacks
6. migração gradual da Nuvem de bearer fixo para sessão/grant
```

## Links

- `docs/plans/flow-os-master-plan.md`
- `docs/plans/ORCHESTRATION.md`
- `IMPLEMENTATION_LEDGER.md`
- `docs/decisions/0002-sdk-api-mcp-cloud-boundary.md`
- `docs/decisions/0005-my-universe-planetary-surface.md`
- `/home/strondinha/lab/antunes-hq/nuvem/servidor/server.py`
- `/home/strondinha/lab/antunes-hq/nuvem/app/src/views/Setup.svelte`
