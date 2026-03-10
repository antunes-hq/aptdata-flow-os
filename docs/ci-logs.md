# CI & Execution Logs

**aptdata** is designed to integrate seamlessly into CI/CD pipelines. Because every execution log and command output can be formatted as structured JSON lines (`--json`), it becomes incredibly easy to capture, parse, and analyze the results of your data pipelines within automated workflows.

## GitHub Actions Example

Here is a complete example of how you can run an `aptdata` system inside a GitHub Actions workflow. This workflow sets up Python, installs the project dependencies, and runs the data pipeline.

```yaml title=".github/workflows/data-pipeline.yml"
name: Run Data Pipeline

on:
  push:
    branches: [ "main" ]
  schedule:
    # Run daily at midnight
    - cron: '0 0 * * *'

jobs:
  run-pipeline:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.10
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install aptdata

    - name: Run aptdata system
      run: |
        # Run the system named "my_system" and output structured JSON logs
        aptdata run my_system --json > pipeline_run.json

    - name: Archive execution logs
      uses: actions/upload-artifact@v3
      with:
        name: aptdata-execution-logs
        path: pipeline_run.json
```

## Realistic Execution Logs

When you run `aptdata` with the `--json` flag, it emits structured NDJSON (Newline Delimited JSON) logs. This is perfect for machine readability.

Here is an example of what the execution logs might look like when running a system:

```json title="pipeline_run.json"
{"event": "system.started", "system_name": "my_system", "env": "prod", "dry_run": false, "timestamp": "2023-10-27T10:00:00.000000Z"}
{"event": "flow.started", "flow_id": "extract_flow", "timestamp": "2023-10-27T10:00:00.050000Z"}
{"event": "component.started", "component_id": "postgres_extractor", "timestamp": "2023-10-27T10:00:00.100000Z"}
{"event": "component.completed", "component_id": "postgres_extractor", "elapsed_seconds": 2.45, "timestamp": "2023-10-27T10:00:02.550000Z"}
{"event": "component.started", "component_id": "data_validator", "timestamp": "2023-10-27T10:00:02.600000Z"}
{"event": "component.completed", "component_id": "data_validator", "elapsed_seconds": 0.82, "timestamp": "2023-10-27T10:00:03.420000Z"}
{"event": "flow.completed", "flow_id": "extract_flow", "elapsed_seconds": 3.42, "timestamp": "2023-10-27T10:00:03.470000Z"}
{"event": "flow.started", "flow_id": "transform_flow", "timestamp": "2023-10-27T10:00:03.500000Z"}
{"event": "component.started", "component_id": "pandas_transformer", "timestamp": "2023-10-27T10:00:03.550000Z"}
{"event": "component.completed", "component_id": "pandas_transformer", "elapsed_seconds": 5.12, "timestamp": "2023-10-27T10:00:08.670000Z"}
{"event": "flow.completed", "flow_id": "transform_flow", "elapsed_seconds": 5.22, "timestamp": "2023-10-27T10:00:08.720000Z"}
{"event": "system.completed", "system_name": "my_system", "env": "prod", "dry_run": false, "elapsed_seconds": 8.77, "timestamp": "2023-10-27T10:00:08.770000Z"}
```

## Standard CLI Output

If you run the CLI without the `--json` flag, you get rich, interactive console output powered by `Rich`, complete with progress bars and syntax highlighting.

```bash
$ aptdata run my_system

[10:00:00] INFO     System 'my_system' started in env 'prod'.
[10:00:00] INFO     Flow 'extract_flow' started.
[10:00:00] INFO     Component 'postgres_extractor' running...
[10:00:02] INFO     Component 'postgres_extractor' completed in 2.45s.
[10:00:02] INFO     Component 'data_validator' running...
[10:00:03] INFO     Component 'data_validator' completed in 0.82s.
[10:00:03] INFO     Flow 'extract_flow' completed in 3.42s.
[10:00:03] INFO     Flow 'transform_flow' started.
[10:00:03] INFO     Component 'pandas_transformer' running...
[10:00:08] INFO     Component 'pandas_transformer' completed in 5.12s.
[10:00:08] INFO     Flow 'transform_flow' completed in 5.22s.
[10:00:08] INFO     System 'my_system' completed successfully in 8.77s.
```
