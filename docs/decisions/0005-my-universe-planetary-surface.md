# ADR 0005 — My Universe como superfície planetária do Flow OS

**Status:** Accepted  
**Data:** 2026-08-16  
**Decisão:** preservar e evoluir o My Universe/Nuvem como a superfície humana, planetária e espacial do Flow OS; não recriar sua experiência no `flow-viz`.

## Contexto real

O melhor produto já construído pelo Lucas até aqui é o My Universe, no repositório:

```text
https://github.com/antunes-hq/nuvem
/home/strondinha/lab/antunes-hq/nuvem
```

O repo é ativo e contém uma PWA Svelte 5 com:

```text
Capturar
Timeline
Constelação
Galáxias
Universo 3D como background
planetas para tasks filhas
estrelas para ideias
clusters/galáxias para padrões
asteroides para itens sem cluster
buraco negro para itens parados/arquivados
```

O repositório `bora-hq/flow` é o framework de captura e contrato 5W2H, e o `flow.db` é a fonte de eventos que a Nuvem consome. A pipeline existente é:

```text
flow.db → filtros → vetorizador → agrupador → rotulador → publicador → /cloud → My Universe PWA
```

## Decisão

A arquitetura do produto terá superfícies especializadas, não uma única UI gigante:

```text
aptdata-flow-os
  = kernel semântico, jornadas, capabilities, execução, evidência e aprendizado

flow / Nuvem
  = framework de contexto, captura, enriquecimento e qualidade

My Universe
  = superfície planetária humana para orientação, memória, exploração e retomada

flow-viz
  = superfície técnica para Definition View, Run View e Control View
```

O My Universe é uma superfície oficial/adotada do Flow OS. Ele não é uma cópia descartável nem um protótipo a ser substituído pelo painel técnico.

## Emenda 0005-a — fronteira não-desenvolvimento (2026-08-16)

O My Universe **não é uma superfície de desenvolvimento por padrão**. Ele é uma superfície humana para vida, memória, reflexão, orientação e retomada. A pessoa pode escolher uma jornada relacionada a software/desenvolvimento quando fizer sentido, mas isso é uma escolha explícita — não uma inferência do sistema.

Regras derivadas:

```text
My Universe não converte automaticamente ideia em task, run ou WorkPacket.
My Universe não mostra jargão de executor, provider, pipeline ou approval como camada inicial.
Ações de desenvolvimento são opt-in e preservam a origem humana da ideia.
Flow/flow-viz continuam sendo as superfícies técnicas para Definition, Run e Control.
```

Esta emenda corrige a interpretação de "superfície humana": humana não significa necessariamente dev; significa que o domínio pertence ao usuário e só ganha uma lente técnica quando ele a escolhe.

## Por que duas superfícies

### My Universe — orientação humana

Responde:

```text
O que está ocupando meu universo?
Que padrões estão surgindo?
Onde está uma ideia?
O que ficou parado?
Como retomo sem recomeçar do zero?
```

Sua linguagem visual é espacial, orgânica e afetiva:

```text
ideia → estrela
cluster → galáxia
pattern → constelação
subtask → planeta
item sem relação → asteroide
pausa/arquivo → buraco negro
```

### flow-viz — inspeção técnica

Responde:

```text
Qual é a definição do fluxo?
Qual foi o run?
Qual adapter executou?
Qual evidência existe?
Qual aprovação está pendente?
Qual provider está saudável?
```

As superfícies são complementares:

```text
My Universe = sentido, orientação e retomada
flow-viz = estrutura, execução e controle
```

Uma não substitui a outra.

## Contrato de integração

O My Universe continua consumindo uma projeção compatível de contexto. O núcleo novo deve adicionar metadados sem quebrar o shape atual:

```json
{
  "nos": [],
  "arestas": [],
  "clusters": [],
  "meta": {
    "workspace_id": "...",
    "generated_at": "...",
    "source": "flow-registry"
  },
  "context_refs": {},
  "journey_refs": {},
  "evidence_refs": {}
}
```

A compatibilidade atual permanece:

```text
nos[].id/texto/quando/jornada/cluster
arestas[].a/b/peso
clusters[].id/rotulo/n
```

Campos novos são aditivos e opcionais. O PWA antigo deve continuar renderizando se receber apenas o shape legado.

## Linhagem visual

Todo objeto visual deve poder apontar para sua origem e próxima camada:

```text
planeta
  → task_id
  → WorkPacket
  → ContextPacket
  → source_message_id

estrela
  → flow_event_id
  → ContextPacket
  → intenção original

galáxia
  → cluster_id
  → capability/pattern evidence
  → learning proposal, quando houver
```

O usuário não precisa ver IDs técnicos na primeira camada. Mas o drawer/detalhe deve permitir abrir a linhagem quando ele quiser.

## Interações de alto valor

### Captura

```text
texto/voz/share
  → ideia nasce como estrela
  → Context Translator estrutura sem bloquear
  → sistema mostra “guardado no seu universo”
```

### Retomada

Uma estrela/planeta parado abre:

```text
onde parei
por que importa
última evidência
mudanças desde a última visita
próximo passo único
```

### Exploração

A pessoa pode alternar:

```text
timeline → constelação → galáxia → detalhe → jornada → run/evidence
```

Sem perder o objeto original.

### Passagem para execução

A partir de uma estrela, cluster ou planeta:

```text
organizar contexto
→ criar WorkPacket
→ escolher squad/capability
→ planejar
→ pedir aprovação
→ executar
```

A ação deve preservar a visão planetária; não mandar o usuário para uma tela vazia e sem origem.

## Fronteiras de dados

```text
Flow Registry       = fonte transacional dos eventos e lifecycle
Nuvem               = contexto derivado, agrupamento e evidência
My Universe         = projeção visual e interação humana
Flow OS Ledger      = runs, receipts, decisões e proveniência transversal
```

Não criar uma segunda tabela canônica de eventos dentro da Nuvem. Não expor SQLite cru pelo MCP. A PWA recebe payload filtrado e versionado.

## Segurança e privacidade

My Universe é privado por padrão:

```text
zero social por padrão
compartilhamento opt-in
exportação controlada
segredos fora de cloud.json
sem transcript bruto por padrão
sem envio automático para providers
```

A experiência deve comunicar:

```text
“Seu universo.”
“Só você vê isso.”
“Nada sai daqui sem você dizer.”
```

## Métricas específicas da superfície

Além das métricas do Flow OS:

```text
capture_to_star_visible
resume_from_planet_success_rate
planet_to_workpacket_conversion
constellation_exploration_rate
cluster_understanding_rate
unresolved_star_age
black_hole_recovery_rate
visual_context_restatement_count
```

Essas métricas medem se a superfície reduz fricção e ajuda a pessoa a se reconhecer no próprio conhecimento. Não são métricas para punir produtividade.

## Critério de aceitação

A continuidade está provada quando:

1. o My Universe continua abrindo e renderizando a visualização planetária atual;
2. uma captura no Flow aparece como estrela sem reimplementação paralela;
3. uma task filha aparece como planeta ligada à origem;
4. um cluster/galáxia possui origem e evidência consultáveis;
5. uma estrela pode virar WorkPacket mantendo seu source context;
6. uma jornada interrompida pode ser retomada pela superfície planetária;
7. o flow-viz técnico mostra a mesma entidade em Definition/Run/Control View;
8. os dois lados usam IDs/referências compartilhados, sem duplicar a fonte transacional;
9. o shape legado do `cloud.json` continua compatível;
10. a pessoa pode usar o My Universe sem conhecer aptdata, MCP ou qualquer executor.

## Ordem de evolução

```text
1. congelar/validar contrato cloud.json legado
2. adicionar refs de contexto/jornada/evidência de forma aditiva
3. conectar captura → ContextPacket → estrela
4. conectar estrela/planeta → WorkPacket
5. conectar retomada → run/evidence
6. conectar galáxia → capability/pattern/learning proposal
7. integrar links My Universe ↔ flow-viz técnico
8. só então ampliar conectores externos
```

## Não-goals

```text
não reescrever o My Universe em outro framework
não transformar a superfície planetária em dashboard corporativo
não substituir a linguagem orgânica por tabelas técnicas
não colocar toda a complexidade do kernel dentro do PWA
não tornar clusters gerados por ML a verdade sobre a pessoa
não publicar o universo pessoal por padrão
```

## Relação com decisões anteriores

- ADR 0002: Control Plane, SDK, MCP e Runner têm fronteiras próprias.
- ADR 0003: tradução e integração de contexto são o núcleo humano.
- ADR 0004: motores/frameworks são extensões do conhecimento.
- Esta ADR define a superfície humana que torna esse conhecimento navegável e significativo.

## Fontes canônicas

- `antunes-hq/nuvem/README.md`
- `antunes-hq/nuvem/CLAUDE.md`
- `antunes-hq/nuvem/contrato-superficie-my-universe.md`
- `antunes-hq/nuvem/docs/rft/0001-my-universe-v2.md`
- `bora-hq/flow/README.md`
- `bora-hq/visu/labs/flow-viz/central.html`
- `docs/plans/flow-os-master-plan.md`
- `IMPLEMENTATION_LEDGER.md`

## Próximo vertical slice

```text
flow.db event
  → ContextPacket
  → cloud payload aditivo com context_refs
  → estrela/planeta no My Universe
  → detalhe com próximo passo único
  → WorkPacket/runa/evidence link no flow-viz
```

A continuação começa no My Universe existente, não em uma tela nova que imite sua estética.