# ADR 0003 — Flow OS como tradutor e integrador de contextos

**Status:** Accepted  
**Data:** 2026-08-16  
**Decisão:** a capacidade central do Flow OS é traduzir e integrar contextos entre pessoas, ferramentas, agentes e jornadas, com suporte cognitivo explícito para pessoas neurodivergentes — sem diagnosticar, infantilizar ou substituir a autonomia do usuário.

## A motivação

Pessoas com TDAH e outros perfis neurodivergentes podem ter alta capacidade de criação, análise e conexão de ideias, mas sofrer fricção em:

```text
capturar uma ideia antes que ela suma
transformar pensamento em próximo passo
manter contexto entre ferramentas
retomar uma jornada interrompida
separar descoberta de execução
converter saída técnica em entendimento
```

O problema não é falta de inteligência ou valor. É o custo de organizar, traduzir e transportar contexto entre sistemas.

## Tese do produto

> **O Flow OS traduz a potência humana em contexto compartilhável e integra esse contexto ao longo da jornada, sem apagar a origem, a intenção ou a autoria.**

A ferramenta não deve exigir uma entrada perfeita. Ela deve aceitar linguagem natural, fragmentos, áudio, links, arquivos e ideias incompletas; explicitar lacunas; e ajudar a transformar tudo em uma sequência compreensível e executável.

## O que significa traduzir contexto

O mesmo contexto muda de forma ao atravessar fronteiras:

```text
pensamento/ideia
  → ContextPacket 5W2H
  → FlowDefinition
  → WorkPacket para squad
  → instrução para executor
  → task/branch/PR
  → deploy/runtime event
  → eval/evidence receipt
  → resumo humano
  → decisão/aprendizado
```

Cada tradução deve preservar:

```text
intenção original
porquê
autoria
incertezas
restrições
critério de sucesso
identidade da jornada
```

E deve registrar o que foi transformado:

```text
translation_id
source_context_id
source_format
target_context_id
target_format
translator/policy
losses_or_open_questions
created_at
```

Contexto não pode desaparecer só porque foi convertido para o formato de outra ferramenta.

## O que significa integrar contexto

Integração não é juntar todos os dados em um banco gigante. É manter relações e referências entre contextos:

```text
source_message_id
context_packet_id
flow_definition_id
run_id
task_id
session_id
artifact_id
deployment_id
eval_id
decision_id
```

O Flow OS deve responder:

```text
De onde veio esta tarefa?
Qual intenção ela preserva?
Qual parte foi interpretada ou assumida?
Quem/qual agente alterou o contexto?
Qual evidência prova o resultado?
Como retomo isso depois de uma interrupção?
```

## Princípios de experiência cognitiva

### Captura sem bloqueio

A entrada inicial pode ser imperfeita. O sistema captura primeiro e organiza depois.

```text
capturar ≠ decidir ≠ executar
```

### Próximo passo único

Cada jornada ativa mostra um próximo passo pequeno e concreto, não uma lista infinita de possibilidades.

### Progressive disclosure

Mostrar primeiro:

```text
o que é
por que importa
próximo passo
```

Detalhes, relações, logs e evidências ficam disponíveis sob demanda.

### Retomada sem punição

Uma jornada interrompida deve retornar com:

```text
onde parei
o que mudou
o que já está comprovado
qual é o próximo passo
quais decisões continuam pendentes
```

### Incerteza explícita

O sistema não deve preencher lacunas silenciosamente. Usar:

```text
unknown
assumption
needs_confirmation
conflict
```

### Tradução reversível

Sempre que possível, o usuário consegue voltar do artefato para a origem:

```text
deploy → commit → task → WorkPacket → intenção original
```

### Autoria e agência

O sistema pode estruturar, sugerir e resumir. Não deve apropriar-se da decisão do usuário nem transformar uma sugestão em fato.

## O que o produto não é

```text
não é ferramenta médica
não diagnostica TDAH
não promete tratar neurodivergência
não é um gerente que pune desorganização
não força produtividade contínua
não transforma toda ideia em task
não remove o direito de pausar, arquivar ou explorar
```

A linguagem de TDAH é uma motivação de design e acessibilidade, não uma classificação obrigatória do usuário.

## Camadas do tradutor

```text
Capture Translator
  fragmento/voz/link → contexto inicial

Meaning Translator
  contexto inicial → 5W2H + lacunas + intenção

Journey Translator
  5W2H → Definition/Run + stages + acceptance

Execution Translator
  stage → WorkPacket + role + skill + executor

Evidence Translator
  logs/commits/deploys/evals → receipt compreensível

Learning Translator
  evidência/decisão → regra, skill, contexto reutilizável
```

Esses tradutores devem ser contratos e funções observáveis, não magia escondida em prompts.

## Segurança e privacidade cognitiva

O contexto humano pode ser sensível. Portanto:

```text
usuário controla o que é persistido
origem e transformação são visíveis
dados pessoais são minimizados
segredos nunca entram no contexto de modelo por padrão
context packs privados ficam isolados
export/delete/retention são capacidades de primeira classe
```

A ferramenta deve explicar quando:

```text
resumiu
inferiu
perdeu detalhe
usou memória
compartilhou com executor/provider
```

## Critério de aceitação

A decisão estará provada quando uma pessoa puder:

1. despejar uma ideia incompleta sem preencher formulário perfeito;
2. receber uma tradução curta com intenção, lacunas e próximo passo;
3. transformar essa ideia em uma jornada sem reexplicar tudo;
4. enviar contexto adequado para uma squad/executor;
5. interromper e retomar sem perder o fio;
6. voltar do resultado para a origem;
7. entender quais partes vieram dela, do sistema e de um executor;
8. exportar a jornada e continuar em outra superfície;
9. usar o sistema sem Claude Code, sem este chat e sem um provider específico;
10. manter controle sobre seus dados e autorizações.

## Impacto na arquitetura

O objeto `ContextTranslation` deve ser de primeira classe junto de:

```text
ContextPacket
WorkPacket
FlowDefinition
FlowRun
EvidenceReceipt
Decision
```

O SDK e o Control Plane precisam expor tradução como operação versionada e auditável. O MCP é apenas uma superfície possível para solicitar ou consultar traduções autorizadas.

## Primeira prova recomendada

Criar um vertical slice sem integração externa destrutiva:

```text
texto fragmentado
  → ContextPacket 5W2H
  → WorkPacket de squad
  → saída mockada/real de executor free
  → EvidenceReceipt
  → resumo de retomada
```

A prova deve usar um caso real de construção do Flow OS, mas preservar o texto original e registrar toda transformação.

## Relação com as decisões anteriores

- ADR 0001: roles e skills são independentes do executor/modelo.
- ADR 0002: SDK é reutilizável; Control Plane é fonte operacional; MCP é adapter; runner protege código e segredos.
- Esta ADR define **por que** essas camadas existem: reduzir o custo humano de traduzir e integrar contexto.

## Links

- `docs/plans/flow-os-master-plan.md`
- `docs/plans/ORCHESTRATION.md`
- `IMPLEMENTATION_LEDGER.md`
- `docs/decisions/0001-executor-agnostic-squad.md`
- `docs/decisions/0002-sdk-api-mcp-cloud-boundary.md`
- `aptdata/core/context.py`
- `aptdata/agents/router.py`
- `aptdata/agents/modes.py`

## Nota de linguagem

O produto deve falar com pessoas como criadoras capazes. Suporte cognitivo significa reduzir fricção, não reduzir a ambição nem presumir incapacidade.

## Próxima decisão operacional

A Fase 1 deve começar pelo contrato `ContextTranslation` + vertical slice de captura → tradução → WorkPacket → retomada, antes de connectors externos.