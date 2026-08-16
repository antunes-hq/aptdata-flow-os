# Contrato — Squad Confiável / WorkPacket v0.1

> **Status:** draft para validação do Maestro
> **Data:** 2026-08-16
> **Escopo:** governança de trabalho da squad antes de qualquer implementação completa do My Universe + IA

## 5W2H

```text
O quê: formalizar squad, WorkPacket, evidências, juiz independente e decisão do Maestro
Por quê: impedir “feito” sem prova e reduzir o risco de confiar em uma IA sem rastreabilidade
Quem: Maestro/usuário; PO; Tech Lead; UI/UX; QA; Judge; executor agnóstico
Quando: antes do desenvolvimento completo do My Universe + IA
Onde: aptdata-flow-os/docs/contracts + futuras implementações no kernel
Como: contrato primeiro → invariantes → modelos executáveis → testes → piloto controlado
Quanto: v0.1 somente governança; sem deploy, sem autonomia destrutiva, sem segredo
```

## 1. Princípio de confiança

A squad não é confiável porque responde bem. Ela é confiável quando consegue mostrar:

```text
contexto → decisão → execução → evidência → julgamento → aprovação/recusa
```

O executor nunca pode ser a única fonte da afirmação de sucesso.

## 2. Papéis

| Papel | Responsabilidade | Pode aprovar o próprio trabalho? |
|---|---|---:|
| Maestro | intenção, limites, calibração e decisões de alto impacto | sim, como autoridade humana |
| PO | traduzir intenção em objetivo, escopo e critérios | não |
| Tech Lead | arquitetura, dependências, riscos técnicos e plano | não |
| UI/UX | experiência, fricção, acessibilidade e linguagem | não |
| QA | critérios verificáveis, testes e regressões | não |
| Executor | produzir alterações/artefatos dentro do WorkPacket | não |
| Judge | verificar consistência, evidência, riscos e condições de GO | não pode ser o executor |
| Integrator | consolidar somente após o Judge e gates | não substitui Maestro |

Um agente pode acumular papéis somente quando isso estiver explicitamente registrado e o Judge for independente da execução avaliada.

## 3. ContextPacket

Entrada humana e contexto de origem. Não é plano técnico.

```yaml
context_packet:
  id: cp_<id>
  version: 1
  source:
    actor: user|system|agent
    channel: my_universe|telegram|cli|pwa|other
    reference: <id/URL/path sanitizado>
  intent: <o que a pessoa quer preservar ou descobrir>
  why: <por que importa>
  domain: personal|learning|creative|development|other
  desired_experience: <como a pessoa quer se sentir/operar>
  constraints: []
  unknowns: []
  assumptions: []
  conflicts: []
  maestro_notes: []
```

Regras:

- `unknowns` não podem ser silenciosamente preenchidos por inferência;
- `domain: development` é opt-in;
- o texto original/proveniência não pode ser substituído pela síntese;
- um ContextPacket pode gerar zero, um ou vários WorkPackets;
- captura não implica execução.

## 4. SquadDefinition

Descrição declarativa da composição e do protocolo da squad.

```yaml
squad_definition:
  id: squad_<id>
  version: 1
  name: <nome>
  roles:
    - id: po
      capability: product_context
      required: true
    - id: tech_lead
      capability: architecture
      required: true
    - id: ui_ux
      capability: human_experience
      required: true
    - id: qa
      capability: verification
      required: true
    - id: judge
      capability: independent_judgement
      required: true
  executor_policy:
    allowed: [hermes, custom, other]
    fallback: explicit_only
  independence:
    judge_must_differ_from_executor: true
    judge_must_receive_evidence: true
    maestro_approval_required_for_high_impact: true
  output_contract: workpacket_v1
```

Invariantes:

```text
SQUAD-001: todos os roles required precisam ter assignment registrado.
SQUAD-002: Judge não pode ser o mesmo assignment que Executor quando independence=true.
SQUAD-003: cada role produz output com status e evidence_refs.
SQUAD-004: fallback não pode ocorrer silenciosamente.
SQUAD-005: versão da SquadDefinition acompanha cada execução.
```

## 5. WorkPacket

Unidade executável derivada de um ContextPacket. É o contrato do trabalho, não a conversa inteira.

```yaml
work_packet:
  id: wp_<id>
  version: 1
  context_packet_id: cp_<id>
  squad_definition_id: squad_<id>
  objective: <resultado observável>
  scope:
    in: []
    out: []
  acceptance_criteria:
    - id: AC-001
      description: <critério testável>
      verification: <comando/checagem>
  constraints: []
  files_or_surfaces: []
  risk:
    level: low|medium|high|critical
    hazards: []
    rollback: <como desfazer>
  assignments:
    - role: po|tech_lead|ui_ux|qa|executor|judge|integrator
      agent_id: <id>
      accepted_at: <timestamp>
  decisions:
    - id: dec_<id>
      question: <decisão>
      options: []
      selected: <opção ou pending>
      authority: maestro|policy|judge
      evidence_refs: []
  state: proposed|ready|running|blocked|awaiting_maestro|judging|approved|rejected|integrated|cancelled
  evidence_refs: []
```

Transições permitidas:

```text
proposed → ready | cancelled
ready → running | blocked | cancelled
running → awaiting_maestro | judging | blocked | cancelled
awaiting_maestro → running | cancelled
judging → approved | rejected | blocked
approved → integrated
rejected → proposed | cancelled
blocked → ready | cancelled
```

Nenhum estado `done`. `integrated` exige todos os gates.

## 6. EvidenceRecord

Toda afirmação verificável precisa apontar para evidência concreta.

```yaml
evidence_record:
  id: ev_<id>
  version: 1
  work_packet_id: wp_<id>
  kind: test|lint|build|runtime|review|file|commit|deploy|decision
  claim: <o que esta evidência prova>
  command: <comando exato, se aplicável>
  output_digest: <hash do output sanitizado>
  result: pass|fail|inconclusive
  source:
    path: <path/URL/handle>
    revision: <commit/tag/container image>
  captured_at: <timestamp UTC>
  captured_by: <agent/profile/human>
  limitations: []
  artifacts: []
```

Regras:

```text
EVID-001: “passou” sem comando/output/handle não fecha gate.
EVID-002: evidência deve apontar para uma revisão identificável.
EVID-003: output com segredo deve ser sanitizado, mas a sanitização precisa ser registrada.
EVID-004: runtime claims exigem fonte live; docs antigas não bastam.
EVID-005: ausência de evidência é inconclusive, não pass.
```

## 7. JudgeResult

O Judge não repete a opinião do executor; ele audita o contrato e as provas.

```yaml
judge_result:
  id: jr_<id>
  version: 1
  work_packet_id: wp_<id>
  judge_agent_id: <id>
  independence_check:
    executor_agent_id: <id>
    independent: true|false
    reason: <explicação>
  checks:
    - id: J-001
      subject: scope
      result: pass|fail|inconclusive
      evidence_refs: []
      note: <curta>
  findings:
    - severity: critical|high|medium|low|info
      kind: contradiction|missing_evidence|security|regression|scope|ux
      statement: <achado>
      evidence_refs: []
      required_action: <ação ou null>
  verdict: go|go_with_conditions|no_go|inconclusive
  conditions: []
  residual_risks: []
  created_at: <timestamp UTC>
```

Regras duras:

```text
JUDGE-001: Judge sem independence_check não vale.
JUDGE-002: no_go se houver falha crítica ou evidência essencial ausente.
JUDGE-003: go_with_conditions exige conditions explícitas e owner.
JUDGE-004: Judge não pode apagar ou reescrever evidência do executor.
JUDGE-005: verdict nunca vira integrated sem aprovação humana quando required.
```

## 8. MaestroDecision

Decisão humana separada do veredito técnico.

```yaml
maestro_decision:
  id: md_<id>
  work_packet_id: wp_<id>
  judge_result_id: jr_<id>
  action: approve|approve_with_conditions|reject|request_revision|pause
  rationale: <curta>
  accepted_risks: []
  rejected_risks: []
  scope_change: <nenhum ou referência a novo packet>
  actor: <human id>
  created_at: <timestamp UTC>
```

O Maestro pode aceitar ou rejeitar um `go`, mas não pode transformar `no_go` em fato técnico. Se decidir seguir apesar do risco, isso fica registrado como decisão humana excepcional.

## 9. Registro mínimo de execução

```text
run_id
work_packet_id
squad_definition_id
context_packet_id
assignments
state transitions
role outputs
commands
commits/artifacts
EvidenceRecords
JudgeResult
MaestroDecision
rollback reference
```

O registro precisa sobreviver ao processo e ser recuperável depois. Memória em processo/EventBus sozinho não satisfaz este contrato.

## 10. Gate de confiança da squad

```text
G0 — contrato válido e versionado
G1 — ContextPacket preservado
G2 — WorkPacket com escopo/AC/risco/rollback
G3 — assignments e fallback registrados
G4 — execução produziu EvidenceRecords
G5 — Judge independente verificou as provas
G6 — Maestro decidiu quando exigido
G7 — integração/rollback verificados
```

Resultado:

```text
G0–G2: planejável
G3–G4: executado, ainda não confiável
G5: tecnicamente julgado
G6: autorizado pelo Maestro
G7: integrado
```

## 11. Fora de escopo v0.1

```text
sem autonomia destrutiva
sem aprovação implícita
sem decisão psicológica/diagnóstica
sem converter conhecimento em task automaticamente
sem provider específico obrigatório
sem segredo em ContextPacket/EvidenceRecord
sem afirmar runtime a partir de snapshot antigo
```

## 12. Próxima implementação autorizável

Somente depois da validação deste contrato:

1. modelos Pydantic/dataclasses para os cinco registros;
2. JSON Schema + invariantes executáveis;
3. store durável append-only ou SQLite dedicado;
4. testes de transição, independência e evidência;
5. um WorkPacket de ensaio read-only;
6. Judge em modo relatório, sem executar ações.

## Checklist do Maestro

```text
[ ] entendi o que cada papel pode fazer
[ ] sei diferenciar fato, observação, hipótese, decisão e risco
[ ] consigo ver a origem de cada afirmação
[ ] consigo rejeitar/corrigir sem perder o contexto
[ ] nenhum agente pode aprovar sozinho o próprio trabalho
[ ] posso pausar, revogar e retomar
[ ] aceito o primeiro piloto read-only
```

**Pergunta de fechamento:** este contrato representa o nível de controle e confiança que você precisa antes de deixar a squad tocar o My Universe?