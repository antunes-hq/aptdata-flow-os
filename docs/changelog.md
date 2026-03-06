# Changelog

All notable changes to **smart-data** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.0.1] – 2026-03-06

### Added

- **Two-layer contract system** – pure `@dataclass + ABC` interfaces (`IDataset`,
  `IStep`, `IPipeline`) and Pydantic-validated base classes (`BaseDataset`,
  `BaseStep`, `BasePipeline`).
- **Plugin registry** – `smart_data.plugins.registry` singleton for registering
  and discovering concrete pipeline implementations by name.
- **CLI** – `smart-data run` command: runs a registered pipeline and emits
  structured JSON events to stdout/stderr.
- **CLI** – `smart-data monitor` command: launches the interactive Textual TUI
  monitoring dashboard.
- **TUI** – `MonitorApp` with DAG panel, per-step status table and memory-usage
  bar; auto-refreshes at a configurable interval.
- **Test suite** – pytest-based tests covering all core interfaces, base
  classes, the CLI and the plugin registry.
- Initial project documentation (this site).
