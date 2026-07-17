# ADR 002: aptdata como Núcleo de Orquestração Pluggable (`.aptdata/`, entry points, camada web)

**Status:** Proposed
**Data:** 2026-07-17
**Contexto:** Consolidação do ecossistema — posicionar o `aptdata` como a biblioteca-base
abstrata que qualquer ferramenta consome, e não como mais um app entre vários.

## 1. Contexto e Problema

O `aptdata` já é um framework declarativo publicado (PyPI, v0.2.0) com três abstrações universais
(`ISystem` / `IFlow` / `IComponent`) e uma camada de agentes que abstrai backends heterogêneos.
Em paralelo, cresceram dois consumidores ao redor dele — um repositório de visualização
(`aptdata-viz`) e um painel de observabilidade num monorepo separado (o "Lab", `ai-labs`) — cada um
com **sua própria cópia de fonte de verdade** (um `agents.yaml` aqui, um `agents.yaml` lá, um
`DEFAULT_CONFIG` acolá) e **sua própria lógica de dashboard**.

O problema não é falta de peças — é **dispersão**. Três sintomas concretos:

* **Fonte de verdade fragmentada.** A configuração declarativa vive hoje em pelo menos três lugares
  distintos: `aptdata.yaml` (manifesto de sistema, lido pelo `YamlSystemBuilder`), `agents.yaml`
  (registry de agentes, lido pelo `AgentRegistry`) e o diretório de estado `~/.aptdata/`. Não há um
  local canônico único de **projeto** que qualquer ferramenta encontre e valide.
* **Extensão exige código, não `pip install`.** Registrar um sistema/componente/agente novo passa
  por chamada imperativa (`registry.register(...)`) ou carregamento por caminho pontilhado. Não há
  descoberta automática — um terceiro não consegue estender o `aptdata` só instalando um pacote.
* **Consumidores reimplementam o núcleo.** Os dashboards (aptdata-viz e o painel do Lab) carregam
  regras, registries e leitura de estado por conta própria, em vez de consumir uma superfície de
  leitura estável do `aptdata`.

O objetivo desta ADR é decidir a arquitetura que faz do `aptdata` o **núcleo abstrato e pluggable**:
um modelo de orquestração no qual (a) qualquer framework/ferramenta pluga por um contrato estável,
(b) toda a estrutura do projeto vive numa **fonte única versionada**, e (c) as camadas de cima
(web, TUI, bots) são **consumidoras**, independentes da ferramenta que dispara o trabalho.

## 2. O achado que orienta a decisão: a base já existe

Boa parte do desenho abaixo **já está no código** — a ADR consolida e fecha pontas, não reescreve.

| Peça | O que já existe | Lacuna a fechar |
|---|---|---|
| Orquestrar qualquer agente | `aptdata/agents/`: contrato `IAgent`, adapters `OpenClawAgent` / `ClaudeCodeAgent` / `OpenCodeAgent`, `Router` + `Skill`, `ConversationEngine`, `Project` / `ProjectRunner` | modos de execução não nomeados; adapter novo ainda exige código |
| Plugar engines/frameworks | `plugins/`: `_SystemRegistry`, `PluginManager` (carga por caminho pontilhado), extras `[pandas/spark/ai/...]` | descoberta manual; sem entry points |
| Fonte declarativa | `YamlSystemBuilder` (YAML→System), `aptdata.yaml`, `agents.yaml`, `schema export` (JSON Schema do `ParsedConfig`), dir `~/.aptdata/` | três fontes divergentes; sem local de projeto unificado |
| Camada web | `aptdata viz` já no CLI (`aptdata/viz/static/`); o plano de viz já a define como consumidora que absorve o painel | os dashboards ainda não convergiram |
| Governança / telemetria | `governance/RuleRegistry` + audit, `EventBus` (JSON Lines), MCP, `dry_run`, `observability/` | evolução opcional (ver §2.5) |

## 2. Decisões Arquiteturais Propostas

### 2.1. Descoberta de plugins por entry points + pluggy

Não hand-rollar o sistema de plugins — usar as ferramentas provadas da comunidade:

* **Descoberta:** o mecanismo padrão da biblioteca-padrão — `importlib.metadata.entry_points(group=...)`,
  estável desde o Python 3.10. Grupos:
  * `aptdata.systems` — implementações de `ISystem`.
  * `aptdata.components` — componentes reutilizáveis.
  * `aptdata.agents` — adapters de backend de agente (kind → classe).
  * `aptdata.plugins` — readers / writers / engines.
  * `aptdata.commands` — subcomandos de CLI (ver §2.4).
* **Gestão de hooks:** [`pluggy`](https://pluggy.readthedocs.io/) — a mesma biblioteca que dá o
  sistema de plugins do `pytest`. Define os hooks de ciclo de vida via `@hookspec` no núcleo e
  `@hookimpl` nos plugins. É o encaixe natural para os hooks `pre_execute` / `post_execute` /
  `on_success` / `on_failure` que a **ADR-001** já pede (a "governança invisível" via event bus deixa
  de ser código ad-hoc e vira hook specs versionados).

Um terceiro passa a estender o `aptdata` **só instalando um pacote** que declare o entry point
correspondente, sem que o núcleo tenha qualquer dependência ou conhecimento prévio dele. O registro
imperativo (`registry.register(...)`) permanece como atalho para scripts e testes locais. Isto
substitui o `PluginManager` / `_SystemRegistry` caseiros (que já citam "entry-point-style discovery"
como intenção) por entry points + pluggy.

```toml
# no pyproject.toml de um pacote de terceiro
[project.entry-points."aptdata.agents"]
meu_backend = "meu_pacote.adapters:MeuAgent"
```

### 2.2. Fonte única de projeto: o diretório `.aptdata/`

Consolidar as fontes de verdade num **dotdir de projeto** `.aptdata/`, no estilo XDG e inspirado no
papel que o `pyproject.toml` cumpre para pacotes Python (um local canônico, seções por
responsabilidade, backend trocável). O `.aptdata/` reúne o que hoje está espalhado:

* `.aptdata/system.yaml` — o manifesto de sistema (hoje `aptdata.yaml`, consumido pelo `YamlSystemBuilder`).
* `.aptdata/agents.yaml` — o registry de agentes (hoje `agents.yaml`, consumido pelo `AgentRegistry`).
* `.aptdata/config.yaml` — a configuração declarativa (`ParsedConfig`).
* Um **JSON Schema versionado** por arquivo, gerado pelo `schema export` já existente — a superfície
  que qualquer ferramenta lê e valida (é o contrato tool-agnóstico).

Ferramentas da comunidade (sem validação manual):

* **[`pydantic-settings`](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/)**
  para o loader tipado e *fail-fast* — o repo já é pydantic-heavy, então o `.aptdata/` vira um
  modelo validado que quebra cedo se a config estiver errada.
* **`check-jsonschema`** no pre-commit/CI, validando os arquivos do `.aptdata/` contra o JSON Schema
  versionado a cada commit.

Distinção importante — **projeto ≠ usuário**:

* `.aptdata/` (na raiz do projeto, versionado no git) = **a estrutura do projeto/usuário** que
  qualquer ferramenta consome.
* `~/.aptdata/` (no home, não versionado) = **estado de máquina** (sessões, `events.db`) — permanece
  separado, é outra responsabilidade.

Um loader único em `aptdata.config` localiza o `.aptdata/` subindo a árvore de diretórios (como o
git e o `pyproject.toml` fazem), de forma que qualquer comando encontre o projeto a partir de
qualquer subpasta.

### 2.3. Modos de agente formalizados

Nomear e documentar **como o `aptdata` executa**, sobre o `IAgent` + `Router` + `ConversationEngine`
que já existem — cada modo com entrada clara no CLI e no `.aptdata/`:

* `oneshot` — um `send` único a um agente resolvido por id/capability.
* `converse` — sessão multi-turno via `ConversationEngine` / `DecisionPolicy` / `SessionStore`.
* `project` — execução orientada a tarefas via `Project` / `ProjectRunner`.
* `orchestrated` — roteamento multi-agente pelo `Router` (mode/skill/confidence).

Isso responde diretamente ao pedido de "colocar alguns modos de agente, como é executado": os modos
deixam de ser conhecimento implícito no código e viram vocabulário de primeira classe.

### 2.4. CLI como produto

O surface do CLI já é amplo (`run`, `agents`, `project`, `mesh`, `converse`, `mcp`, `obs`, `viz`, …).
Fechar as pontas que faltam para tratá-lo como produto completo:

* `aptdata init` — cria o `.aptdata/` do projeto a partir de um template.
* `aptdata plugins` — lista o que foi **descoberto por entry point** (systems/components/agents/plugins).
* `aptdata doctor` — valida o `.aptdata/` contra os JSON Schemas versionados (via `check-jsonschema`).
* Consistência de `--json` e `dry_run` (plan-only) em **todos** os comandos que mudam estado.

O CLI já é **Typer** (moderno, sobre Click). Subcomandos de terceiros entram pelo grupo de entry
point `aptdata.commands` e são montados com `app.add_typer(...)` na inicialização — o padrão
[`click-plugins`](https://github.com/click-contrib/click-plugins) aplicado ao Typer. Assim um pacote
instalado pode adicionar um subcomando sem tocar no núcleo.

### 2.5. Governança e telemetria (evolução alinhada à ADR-001)

Manter a direção da ADR-001 (governança invisível via event bus). Como evolução **opcional** e não
bloqueante: os eventos do `EventBus` podem ganhar campos "5W" (o quê / quando / onde / quem / porquê)
para auditoria uniforme, e as `BusinessRule` do `RuleRegistry` podem virar um passo de verificação
bloqueante do workflow. Fica registrado como caminho, não como pré-requisito desta ADR.

### 2.6. Toolchain e DX (stack moderno)

Adotar o toolchain Python que a comunidade consolidou em 2025/26, tratando os três repositórios como
um só espaço de trabalho:

* **[`uv`](https://andrewodendaal.com/python-packaging-2026-uv-poetry-modern-ecosystem/)** no lugar do
  Poetry — resolução 10–100× mais rápida e **workspace** nativo, que cobre `smart-data` (o núcleo),
  a camada web e o Lab num monorepo lógico com um lockfile reproduzível.
* **`ruff`** (já em uso) como linter + formatter único.
* **`pre-commit`** rodando `ruff` + `check-jsonschema` (valida o `.aptdata/`) antes de cada commit.
* **Type-check estrito** (`mypy`, ou `ty` quando amadurecer) — os contratos Pydantic estritos do
  `aptdata` tornam a checagem de tipos um ganho real, não cerimônia.
* Mantém `pytest` + cobertura ≥ 80% e os workflows de CI existentes (adaptados para `uv`).

## 3. Consumidores: camada web única e o papel do Lab

A lógica de negócio (registries, orquestração, observabilidade) vive **só no núcleo**. As camadas de
cima são consumidoras da superfície de leitura do `aptdata`:

* **Camada web (o repo hoje chamado `aptdata-viz`)** passa a ser a **única** superfície web —
  consumidora da read-API do `aptdata` (event store da observability + registry via MCP; ao vivo via
  SSE plugado no `EventBus`), **absorvendo os dashboards existentes** num só. Como o escopo cresceu
  além de "visualização", o nome "viz" fica apertado; sugere-se renome (ex.: `aptdata-console` /
  `aptdata-hub` / `aptdata-studio`) — a decisão de nome fica para a revisão.
* **O Lab (`ai-labs`)** segue como fábrica de kits + o `lab` CLI; seu painel deixa de ser dono da
  lógica de agentes/observabilidade e passa a **consumir o `aptdata` como biblioteca** (ou é
  absorvido pela camada web). O `agents.yaml` do Lab converge no formato de `.aptdata/agents.yaml`.

## 4. Trade-offs e Consequências

* **Positivo:** uma fonte de verdade só (`.aptdata/`), extensão por `pip install`, e consumidores
  finos que não reimplementam o núcleo. O ecossistema deixa de divergir.
* **Positivo:** o contrato tool-agnóstico (JSON Schema versionado) torna o `aptdata` consumível por
  qualquer ferramenta — Claude ou qualquer outra —, que é a meta central.
* **Atenção (migração):** consolidar `aptdata.yaml` + `agents.yaml` no `.aptdata/` exige um caminho
  de migração e compatibilidade temporária (loader aceita o formato antigo com aviso de depreciação).
* **Atenção (descoberta implícita):** entry points tornam a origem de um plugin menos óbvia no
  código; mitiga-se com `aptdata plugins` (lista a proveniência) e `aptdata doctor`.
* **Atenção (toolchain):** migrar Poetry→`uv` e adotar workspace/type-check é ganho de DX, mas mexe
  no CI e no fluxo de contribuição; fazer como PR 0 isolado, com o lockfile commitado, antes das
  mudanças de arquitetura.

## 5. Próximos Passos (roadmap de PRs, cada um entregável)

0. **DX/toolchain:** migração Poetry→`uv` (workspace dos três repos) + `pre-commit`
   (`ruff` + `check-jsonschema`) + type-check (`mypy`/`ty`) + CI adaptado. Base para o resto.
1. **Plugins:** entry points + `pluggy` (grupos + `hookspec`s de ciclo de vida), migrando o
   `PluginManager` / `_SystemRegistry` + comando `aptdata plugins`.
2. **`.aptdata/`:** loader com `pydantic-settings` + JSON Schemas versionados + `aptdata init` /
   `aptdata doctor` (com migração de `aptdata.yaml` / `agents.yaml`).
3. Modos de agente formalizados (CLI + `.aptdata/` + docs).
4. Camada web como consumidora da read-API, absorvendo os dashboards.
5. Painel do Lab migrado para consumir o `aptdata`.
