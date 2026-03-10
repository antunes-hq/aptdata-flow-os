# Changelog

All notable changes to **aptdata** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
