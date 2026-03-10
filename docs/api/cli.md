# CLI Reference

The `aptdata` command-line interface emits **structured JSON** on every
outcome, making it suitable for use inside AI orchestrators, CI/CD pipelines
and shell scripts.

---

## `aptdata run`

Run a registered pipeline by name.

```
aptdata run PIPELINE [OPTIONS]
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
aptdata run my_pipeline

# Run against production
aptdata run my_pipeline --env prod

# Validate without executing
aptdata run my_pipeline --dry-run

# Capture and parse JSON output with jq
aptdata run my_pipeline | jq '.elapsed_seconds'
```

---

## `aptdata monitor`

Launch the interactive TUI monitoring dashboard.

```
aptdata monitor [OPTIONS]
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
aptdata monitor

# Faster refresh for high-frequency pipelines
aptdata monitor --refresh 0.25
```

---

---

## `aptdata system`

Inspect and validate registered systems.

### `aptdata system list [--json]`

List all systems in the plugin registry.

```bash
aptdata system list
aptdata system list --json
```

### `aptdata system info NAME [--json]`

Show detailed info about a registered system (class name, module, docstring).

```bash
aptdata system info my_pipeline
aptdata system info my_pipeline --json
```

### `aptdata system validate NAME`

Instantiate the system and compile all its flows without executing.

```bash
aptdata system validate my_pipeline
```

---

## `aptdata plugin`

Manage and inspect registered reader / writer plugins.

### `aptdata plugin list [--json]`

List all registered readers and writers.

```bash
aptdata plugin list
aptdata plugin list --json
```

### `aptdata plugin inspect NAME [--json]`

Show constructor argument schema for a plugin.

```bash
aptdata plugin inspect csv_reader
aptdata plugin inspect csv_reader --json
```

### `aptdata plugin preview READER [--limit N]`

Execute a reader and display the first N records (default: 5).

```bash
aptdata plugin preview csv_reader --limit 10
```

### `aptdata plugin load MODULE_PATH`

Dynamically import a Python module (for plugin discovery).

```bash
aptdata plugin load my_package.plugins
```

---

## `aptdata config`

Manage declarative YAML pipeline configurations.

### `aptdata config validate PATH`

Parse and validate a YAML config file.

```bash
aptdata config validate pipeline.yaml
```

### `aptdata config init [--output PATH]`

Generate a starter YAML configuration template.

```bash
aptdata config init
aptdata config init --output my_pipeline.yaml
```

### `aptdata config show PATH`

Pretty-print a YAML config file with syntax highlighting.

```bash
aptdata config show pipeline.yaml
```

### `aptdata config run PATH [--env ENV]`

Parse a YAML config, register the system, and execute it.

```bash
aptdata config run pipeline.yaml
aptdata config run pipeline.yaml --env prod
```

---

## `aptdata telemetry`

Inspect OpenTelemetry telemetry configuration.

### `aptdata telemetry status [--json]`

Show whether OpenTelemetry is configured and the active tracer provider.

```bash
aptdata telemetry status
aptdata telemetry status --json
```

### `aptdata telemetry export [--format json]`

Export collected telemetry spans/metrics as JSON.

```bash
aptdata telemetry export
aptdata telemetry export --format json
```

---

## `aptdata interactive`

Launch the guided interactive wizard.

```bash
aptdata interactive
```

See [CLI Interactive Wizard](cli-interactive.md) for full documentation.

---

## App module

::: aptdata.cli.app
    options:
      members:
        - run
        - monitor
