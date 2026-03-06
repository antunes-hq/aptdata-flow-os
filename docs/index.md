# smart-data

**smart-data** is a declarative, extensible framework for building smart data
pipelines in Python.  It provides a clean two-layer contract system —
lightweight `I*` interfaces defined as dataclasses and `Base*` classes backed
by Pydantic validation — so you can build, test and compose data pipelines with
confidence.

---

## Key features

| Feature | Description |
|---|---|
| **Contract-first design** | Pure-Python `@dataclass + ABC` interfaces (`IDataset`, `IStep`, `IPipeline`) make the expected behaviour explicit before any concrete code is written. |
| **Pydantic-validated base classes** | `BaseDataset`, `BaseStep` and `BasePipeline` extend the interfaces and add Pydantic-validated fields, giving you runtime type safety for free. |
| **Plugin registry** | Third-party adapters (Spark, REST, databases, …) register concrete pipeline implementations by name, so the CLI can discover and launch them without any code changes. |
| **Structured CLI** | Every outcome is emitted as a machine-readable JSON line — perfect for AI orchestrators and CI/CD pipelines. |
| **Interactive TUI** | A Textual-based terminal dashboard lets you monitor DAG progress and memory usage in real time. |

---

## Quick look

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import BaseDataset, BaseStep, BasePipeline, IDataset

@pydantic_dataclass
class CsvDataset(BaseDataset):
    """A simple CSV-backed dataset."""

    def __post_init__(self) -> None:
        self._data = None

    def read(self):
        import csv, pathlib
        self._data = list(csv.DictReader(pathlib.Path(self.uri).open()))
        return self._data

    def write(self, data) -> None:
        self._data = data


@pydantic_dataclass
class FilterStep(BaseStep):
    """Keep only rows whose 'active' field is truthy."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return len(inputs) == 1

    def execute(self, inputs: list[IDataset]) -> IDataset:
        rows = inputs[0].read()
        out = CsvDataset(uri="/tmp/filtered.csv")
        out.write([r for r in rows if r.get("active")])
        return out
```

---

## Navigation

- 🚀 [Getting Started](getting-started.md) — install and run your first pipeline
- 🏛 [Architecture](architecture.md) — understand the `I*` → `Base*` design
- 📖 [API Reference](api/core.md) — full class and method documentation
- 📋 [Changelog](changelog.md) — version history
