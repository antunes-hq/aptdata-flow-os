# smart-data

> **v0.0.2** · A declarative, extensible framework for building smart data pipelines in Python.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.0.2-orange)](CHANGELOG.md)

---

## Overview

**smart-data** is built around three universal abstractions — **System**,
**Flow**, and **Component** — that cover every data-processing paradigm in a
single, coherent model:

```
IComponent / IFlow / ISystem       ← @dataclass + ABC  (pure interfaces)
         ↓
BaseComponent / BaseFlow / BaseSystem  ← @pydantic_dataclass  (validated fields)
         ↓
Your concrete implementations
```

Datasets remain the fundamental data-exchange contract (`IDataset` /
`BaseDataset`).  Every outcome from the CLI is emitted as a machine-readable
JSON line, making smart-data a natural fit for AI orchestrators, CI/CD
pipelines and scripted workflows.

---

## Requirements

- Python ≥ 3.10
- [Poetry](https://python-poetry.org/) (for development)

---

## Installation

```bash
git clone https://github.com/strondata/smart-data.git
cd smart-data
poetry install
```

---

## Quick start

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import (
    BaseDataset, IDataset,
    BaseComponent, ComponentMeta, ComponentKind,
    BaseFlow, IFlow,
    BaseSystem,
)

@pydantic_dataclass
class MemoryDataset(BaseDataset):
    def __post_init__(self): self._data = None
    def read(self): return self._data
    def write(self, data): self._data = data

@pydantic_dataclass
class DoubleComponent(BaseComponent):
    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return len(inputs) == 1
    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        out = MemoryDataset(uri="memory://out")
        out.write([x * 2 for x in inputs[0].read()])
        return [out]

@pydantic_dataclass
class ETLFlow(BaseFlow):
    def __post_init__(self):
        self._nodes = {}
        self._edges = []
        self._compiled = False
    def add_component(self, c): self._nodes[c.component_id] = c
    def connect(self, src, tgt, condition=None): ...
    def compile(self): self._compiled = True
    def run(self, inputs): return inputs  # wire your logic here

@pydantic_dataclass
class MySystem(BaseSystem):
    def __post_init__(self): self._flows: list[IFlow] = []
    def register_flow(self, flow): self._flows.append(flow)
    def run(self):
        for flow in self._flows:
            flow.run([])

# Register and run via CLI
from smart_data.plugins import registry
registry.register("my_system", MySystem)
```

```bash
smart-data run my_system
# {"event": "pipeline.started", "pipeline": "my_system", "env": "dev", "dry_run": false}
# {"event": "pipeline.completed", "pipeline": "my_system", "env": "dev", "dry_run": false, "elapsed_seconds": 0.001}
```

---

## CLI reference

```
smart-data run SYSTEM_NAME [--env ENV] [--dry-run]
smart-data monitor [--refresh SECONDS]
smart-data scaffold PROJECT_NAME [--output PATH]
smart-data schema export --output schema.json
```

---

## Development

```bash
make install   # install all dependencies
make test      # run the test suite
make lint      # lint with ruff
make docs      # build the documentation
```

---

## Documentation

Full documentation is available in the [`docs/`](docs/) directory and can be
served locally with:

```bash
mkdocs serve
```

---

## License

[MIT](LICENSE)
