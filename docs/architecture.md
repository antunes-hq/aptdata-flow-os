# Architecture

smart-data is built around a **two-layer contract system** that cleanly
separates the *behavioural contract* (what a type must do) from the *data
contract* (what fields it carries).

---

## The two layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 – Interfaces (I*)                                  │
│  @dataclass + ABC                                           │
│                                                             │
│  IDataset      IStep          IPipeline                     │
│  ─────────     ──────────     ────────────────              │
│  read()        validate_inputs()  register_step()           │
│  write()       execute()          compile_dag()             │
│                                   run()                     │
└─────────────────────────────────────────────────────────────┘
            │                   │                   │
            ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 – Base classes (Base*)                             │
│  @pydantic_dataclass                                        │
│                                                             │
│  BaseDataset   BaseStep       BasePipeline                  │
│  ─────────     ──────────     ────────────────              │
│  uri: str      step_id: str   (no extra fields)             │
│  schema_metadata: dict                                      │
└─────────────────────────────────────────────────────────────┘
            │                   │                   │
            ▼                   ▼                   ▼
        Your concrete implementations
```

---

## Layer 1 – `I*` interfaces

Each `I*` class is a plain Python `@dataclass` that also inherits from `ABC`.
It declares **only abstract methods** — no fields, no implementation.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class IDataset(ABC):
    @abstractmethod
    def read(self) -> Any: ...

    @abstractmethod
    def write(self, data: Any) -> None: ...
```

**Why dataclasses?**

- Standard-library, zero external dependencies for the interface layer.
- ABCMeta enforcement: instantiating an `I*` class directly (without
  implementing all abstract methods) raises `TypeError` at runtime.
- IDE-friendly: tools understand `@dataclass` semantics and generate
  accurate completions.

---

## Layer 2 – `Base*` classes

Each `Base*` class uses Pydantic's `@pydantic_dataclass` decorator and
inherits from the corresponding `I*` interface.  It adds **validated fields**
but still does not implement the abstract methods, so it remains uninstantiable
on its own.

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from dataclasses import field
from typing import Any

@pydantic_dataclass
class BaseDataset(IDataset):
    uri: str
    schema_metadata: dict[str, Any] = field(default_factory=dict)
```

**Why Pydantic dataclasses?**

- Field validation (type coercion, constraints) at construction time.
- Compatible with Pydantic's ecosystem (serialisation, settings, etc.).
- Still a real Python dataclass under the hood, so `isinstance` checks and
  `dataclasses.fields()` work as expected.

---

## Concrete implementations

Users (and adapter packages) inherit from the `Base*` classes and implement
the remaining abstract methods:

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import BaseDataset, IDataset

@pydantic_dataclass
class ParquetDataset(BaseDataset):
    """Reads and writes Parquet files using pandas."""

    def __post_init__(self) -> None:
        self._df = None  # private mutable state lives here

    def read(self):
        import pandas as pd
        self._df = pd.read_parquet(self.uri)
        return self._df

    def write(self, data) -> None:
        data.to_parquet(self.uri, index=False)
        self._df = data
```

!!! tip "Private state"
    Use `__post_init__` to initialise private attributes.  Pydantic validates
    only the declared dataclass fields; everything assigned in `__post_init__`
    is treated as a plain Python attribute.

---

## Plugin registry

Concrete pipeline implementations are registered by name in the global
`registry` singleton:

```
smart_data.plugins.registry
       │
       ├── "pipeline_a"  →  PipelineA (class)
       ├── "pipeline_b"  →  PipelineB (class)
       └── ...
```

The CLI calls `registry.get(name)` to resolve a name to a class, instantiates
it, compiles the DAG, and calls `run()`.

```
CLI  ──▶  registry.get("pipeline_x")
                │
                ▼
          PipelineX()
                │
                ├── compile_dag()
                └── run()
```

---

## Data-flow through a pipeline

```
Input Dataset(s)
      │
      ▼
  Step 1 – validate_inputs() → execute() → Output Dataset
                                                  │
                                                  ▼
                                           Step 2 – ...
                                                  │
                                                  ▼
                                            Final Dataset
```

Each step is responsible for validating its own inputs, executing its
transformation, and returning a new dataset.  This makes steps **independently
testable** without a full pipeline context.

---

## Monitoring (TUI)

The `smart-data monitor` command launches a
[Textual](https://textual.textualize.io/)-based terminal dashboard that
displays:

- An ASCII representation of the pipeline DAG.
- A per-step status table (pending / running / done).
- A memory-usage bar (uses `psutil` when available, falls back to
  `/proc/meminfo`).
