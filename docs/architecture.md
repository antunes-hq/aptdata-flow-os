# Architecture

smart-data is built around a **two-layer contract system** for each of its
three universal abstractions — **Component**, **Flow**, and **System** — plus
the foundational **Dataset** type.

---

## The three-abstraction model

```
┌────────────────────────────────────────────────────────────────────┐
│  Abstraction   Purpose                                             │
│  ──────────    ────────────────────────────────────────────────── │
│  Component     A reusable unit of work (ETL step, filter, …)      │
│  Flow          A directed graph of Components                      │
│  System        Top-level orchestrator that owns one or more Flows  │
└────────────────────────────────────────────────────────────────────┘
```

---

## The two layers

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 1 – Interfaces (I*)                                               │
│  @dataclass + ABC                                                        │
│                                                                          │
│  IDataset      IComponent           IFlow              ISystem           │
│  ─────────     ──────────────────   ────────────────   ─────────────     │
│  read()        validate_inputs()    add_component()    register_flow()   │
│  write()       execute()            connect()          run()             │
│                meta (property)      compile()                            │
│                                     run()                                │
└──────────────────────────────────────────────────────────────────────────┘
             │               │                   │               │
             ▼               ▼                   ▼               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 2 – Base classes (Base*)                                          │
│  @pydantic_dataclass                                                     │
│                                                                          │
│  BaseDataset   BaseComponent        BaseFlow           BaseSystem        │
│  ─────────     ──────────────────   ────────────────   ─────────────     │
│  uri: str      component_id: str    flow_id: str       system_id: str    │
│  schema_meta…  metadata: CompMeta                                        │
└──────────────────────────────────────────────────────────────────────────┘
             │               │                   │               │
             ▼               ▼                   ▼               ▼
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
- ABCMeta enforcement: instantiating an `I*` class directly raises `TypeError`.
- IDE-friendly: tools understand `@dataclass` semantics.

---

## Layer 2 – `Base*` classes

Each `Base*` class uses Pydantic's `@pydantic_dataclass` decorator and
inherits from the corresponding `I*` interface.  It adds **validated fields**
but still does not implement the abstract methods.

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from dataclasses import field
from typing import Any

@pydantic_dataclass
class BaseDataset(IDataset):
    uri: str
    schema_metadata: dict[str, Any] = field(default_factory=dict)
```

---

## Concrete implementations

Users inherit from the `Base*` classes and implement the remaining abstract
methods:

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import BaseDataset, IDataset

@pydantic_dataclass
class ParquetDataset(BaseDataset):
    def __post_init__(self) -> None:
        self._df = None

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

## ComponentMeta & ComponentKind

Every `BaseComponent` carries a `ComponentMeta` instance that describes its
role, tags and branching behaviour:

```python
from smart_data.core import ComponentMeta, ComponentKind

meta = ComponentMeta(
    kind=ComponentKind.TRANSFORM,
    tags=["etl", "prod"],
    branch_on="status",          # field name used for conditional routing
    description="Doubles values",
    extra={"owner": "team-a"},
)
```

`ComponentKind` values: `TRANSFORM`, `FILTER`, `AGGREGATE`, `EXTRACT`,
`LOAD`, `CUSTOM`.

---

## Flow graph primitives

`FlowEdge` connects two components and can carry an optional predicate to
enable conditional / branching execution:

```python
from smart_data.core import FlowEdge

# Unconditional edge
FlowEdge(source_id="extract", target_id="transform")

# Conditional edge – only traversed when the predicate returns True
FlowEdge(source_id="transform", target_id="load",
         condition=lambda outputs: len(outputs) > 0)
```

`FlowNode` wraps a component inside a flow and keeps a back-reference to the
owning `IFlow`.

---

## Plugin registry

Concrete system implementations are registered by name in the global
`registry` singleton:

```
smart_data.plugins.registry
       │
       ├── "etl_system"  →  EtlSystem (class)
       ├── "ml_system"   →  MlSystem  (class)
       └── ...
```

The CLI calls `registry.get(name)` to resolve a name to a class, instantiates
it with `system_id=name`, and calls `run()`.

```
CLI  ──▶  registry.get("etl_system")
                │
                ▼
          EtlSystem(system_id="etl_system")
                │
                └── run()
```

---

## Data-flow through a system

```
Initial Dataset(s)
      │
      ▼
  Flow.compile()          ← validate graph structure
      │
      ▼
  Component 1  ─ validate_inputs() → execute() → [Dataset, …]
      │
      ▼  (FlowEdge, optional condition)
  Component 2  ─ validate_inputs() → execute() → [Dataset, …]
      │
      ▼
  Final Dataset(s)
```

Each component validates its own inputs, executes its transformation, and
returns a **list** of datasets (enabling multi-output / branching flows).

---

## Monitoring (TUI)

The `smart-data monitor` command launches a
[Textual](https://textual.textualize.io/)-based terminal dashboard that
displays:

- An ASCII representation of the flow graph.
- A per-component status table (pending / running / done).
- A memory-usage bar (uses `psutil` when available, falls back to
  `/proc/meminfo`).
