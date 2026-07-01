# Sincronização CLI ↔ viz ↔ UI ↔ docs — north star + working agreement

> Brief de direção para agentes trabalhando neste repositório. A meta não é só
> "não ter bug": é ter **tecnologia suficiente para manter CLI, viz, UI e docs
> sincronizados** a partir de uma fonte única — que uma mudança na fonte se
> propague (ou quebre o CI) em todas as superfícies.

## 1. North star
- **Uma fonte única de verdade por domínio.** CLI, viz, UI e docs são **projeções**
  dessa fonte, nunca cópias que divergem. (Ecoa o problema dos "3 registros
  divergentes" que o `agents.yaml` resolveu — não recriar essa dor em outra camada.)
- **Contrato antes de superfície.** Os shapes canônicos (`AgentSpec`, `RouteDecision`,
  os payloads da API do viz, os eventos de observabilidade) são o contrato. Toda
  superfície lê o MESMO contrato — não redefine.
- **Sincronização é verificável.** Divergência entre código, CLI, viz e docs deve
  **falhar o CI**, não passar silenciosa. "Docs drift" é bug.

## 2. As camadas (e como se ligam)
- **Fonte**: modelos/esquemas (pydantic) + `agents.yaml` + event store (observability).
- **aptdata (núcleo)**: System/Flow/Component, `agents/` (Registry/Router/Project),
  MCP, observability.
- **CLI** (`aptdata/cli`): projeção operável do núcleo. Todo comando com `--json`.
- **viz/UI** (`aptdata/viz`): projeção visual — API de leitura (contrato) + frontends
  finos (web + TUI) que só consomem. Adicionar view = endpoint + consumidor, sem
  duplicar lógica.
- **docs** (`docs/**`, docstrings, README): projeção textual — deve refletir o código
  atual, com exemplos que rodam.
- Planos vivos em `docs/plans/`: observability, cli-tdd, telegram-orchestration, aptdata-viz.

## 3. TDD (disciplina inegociável)
- **Red → Green → Refactor**: escreva o teste que descreve o comportamento ANTES,
  veja falhar, implemente o mínimo, refatore com o teste te protegendo.
- **Todo bug corrigido nasce com um teste que o reproduz** (senão ele volta).
- **Todo comando/endpoint novo nasce com testes de contrato** antes de "estar pronto".

## 4. O que é um bom caso de teste
- Testa o **contrato** (entrada → saída, exit code, formato JSON), não a implementação.
- Cobre **edge cases e caminhos de erro**, não só o happy path.
- **Determinístico e isolado**: stub de rede/subprocess/agentes (padrão em
  `tests/test_cli_agents_cmd.py` — `monkeypatch` em `OpenClawAgent.send`).
- **Um comportamento por teste**, com assert claro; nome que diz o que garante.

## 5. Painel (viz/UI) bem definido e escalável
- A **API de leitura do viz é o contrato**; os frontends (web/TUI) são clientes finos.
- **Zero lógica de negócio no viz** — ele lê a mesma fonte (registry/observability) e
  renderiza. Escala adicionando view = endpoint + consumidor.
- Uma view nova só entra com: contrato do endpoint + teste do endpoint + consumidor.

## 6. Docs sincronizadas
- `docs/**`, docstrings, README e exemplos refletem o código ATUAL. Assinaturas,
  nomes de comando, flags e comportamento têm que bater.
- Meta de tecnologia: um **check de sincronização** (docs-vs-realidade) — ex: validar
  que os comandos/flags citados nas docs existem no CLI, que os exemplos executam.
  Enquanto não existe, tratar divergência como bug e corrigir na mesma PR.

## 7. Gates de qualidade
- `ruff check aptdata/ tests/` = 0.
- `pytest -q` verde; cobertura de `aptdata/cli` ≥ 75% (gate global de 80% é aspiracional
  — a main está ~69%; decisão de baixar pra ~68% está pendente).
- Nada de segredo commitado.

## 8. Working agreement (fluxo)
- A `main` tem **ruleset**: nunca commitar direto — sempre branch + PR.
- Branch a partir de `origin/main`; commit convencional + `Co-Authored-By`.
- PR com label de release (`release:minor|patch|major` para feature/fix; `release:skip`
  para chore/docs). O `release.yml` + `tag-release.yml` cuidam de bump + tag + PyPI +
  GitHub Release automaticamente.
- Mudanças focadas no escopo; se não tem certeza de um bug, **flag em vez de "consertar"
  no chute**.
