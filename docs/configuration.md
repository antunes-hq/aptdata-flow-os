# Configuration

aptdata supports declarative pipeline configuration via a `aptdata.yaml`
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

Validate a `aptdata.yaml` file against the schema without running anything:

```bash
aptdata config validate aptdata.yaml
```

### `config init`

Generate a starter `aptdata.yaml` in the current directory:

```bash
aptdata config init
aptdata config init --output /path/to/aptdata.yaml
```

### `config show`

Pretty-print the resolved configuration (after environment variable substitution):

```bash
aptdata config show aptdata.yaml
```

### `config run`

Load the configuration file and execute all enabled systems:

```bash
aptdata config run aptdata.yaml
aptdata config run aptdata.yaml --env production
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

The `scaffold` command generates a `aptdata.yaml` as part of the project
skeleton.  For example:

```bash
aptdata scaffold my_project --template medallion
# creates my_project/aptdata.yaml with a pre-filled configuration
```

See [Scaffold Templates](scaffold-templates.md) for all available templates.

---

## Further reading

- [Getting Started](getting-started.md) — run your first system
- [API Reference – CLI](api/cli.md) — full CLI reference
- [Scaffold Templates](scaffold-templates.md) — project bootstrapping
