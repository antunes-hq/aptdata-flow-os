# Flow OS — Orchestration Contract

> Este documento define **como** o plano mestre é executado. O centro é o fork `aptdata-flow-os`; qualquer chat, Claude Code, Claude Design, Hermes ou CLI é somente uma superfície/adapter.

## 1. Lei anti-repetição

Antes de iniciar qualquer trabalho:

```text
1. localizar a demanda no IMPLEMENTATION_LEDGER.md;
2. localizar a fase no flow-os-master-plan.md;
3. procurar artefatos existentes por nome, contrato e comportamento;
4. marcar como reuse/extend/duplicate antes de criar arquivos;
5. registrar a decisão no ledger;
6. só então escrever código.
```

Se uma conversa pedir novamente uma visão já registrada, o executor deve apontar para o artefato canônico e propor **consolidar/adaptar**, nunca gerar uma segunda implementação silenciosa.

## 2. Papéis

| Papel | Responsabilidade | Não pode fazer |
|---|---|---|
| Lucas | visão, limites, decisões de produto, aprovação de ações de risco | ser memória operacional implícita do sistema |
| aptdata kernel | contratos, agents, modes, plugins, events, lineage, telemetry, MCP | conhecer detalhes de cada provider |
| Flow OS | registry, context, definitions/runs, control, hygiene, licensing | substituir provider/executor |
| executor coder | implementar código e testes em branch/task delimitada | decidir arquitetura sem registrar decisão |
| executor infra | deploy, VPS, Docker, DNS com approval | alterar produção sem evidence gate |
| executor pool | oferecer backends substituíveis por capability/custo/health | tornar Claude Code obrigatório |
| reviewer | verificar requisitos e evidências contra ledger | aceitar relato sem artefato |
| chat surfaces | capturar, consultar, disparar ações autorizadas | ser fonte de verdade |

## 3. Ferramentas como adapters

```text
Hermes/default      → roteador/conversa opcional
Claude Code        → executor de coding opcional
Claude Design      → executor de exploração visual opcional
GitHub             → código/PR/release adapter
Vercel             → deploy adapter
Hostinger + SSH    → infra/DNS/runtime adapter
Google APIs        → knowledge/document adapter
OpenRouter/Claude  → model/provider adapter
```

Cada adapter deve declarar:

```text
capabilities
inputs
outputs
required_scopes
risk_level
read_only_support
approval_requirements
verification_commands
rollback
```

## 4. Visões não substituíveis

Toda implementação de superfície precisa declarar qual visão atende:

```text
Definition View → arquitetura declarada: apps, skills, providers, contracts, dependências
Run View        → execução observada: tasks, sessions, artifacts, deploys, evals
Control View    → ações e aprovações: connect, inspect, dispatch, approve, deploy, rollback
```

Uma visão não pode reimplementar silenciosamente outra. Se uma task tocar mais de uma visão, o WorkPacket lista cada contrato e cada teste correspondente.

## 5. Unidade de trabalho

Nenhum agente recebe uma instrução solta como contrato final. O input é um `WorkPacket`:

```yaml
work_id: required
five_w:
  o_que: required
  por_que: required
  quem: required
  quando: required
  onde: required
  como: required
  quanto: optional
context_refs: []
project_id: required
flow_definition_id: required
flow_version: required
stage_id: required
executor_id: required
skill_ids: []
constraints: []
acceptance: []
evidence_required: []
```

O executor pode receber texto adicional, mas o `WorkPacket` é a fonte contratual.

## 5. Ciclo obrigatório por task

```text
DISCOVER
  localizar task/artefato/contrato existentes

PLAN
  criar/atualizar WorkPacket e acceptance checks

RED
  escrever teste/checagem que falha ou reproduz o gap

GREEN
  implementar o mínimo

VERIFY
  rodar testes, lint, build e smoke de escopo

EVIDENCE
  registrar comandos, saídas, paths, commit e links

REVIEW
  spec compliance + quality + anti-duplicação

INTEGRATE
  merge/deploy somente se gates passarem

LEARN
  registrar decisão, finding ou skill nova
```

## 6. Gates que bloqueiam fechamento

### Gate G0 — identidade

- repo e branch corretos;
- worktree conhecido;
- task ligada ao projeto;
- nenhum trabalho paralelo escrevendo nos mesmos arquivos.

### Gate G1 — contrato

- 5W preenchido;
- Definition/Run/Control identificado;
- acceptance criteria objetivos;
- não-goals explícitos.

### Gate G2 — anti-duplicação

- busca por nomes, rotas, classes, endpoints, mockups e docs feita;
- artefato existente foi reutilizado, estendido ou marcado como duplicata;
- decisão registrada no ledger.

### Gate G3 — implementação

- arquivos esperados existem;
- diff corresponde ao escopo;
- testes de contrato existem;
- sem segredo ou artefato gerado indevido.

### Gate G4 — runtime

- serviço/build executado de verdade;
- endpoint/browser smoke quando aplicável;
- estado live conferido na fonte original;
- claims do agente não substituem verificação.

### Gate G5 — evidência

Toda task fechada precisa de:

```text
ledger_id
status
files
tests + output
commit
runtime evidence (quando aplicável)
reviewer
next link/decision
```

Sem isso: `implemented_unverified`, nunca `done`.

## 7. Classes de ação e aprovação

| Classe | Exemplos | Aprovação |
|---|---|---|
| read | scan, list, test, inspect | automática |
| reversible | branch, PR, snapshot, preview deploy | policy/usuário conforme workspace |
| production | restart, deploy prod, DNS, OAuth scopes | Lucas/owner obrigatório |
| destructive | delete repo/branch/data, revoke secret | aprovação explícita + backup |

## 8. Sequenciamento

### Wave 0 — Fase 0

Somente registry, contratos, ledger e validação de fontes reais.

### Wave 1 — Context Kernel

Modelos + round-trip tests. Nenhum connector novo.

### Wave 2 — Run Ledger

Correlacionar `run_id` existente e adicionar IDs faltantes sem copiar bancos.

### Wave 3 — Definition/Run Studio

Duas visões explícitas; uma não substitui a outra.

### Wave 4 — Hygiene

Findings/policies/evidence; scanners read-only primeiro.

### Wave 5 — Connectors

Um por vez: GitHub → Vercel → Hostinger → Google → Claude.

### Wave 6 — License/Product

Somente depois dos contratos e de um vertical slice verificável.

## 9. Delegação

O caminho padrão é **squad + skills + executor pool**, não Claude Code.

```text
PO → Tech Lead + UI/UX → QA → Judge → Integrator
```

Cada papel é executado por um backend disponível no pool. Se o executor preferido estiver indisponível, o Router aplica fallback por capability, custo e health. Claude Code pode ser escolhido quando houver cota, mas sua indisponibilidade nunca bloqueia o Flow.

Subagente free pode executar código quando o WorkPacket está fechado. O subagente deve retornar:

```text
work_id
files_changed
commands_run
test_output
commit_sha
runtime_handles
unresolved_risks
```

O orquestrador verifica tudo no disco/git/runtime. Resumo do agente é pista, não evidência.

Claude Code/Claude Design/Hermes podem ser usados como executors, mas nenhum deles pode criar uma fonte de verdade paralela.

## 10. Ritual de revisão

### Antes da sessão

```text
abrir ledger
selecionar UMA task
ler contrato e refs
confirmar fonte live
```

### Depois da sessão

```text
registrar evidência
atualizar status
registrar decisão/aprendizado
commit/push quando aplicável
não abrir nova frente sem fechar o loop
```

### Semanal

- revisar tasks `implemented_unverified`;
- procurar duplicatas;
- checar claims contra runtime;
- promover descobertas para contratos/skills;
- arquivar experimentos sem apagar evidência.

## Definição de pronto global

Uma fase só é `done` quando:

```text
código existe
+ contrato existe
+ testes passam
+ integração foi exercitada
+ fonte live foi conferida
+ evidência está no ledger
+ documentação aponta para o artefato
+ nenhuma duplicata concorrente ficou ativa
```

## Fora do centro

Este documento não depende de um chat específico. Uma implementação deve continuar se todas as conversas forem apagadas. O centro é o repositório, os contratos e o ledger.

## Próxima execução

Fase 0 / Task F0.1: inventariar e registrar os objetos do Universe Registry a partir de fontes reais, sem criar adapters ou UI nova.

Ver `IMPLEMENTATION_LEDGER.md`.
