# ADR 0004 — Frameworks de execução como extensões do conhecimento

**Status:** Accepted  
**Data:** 2026-08-16  
**Decisão:** LangGraph, LangChain, CrewAI, Hermes, SDKs de agentes e motores de workflow são extensões intercambiáveis do arsenal de conhecimento do Flow OS; não são o centro semântico do produto.

## Problema

O ecossistema já possui muitos motores valiosos:

```text
LangGraph
LangChain
CrewAI
Hermes
Claude Code
OpenAI/Codex
OpenRouter
Prefect
LlamaIndex Workflows
scripts, CLIs e workers próprios
```

Cada motor resolve uma parte da execução. O problema maior permanece entre:

```text
conhecimento → intenção → contexto → capacidade → execução → evidência → aprendizado
```

Se o Flow OS virar apenas mais um framework de agents, ele repetirá o problema que pretende resolver e ficará preso ao motor da moda.

## Decisão

O Flow OS opera acima dos motores de execução e abaixo da experiência humana, como uma camada de tradução, integração e medida.

```text
┌─────────────────────────────────────────────────┐
│ Human meaning / knowledge                       │
│ intenção · contexto · decisões · aprendizado    │
├─────────────────────────────────────────────────┤
│ Flow OS semantic layer                          │
│ ontology · journeys · contracts · policies      │
│ capability registry · translation · evidence    │
│ metrics · evolution                             │
├─────────────────────────────────────────────────┤
│ Execution adapters                              │
│ LangGraph · LangChain · Crew · Hermes · custom  │
│ workflow engines · local models · provider APIs │
├─────────────────────────────────────────────────┤
│ External systems                                │
│ repos · deploys · docs · infra · channels       │
└─────────────────────────────────────────────────┘
```

## Camadas fundamentais do Flow OS

### 1. Knowledge Plane

Representa o que o sistema sabe e de onde veio:

```text
concepts
skills
policies
decisions
context packs
lessons
framework capabilities
```

Cada conhecimento deve possuir:

```text
source
owner
version
confidence
validity
relations
last_verified
```

### 2. Context Plane

Mantém a intenção e suas traduções:

```text
ContextPacket
ContextTranslation
WorkPacket
open questions
assumptions
losses
provenance
```

### 3. Journey Plane

Descreve transformação e continuidade:

```text
Journey
FlowDefinition
FlowVersion
Stage
handoff
resume point
acceptance
```

### 4. Capability Plane

Descreve o que uma ferramenta ou framework consegue fazer, sem confundir a ferramenta com o significado:

```text
Capability
Executor
Skill
FrameworkAdapter
Provider
constraints
cost
latency
health
```

Exemplo:

```text
capability: parallel-agent-review
provided_by:
  - langgraph.adapter
  - crew.adapter
  - hermes.squad
  - custom.worker
requires:
  - WorkPacket
produces:
  - ReviewEvidence
```

O Router escolhe uma implementação compatível. O Flow OS mantém o contrato.

### 5. Execution Plane

Executa a jornada através de um adapter:

```text
dispatch
state
retry
checkpoint
human approval
artifact
```

O motor pode mudar sem mudar o significado da jornada.

### 6. Evidence and Learning Plane

Converte execução em conhecimento novo:

```text
EvidenceReceipt
Evaluation
Decision
Lesson
Skill improvement
Capability score
```

Aprendizado não é alterar o sistema silenciosamente. É propor uma atualização com origem, evidência e revisão.

## Contrato de extensão

Um framework entra no arsenal por um adapter declarativo:

```yaml
id: framework.langgraph
kind: execution_framework
version: "..."
capabilities:
  - graph_workflow
  - checkpointing
  - human_in_the_loop
accepts:
  - WorkPacket
produces:
  - StageRun
  - EvidenceReceipt
limits:
  - requires_python: ">=3.11"
  - state_backend: configurable
risk_policy:
  default: approval_required
metrics:
  - latency
  - cost
  - failure_rate
  - context_loss
```

O adapter precisa implementar:

```text
discover_capabilities()
validate_work_packet()
plan()
execute()
checkpoint()
resume()
collect_evidence()
translate_result()
health()
```

Nenhum adapter pode exigir que o Flow OS adote sua ontologia inteira como fonte de verdade.

## Organicidade

“Orgânico” não significa o sistema se alterar sozinho sem controle. Significa que ele evolui a partir do uso real:

```text
jornada executada
  → evidência observada
  → avaliação
  → padrão detectado
  → hipótese de melhoria
  → proposta de mudança
  → aprovação/teste
  → nova versão de skill/flow/adapter
```

O crescimento é:

```text
incremental
observável
reversível
proveniente do uso
compatível com versões anteriores quando possível
```

O sistema pode recomendar:

```text
esta skill é redundante
este adapter performa melhor nesta capability
este fluxo perde contexto no handoff
este executor custa mais sem melhorar o resultado
esta decisão contradiz uma anterior
```

Mas não deve promover recomendações para verdade sem gate.

## Métricas fundamentais

As métricas não servem para medir o valor da pessoa. Servem para localizar fricção e orientar melhoria do sistema.

### Continuidade de contexto

```text
context_continuity_rate
= handoffs com origem/proveniência preservada / handoffs totais
```

```text
context_restatement_count
= vezes que o usuário precisou reexplicar a mesma intenção
```

```text
resume_success_rate
= retomadas que chegam ao próximo passo correto sem reexplicação
```

### Fidelidade de tradução

```text
translation_loss_rate
= campos/decisões perdidos ou alterados sem registro / campos traduzidos
```

```text
assumption_visibility_rate
= assumptions explicitadas / assumptions detectadas
```

```text
intent_recovery_score
= avaliação de quanto a saída ainda representa o porquê original
```

### Eficiência cognitiva e operacional

```text
capture_to_first_action
= tempo entre captura e próximo passo executável
```

```text
friction_events
= bloqueios, voltas, trocas desnecessárias, retrabalho e handoffs quebrados
```

```text
rework_rate
= trabalho refeito por contexto perdido ou contrato ambíguo
```

```text
interruption_recovery_time
= tempo para retomar uma jornada interrompida
```

### Qualidade e evidência

```text
evidence_completeness
= receipts presentes / receipts exigidos
```

```text
verified_outcome_rate
= resultados com verificação externa / resultados declarados
```

```text
decision_traceability
= decisões ligadas a evidência e origem / decisões totais
```

### Arsenal e aprendizado

```text
capability_reuse_rate
= execuções que reutilizam capacidades registradas / execuções totais
```

```text
framework_substitutability
= jornadas executadas por mais de um adapter compatível / jornadas avaliadas
```

```text
learning_conversion_rate
= avaliações que viram melhoria versionada / avaliações acionáveis
```

```text
knowledge_half_life
= tempo até uma regra/skill precisar de revisão
```

### Custo e impacto

```text
cost_per_verified_outcome
latency_to_verified_outcome
fallback_rate
failure_recovery_rate
```

Métricas devem ser segmentáveis por jornada, capability, adapter e workspace — nunca usadas para ranquear pessoas sem contexto.

## Definition of Done desta camada

A camada semântica está provada quando:

1. a mesma jornada roda em dois motores diferentes;
2. o contrato de entrada/saída permanece igual;
3. o Flow OS mede tradução, continuidade e evidência, não só latência;
4. uma falha de motor pode acionar fallback sem perder a intenção;
5. um aprendizado nasce como proposta versionada;
6. o usuário consegue entender por que um adapter foi escolhido;
7. o sistema distingue capacidade, skill, executor, provider e framework;
8. métricas podem ser auditadas voltando à evidência original;
9. uma melhoria pode ser revertida;
10. nenhum motor externo vira dependência semântica do produto.

## Não-goals

```text
não construir um clone do LangGraph
não competir com LangChain em abstrações de prompts
não criar um super-router proprietário antes do contrato semântico
não esconder decisões em prompts de um modelo
não medir apenas tokens, latência ou quantidade de tarefas
não automatizar evolução sem provenance e aprovação
```

## Impacto no roadmap

Antes de connectors profundos, o Flow OS deve construir:

```text
ontology mínima
capability registry
ContextTranslation
adapter contract
EvidenceReceipt
metric events
learning proposal
```

O primeiro benchmark não deve perguntar “qual framework é melhor?”. Deve perguntar:

> **Qual combinação de conhecimento, jornada, capability e executor preserva melhor contexto e produz resultado verificável para este tipo de trabalho?**

## Relação com decisões anteriores

- ADR 0001: squad e roles são agnósticos de executor.
- ADR 0002: SDK, Control Plane, MCP e Runner têm fronteiras próprias.
- ADR 0003: traduzir e integrar contexto é o núcleo humano do produto.
- Esta ADR posiciona frameworks externos como extensões mensuráveis desse núcleo.

## Próximo vertical slice

```text
registrar Capability
  → escolher dois adapters de execução
  → enviar o mesmo WorkPacket
  → comparar tradução, evidência, custo e continuidade
  → registrar learning proposal
```

A primeira implementação pode usar adapters simples para um executor Hermes/subagente e um segundo executor disponível. LangGraph/LangChain/Crew entram quando houver um caso concreto que prove o valor da extensão, não por acumulação de integrações.
