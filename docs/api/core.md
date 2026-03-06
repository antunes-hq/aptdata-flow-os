# Core API

The `smart_data.core` package exposes the two-layer contract system.

---

## Interfaces

### `IDataset`

::: smart_data.core.dataset.IDataset

---

### `IStep`

::: smart_data.core.step.IStep

---

### `IPipeline`

::: smart_data.core.pipeline.IPipeline

---

## Base classes

### `BaseDataset`

::: smart_data.core.dataset.BaseDataset

---

### `BaseStep`

::: smart_data.core.step.BaseStep

---

### `BasePipeline`

::: smart_data.core.pipeline.BasePipeline

---

## Quick-import

All six names are re-exported from the top-level `smart_data.core` package:

```python
from smart_data.core import (
    IDataset, BaseDataset,
    IStep,    BaseStep,
    IPipeline, BasePipeline,
)
```
