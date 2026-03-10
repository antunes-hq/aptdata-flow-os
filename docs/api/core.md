# Core API

The `aptdata.core` package exposes the two-layer contract system for all
four foundational types.

---

## Dataset

### `IDataset`

::: aptdata.core.dataset.IDataset

---

### `BaseDataset`

::: aptdata.core.dataset.BaseDataset

---

## Component

### `ComponentKind`

::: aptdata.core.system.ComponentKind

---

### `ComponentMeta`

::: aptdata.core.system.ComponentMeta

---

### `IComponent`

::: aptdata.core.system.IComponent

---

### `BaseComponent`

::: aptdata.core.system.BaseComponent

---

## Flow

### `FlowEdge`

::: aptdata.core.system.FlowEdge

---

### `FlowNode`

::: aptdata.core.system.FlowNode

---

### `IFlow`

::: aptdata.core.system.IFlow

---

### `BaseFlow`

::: aptdata.core.system.BaseFlow

---

## System

### `ISystem`

::: aptdata.core.system.ISystem

---

### `BaseSystem`

::: aptdata.core.system.BaseSystem

---

## Quick-import

All names are re-exported from the top-level `aptdata.core` package:

```python
from aptdata.core import (
    IDataset, BaseDataset,
    ComponentKind, ComponentMeta,
    IComponent,   BaseComponent,
    FlowEdge,     FlowNode,
    IFlow,        BaseFlow,
    ISystem,      BaseSystem,
)
```
