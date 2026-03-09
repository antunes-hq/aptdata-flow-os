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
# {"event": "pipeline.started", "pipeline": "my_system", "env": "dev", "dry_run": false, "trace_id": null}
# {"event": "pipeline.completed", "pipeline": "my_system", "env": "dev", "dry_run": false, "elapsed_seconds": 0.001, "trace_id": null}
```

---

## CLI reference

```
smart-data run SYSTEM_NAME [--env ENV] [--dry-run]
smart-data monitor [--refresh SECONDS]
smart-data scaffold PROJECT_NAME [--template TEMPLATE] [--output PATH]
smart-data schema export --output schema.json
smart-data system list [--json]
smart-data system info NAME [--json]
smart-data system validate NAME
smart-data plugin list [--json]
smart-data plugin inspect NAME [--json]
smart-data plugin preview READER [--limit N]
smart-data plugin load MODULE_PATH
smart-data config validate PATH
smart-data config init [--output PATH]
smart-data config show PATH
smart-data config run PATH [--env ENV]
smart-data telemetry status [--json]
smart-data telemetry export [--format json]
smart-data interactive
```

Every static command supports `--json` for machine-readable JSON line output
(backward compatible). Without `--json`, commands render Rich tables, panels,
and syntax-highlighted output.

### Scaffold templates

| Template            | Description                                         |
|---------------------|-----------------------------------------------------|
| `hello-world`       | Minimal pandas pipeline (default)                   |
| `medallion`         | Bronze → Silver → Gold data lakehouse               |
| `rag-ingestion`     | RAG pipeline: extract → chunk → embed → load        |
| `data-quality-test` | Schema contract + expectation suite                  |

```bash
smart-data scaffold my_lakehouse --template medallion
```

---

## Processing Engines

Engine-agnostic transformation wrappers for pandas and PySpark:

```python
from smart_data.plugins.transform import PandasTransformer

def clean(df):
    return df.dropna().drop_duplicates()

transformer = PandasTransformer("clean", clean)
result = transformer.transform(my_dataset)
```

See [Transform Engines docs](docs/transform-engines.md) for PySpark usage.

---

## Data Quality & Contracts

```python
from smart_data.plugins.quality import (
    EnforcementMode, ExpectColumnToNotBeNull,
    QualityValidator, SchemaContract,
)

validator = QualityValidator(
    expectations=[ExpectColumnToNotBeNull("id")],
    enforcement=EnforcementMode.ABORT,
)
clean_data = validator.validate(raw_df)
```

See [Quality docs](docs/quality.md) for all built-in expectations.

---

## Data Governance

```python
from smart_data.plugins.governance import (
    BusinessRule, DatasetCatalog, DatasetCatalogEntry, LineageStore,
)
from smart_data.core.lineage import LineageGraph, LineageNode, LineageEventType

# Lineage tracking
graph = LineageGraph(run_id="run-1", workflow_name="etl")
graph.add_node(LineageNode(dataset_uri="s3://raw/data", event_type=LineageEventType.READ))

store = LineageStore()
store.save(graph)
```

See [Governance docs](docs/governance.md) for the full API.

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
