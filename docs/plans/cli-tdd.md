# Plano de TDD completo do CLI — aptdata

> Objetivo: travar o **contrato** de cada comando do CLI Typer (`aptdata/cli/`)
> com testes. Este documento é **só planejamento** — não implementa features
> nem escreve os testes. Ele define, comando a comando: o que DEVE fazer,
> saídas (texto + JSON), exit codes, casos de erro, cobertura atual e os casos
> de teste a escrever.

Estado da árvore (2026-07-01): coverage do subconjunto CLI = **83%**
(gate CI `--cov-fail-under=75` no job "CLI tests"). Gate global de 80% do repo
(~69%) **não é foco** deste plano, mas gaps globais ficam registrados abaixo.

---

## 1. Inventário de comandos

### Padrões de contrato (2 famílias — já é a 1ª inconsistência)

- **Família A — "always-JSON" (`_emit`)**: comandos no `app.py`
  (`run`, `mcp-start`, `schema export`) e `scaffold.py` sempre emitem 1 linha
  JSON, com `event` de ciclo de vida (`*.started` / `*.completed` / `*.error`).
  Erro → stderr + `raise SystemExit(1)`. Sucesso → `raise SystemExit(0)`.
  Só o `app._emit` injeta `trace_id`; o `scaffold._emit` **não** (divergência).
- **Família B — dual-mode (`SmartConsole` + `--json`)**: sub-apps
  `system / plugin / config / telemetry / mesh / agents / project`.
  Modo texto = Rich; `--json` = 1 linha JSON. Erro via `console.error`
  (stderr) + `raise typer.Exit(1)`. Sucesso = exit 0 implícito.
- Vários comandos da Família B **não têm `--json`** (`system validate`,
  `plugin preview`, `plugin load`, `config *`, `telemetry export`) — ver §4.

### 1.1 Comandos top-level (`aptdata/cli/app.py` + `scaffold.py`)

| # | Comando | Assinatura | Contrato resumido |
|---|---------|-----------|-------------------|
| 1 | `run` | `run PIPELINE [--env/-e dev] [--dry-run]` | Lookup em `plugins.registry`; instancia `pipeline_cls(system_id=)`, roda (a menos de `--dry-run`). Emite `pipeline.started` → `pipeline.completed` (com `elapsed_seconds`). Pipeline ausente → `LookupError` → `pipeline.error` stderr, exit 1. Qualquer exceção no `.run()` → `pipeline.error`, exit 1. |
| 2 | `monitor` | `monitor [--refresh/-r 1.0]` | Abre TUI `MonitorApp(refresh_interval=)` e `.run()`. Sem contrato de stdout. |
| 3 | `mcp-start` | `mcp-start [--transport/-t stdio]` | Emite `mcp.server.starting`; sobe `mcp.server.run(transport=)`. Exceção → `mcp.server.error` stderr, exit 1. |
| 4 | `scaffold` | `scaffold PROJECT_NAME [--output/-o .] [--template/-t hello-world]` | Valida nome (`^[A-Za-z][A-Za-z0-9_]*$`), valida template ∈ 6 templates, recusa dir existente. Emite `scaffold.started` → `scaffold.completed`. Erros → `scaffold.error` stderr, exit 1. |
| 5 | `interactive` | `interactive` | Wizard `questionary`/fallback `typer.prompt`. Loop de menu. |
| 6 | `schema export` | `schema export --output/-o PATH` | `write_domain_schema(output)`. Emite `schema.export.started` → `schema.export.completed`. Exceção → `schema.export.error` stderr, exit 1. |

### 1.2 `system` (`commands/system_cmd.py`)

| # | Comando | Assinatura | Contrato |
|---|---------|-----------|----------|
| 7 | `system list` | `[--json]` | Lista `registry.list_systems()`. JSON: `{systems, count}`. Vazio texto → warning. |
| 8 | `system info` | `NAME [--json]` | `registry.get(name)`. JSON: `{name, class, module, doc}`. Ausente → error, exit 1. |
| 9 | `system validate` | `NAME` (**sem --json**) | Instancia e `.compile()` cada flow. Sucesso → `console.success`. Ausente → error exit 1. Exceção de compile → error exit 1. |

### 1.3 `plugin` (`commands/plugin_cmd.py`)

| # | Comando | Assinatura | Contrato |
|---|---------|-----------|----------|
| 10 | `plugin list` | `[--json]` | `plugin_manager.list_plugins()`. JSON = dict readers/writers. Vazio texto → warning. |
| 11 | `plugin inspect` | `NAME [--json]` | `get_plugin_schema(name)`. `KeyError` → error exit 1. |
| 12 | `plugin preview` | `READER [--limit/-n 5]` (**sem --json**) | `preview_dataset(reader)[:limit]` em tabela Rich. Vazio → warning. `KeyError` → error exit 1. Outra exceção → "Preview failed" exit 1. |
| 13 | `plugin load` | `MODULE_PATH` (**sem --json**) | `load_module()`. Sucesso → success. `ModuleNotFoundError` → "Module not found" exit 1. Outra → "Load failed" exit 1. |

### 1.4 `config` (`commands/config_cmd.py`) — **nenhum tem --json**

| # | Comando | Assinatura | Contrato |
|---|---------|-----------|----------|
| 14 | `config validate` | `PATH (exists=True)` | Parse via `YamlConfigParser`. Sucesso → `Config valid: system_id=...`. Exceção → "Validation failed" exit 1. Path inexistente → Typer erro exit 2. |
| 15 | `config init` | `[--output/-o pipeline.yaml] [--template]` | Escreve `_STARTER_YAML`. Recusa arquivo existente (exit 1). Renderiza preview. |
| 16 | `config show` | `PATH (exists=True)` | Pretty-print YAML. Path inexistente → exit 2. |
| 17 | `config run` | `PATH (exists=True) [--env/-e dev]` | Parse → registra → `.run()`. Sucesso → success. Exceção → "Execution failed" exit 1. |

### 1.5 `telemetry` (`commands/telemetry_cmd.py`)

| # | Comando | Assinatura | Contrato |
|---|---------|-----------|----------|
| 18 | `telemetry status` | `[--json]` | `_get_telemetry_status()` → `{configured, provider, service}`. |
| 19 | `telemetry export` | `[--format/-f json]` (**--format, não --json**) | `json` → dump indentado. Formato != json → error exit 1. |

### 1.6 `mesh` (`commands/mesh_cmd.py`)

| # | Comando | Assinatura | Contrato |
|---|---------|-----------|----------|
| 20 | `mesh list` | `[--dir/-d .] [--json]` | `rglob(mesh.yaml)` → `{component,type,version,path}`. JSON `{components,count}`. Vazio → warning. YAML inválido → entry com `error`. |
| 21 | `mesh run` | `COMPONENT [--dir/-d .] [--dry-run] [--json]` | Resolve mesh.yaml (por dir ou por campo `component`). Ausente → `mesh.error` exit 1. `--dry-run` → `mesh.run.dry_run` com `command`. `job-wheel`/`docker-compose-app` executados via subprocess; `mesh.run.started/completed`. Tipo desconhecido → ValueError → `mesh.run.error` exit 1. Subprocess !=0 → RuntimeError → error exit 1. |
| 22 | `mesh build` | `COMPONENT [--dir/-d .] [--json]` | Idem run mas build (`pip wheel` / `docker compose build`). `mesh.build.started/completed/error`. |

### 1.7 `agents` (`commands/agents_cmd.py`)

| # | Comando | Assinatura | Contrato |
|---|---------|-----------|----------|
| 23 | `agents list` | `[--file/-f] [--enabled] [--json]` | `registry.specs()` ordenado (enabled first). JSON `{agents,count}`. Vazio texto → warning. Arquivo ausente → `BadParameter` exit 2. |
| 24 | `agents send` | `AGENT_ID PROMPT [--file/-f] [--json]` | `registry.get` → `agent.send(prompt)`. `KeyError` → error exit 1. `result.ok=False` → error + exit 1. JSON = `result.to_dict()`. |
| 25 | `agents route` | `TEXT [--file/-f] [--json]` | `Router.route(text)` (não envia). JSON = `decision.to_dict()`. |
| 26 | `agents dispatch` | `TEXT [--file/-f] [--json]` | Route + send. `agent_id None` → error exit 1. `result.ok=False` → exit 1. JSON = `{routed_to, mode, **result}`. |
| 27 | `agents resolve` | `CAPABILITY [--file/-f] [--json]` | `registry.resolve(capability)`. None → warning/JSON `{agent:null}` **exit 1**. |

### 1.8 `project` (`commands/project_cmd.py`)

| # | Comando | Assinatura | Contrato |
|---|---------|-----------|----------|
| 28 | `project init` | `NAME [--out/-o] [--json]` | `scaffold_project(name).to_yaml()`. Arquivo existente → error exit 1. JSON `{created,tasks}`. |
| 29 | `project plan` | `PROJECT_FILE [--file/-f] [--json]` | `ProjectRunner.plan()` (dry-run rota). Arquivo ausente → `BadParameter` exit 2. |
| 30 | `project run` | `PROJECT_FILE [--file/-f] [--json]` | `ProjectRunner.run()`. Se `ok < total` → exit 1. JSON `{project,ok,total,results}`. |

**Total: 30 comandos** (2 não-testáveis por CLI puro: `monitor`, `interactive`).

---

## 2. Mapa de cobertura atual

Fonte: `pytest <subset CLI> --cov=aptdata/cli --cov-report=term-missing`
(subset = os 12 arquivos `test_cli*`, `test_agents_cli`, `test_scaffold_templates`).

| Arquivo | Cover | Linhas faltantes (o que são) |
|---------|-------|------------------------------|
| `app.py` | 80% | 117-128 (run: `except Exception` genérico), 150-153 (`monitor`), 175-185 (`mcp-start` corpo+erro), 214 (`interactive` wrapper), 241-251 (`schema export` erro) |
| `commands/mesh_cmd.py` | 70% | 24-39 (fallback parser sem PyYAML), 59-64 (`_resolve_mesh_file` por campo), 107-108 (`mesh list` YAML inválido), 215-233 (`mesh run` execução+erro), 247, 318-336 (`mesh build` execução+erro), 372/396-426 (helpers subprocess) |
| `completions.py` | 73% | 12-13,22-23,32-33,55-56 (branches `except`) |
| `interactive.py` | 51% | 147-191 (`_wizard_config`), 196-222 (`_wizard_scaffold`), 236-238, dispatch de menu |
| `plugin_cmd.py` | 88% | 71 (`inspect` KeyError), 84-86 (`preview` erros), 105-107 (`load` erros) |
| `system_cmd.py` | 87% | 30 (list vazio warning), 85-90 (`validate` exceção) |
| `config_cmd.py` | 94% | 126-128 (`config run` exceção) |
| `agents_cmd.py` | 95% | 75-76 (list vazio), 138-139 (dispatch sem rota), 172 (resolve none warning) |
| `project_cmd.py` | 100% | — |
| `telemetry_cmd.py` | 100% | — |
| `scaffold.py` | 100% | — |
| `rendering/*` | 96-100% | logger 25-26; panels 40/60; console 48 |

### ⚠️ Furo estrutural: `mesh` fora do job "CLI tests"

`mesh` só é exercitado por `tests/test_e2e.py` e `tests/test_integration.py`,
que **não estão** no job `ci-cli.yml`. Dentro do subset da CI de CLI, as
funções de `mesh_cmd` têm **zero** teste comportamental (os 70% vêm só do
import: assinaturas/decorators). Ou seja, o contrato do `mesh` **não está
travado pelo gate do CLI**. Prioridade máxima.

---

## 3. Plano de testes TDD (por gap)

Convenção de stub (padrão já usado no repo):
- `from typer.testing import CliRunner`; `runner.invoke(app, [...])`.
- **Agentes**: fixture `autouse` faz `monkeypatch` de `OpenClawAgent.send`
  (e afins) devolvendo `AgentResponse` — ver `test_cli_agents_cmd.py::_stub_send`.
  Nunca bater na rede.
- **Registry/plugins**: `patch("aptdata.plugins.registry.get"/".list_systems")`,
  `patch("aptdata.plugins.plugin_manager....")`.
- **mesh subprocess**: `monkeypatch.setattr(mesh_cmd.subprocess, "run", fake)`
  devolvendo objeto com `.returncode`; nunca chamar docker/pip de verdade.
- **mcp-start**: `patch("aptdata.mcp.server.mcp.run")` para não bloquear.
- **monitor**: `patch("aptdata.tui.monitor.MonitorApp")` (MagicMock `.run`).
- Sempre validar **stdout JSON** com `json.loads(result.stdout)` e **exit_code**.

### P0 — `tests/test_cli_mesh_cmd.py` (NOVO, arquivo inexistente)
Trava o contrato do `mesh` dentro do gate de CLI. Casos:
1. `mesh list` dir vazio → texto warning; `--json` `{components:[],count:0}`.
2. `mesh list` acha 1+ `mesh.yaml` (usar `tmp_path` + escrever yaml) → campos
   corretos, ordenado; `--json` count>0.
3. `mesh list` com yaml inválido → entry contém `error` (linha 107-108).
4. `mesh run` componente inexistente → `mesh.error`, exit 1 (texto e `--json`).
5. `mesh run --dry-run` job-wheel → `mesh.run.dry_run` com `command` = entrypoint+args.
6. `mesh run --dry-run` docker-compose-app → command `["docker","compose","up"]`.
7. `mesh run` job-wheel sucesso → `subprocess.run` stubado rc=0 → `mesh.run.completed`.
8. `mesh run` job-wheel rc!=0 → RuntimeError → `mesh.run.error` exit 1.
9. `mesh run` tipo desconhecido → ValueError → `mesh.run.error` exit 1.
10. `mesh build` job-wheel sucesso/rc!=0 → `mesh.build.completed`/`error`.
11. `mesh build`/`run` docker-compose-app com subprocess stubado.
12. `_resolve_mesh_file` por **campo `component`** (não só por dir) — cria
    `sub/mesh.yaml` com `component: X`, roda `mesh run X` (cobre 59-64).
13. `_load_mesh` fallback sem PyYAML: `monkeypatch` para forçar `ImportError`
    no import de `yaml` e validar o parser mínimo (cobre 24-39).

### P0 — `tests/test_cli.py` (estender): paths de erro top-level
14. `run` pipeline cujo `.run()` levanta exceção genérica → `pipeline.error`,
    exit 1 (cobre 117-128; hoje só `LookupError` está coberto). Stub: registrar
    pipeline mock cujo `run()` faz `raise RuntimeError`.
15. `schema export` com `write_domain_schema` que levanta (patch para raise) →
    `schema.export.error` stderr, exit 1 (cobre 241-251).
16. `mcp-start` sucesso: `patch mcp.run` → `mcp.server.starting` emitido, sem erro.
17. `mcp-start` erro: `mcp.run` raise → `mcp.server.error`, exit 1 (cobre 175-185).
18. `monitor`: `patch MonitorApp` → `.run()` chamado (cobre 150-153).

### P1 — `tests/test_cli_plugin_cmd.py` (estender)
19. `plugin inspect` nome inexistente → `KeyError` → error, exit 1 (linha 71).
20. `plugin preview` reader inexistente (`KeyError`) → exit 1; reader vazio →
    warning; reader com registros → tabela (cobre 84-86). Stub `preview_dataset`.
21. `plugin load` módulo inexistente → `ModuleNotFoundError` → exit 1; módulo ok
    → success (cobre 105-107).

### P1 — `tests/test_cli_system_cmd.py` (estender)
22. `system list` vazio → warning (linha 30).
23. `system validate` sucesso (system mock com flow.compile) → success.
24. `system validate` com flow.compile que raise → "Validation failed" exit 1
    (cobre 85-90).

### P1 — `tests/test_cli_config_cmd.py` (estender)
25. `config run` cujo `.run()` levanta → "Execution failed" exit 1 (cobre 126-128).
26. `config validate/show/run` com path inexistente → exit code **2** (Typer
    `exists=True`) — trava esse contrato explicitamente.

### P2 — `tests/test_cli_agents_cmd.py` (estender — completar 95%→100%)
27. `agents list` registry vazio → warning (75-76).
28. `agents dispatch` texto sem rota (`agent_id None`) → error exit 1 (138-139).
29. `agents resolve` capability sem agente → warning + **exit 1** (172).

### P2 — `tests/test_cli_completions.py` (estender)
30. Cada `complete_*` com registry/plugin_manager que levanta exceção →
    retorna `[]` (branches 12-13/22-23/32-33/55-56). `patch` para forçar raise.

### P3 — `tests/test_cli_interactive.py` (estender — UX, baixo risco)
31. `_wizard_config` (validate + generate template) com prompts mockados (147-191).
32. `_wizard_scaffold` com prompts mockados → invoca scaffold (196-222).

---

## 4. Inconsistências de contrato a corrigir (itens de dívida)

| # | Inconsistência | Onde | Ação sugerida |
|---|----------------|------|---------------|
| C1 | `--json` ausente em comandos que deveriam ser máquina-legíveis | `system validate`, `plugin preview`, `plugin load`, `config validate/init/show/run` | Adicionar `--json` (ou documentar explicitamente que são text-only). Travar decisão com teste. |
| C2 | `telemetry export` usa `--format json` em vez do padrão `--json` | `telemetry_cmd.py` | Alinhar com o resto (`--json`) ou documentar. |
| C3 | Duas famílias de emissão (`_emit` always-JSON vs `SmartConsole --json`) | `app.py`/`scaffold.py` vs sub-apps | Unificar contrato (idealmente `SmartConsole` em todos) — grande refactor; ao menos documentar. |
| C4 | `scaffold._emit` **não injeta `trace_id`**; `app._emit` injeta | `scaffold.py:17` vs `app.py:33` | Unificar (`trace_id` em ambos ou nenhum). Teste deve fixar. |
| C5 | Exit codes: `raise SystemExit(1)` (app) vs `typer.Exit(1)` (sub-apps) | global | Comportamento igual, estilo divergente — padronizar em `typer.Exit`. |
| C6 | Erro em `--json` mode às vezes vai como `console.error` (JSON `{level:error}` no stderr), às vezes como `_emit(..., error=True)` (JSON `{event:*.error}`) | `agents send`/`mesh run` | Definir 1 schema de erro JSON e travar. |
| C7 | `agents resolve` sem match retorna **exit 1** (é "sem resultado", não erro) — pode quebrar scripts | `agents_cmd.py:173` | Decidir: exit 0 com `{agent:null}` vs exit 1. Travar com teste. |

---

## 5. Ordem de ataque (prioridade)

1. **P0 — `test_cli_mesh_cmd.py` (novo)** + paths de erro top-level em
   `test_cli.py` (run genérico, schema export erro, mcp-start, monitor).
   Fecha o maior furo: `mesh` sem contrato no gate CLI + branches de erro do app.
2. **P1 — plugin/system/config** paths de erro (preview/load/validate/config run
   + path inexistente exit 2). Alto valor, baixo custo.
3. **P2 — agents/completions** para 100% e branches defensivas.
4. **P3 — interactive** wizard flows (UX, baixo risco).
5. **Dívida de contrato (C1–C7)**: abrir issues; decidir `--json` universal e
   schema de erro único antes de escrever testes que os fixem.

Meta: subset CLI de 83% → ~95%; e mover cobertura de `mesh` para dentro do job
`ci-cli.yml` (adicionar `tests/test_cli_mesh_cmd.py` à lista do workflow).

---

### Nota sobre o gate global (fora de escopo, registrado)
Repo global ~69% < gate 80%. Gaps fora do CLI não são deste plano, mas os
maiores contribuintes tocados aqui são `interactive.py` (51%) e `mesh_cmd.py`
(70%); fechá-los ajuda os dois gates.
