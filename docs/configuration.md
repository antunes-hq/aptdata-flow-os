# Configuration

smart-data supports declarative pipeline configuration via a `smart-data.yaml`
file, allowing you to define, validate, and run pipelines without writing any
Python bootstrap code.

---

## File format

The configuration file follows this top-level schema:

```yaml
version: "1"           # config schema version (required)
env: dev               # target environment (default: dev)

systems:
  - name: my_system    # matches the name used in registry.register()
    enabled: true      # set to false to skip during config run

plugins:
  - module: my_package.systems  # Python module to import before resolving systems

telemetry:
  enabled: true
  exporter: console    # console | otlp
  endpoint: ""         # OTLP endpoint (when exporter: otlp)
```

### Minimal example

```yaml
version: "1"
env: production

plugins:
  - module: my_project.systems

systems:
  - name: etl_pipeline
    enabled: true
  - name: quality_checks
    enabled: true
```

---

## CLI commands

### `config validate`

Validate a `smart-data.yaml` file against the schema without running anything:

```bash
smart-data config validate smart-data.yaml
```

### `config init`

Generate a starter `smart-data.yaml` in the current directory:

```bash
smart-data config init
smart-data config init --output /path/to/smart-data.yaml
```

### `config show`

Pretty-print the resolved configuration (after environment variable substitution):

```bash
smart-data config show smart-data.yaml
```

### `config run`

Load the configuration file and execute all enabled systems:

```bash
smart-data config run smart-data.yaml
smart-data config run smart-data.yaml --env production
```

---

## Environment variable substitution

Values in the YAML file can reference environment variables using the
`${VAR_NAME}` syntax:

```yaml
telemetry:
  endpoint: "${OTEL_EXPORTER_OTLP_ENDPOINT}"
```

---

## Scaffold templates

The `scaffold` command generates a `smart-data.yaml` as part of the project
skeleton.  For example:

```bash
smart-data scaffold my_project --template medallion
# creates my_project/smart-data.yaml with a pre-filled configuration
```

See [Scaffold Templates](scaffold-templates.md) for all available templates.

---

## Further reading

- [Getting Started](getting-started.md) — run your first system
- [API Reference – CLI](api/cli.md) — full CLI reference
- [Scaffold Templates](scaffold-templates.md) — project bootstrapping
