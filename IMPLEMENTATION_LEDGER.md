# Flow OS — Implementation Ledger

> Este ledger é a proteção contra trabalho repetido e contra "feito" sem prova.
> O estado aqui é o estado oficial das entregas do Flow OS. Conversas, prompts e relatos de agentes não fecham tasks sozinhos.

## Estados permitidos

```text
proposed
planned
in_progress
implemented_unverified
verified
integrated
blocked
superseded
retired
```

`done` não é um estado permitido. Use `integrated` somente quando todos os gates passaram.

## Evidência mínima para `verified`

```text
- arquivo(s) e diff identificáveis;
- teste/checagem executado com comando exato e saída real;
- commit SHA;
- fonte live conferida quando houver runtime/provider;
- risco residual;
- reviewer/verificador;
```

## Evidência mínima para `integrated`

```text
- `verified` já registrado;
- integração exercitada no ambiente alvo;
- URL/ID/handle externo ou saída de deploy;
- rollback conhecido;
- documentação/registry atualizado;
- nenhuma duplicata concorrente ativa;
```

## Ledger

| ID | Fase | Entrega | Estado | Artefatos | Prova | Próximo passo |
|---|---|---|---|---|---|---|
| F0.0 | 0 | Reconhecer aptdata como kernel candidato e criar fork de laboratório | verified | `https://github.com/antunes-hq/aptdata-flow-os` | `pytest -q`: 732 passed, 10 skipped; fork API confirma `fork=true`, parent `bora-hq/aptdata` | executar F0.1 |
| F0.1 | 0 | Universe Registry inicial de repos, apps, skills, executors e providers | planned | — | — | inventariar fontes reais e registrar objetos |
| F0.2 | 0 | Contratos `WorkPacket`, identidade universal e Definition/Run/Control | planned | — | — | escrever schemas + contract tests |
| F0.3 | 0 | Check anti-duplicação para demanda/artefato antes de implementação | planned | — | — | definir matching por ID, path, símbolo e comportamento |
| F0.4 | 0 | Fronteira SDK + Control Plane + MCP + Runner e security threat model inicial | verified | `docs/decisions/0002-sdk-api-mcp-cloud-boundary.md` | contrato versionado; MCP atual explicitamente não aprovado como gateway cloud | transformar em WorkPacket de implementação |
| F1.0 | 1 | Context Kernel + Translation Layer + Semantic Layer + SquadDefinition agnóstica de executor + pool/fallback | planned | — | — | modelar ContextTranslation, Capability Registry e vertical slice captura → tradução → WorkPacket → retomada |
| F1.1 | 1 | Continuidade My Universe/Nuvem como superfície planetária humana | planned | `docs/decisions/0005-my-universe-planetary-surface.md` | contrato real do repo `antunes-hq/nuvem`, flow.db e cloud.json legado auditados | integrar refs aditivas sem recriar PWA |
| F1.2 | 1 | Telegram event notifier + outbox + Browser Session Grant temporário | in_progress | `docs/decisions/0006-telegram-notifications-and-browser-session.md` | protocolo versionado; Nuvem atual 401 sem Bearer confirmado; grant ainda não implementado | F1.2a/F1.2b verified; F1.2c browser grant depois |
| F2.0 | 2 | Run Ledger correlacionado ao `run_id` do aptdata | planned | — | — | definir eventos e receipts |
| F3.0 | 3 | Studio com Definition View e Run View explícitas | planned | — | — | contrato de read API + consumidor |
| F3.1 | 3 | Control View com actions/approvals/audit | planned | — | — | policy engine read/dry-run primeiro |
| F4.0 | 4 | HygieneFinding → policy → action → approval → evidence | planned | — | — | implementar scanner read-only base |
| F5.0 | 5 | Connector GitHub read-only + evidências | planned | — | — | adapter contract + smoke |
| F5.1 | 5 | Connector Vercel read-only + deployments/domains | planned | — | — | adapter contract + smoke |
| F5.2 | 5 | Connector Hostinger API + SSH/Docker read-only | planned | — | — | adapter contract + smoke |
| F5.3 | 5 | Connector Google OAuth + Drive metadata | planned | — | — | adapter contract + scopes |
| F5.4 | 5 | Connector Claude Code/Agent SDK como executor opcional | planned | — | — | WorkPacket adapter + receipt |
| F6.0 | 6 | Separação Flow OS core / Lucas Pack / workspace do usuário | planned | — | — | definir boundaries e instalação limpa |

## Registro de duplicatas/consolidação

| Tema | Artefatos existentes | Decisão canônica |
|---|---|---|
| Mapa operacional | `bora-hq/visu/labs/flow-viz/central.html` + `central.srv...` | Run View; preservar e não recriar como arquitetura |
| Mapa arquitetural | `antunes-hq/mockups/my-universe-flow-map.html` | Definition View de referência; promover depois para Studio |
| Kernel de agentes/plugins | `bora-hq/aptdata` → fork `antunes-hq/aptdata-flow-os` | aptdata é kernel candidato; Flow OS é camada de produto |
| Chat/assistente | Hermes/este chat/Claude Code | adapters/surfaces; nenhum é centro |
| Snapshot operacional | `central-map.json` + publisher timer | projeção, não fonte canônica |
| Desktop Tauri | `hermes-desktop` / Hermes Voice | produto separado; não confundir com Definition/Run Studio |

## Log de evidências

### F1.2a — envelope de eventos + outbox durável

```text
WorkPacket: docs/contracts/f12a-event-outbox-workpacket.md
Implementation commit: 14a0dc6 feat(events): add durable delivery outbox
Files: aptdata/events/{__init__.py,models.py}; aptdata/delivery/{__init__.py,outbox.py}; tests/test_events_outbox.py
Focused verification: uv run pytest tests/test_events_outbox.py -v → 20 passed in 0.16s
Full verification: uv run pytest -q → 752 passed, 10 skipped in 18.09s
Lint: uv run ruff check aptdata/events/ aptdata/delivery/ tests/test_events_outbox.py → All checks passed
Independent scope check: aptdata/mcp/server.py untouched; no network/tokens/credentials
Residual risk: no backoff/max-retry policy; same-instance thread safety is not guaranteed. Next delivery layer owns these concerns.
Status: verified
```

### F1.2b — Telegram notifier read-only

```text
WorkPacket: docs/contracts/f12b-telegram-notifier-workpacket.md
Implementation commit: c426b30 feat(delivery): add Telegram outbox notifier
Files: aptdata/delivery/telegram_notifier.py; aptdata/delivery/__init__.py; tests/test_telegram_notifier.py
Focused verification: uv run pytest tests/test_telegram_notifier.py -v → 33 passed in 0.19s
Full verification: uv run pytest -q → 785 passed, 10 skipped in 18.17s
Lint: uv run ruff check aptdata/delivery/telegram_notifier.py aptdata/delivery/__init__.py tests/test_telegram_notifier.py → All checks passed
Independent scope check: no Nuvem, MCP server, production, credentials or network tests touched
Residual risk: existing outbox claim bumps attempts for non-Telegram channels; no exponential backoff/dead-letter queue; approval callbacks/browser grant remain F1.2c
Status: verified
```

### F0.0 — verificação inicial

```text
Repo: /home/strondinha/lab/bora-hq/aptdata-flow-os
Origin: https://github.com/antunes-hq/aptdata-flow-os.git
Upstream: https://github.com/bora-hq/aptdata.git
Suite: uv run pytest -q
Resultado: 732 passed, 10 skipped, 20.84s
Fork: GitHub API confirmou fork=true e parent=bora-hq/aptdata
```

## Regras de atualização

1. Criar a linha no ledger antes de codar.
2. Uma task tem um único responsável e uma fronteira de arquivos.
3. Agente não pode fechar sua própria task sem output verificável.
4. Mudança de escopo cria nova linha ou decisão; não reescreve histórico.
5. Se um artefato existente resolver a demanda, registrar `reuse` e não duplicar.
6. Se duas implementações existem, uma recebe `superseded`/`retired` com motivo.
7. Falha vira evidência e `blocked`, não é escondida reescrevendo o critério.
8. Toda conclusão deve apontar para arquivo, teste, commit e/ou handle externo.

## Template de nova entrada

```markdown
| F?.? | fase | entrega específica | planned | path | — | próximo passo |
```

Evidência após implementação:

```text
work_id:
files:
commands:
output:
commit:
runtime_handle:
reviewer:
risks:
```

## Primeira task autorizada

```text
F0.1 — Universe Registry inicial
Escopo: somente inventário e contrato; sem connector, sem UI nova, sem mudança de produção.
Fonte: repos locais, GitHub, ~/.hermes skills, runtime local/VPS, docs existentes.
Saída: registry versionado + relatório de divergências + testes de schema.
Gate: cada item tem source, role, lifecycle, owner, capabilities e evidence.
```
