# Getting Started

## Requirements

- Python ≥ 3.10
- [Poetry](https://python-poetry.org/) (recommended) **or** pip

---

## Installation

### From source (development)

```bash
git clone https://github.com/strondata/smart-data.git
cd smart-data
poetry install
```

### With pip (once published to PyPI)

```bash
pip install smart-data
```

---

## Verifying the installation

```bash
smart-data --help
```

You should see output like:

```
Usage: smart-data [OPTIONS] COMMAND [ARGS]...

  Smart Data – declarative data-pipeline framework.

Options:
  --help  Show this message and exit.

Commands:
  monitor  Open the interactive TUI monitoring dashboard.
  run      Run a registered data pipeline.
```

---

## Writing your first pipeline

### 1. Create a dataset

A dataset is a Pydantic-validated dataclass that knows how to read and write
data.  Inherit from [`BaseDataset`](api/core.md) and implement `read` /
`write`:

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import BaseDataset, IDataset


@pydantic_dataclass
class MemoryDataset(BaseDataset):
    """In-memory dataset for testing."""

    def __post_init__(self) -> None:
        self._data = None

    def read(self):
        return self._data

    def write(self, data) -> None:
        self._data = data
```

### 2. Create a step

A step receives a list of `IDataset` objects, validates them and returns a
single `IDataset` output.  Inherit from [`BaseStep`](api/core.md) and
implement `validate_inputs` / `execute`:

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import BaseStep, IDataset


@pydantic_dataclass
class DoubleStep(BaseStep):
    """Double every numeric value in the input list."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return len(inputs) == 1

    def execute(self, inputs: list[IDataset]) -> IDataset:
        data = inputs[0].read()
        out = MemoryDataset(uri="memory://output")
        out.write([x * 2 for x in data])
        return out
```

### 3. Create a pipeline

A pipeline wires datasets and steps together.  Inherit from
[`BasePipeline`](api/core.md) and implement `register_step`, `compile_dag`
and `run`:

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from smart_data.core import BasePipeline, IStep, IDataset


@pydantic_dataclass
class SimplePipeline(BasePipeline):
    def __post_init__(self) -> None:
        self._steps: list[IStep] = []

    def register_step(self, step: IStep) -> None:
        self._steps.append(step)

    def compile_dag(self) -> None:
        pass  # validate DAG here

    def run(self) -> None:
        ds = MemoryDataset(uri="memory://input")
        ds.write([1, 2, 3])
        inputs: list[IDataset] = [ds]
        for step in self._steps:
            if step.validate_inputs(inputs):
                inputs = [step.execute(inputs)]
```

### 4. Register and run via the CLI

```python
# my_pipelines.py
from smart_data.plugins import registry
registry.register("my_pipeline", SimplePipeline)
```

```bash
smart-data run my_pipeline
```

Expected output:

```json
{"event": "pipeline.started", "pipeline": "my_pipeline", "env": "dev", "dry_run": false}
{"event": "pipeline.completed", "pipeline": "my_pipeline", "env": "dev", "dry_run": false, "elapsed_seconds": 0.001}
```

---

## CLI options

### `smart-data run`

| Option | Default | Description |
|---|---|---|
| `pipeline` | *(required)* | Pipeline name registered in the plugin registry |
| `--env`, `-e` | `dev` | Target execution environment label |
| `--dry-run` | `false` | Compile and validate without executing |

### `smart-data monitor`

| Option | Default | Description |
|---|---|---|
| `--refresh`, `-r` | `1.0` | Dashboard auto-refresh interval (seconds) |

---

## Running the test suite

```bash
make test
# or
poetry run pytest tests/ -v
```
