# ADR 0002 — SDK, Control Plane, MCP e Runner

**Status:** Accepted  
**Data:** 2026-08-16  
**Decisão:** o Flow OS terá SDK próprio, API cloud canônica, MCP como adapter e runners isolados.

## Problema

Precisamos reutilizar a mesma análise, contexto, jornadas e governança em:

- operação pessoal do Lucas;
- apps próprios;
- agents e squads;
- Telegram/Hermes/Claude Code;
- cloud/VPS;
- futuros usuários licenciados.

Um único MCP não resolve isso. MCP é protocolo de exposição para clients/agents, não deve ser o banco, o orquestrador nem a fronteira de tenancy.

## Arquitetura decidida

```text
                    ┌─────────────────────────┐
                    │ Flow OS clients          │
                    │ web · desktop · CLI      │
                    │ Telegram · Hermes        │
                    └────────────┬────────────┘
                                 │ SDK/API
                    ┌────────────▼────────────┐
                    │ Flow OS Control Plane   │
                    │ context · flows · runs │
                    │ policy · approval       │
                    │ evidence · audit        │
                    └───────┬─────────┬────────┘
                            │         │
                 ┌──────────▼───┐ ┌──▼────────────┐
                 │ MCP adapter  │ │ Connectors    │
                 │ tools safe   │ │ GitHub/Vercel │
                 │ resources    │ │ Hostinger/Goog│
                 └──────┬───────┘ └──┬────────────┘
                        │             │
                 ┌──────▼─────────────▼──────┐
                 │ Runner / execution plane │
                 │ local · VPS · self-hosted│
                 │ sandbox · worktree        │
                 └──────────────────────────┘
```

## Camadas

### 1. `flowos-core` / SDK

Biblioteca reutilizável, testável e instalável. Contém contratos e clientes, não segredos:

```text
ContextPacket
WorkPacket
FlowDefinition / FlowVersion
SquadDefinition / RoleContract
FlowRun / StageRun
EvidenceReceipt
Finding / Policy / Approval
Connector contracts
Executor pool contracts
```

Distribuições possíveis:

```text
Python SDK  → aptdata/flowos integrations, workers, CLI
TypeScript SDK → web/desktop clients
CLI          → operação local e self-hosted
```

O SDK pode funcionar offline com storage local e sincronizar com o Control Plane quando configurado.

### 2. Control Plane API

Fonte operacional para workspace, definição, runs, aprovações, evidências e auditoria.

A API cloud não expõe banco bruto. Ela expõe contratos versionados e read models autorizados.

Responsabilidades:

```text
workspace/tenant isolation
project registry
context packets
flow definitions and versions
run ledger
approval queue
policy evaluation
connector account references
executor registry/health
artifact/evidence metadata
audit trail
```

### 3. MCP adapter

MCP é uma projeção controlada da API para clients compatíveis:

```text
Flow OS MCP
├── resources: definição/contexto/evidência autorizados
├── tools read: inspect/list/trace/status
├── tools plan: preview/dry-run
└── tools action: somente com policy + approval
```

O MCP não deve:

```text
- ser a fonte de verdade;
- receber credenciais de providers em prompts;
- expor raw DB/SQL/filesystem;
- oferecer shell arbitrário;
- executar `dispatch(prompt)` sem WorkPacket, policy e audit;
- executar `run_flow(flow_id)` sem workspace, scope e approval;
- repassar o bearer token do cliente para APIs upstream.
```

### 4. Runner / execution plane

Execução próxima do código e da infraestrutura do usuário:

```text
local runner
VPS runner
self-hosted runner
sandbox/worktree runner
```

O Control Plane envia um WorkPacket assinado/autorizado. O runner retorna receipts. O runner não precisa entregar todo o código ou segredo para a nuvem.

## Segurança

### Identidade e tenancy

Toda requisição operacional carrega:

```text
user_id
workspace_id
tenant_id
project_id
flow_definition_id
run_id
```

O servidor verifica autorização no servidor; IDs recebidos pelo client nunca são autorização.

O workspace do Lucas é separado dos workspaces licenciados. O `Lucas Pack` não é enviado ao tenant de outro usuário.

### Autenticação

Modo pessoal/self-hosted inicial:

```text
TLS
bearer token por client/bridge
allowlist de client
rotação/revogação
rate limit
request id
```

Modo cloud/licenciado:

```text
OAuth 2.1/OIDC
access tokens com audience do Control Plane
scopes por workspace/capability
refresh tokens somente no client/vault apropriado
```

Para MCP público, seguir a autorização MCP/OAuth vigente: protected resource metadata, discovery do authorization server, resource indicator e validação de audience. O token recebido pelo MCP nunca é passado diretamente para upstreams.

### Scopes

Exemplos:

```text
flow:read
flow:write
run:read
run:plan
run:dispatch
artifact:read
connector:read
connector:use
deploy:preview
deploy:production
admin:workspace
```

Ações de produção e destrutivas exigem scope + policy + approval. Scope sozinho não é aprovação.

### Tool classes

```text
READ       → lista/consulta; sem efeito colateral
PLAN       → calcula proposta/dry-run; sem efeito colateral
REVERSIBLE → branch, preview, snapshot; policy + talvez approval
PRODUCTION → deploy/restart/DNS; approval explícito
DESTRUCTIVE → delete/revoke/data; aprovação explícita + backup + confirmação
```

### Segredos

```text
MCP/client → secret reference
Control Plane → vault/keyring provider
Connector → resolve segredo no boundary de execução
Provider → recebe segredo somente quando necessário
Model → nunca recebe segredo bruto
Frontend → nunca recebe segredo bruto
Ledger → registra secret_ref e resultado, nunca valor
```

Para Lucas, `.env`/keyring continuam sendo opção local. Para produto licenciado, usar secret manager do deployment/tenant; não colocar tokens no registry versionado.

### Dados e exposição

Default:

```text
minimização de payload
sem raw DB
sem transcript completo por padrão
sem código privado na cloud sem opt-in
retention configurável
redaction antes de telemetry/evidence
logs sem tokens
```

O run ledger guarda referências, hashes, metadados e receipts. O artefato completo permanece no repo/storage autorizado quando possível.

### Auditoria e replay

Toda ação relevante gera:

```text
audit_event_id
actor
workspace
capability
requested_action
policy_decision
approval_id
start/end
result
external_handle
rollback_hint
```

`resolved` exige receipt verificável. Falha de connector, fallback de executor e intervenção humana também são eventos.

## Reuso/licenciamento

```text
aptdata              → kernel/framework
flowos-core          → SDK e contratos
flowos-control-plane → serviço/API
flowos-mcp           → adapter MCP
flowos-connectors    → módulos por provider
flowos-runner        → execução local/VPS/self-hosted
lucas-context-pack   → contexto proprietário do Lucas
```

O produto deve permitir:

```text
local-only
self-hosted
cloud-hosted
hybrid (control plane cloud + runner local)
```

O modo híbrido é o padrão recomendado para código privado e infraestrutura pessoal.

## Segurança do MCP atual do aptdata

O módulo existente `aptdata/mcp/server.py` é reaproveitável como referência de ferramentas e compatibilidade, mas não é o gateway cloud final. Antes de qualquer exposição pública, deve passar por uma evolução explícita:

```text
FastMCP/demo tools
  → MCP adapter sobre Control Plane
  → auth/scope/tenant middleware
  → safe tool registry
  → approval/policy integration
  → audit/evidence
  → threat tests
```

A implementação cloud não deve simplesmente publicar o módulo atual por Traefik.

## Critério de aceitação da arquitetura

A arquitetura está provada quando:

1. um app local usa o SDK sem cloud;
2. o mesmo WorkPacket pode ser enviado ao Control Plane;
3. um client MCP consulta apenas dados autorizados;
4. uma ação `PLAN` não altera estado;
5. uma ação `PRODUCTION` fica pendente sem approval;
6. o runner executa sem entregar segredo ao model;
7. cada evento pode ser auditado por workspace/run;
8. outro workspace não consegue ler IDs, skills privadas ou artefatos do Lucas;
9. a indisponibilidade do MCP não impede o SDK/CLI local de continuar;
10. o token do MCP não é aceito como token de Vercel/Hostinger/Google.

## Ordem de construção

```text
1. SDK contracts + local fake/in-memory Control Plane
2. WorkPacket/run/evidence round-trip
3. policy + approval model
4. Control Plane read/plan API
5. local runner
6. safe MCP read/plan adapter
7. connector GitHub read-only
8. connector Vercel/Hostinger/Google por capability
9. action tools com approval
10. OAuth/multi-tenant/licensing hardening
```

Não começar pelo MCP público. Começar pelos contratos e pelo SDK local.

## Referências

- `docs/plans/flow-os-master-plan.md`
- `docs/plans/ORCHESTRATION.md`
- `IMPLEMENTATION_LEDGER.md`
- `aptdata/mcp/server.py` (estado atual, não gateway final)
- MCP Authorization: https://modelcontextprotocol.io/specification/latest/basic/authorization
