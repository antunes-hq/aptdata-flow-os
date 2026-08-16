# ADR 0001 — Squad agnóstica de executor

**Status:** Accepted  
**Data:** 2026-08-16  
**Decisão:** Claude Code não é dependência arquitetural do Flow OS.

## Contexto

A fábrica precisa continuar operando quando uma licença, cota, provider ou CLI não estiver disponível. A tentativa de modelar "Claude Code = coder" cria acoplamento, aumenta fricção e impede que a mesma jornada seja executada por Hermes, OpenRouter, modelos locais ou outros executors.

## Decisão

O Flow OS modela a **squad como um grafo de papéis, skills, contratos e gates**. O modelo/CLI é apenas o executor escolhido pelo Router para cada etapa.

```text
FlowDefinition
  → SquadDefinition
    → RoleContract
      → SkillContract
        → ExecutorAdapter
          → EvidenceReceipt
```

Papéis canônicos:

```text
PO → Tech Lead + UI/UX (paralelo) → QA → Judge → Integrator
```

Um role declara:

```text
receives
produces
skills_required
acceptance_checks
evidence_required
risk_policy
```

O role **não declara um modelo obrigatório**.

## Pool de executors

Ordem de preferência configurável por workspace/capability:

1. executor free/cheap configurado no pool;
2. Hermes subprocess/profile;
3. modelo local;
4. Claude Code/Agent SDK, quando houver cota e o usuário escolher;
5. fallback de outro provider compatível.

A ausência de Claude Code deve gerar `executor.unavailable` e acionar fallback, não bloquear a jornada inteira.

## Qualidade sem Claude Code

Quando o mesmo executor atende mais de um role, a independência não deve ser presumida. A qualidade vem de:

- WorkPacket idêntico e versionado;
- fronteiras de arquivo explícitas;
- testes de contrato e regressão;
- Judge baseado em critérios/evidências, não em confiança do modelo;
- tentativas independentes quando o risco justificar;
- aprovação humana para ações de alto risco;
- verificação live pelo integrador;
- ledger obrigatório.

Se houver mais de um executor disponível, o Router pode diversificar PO/Tech/QA/Judge. Se houver apenas um, o fluxo continua, mas registra `review_independence=limited`.

## O que é skill

Skill é um contrato/procedimento reutilizável, não um agente e não uma licença:

```text
skill → descreve como executar/verificar
role  → define responsabilidade na jornada
flow  → define sequência e handoffs
agent → oferece capacidade de execução
model → é um recurso substituível
```

## O que é Flow

O Flow é a unidade de coordenação:

```text
intenção
  → PO estrutura o WorkPacket
  → Tech/UX especificam
  → QA transforma pronto em checks
  → Judge decide go/no-go
  → executor implementa
  → Integrator verifica e registra evidência
```

O Flow OS deve conseguir executar o mesmo Flow com Claude Code, Hermes, OpenRouter, modelo local ou combinação deles.

## Consequências

### Positivas

- zero lock-in operacional em Claude Code;
- custo e disponibilidade são políticas configuráveis;
- o conhecimento fica nas skills/contracts, não na sessão de um modelo;
- o mesmo produto pode ser self-hosted/licenciado;
- fallback torna-se métrica observável e não surpresa.

### Trade-offs

- executors diferentes têm capacidades e formatos de evidência diferentes;
- um pool de um único modelo reduz independência de revisão;
- cada adapter precisa declarar limitações e health;
- a qualidade precisa ser provada por testes/evidência, não pelo nome do provider.

## Critério de aceitação

Uma implementação desta decisão está válida quando um Flow de exemplo:

1. roda com Claude Code desabilitado;
2. seleciona outro executor do pool;
3. executa os mesmos roles/skills;
4. produz o mesmo contrato de saída;
5. registra executor/model/provider efetivos;
6. passa pelos mesmos gates e evidências;
7. mostra no ledger que nenhum trabalho foi perdido por indisponibilidade do Claude Code.

## Não decidido ainda

- quais modelos free ficam no pool padrão;
- política de diversificação por risco;
- se cada workspace pode registrar executors remotos;
- limites de custo por role.

Essas decisões entram no Registry/Policy da Fase 1, não ficam escondidas no código do Router.

## Relação com o chat

Este chat pode ser um executor ou superfície de captura. Não é o centro, não é fonte de verdade e não é requisito para executar o Flow.

## Links canônicos

- `docs/plans/flow-os-master-plan.md`
- `docs/plans/ORCHESTRATION.md`
- `IMPLEMENTATION_LEDGER.md`
- `aptdata/agents/base.py`
- `aptdata/agents/router.py`
- `aptdata/agents/modes.py`
