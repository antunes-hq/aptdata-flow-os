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

## App module

::: smart_data.cli.app
    options:
      members:
        - run
        - monitor
