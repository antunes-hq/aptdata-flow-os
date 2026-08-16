# Flow OS — Plano Mestre Externo

> **Status:** baseline aprovado para execução por fases
> **Núcleo:** aptdata
> **Produto:** Flow OS
> **Centro operacional:** aptdata-flow-os, não este chat
> **Última revisão:** 2026-08-16

## 5W2H do produto

```text
O quê: transformar aptdata em kernel de um sistema operacional de contexto para construir software
Por quê: eliminar perda de contexto, repetição de visão e dispersão entre repos, agents, skills e providers
Quem: Lucas como arquiteto; aptdata como kernel; executors especializados por domínio; usuários licenciados depois
Quando: evolução incremental; cada fase só fecha com evidência registrada no ledger
Onde: fork antunes-hq/aptdata-flow-os; Flow OS Studio; adapters locais, VPS e serviços externos
Como: registry declarativo → context packets → Definition/Run/Control Views → hygiene/evidence → connectors → licença
Quanto: usar ferramentas existentes primeiro; subagentes free para execução; paid providers apenas quando declarados
```

## Tese

Software não deve apenas executar tarefas. Deve preservar intenção, produzir evidência e aumentar o entendimento de quem o constrói.

O Flow OS é um **Context Control Plane para software factories**. Ele coordena ferramentas externas sem tentar substituí-las:

```text
Lucas/usuário → intenção → contexto → jornada → executor → artefato → deploy → evidência → decisão
```

## Regra de centro

Este chat, Claude Code, Claude Design, Hermes, Vercel, Hostinger, Google, GitHub e providers são **ferramentas/adapters**.

O centro é:

```text
aptdata kernel + Flow OS registry + Flow OS ledger + Studio próprio
```

Nenhuma decisão arquitetural pode depender de memória de uma conversa. Toda decisão deve existir em `docs/decisions/`, `docs/contracts/` ou no ledger.

## Arquitetura alvo

```text
Flow OS
├── Knowledge Layer
│   ├── Universe Registry
│   ├── skills
│   ├── context packs
│   ├── decisions
│   ├── policies
│   └── lessons/evals
├── Human Surface Layer
│   ├── My Universe / Nuvem planetary PWA
│   ├── capture · timeline · constellation · galaxies
│   └── resume-oriented spatial navigation
├── Delivery Layer
│   ├── Telegram event notifier
│   ├── durable outbox
│   ├── browser session grants
│   └── deep links to runs/evidence
├── Semantic Layer
│   ├── ontology
│   ├── capability registry
│   ├── context translation
│   ├── provenance
│   └── learning proposals
├── Flow Layer
│   ├── ContextPacket 5W2H
│   ├── FlowDefinition
│   ├── FlowVersion
│   ├── Journey
│   └── contracts
├── Execution Layer
│   ├── FlowRun
│   ├── StageRun
│   ├── Task
│   ├── AgentSession
│   ├── Artifact
│   ├── Deployment
│   └── EvidenceReceipt
├── Control Layer
│   ├── approvals
│   ├── policies
│   ├── retries
│   ├── rollback
│   └── audit trail
├── SDK / API / MCP Boundary
│   ├── flowos-core SDK
│   ├── Control Plane API
│   ├── safe MCP adapter
│   └── local/VPS/self-hosted runners
└── Adapters
    ├── chat/Telegram/Hermes (optional surfaces)
    ├── Claude Code / Agent SDK
    ├── GitHub
    ├── Vercel
    ├── Hostinger API + SSH/Docker
    ├── Google Drive/Docs/Sheets
    ├── OpenRouter/Anthropic
    └── local filesystem
```

## As três visões obrigatórias

Além das visões técnicas, o Flow OS preserva a superfície humana planetária do My Universe/Nuvem. Ela é complementar às três visões abaixo.

```text
My Universe = orientação, memória, padrões e retomada
flow-viz = arquitetura, execução e controle
```

### Definition View

Mostra a arquitetura declarada:

```text
apps · skills · providers · executors · contracts · dependencies · policies
```

Pergunta: **o que existe e como deveria funcionar?**

### Run View

Mostra a execução observada:

```text
capture → flow → task → session → artifact → deploy → eval → decision
```

Pergunta: **o que aconteceu de verdade?**

### Control View

Mostra ações disponíveis e aprovações:

```text
connect · inspect · plan · dispatch · approve · deploy · rollback · hygiene
```

Pergunta: **o que posso fazer com segurança agora?**

Uma visão nunca substitui outra.

## Identidade universal

Toda jornada deve propagar, quando aplicável:

```text
workspace_id
project_id
journey_id
flow_definition_id
flow_version
source_message_id
flow_event_id
task_id
run_id
stage_id
skill_id
provider_account_id
agent_session_id
artifact_id
deployment_id
eval_id
decision_id
```

Campos ausentes são explicitamente `null`/`unknown`; nunca inventados.

## Fases de execução

### Fase 0 — Baseline e anti-repetição

Objetivo: impedir que novas sessões reimplementem visões já construídas.

Entregas:

- este plano mestre;
- `ORCHESTRATION.md`;
- `IMPLEMENTATION_LEDGER.md`;
- `docs/contracts/`;
- registry inicial de capacidades;
- decisão explícita: chat é adapter, não centro.

Gate:

- cada demanda nova aponta para uma fase/task do plano;
- nenhuma task fecha sem evidência no ledger;
- duplicatas são vinculadas, não reimplementadas.

### Fase 1 — Knowledge Registry

Objetivo: saber o que existe, por que existe e qual é o estado real.

Entidades:

```text
Workspace · Project · Capability · Skill · Executor · Provider · Surface · Decision
```

Estados:

```text
discovery · validated · adopted · paused · retired
```

Entregas:

- registry declarativo versionado;
- import/auditoria dos repos e skills existentes;
- relações entre aptdata, Flow, Hermes, Claude Code, providers e Studio;
- Definition View inicial read-only.

Gate:

- todo item tem fonte, papel, lifecycle e owner;
- nenhum item é `adopted` sem teste ou evidência de uso;
- inventário cru não é confundido com arquitetura adotada.

### Fase 1 — Context Kernel e Translation Layer

Objetivo: traduzir intenção humana entre superfícies sem perder origem, autoria, lacunas ou critério de sucesso.

Entregas:

- `ContextPacket` 5W2H;
- `ContextTranslation` versionada e auditável;
- ontology mínima e capability registry;
- camadas Capture/Meaning/Journey/Execution/Evidence/Learning Translator;
- `SquadDefinition` com roles agnósticos de executor;
- pool de executors com fallback por capability/custo/health;
- critérios de pronto;
- contexto projetado por estágio;
- pacote para executor;
- resumo de retomada após interrupção;
- validação de campos, origem e perdas;
- compatibilidade com `aptdata` agents/projects/modes.

Gate:

- uma ideia incompleta pode ser capturada sem formulário perfeito;
- a tradução explicita lacunas e não inventa fatos;
- uma intenção vira pacote serializável;
- a origem é recuperável a partir do WorkPacket;
- o pacote atravessa router, task e executor;
- o executor recebe contexto sem Lucas reexplicar;
- uma execução pode ser retomada com próximo passo único;
- teste de round-trip comprova preservação e registra perdas assumidas;
- o mesmo slice roda sem Claude Code, este chat ou provider específico.

Métricas obrigatórias da camada:

```text
context_continuity_rate
context_restatement_count
resume_success_rate
translation_loss_rate
evidence_completeness
verified_outcome_rate
capability_reuse_rate
framework_substitutability
learning_conversion_rate
cost_per_verified_outcome
```

### Fase 3 — Run Ledger e evidência

Objetivo: provar cada execução.

Entregas:

- `FlowDefinition`/`FlowVersion`;
- `FlowRun`/`StageRun`;
- receipts de comando, teste, commit, deploy e decisão;
- correlação com `run_id` existente do aptdata;
- Run View consumidora do ledger.
- SDK local capaz de operar sem cloud;
- receipts que não carregam segredos nem bancos brutos.
- integração aditiva de `context_refs`, `journey_refs` e `evidence_refs` no payload consumido pelo My Universe;
- linhagem estrela/planeta/galáxia → evento/task/run/evidence.

Gate:

- uma execução pode ser reconstruída do início ao fim;
- `resolved` exige evidência;
- falha e intervenção humana também são eventos;
- o ledger não copia bancos de domínio: mantém referências/projeções.
- o My Universe renderiza a projeção sem perder a experiência planetária;
- uma estrela/planeta consegue abrir o WorkPacket e voltar à origem.

Entrega de acompanhamento:

- envelope de eventos por `run_id`;
- outbox durável para Telegram;
- notificações de início, checkpoint, bloqueio, aprovação e encerramento;
- Browser Session Grant temporário e one-shot para abrir o run no navegador;
- link profundo My Universe/flow-viz com escopo read-only por padrão.

Gate de entrega:

- falha do Telegram não perde o evento;
- nenhuma mensagem contém segredo ou token de infraestrutura;
- grant expira, é revogável e não é repassado a upstream;
- navegador revalida `workspace_id`, `run_id` e scopes no servidor.

### Fase 4 — Hygiene e governança

Objetivo: converter entropia em findings acionáveis.

Pipeline:

```text
scan → enrich → classify → propose → approve → execute → verify → learn
```

Entregas:

- `HygieneFinding`;
- `HygienePolicy`;
- `HygieneAction`;
- `ApprovalGate`;
- `EvidenceReceipt`;
- scanners de repos, paths, skills, runtime, providers, docs e segurança.

Gate:

- read-only por padrão;
- ações destrutivas exigem aprovação;
- cada correção gera antes/depois/evidência;
- nenhum scanner pode alegar estado sem fonte live.

### Fase 5 — Control View e connectors

Objetivo: operar múltiplos sistemas de um ponto sem transformar o Flow OS em cópia deles.

Ordem:

1. GitHub read-only + PR/branch evidence;
2. Vercel projects/deploys/domains;
3. Hostinger inventory + SSH/Docker health;
4. Google OAuth + Drive/Docs metadata;
5. executor Claude Code/Agent SDK opcional;
6. OpenRouter/Anthropic cost and route metadata;
7. testar o mesmo Flow com Claude Code desabilitado e fallback ativo.

Para cada connector:

```text
discovery → read-only → dry-run → approval → action → verification → rollback
```

O MCP é uma projeção segura da API, não a fonte de verdade. A primeira versão cloud expõe apenas leitura e planejamento; ações mutáveis entram após policy, scope e approval.

Gate:

- credenciais ficam no vault/keyring/env do usuário;
- frontend nunca recebe segredo;
- adapter tem contrato, testes, audit events e smoke real;
- connector indisponível não derruba o kernel.

### Fase 6 — Productization e licença

Objetivo: separar o software do contexto do Lucas.

```text
aptdata core          → kernel reutilizável
Flow OS core          → produto
Lucas Pack            → contexto privado/proprietário
connector packages    → integrações
user workspace        → dados do cliente
```

Entregas:

- workspace/user isolation;
- OAuth por usuário;
- secret references;
- roles/approvals;
- packs instaláveis;
- edição self-hosted/cloud/desktop;
- modelo de licença e atualização.

Gate:

- remover o Lucas Pack não quebra o core;
- outro usuário consegue configurar seu workspace;
- nenhum segredo ou dado do Lucas entra no pacote genérico;
- instalação limpa reproduz o caminho documentado.

Distribuições previstas:

```text
local-only · self-hosted · cloud-hosted · hybrid (Control Plane cloud + runner local)
```

## Não-goals atuais

- não transformar este chat no centro;
- não criar um mega-dashboard antes do registry e ledger;
- não duplicar o aptdata em outro framework;
- não copiar bancos de domínio para um banco central;
- não automatizar delete/deploy/DNS sem approval gate;
- não criar vinte connectors antes de provar o contrato de um;
- não marcar trabalho como pronto por narrativa de agente;
- não criar desktop antes de validar as visões no Studio web.

## Critério de sucesso da visão grande

Uma intenção entra uma vez e pode ser seguida sem reexplicação:

```text
intenção → ContextPacket → FlowDefinition → FlowRun → executor
         → artefato → deploy → eval → decisão → aprendizado
```

Se isso não puder ser reconstruído com evidência, a fase não está pronta.

## Próximo passo único

Executar a **Fase 0**: criar e validar o Universe Registry inicial contra os repositórios, skills, executors e providers reais, sem implementar novos conectores ainda.

Consulte `ORCHESTRATION.md` para o processo e `IMPLEMENTATION_LEDGER.md` para o gate de evidência.
