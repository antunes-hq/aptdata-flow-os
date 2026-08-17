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
| F0.5 | 0 | Contrato de Squad Confiável, WorkPacket, EvidenceRecord, JudgeResult e MaestroDecision | verified | `docs/contracts/squad-confiavel-workpacket.md`; `schemas/governance/`; `aptdata/governance/`; `aptdata/events/models.py`; `tests/test_governance_real_flow*.py` | G0–G7: schema/invariantes, store append-only, transições versionadas, FlowEvent/run_id, BronzeFlow real, SilverFlow failure, Judge independente, MaestroDecision, integração e recuperação; 960 passed/10 skipped | próximo: F1.0 Context Kernel; autonomia destrutiva continua fora |
| F1.0 | 1 | Context Kernel + Translation Layer + Semantic Layer + SquadDefinition agnóstica de executor + pool/fallback | planned | — | — | modelar ContextTranslation, Capability Registry e vertical slice captura → tradução → WorkPacket → retomada |
| F1.1 | 1 | My Universe como interface epistemológica pessoal; flows como infraestrutura invisível | planned | `docs/decisions/0005-my-universe-planetary-surface.md` | ADR 0005 + emenda 0005-a: visualizar o próprio conhecimento; desenvolvimento apenas opt-in; Flow/flow-viz técnico por trás | definir vertical slice conhecimento → visualização → retomada, sem presumir task/dev |
| F1.2 | 1 | Telegram event notifier + outbox + Browser Session Grant temporário | verified | `docs/decisions/0006-telegram-notifications-and-browser-session.md` | protocolo versionado; integração Telegram real ainda não publicada | F1.2a/F1.2b/F1.2c verified; F1.3/F1.4/F1.5 verified |
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

### F1.2c — Browser Session Grant

```text
WorkPacket: docs/contracts/f12c-browser-session-grant-workpacket.md
Implementation commit: d952ff8 feat(auth): add browser session grants
Security fix commit: 3b7a3f6 fix(auth): validate redeemed browser sessions
Files: aptdata/auth/{__init__.py,session_grant.py}; aptdata/delivery/session_response.py; tests/test_browser_session_grant.py
Focused verification: uv run pytest tests/test_browser_session_grant.py -v → 44 passed in 0.23s
Full verification: uv run pytest -q → 829 passed, 10 skipped in 18.32s
Lint: uv run ruff check aptdata/auth/ aptdata/delivery/session_response.py tests/test_browser_session_grant.py → All checks passed
Independent scope check: no Nuvem, MCP server, production, credentials or network tests touched
Security evidence: raw grant hash-only; one-shot atomic redeem; TTL; revoke; get_session revalidates expiry/revocation/workspace/run/scopes; cookie structure is HttpOnly-capable
Residual risk: HTTP endpoint, CSRF/origin policy, secure cookie enforcement in production and Telegram-to-grant issuance are not implemented; integration remains local/self-hosted next slice
Status: verified
```

### F1.3 — Browser Grant HTTP Adapter

```text
WorkPacket: docs/contracts/f13-browser-grant-http-adapter-workpacket.md
Implementation commit: 930a5ad feat(auth): add browser grant HTTP boundary
Security hardening in final integration: project binding + sanitized unexpected-error logging
Files: aptdata/auth/{__init__.py,browser_grant_http.py,session_grant.py}; tests/test_browser_grant_http.py
Focused verification: uv run pytest tests/test_browser_grant_http.py tests/test_browser_session_grant.py -q → 106 passed in 0.46s
Full verification: uv run pytest -q → 891 passed, 10 skipped in 18.73s
Lint: uv run ruff check aptdata/auth/ aptdata/delivery/session_response.py tests/test_browser_grant_http.py tests/test_browser_session_grant.py → All checks passed
Independent scope check: no Nuvem, MCP server, production, credentials, FastAPI/Starlette or network tests touched
Security evidence: one-shot redeem; 303 URL without grant; HttpOnly cookie; Secure policy; no-store/no-referrer/nosniff; mutable scopes rejected; workspace/project/run binding; raw URL/hash/exception message not logged
Residual risk: HTTP framework mounting, CSRF/rate-limit policy and Telegram grant issuance remain future layers; production must set secure=True
Status: verified
```

### F1.4 — Control Plane HTTP + browser link

```text
WorkPacket: docs/contracts/f14-control-plane-browser-link-workpacket.md
SDK extension commit: da592f5 feat(auth): support dynamic project/run and base_url in browser grant HTTP adapter
SDK contract commit: e4fc6f5 docs(contracts): add F1.4 control plane browser link workpacket
Control Plane commit: visu d656641 feat(control-plane): complete browser grant integration
Files: flow-viz FastAPI adapter + browser_link issuer + SDK Git dependency/lock + tests
Focused verification: .venv/bin/python -m pytest tests/ -q → 20 passed in 0.58s
Full SDK verification: uv run pytest -q → 899 passed, 10 skipped in 18.39s
Lint: uvx ruff check flow-viz F1.4 slice → All checks passed
Build/config: docker compose config --quiet → ok
Security evidence: flow-viz delegates redeem/cookie/headers/redirect to SDK; separate browser-grants DB; dynamic project/run binding; one-shot 303; read-only scope rejection; no Telegram/VPS/Nuvem change
Independent scope check: flow-viz central-map.json remained local-only and was excluded from commit
Residual risk: flow-viz has two pre-existing warnings (Starlette httpx deprecation and Pydantic class Config deprecation); Telegram emission remains F1.5; no deploy performed
Status: verified
```

### F1.5 — Browser Session Consumer Bridge

```text
WorkPacket: docs/contracts/f15-browser-session-consumer-bridge-workpacket.md
SDK commits: 246b6bb feat(auth): support shared browser session cookie domain; 6701f4a chore(auth): format shared session cookie header
Nuvem commits: 04e0053 feat(browser): consume read-only session grants; 0d581a2 fix(browser): share grant WAL directory
Control Plane commits: e0c637d feat(control-plane): share browser session with My Universe; 9efe9fe fix(control-plane): share browser grant WAL directory
Local verification: SDK 904 passed/10 skipped; flow-capture 28 passed; PWA 16 passed; PWA build OK; flow-viz lint/config OK
Runtime verification: grant → 303 + Domain=.srv1723096.hstgr.cloud + HttpOnly/Secure; flow /cloud with cookie → 200 (39,530 bytes); cookie capture → 401; grant reuse → 401; browser PWA rendered 83 stars; localStorage/document.cookie exposed no session
Security evidence: browser session is read-only and requires flow:read; CAPTURE_TOKEN remains required for capture/pending/ack/POST cloud; shared SQLite directory includes WAL/SHM; flow.db untouched
Deploy evidence: flow-capture and flow-viz-central recreated with SDK and shared `/opt/flow-capture-data/browser-grants-shared.db`; no Telegram change
Residual risk: first browser navigation showed onboarding until reload while async cookie boot completed; subsequent reload rendered PWA correctly; improve loading state before calling this a UX-polished flow
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
