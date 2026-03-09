# CLI Reference

The `smart-data` command-line interface emits **structured JSON** on every
outcome, making it suitable for use inside AI orchestrators, CI/CD pipelines
and shell scripts.

---

## `smart-data run`

Run a registered pipeline by name.

```
smart-data run PIPELINE [OPTIONS]
```

### Arguments

| Name | Required | Description |
|------|----------|-------------|
| `PIPELINE` | ✅ | Pipeline identifier registered in the plugin registry |

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--env`, `-e` | `dev` | Target execution environment label (e.g. `dev`, `staging`, `prod`) |
| `--dry-run` | `false` | Compile and validate the pipeline without executing `run()` |
| `--help` | | Show help and exit |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Pipeline completed successfully |
| `1` | An error occurred (pipeline not found, runtime exception, etc.) |

### JSON events

**`pipeline.started`** – emitted immediately after the CLI receives the
command:

```json
{
  "event": "pipeline.started",
  "pipeline": "my_pipeline",
  "env": "prod",
  "dry_run": false
}
```

**`pipeline.completed`** – emitted when the pipeline finishes successfully:

```json
{
  "event": "pipeline.completed",
  "pipeline": "my_pipeline",
  "env": "prod",
  "dry_run": false,
  "elapsed_seconds": 1.234
}
```

**`pipeline.error`** – emitted to *stderr* when an error occurs:

```json
{
  "event": "pipeline.error",
  "pipeline": "my_pipeline",
  "env": "prod",
  "error": "Pipeline 'my_pipeline' not found in registry.",
  "elapsed_seconds": 0.001
}
```

### Examples

```bash
# Run in the default dev environment
smart-data run my_pipeline

# Run against production
smart-data run my_pipeline --env prod

# Validate without executing
smart-data run my_pipeline --dry-run

# Capture and parse JSON output with jq
smart-data run my_pipeline | jq '.elapsed_seconds'
```

---

## `smart-data monitor`

Launch the interactive TUI monitoring dashboard.

```
smart-data monitor [OPTIONS]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--refresh`, `-r` | `1.0` | Dashboard auto-refresh interval in seconds |
| `--help` | | Show help and exit |

### Key bindings

| Key | Action |
|-----|--------|
| `r` | Manually refresh all panels |
| `q` / `Ctrl+C` | Quit |

### Examples

```bash
# Open with default 1-second refresh
smart-data monitor

# Faster refresh for high-frequency pipelines
smart-data monitor --refresh 0.25
```

---

---

## `smart-data system`

Inspect and validate registered systems.

### `smart-data system list [--json]`

List all systems in the plugin registry.

```bash
smart-data system list
smart-data system list --json
```

### `smart-data system info NAME [--json]`

Show detailed info about a registered system (class name, module, docstring).

```bash
smart-data system info my_pipeline
smart-data system info my_pipeline --json
```

### `smart-data system validate NAME`

Instantiate the system and compile all its flows without executing.

```bash
smart-data system validate my_pipeline
```

---

## `smart-data plugin`

Manage and inspect registered reader / writer plugins.

### `smart-data plugin list [--json]`

List all registered readers and writers.

```bash
smart-data plugin list
smart-data plugin list --json
```

### `smart-data plugin inspect NAME [--json]`

Show constructor argument schema for a plugin.

```bash
smart-data plugin inspect csv_reader
smart-data plugin inspect csv_reader --json
```

### `smart-data plugin preview READER [--limit N]`

Execute a reader and display the first N records (default: 5).

```bash
smart-data plugin preview csv_reader --limit 10
```

### `smart-data plugin load MODULE_PATH`

Dynamically import a Python module (for plugin discovery).

```bash
smart-data plugin load my_package.plugins
```

---

## `smart-data config`

Manage declarative YAML pipeline configurations.

### `smart-data config validate PATH`

Parse and validate a YAML config file.

```bash
smart-data config validate pipeline.yaml
```

### `smart-data config init [--output PATH]`

Generate a starter YAML configuration template.

```bash
smart-data config init
smart-data config init --output my_pipeline.yaml
```

### `smart-data config show PATH`

Pretty-print a YAML config file with syntax highlighting.

```bash
smart-data config show pipeline.yaml
```

### `smart-data config run PATH [--env ENV]`

Parse a YAML config, register the system, and execute it.

```bash
smart-data config run pipeline.yaml
smart-data config run pipeline.yaml --env prod
```

---

## `smart-data telemetry`

Inspect OpenTelemetry telemetry configuration.

### `smart-data telemetry status [--json]`

Show whether OpenTelemetry is configured and the active tracer provider.

```bash
smart-data telemetry status
smart-data telemetry status --json
```

### `smart-data telemetry export [--format json]`

Export collected telemetry spans/metrics as JSON.

```bash
smart-data telemetry export
smart-data telemetry export --format json
```

---

## `smart-data interactive`

Launch the guided interactive wizard.

```bash
smart-data interactive
```

See [CLI Interactive Wizard](cli-interactive.md) for full documentation.

---

## App module

::: smart_data.cli.app
    options:
      members:
        - run
        - monitor
