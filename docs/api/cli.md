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
  "dry_run": false,
  "trace_id": null
}
```

> Every JSON event carries a `trace_id` field — the current OpenTelemetry
> trace id when telemetry is configured, `null` otherwise.

**`pipeline.completed`** – emitted when the pipeline finishes successfully:

```json
{
  "event": "pipeline.completed",
  "pipeline": "my_pipeline",
  "env": "prod",
  "dry_run": false,
  "elapsed_seconds": 1.234,
  "trace_id": null
}
```

**`pipeline.error`** – emitted to *stderr* when an error occurs:

```json
{
  "event": "pipeline.error",
  "pipeline": "my_pipeline",
  "env": "prod",
  "error": "Pipeline 'my_pipeline' not found in registry.",
  "elapsed_seconds": 0.001,
  "trace_id": null
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

## `aptdata scaffold`

Generate a plug-and-play project from a template. Always emits JSON lines
(`scaffold.started` → `scaffold.completed`, errors as `scaffold.error` on
stderr with exit code 1).

```
aptdata scaffold PROJECT_NAME [--template TEMPLATE] [--output PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--template`, `-t` | `hello-world` | One of the templates in [Scaffold Templates](../scaffold-templates.md) |
| `--output`, `-o` | `.` | Directory in which the project folder is created |

```bash
aptdata scaffold my_lakehouse --template medallion
```

---

## `aptdata schema export`

Write the aptdata domain JSON Schema to disk. Emits
`schema.export.started` → `schema.export.completed` JSON lines.

```bash
aptdata schema export --output schema.json
```

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

## `aptdata plugins`

Discover plugins registered via [entry points](https://docs.python.org/3/library/importlib.metadata.html#entry-points) (ADR-002 §2.1).
Lists every entry point declared under the `aptdata.*` groups (`aptdata.agents`,
`aptdata.plugins`, `aptdata.systems`, `aptdata.components`, `aptdata.commands`) with
name, `module:attr` value, and load status. Broken plugins are surfaced with their
error instead of being hidden — this is the diagnostic surface promised by ADR-002 §4
("entry points tornam a origem menos óbvia; mitiga-se com `aptdata plugins`").

### `aptdata plugins list [--json]`

```bash
aptdata plugins list
aptdata plugins list --json
```

In `--json` mode, emits one JSON line per discovered entry point:

```json
{"group": "aptdata.agents", "name": "anthropic", "value": "aptdata.agents.anthropic:AnthropicAgent", "loaded": true, "error": null}
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

## `aptdata mesh`

Discover and run data-mesh components described by `mesh.yaml` manifests
(types: `job-wheel`, `docker-compose-app`).

### `aptdata mesh list [--dir DIR] [--json]`

Recursively find `mesh.yaml` manifests and list component name/type/version.

### `aptdata mesh run COMPONENT [--dir DIR] [--dry-run] [--json]`

Execute a component (`--dry-run` prints the command without running it).
Emits `mesh.run.started` / `mesh.run.completed` / `mesh.run.dry_run`;
failures emit `mesh.run.error` and exit 1.

### `aptdata mesh build COMPONENT [--dir DIR] [--json]`

Build a component (`pip wheel` / `docker compose build`), with the
equivalent `mesh.build.*` events.

```bash
aptdata mesh list --json
aptdata mesh run analytics-job --dry-run
```

---

## `aptdata agents`

Operate the multi-agent registry/router defined in `agents.yaml`
(override the file with `--file/-f` or `APTDATA_AGENTS_FILE`).

### `aptdata agents list [--file PATH] [--enabled] [--json]`

List registered agents (enabled first).

### `aptdata agents send AGENT_ID PROMPT [--file PATH] [--json]`

Send a prompt to a specific agent. JSON output is the full
`AgentResponse`: `{ok, agent_id, text, error, raw}`. Failure exits 1.

### `aptdata agents route TEXT [--file PATH] [--json]`

Show which agent *would* handle a prompt and why — prefix, skill, llm or
default — without sending. JSON output is the `RouteDecision`:
`{agent_id, mode, confidence, skill, matched_keyword, text}`.

### `aptdata agents dispatch TEXT [--file PATH] [--json]`

Route **and** send in one step. Exits 1 when no agent is available or the
send fails.

### `aptdata agents resolve CAPABILITY [--file PATH] [--json]`

Resolve the best enabled agent for a capability. No match prints
`{"agent": null}` and exits 1.

```bash
aptdata agents route "mexer no frontend" --json
aptdata agents dispatch "/zeca deploy do painel"
```

---

## `aptdata project`

Run multi-task projects (YAML) where every task is routed to an agent.

### `aptdata project init NAME [--out PATH] [--json]`

Scaffold a starter `NAME.project.yaml` (refuses to overwrite).

### `aptdata project plan PROJECT_FILE [--file PATH] [--json]`

Dry-run: show how each task would be routed, without sending.

### `aptdata project run PROJECT_FILE [--file PATH] [--json]`

Execute the project. JSON output is `{project, ok, total, results}` where
each result carries `{task_id, agent_id, mode, ok, text, skipped, error}`.
Exits 1 when any task fails.

---

## `aptdata setup`

Diagnose and configure the aptdata ecosystem. The wizard shows every check
transparently, offers to create a starter `agents.yaml` (with the `routing:`
policy block) and configures the Telegram channel — the bot token stays in
the `TELEGRAM_BOT_TOKEN` env var, **never in a file** (the yaml records only
`token_env`).

```
aptdata setup [--file/-f PATH]           # wizard interativo
aptdata setup --check [--json]           # não interativo; exit 1 se incompleto
```

`--check` reports: `agents_file`*, `router`* (agents/skills carregados),
`routing_policy`, `telegram_token`, `telegram_transport`, `observability`,
`viz` (* = obrigatórios para o exit 0). See [Telegram](../telegram.md).

---

## `aptdata telegram`

Run the thin Telegram transport (long-polling) over the ConversationEngine —
text messages become `converse` turns, inline buttons resolve confirmations.
No routing logic lives in the transport.

```bash
export TELEGRAM_BOT_TOKEN=123:abc
aptdata telegram [--file PATH] [--token-env TELEGRAM_BOT_TOKEN]
```

---

## `aptdata converse`

One conversation turn against the multi-agent ecosystem, via the
`ConversationEngine` (route → dispatch / confirm / clarify per the policy in
the `routing:` block of `agents.yaml`). Sessions are multi-turn ("continua"
reuses the last agent) and persist under `~/.aptdata/sessions`
(`$APTDATA_SESSIONS_DIR`).

```
aptdata converse TEXT [--session/-s ID] [--file/-f PATH] [--yes] [--json]
aptdata converse --confirm DECISION_ID [--choose AGENT] [--session/-s ID]
```

- High-confidence routes (prefix, strong skill match) dispatch directly.
- Medium confidence / LLM routes return `needs_confirmation` with a
  `decision_id`; approve with `--confirm` (or `--yes` inline), or reroute
  with `--choose AGENT`.
- Agents holding a **guarded capability** (`routing.guarded_capabilities`,
  e.g. deploy/ssh/docker) always require confirmation, regardless of
  confidence.
- Every turn is recorded in the observability trace
  (`permission.requested`/`permission.resolved`, dispatches).

```bash
aptdata converse "mexer no frontend" --json         # dispatch direto
aptdata converse "/hermez deploy" -s ops            # guardrail -> confirmação
aptdata converse --confirm 1a2b3c4d -s ops          # aprova e despacha
```

---

## `aptdata viz`

Serve the aptdata-viz web view of the agent ecosystem (read-only API +
thin frontend). Endpoints: `/api/agents`, `/api/health`, `/api/route?text=`
(503 on router failure), `/api/observability` (event-store summary) and
`/api/events` — live **SSE** feed of the observability trace
(`?backlog=N` replays the last N events on connect).

```
aptdata viz [--file PATH] [--host HOST] [--port PORT]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--file`, `-f` | `agents.yaml` | Agents file to visualise |
| `--host` | `0.0.0.0` | Bind host |
| `--port`, `-p` | `4570` | HTTP port |

---

## `aptdata obs`

Inspect the aptdata observability trace — the local event store where routing
decisions, agent dispatches/responses and app start-ups are recorded (see
[Observability](../observability.md)). Store path: `$APTDATA_OBS_DB`
(default `~/.aptdata/events.db`); disable emission with
`APTDATA_OBS_DISABLED=1`.

### `aptdata obs summary [--json]`

Aggregated view: totals by event kind, routing decisions by mode, dispatch
success rate and average latency.

### `aptdata obs tail [--limit N] [--kind KIND] [--run-id ID] [--json]`

Latest events in chronological order. Filter by kind
(`routing.decision`, `agent.dispatch`, `agent.response`, `app.started`, …)
or correlate a whole run with `--run-id`.

```bash
aptdata agents dispatch "mexer no frontend" --json
aptdata obs tail --json           # decisão + dispatch + response, mesmo run_id
aptdata obs summary
```

---

## `aptdata mcp-start`

Start the MCP (Model Context Protocol) server so AI agents can discover and
run pipelines. Emits `mcp.server.starting`; failures emit
`mcp.server.error` and exit 1.

```bash
aptdata mcp-start [--transport stdio|sse]
```

See the [MCP documentation](../mcp.md) for tools and resources.

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
