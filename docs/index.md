# aptdata

**aptdata** is a declarative, extensible framework for building smart data
pipelines in Python.  It provides a clean two-layer contract system built
around three universal abstractions — **Component**, **Flow**, and **System**
— so you can build, test and compose data pipelines with confidence.

---

## Key features

| Feature | Description |
|---|---|
| **Contract-first design** | Pure-Python `@dataclass + ABC` interfaces (`IDataset`, `IComponent`, `IFlow`, `ISystem`) make the expected behaviour explicit before any concrete code is written. |
| **Pydantic-validated base classes** | `BaseDataset`, `BaseComponent`, `BaseFlow` and `BaseSystem` extend the interfaces and add Pydantic-validated fields, giving you runtime type safety for free. |
| **Metadata-driven components** | `ComponentMeta` carries kind, tags, branching key and arbitrary extras — no need to inspect component internals. |
| **Conditional flows** | `FlowEdge` supports optional predicates so flows can branch based on runtime output. |
| **Plugin registry** | Third-party adapters register concrete `ISystem` implementations by name, so the CLI can discover and launch them without any code changes. |
| **Structured CLI** | Every outcome is emitted as a machine-readable JSON line — perfect for AI orchestrators and CI/CD pipelines. |
| **Interactive TUI** | A Textual-based terminal dashboard lets you monitor flow progress and memory usage in real time. |

---

## Quick look

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from aptdata.core import (
    BaseDataset, IDataset,
    BaseComponent, ComponentMeta, ComponentKind,
    BaseFlow, BaseSystem, IFlow,
)

@pydantic_dataclass
class MemoryDataset(BaseDataset):
    def __post_init__(self): self._data = None
    def read(self): return self._data
    def write(self, data): self._data = data


@pydantic_dataclass
class FilterComponent(BaseComponent):
    """Keep only rows where 'active' is truthy."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return len(inputs) == 1

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        rows = inputs[0].read()
        out = MemoryDataset(uri="memory://filtered")
        out.write([r for r in rows if r.get("active")])
        return [out]
```

---

## Navigation

- 🚀 [Getting Started](getting-started.md) — install and run your first system
- 🏛 [Architecture](architecture.md) — understand the `I*` → `Base*` design
- ⚙️ [Transform Engines](transform-engines.md) — pandas & PySpark wrappers
- ✅ [Data Quality](quality.md) — schema contracts & expectations
- 🏗 [Governance](governance.md) — lineage, catalog & classification
- 🧩 [Scaffold Templates](scaffold-templates.md) — project bootstrapping
- 📡 [Telemetry](telemetry.md) — OpenTelemetry integration
- 🤖 [MCP Server](mcp.md) — AI agent integration
- ⚙️ [Configuration](configuration.md) — YAML config files
- 📖 [API Reference](api/core.md) — full class and method documentation
- 📋 [Changelog](changelog.md) — version history
