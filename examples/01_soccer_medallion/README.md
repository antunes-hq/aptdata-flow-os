# 01 Soccer Medallion Pipeline

This is an example scaffold implementing a Medallion Architecture data pipeline using the `aptdata` framework.

The example demonstrates two approaches for creating pipelines:

1. **Object-Oriented Architecture (`system_oo.py`)**: Demonstrates the core, robust approach using classes inheriting from `BaseSystem`, `BaseFlow`, and `BaseComponent`. Enforces data contracts via Pydantic and relies heavily on Dependency Injection and strict boundaries.

2. **Declarative YAML & Functional Architecture (`run_yaml.py`, `pipeline.yaml`, `components_func.py`)**: Demonstrates a cleaner, functional Developer Experience (DX). Data Engineers can define simple logic wrapped in `@component` decorators and orchestrate the flow dynamically via a `pipeline.yaml` configuration file.

## Running the Examples

Ensure you have installed the project via `poetry install --with dev`.

### Running Object-Oriented Way

```bash
poetry run python examples/01_soccer_medallion/system_oo.py
```

### Running Declarative YAML Way

```bash
poetry run python examples/01_soccer_medallion/run_yaml.py
```
