# CLI Interactive Wizard

The `smart-data interactive` command launches a guided menu-driven wizard that
exposes all framework capabilities without requiring knowledge of the full
command tree.

---

## Starting the wizard

```bash
smart-data interactive
```

The wizard uses [questionary](https://github.com/tmbo/questionary) for
interactive prompts when it is installed.  It gracefully falls back to plain
`typer.prompt()` / `typer.confirm()` if questionary is not available.

---

## Main menu

```
What would you like to do?
  🚀 Run a registered system
  📋 List systems / plugins
  🔍 Inspect a plugin
  📝 Config (validate / run YAML)
  🏗️  Scaffold a new project
  ⚙️  Telemetry status
  ❌ Exit
```

---

## Wizard flows

### 🚀 Run

1. Select a registered system from the registry
2. Choose an environment: `dev`, `staging`, or `prod`
3. Confirm dry-run (yes → skip execution, no → call `run()`)
4. Execute and stream Rich live output

### 📋 List

1. Choose what to list: Systems / Readers / Writers / All plugins
2. View a Rich table
3. Optionally inspect a specific item

### 🔍 Inspect

1. Select a plugin from the registered readers + writers
2. View the constructor argument schema in a Rich table

### 📝 Config

1. Choose: Load existing YAML or generate a template
2. Validate the file (reports errors with context)
3. Preview the YAML content with syntax highlighting
4. Optionally run the system

### 🏗️ Scaffold

1. Enter the project name
2. Select a template: `hello-world`, `medallion`, `rag-ingestion`,
   `data-quality-test`
3. Enter the output directory (default: `.`)
4. Generate files and confirm success

### ⚙️ Telemetry

1. Show OpenTelemetry provider status
2. Optionally export telemetry as JSON

---

## Configuration

The wizard reuses the same rendering and logic as the static CLI commands,
so all output (tables, panels, syntax highlighting) is consistent.

### Disabling questionary

If you want to use plain prompts without the questionary dependency, simply
uninstall it:

```bash
pip uninstall questionary
```

The wizard will automatically fall back to `typer.prompt()`.
