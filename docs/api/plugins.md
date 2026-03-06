# Plugins & Registry

The plugin registry lets external packages register concrete pipeline
implementations so the CLI can discover and instantiate them by name —
without any changes to the `smart-data` core.

---

## How it works

```
Your adapter package
        │
        │  from smart_data.plugins import registry
        │  registry.register("my_pipeline", MyPipeline)
        │
        ▼
smart_data.plugins.registry
        │
        │  registry.get("my_pipeline")  →  MyPipeline class
        │
        ▼
smart-data CLI
        smart-data run my_pipeline
```

---

## Registering a pipeline

```python
# my_package/pipelines.py
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import BasePipeline, IStep
from smart_data.plugins import registry


@pydantic_dataclass
class SalesPipeline(BasePipeline):
    def __post_init__(self) -> None:
        self._steps: list[IStep] = []

    def register_step(self, step: IStep) -> None:
        self._steps.append(step)

    def compile_dag(self) -> None:
        if not self._steps:
            raise ValueError("Pipeline has no steps.")

    def run(self) -> None:
        # Execute your steps here
        ...


# Register at import time so the CLI can find it
registry.register("sales_pipeline", SalesPipeline)
```

Then run it:

```bash
smart-data run sales_pipeline --env prod
```

---

## Auto-discovery with entry points

You can auto-register pipelines when your package is installed by declaring a
`smart_data.pipelines` entry-point group in your `pyproject.toml`:

```toml
[tool.poetry.plugins."smart_data.pipelines"]
sales_pipeline = "my_package.pipelines:SalesPipeline"
```

!!! note
    Built-in entry-point auto-discovery is planned for a future release.
    For now, call `registry.register()` explicitly at import time.

---

## `_PipelineRegistry` API

::: smart_data.plugins._PipelineRegistry

---

## Global singleton

::: smart_data.plugins.registry
