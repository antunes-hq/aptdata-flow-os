# Core API

The `smart_data.core` package exposes the two-layer contract system for all
four foundational types.

---

## Dataset

### `IDataset`

::: smart_data.core.dataset.IDataset

---

### `BaseDataset`

::: smart_data.core.dataset.BaseDataset

---

## Component

### `ComponentKind`

::: smart_data.core.system.ComponentKind

---

### `ComponentMeta`

::: smart_data.core.system.ComponentMeta

---

### `IComponent`

::: smart_data.core.system.IComponent

---

### `BaseComponent`

::: smart_data.core.system.BaseComponent

---

## Flow

### `FlowEdge`

::: smart_data.core.system.FlowEdge

---

### `FlowNode`

::: smart_data.core.system.FlowNode

---

### `IFlow`

::: smart_data.core.system.IFlow

---

### `BaseFlow`

::: smart_data.core.system.BaseFlow

---

## System

### `ISystem`

::: smart_data.core.system.ISystem

---

### `BaseSystem`

::: smart_data.core.system.BaseSystem

---

## Quick-import

All names are re-exported from the top-level `smart_data.core` package:

```python
from smart_data.core import (
    IDataset, BaseDataset,
    ComponentKind, ComponentMeta,
    IComponent,   BaseComponent,
    FlowEdge,     FlowNode,
    IFlow,        BaseFlow,
    ISystem,      BaseSystem,
)
```
