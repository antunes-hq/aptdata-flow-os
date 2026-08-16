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
| F1.0 | 1 | Context Kernel 5W2H com round-trip preservando intenção | planned | — | — | modelar pacote e testes |
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
