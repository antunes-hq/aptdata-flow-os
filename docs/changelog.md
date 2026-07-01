# Changelog

All notable changes to **aptdata** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.0] – 2026-07-01

### Added

- **Multi-agent core (`aptdata.agents`)** — `IAgent`/`AgentRegistry`, `Router` (prefix/skill/llm/default), `Project`/`ProjectRunner`, adapters reais (OpenClaw, ClaudeCode, OpenCode via CLI) e MCP dispatch. Novos comandos `aptdata agents` (list/send/route/dispatch/resolve) e `aptdata project` (init/plan/run).
- **Google Calendar OAuth2** — New `aptdata.integrations` module with OAuth2 client for Google Calendar API.
- **Analytics Engine** — Migrated analytics and gamification engine from mindflow (`aptdata.analytics.indicators`, stats, clusters, dedup, TF-IDF).
- **Gamificação** — XP, streak e levels portados do mindflow para `aptdata.gamification`.
- **Guardrails** — `.gitignore` for secrets and `.env.example` template.

### Fixed

- **Observabilidade** — Added `timed_create` to `__init__.py` exports.
- **CI** — Lint errors and test dependency failures resolved across multiple PRs.
- **Lint** — Zerada a dívida de `ruff` em `aptdata/` e `tests/` (imports, linhas longas, `__all__` nos re-exports).

### Changed

- **Quick start example** — Updated to reflect current API with `IExecutor`/`DefaultExecutor`.

---

## [0.0.3] – 2026-03-11

### Added

- **`docs/prompts/docs-agent.md`** — Authored the DevPortal Docs Agent prompt, establishing strict guidelines for Brazilian Portuguese language, anti-prolixity, MkDocs Material features, and documentation architecture.
- **`IExecutor` and `DefaultExecutor`** — Added graph execution decoupling from `BaseWorkflow`.
- **`IAsyncComponent`** — Added native async/await support for I/O bound pipelines and LLMs.
- **`IIterableDataset`** — Added generator-based datasets to support lazy evaluation and streaming contracts.

### Changed

- **DevPortal Rewrite** — Overhauled all core documentation (`index`, `getting-started`, `architecture`, `scaffold-templates`, `configuration`, `telemetry`, `quality`, `governance`, `transform-engines`, `diys`, `ci-logs`, `mcp`) translating content to Brazilian Portuguese.
- **UI/UX Evolution** — Implemented MkDocs Material admonitions, content tabs, and grids across documentation files to improve Developer Experience (DX).
- **Navigation Audit** — Re-structured the `mkdocs.yml` navigation tree into `Getting Started -> Core -> Plugins -> API`. Enabled the `md_in_html` extension for layout support.
- **`IDataset` Generics** — Refactored `IDataset` to inherit from `Generic[T]`, enforcing strict typing contracts.
- **StateBackend Optimization** — Removed raw record materialization from workflow checkpoints, persisting only metadata to prevent OOM errors in Big Data flows.

### Added

- **`aptdata.core.workflow`** — context-aware workflow module introducing:
  - `IWorkflow` / `BaseWorkflow` with `before_run` / `after_run` hooks.
  - `WorkflowNode` / `WorkflowEdge` graph primitives with optional conditional
    routing.
  - `compile()` adjacency-list precomputation and cycle validation.
  - `run()` execution with hook lifecycle and `ExecutionContext` integration.
- **`tests/test_workflow.py`** — tests covering workflow primitives, lifecycle,
  compile validation, and conditional execution behavior.

### Changed

- `aptdata.core.__init__` now exports workflow abstractions.

---

## [0.0.2] – 2026-03-08

### Added

- **`system.py`** — universal architecture module introducing:
  - `ComponentKind` enum (TRANSFORM, FILTER, AGGREGATE, EXTRACT, LOAD, CUSTOM).
  - `ComponentMeta` dataclass — rich metadata (kind, tags, branch_on,
    description, extra).
  - `IComponent` / `BaseComponent` — replaces `IStep`/`BaseStep`; components
    return `list[IDataset]` enabling multi-output and branching flows.
  - `FlowEdge` — directed edge with optional conditional predicate.
  - `FlowNode` — graph node with back-reference to its owning `IFlow`.
  - `IFlow` / `BaseFlow` — directed execution graph with `add_component()`,
    `connect()`, `compile()` and `run()`.
  - `ISystem` / `BaseSystem` — top-level orchestrator with `register_flow()`
    and `run()`.
- **`tests/test_system.py`** — 34 tests covering all new abstractions.

### Changed

- `aptdata.plugins`: `_PipelineRegistry` renamed to `_SystemRegistry`;
  `list_pipelines()` renamed to `list_systems()`.
- `aptdata.cli.app`: CLI now instantiates systems with `system_id=<name>`.
- `aptdata.core.__init__`: exports updated to the new architecture.
- `tests/test_core.py`: stripped to dataset-only tests.
- `tests/test_cli.py`: mock updated from `_MockPipeline` to `_MockSystem`.
- All documentation updated to reflect the new System/Component/Flow model.

### Removed

- `aptdata/core/pipeline.py` (`IPipeline`, `BasePipeline`).
- `aptdata/core/step.py` (`IStep`, `BaseStep`).

---

## [0.0.1] – 2026-03-06

### Added

- **Two-layer contract system** – pure `@dataclass + ABC` interfaces
  (`IDataset`, `IStep`, `IPipeline`) and Pydantic-validated base classes
  (`BaseDataset`, `BaseStep`, `BasePipeline`).
- **Plugin registry** – `aptdata.plugins.registry` singleton for
  registering and discovering concrete pipeline implementations by name.
- **CLI** – `aptdata run` command: runs a registered pipeline and emits
  structured JSON events to stdout/stderr.
- **CLI** – `aptdata monitor` command: launches the interactive Textual TUI
  monitoring dashboard.
- **TUI** – `MonitorApp` with DAG panel, per-step status table and
  memory-usage bar; auto-refreshes at a configurable interval.
- **Test suite** – pytest-based tests covering all core interfaces, base
  classes, the CLI and the plugin registry.
- Initial project documentation.
