"""Typer-based static CLI for aptdata.

Design goals
------------
* Machine / AI-readable: every outcome is emitted as a single JSON line on
  stdout (success) or stderr (error).
* Exit codes: 0 = success, 1 = error.
* Self-documenting: Typer generates --help automatically from the docstrings
  and type annotations.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import typer
from opentelemetry import trace

from aptdata.cli.scaffold import scaffold
from aptdata.config.schema import write_domain_schema

app = typer.Typer(
    name="aptdata",
    help="Smart Data – declarative data-pipeline framework.",
    add_completion=False,
)
schema_app = typer.Typer(help="Schema utilities for declarative configuration.")


def _emit(payload: dict, *, error: bool = False) -> None:
    """Emit *payload* as a single JSON line to stdout or stderr."""
    event = dict(payload)
    span_context = trace.get_current_span().get_span_context()
    event["trace_id"] = (
        f"{span_context.trace_id:032x}" if span_context.is_valid else None
    )
    line = json.dumps(event, default=str)
    if error:
        print(line, file=sys.stderr, flush=True)
    else:
        print(line, flush=True)


@app.command()
def run(
    pipeline: str = typer.Argument(..., help="Pipeline name / identifier to run."),
    env: str = typer.Option("dev", "--env", "-e", help="Target execution environment."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate and compile the pipeline without executing it.",
    ),
) -> None:
    """Run a registered data pipeline.

    Emits structured JSON logs and returns exit code 0 on success or 1 on
    failure so that orchestrators and AI agents can parse the outcome.

    Examples
    --------
    aptdata run pipeline_x --env prod
    aptdata run pipeline_x --env staging --dry-run
    """
    started_at = time.time()
    _emit(
        {
            "event": "pipeline.started",
            "pipeline": pipeline,
            "env": env,
            "dry_run": dry_run,
        }
    )

    try:
        # Plugin registry look-up (stub – real implementations are in plugins/)
        from aptdata.plugins import registry  # noqa: PLC0415

        pipeline_cls = registry.get(pipeline)
        if pipeline_cls is None:
            raise LookupError(f"Pipeline '{pipeline}' not found in registry.")

        instance = pipeline_cls(system_id=pipeline)

        if not dry_run:
            instance.run()

        elapsed = round(time.time() - started_at, 3)
        _emit(
            {
                "event": "pipeline.completed",
                "pipeline": pipeline,
                "env": env,
                "dry_run": dry_run,
                "elapsed_seconds": elapsed,
            }
        )
        raise SystemExit(0)

    except LookupError as exc:
        elapsed = round(time.time() - started_at, 3)
        _emit(
            {
                "event": "pipeline.error",
                "pipeline": pipeline,
                "env": env,
                "error": str(exc),
                "elapsed_seconds": elapsed,
            },
            error=True,
        )
        raise SystemExit(1) from exc

    except Exception as exc:  # noqa: BLE001
        elapsed = round(time.time() - started_at, 3)
        _emit(
            {
                "event": "pipeline.error",
                "pipeline": pipeline,
                "env": env,
                "error": str(exc),
                "elapsed_seconds": elapsed,
            },
            error=True,
        )
        raise SystemExit(1) from exc


@app.command()
def monitor(
    refresh: float = typer.Option(
        1.0,
        "--refresh",
        "-r",
        help="Dashboard refresh interval in seconds.",
    ),
) -> None:
    """Open the interactive TUI monitoring dashboard.

    Displays the pipeline DAG, memory usage and task status in real time.
    Press **q** or **Ctrl+C** to exit.

    Examples
    --------
    aptdata monitor
    aptdata monitor --refresh 0.5
    """
    from aptdata.tui.monitor import MonitorApp  # noqa: PLC0415

    app_instance = MonitorApp(refresh_interval=refresh)
    app_instance.run()


@app.command()
def mcp_start(
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="MCP transport to use (stdio or sse).",
    ),
) -> None:
    """Start the MCP (Model Context Protocol) server.

    This exposes aptdata tools and resources so that AI agents
    (Claude Desktop, Copilot, Devin, …) can discover and run pipelines.

    Examples
    --------
    aptdata mcp-start
    aptdata mcp-start --transport sse
    """
    _emit({"event": "mcp.server.starting", "transport": transport})
    try:
        from aptdata.mcp.server import mcp as mcp_server  # noqa: PLC0415

        mcp_server.run(transport=transport)
    except Exception as exc:  # noqa: BLE001
        _emit(
            {"event": "mcp.server.error", "error": str(exc)},
            error=True,
        )
        raise SystemExit(1) from exc


app.command()(scaffold)
app.add_typer(schema_app, name="schema")

from aptdata.cli.commands import (  # noqa: E402
    agents_app,
    config_app,
    mesh_app,
    plugin_app,
    project_app,
    system_app,
    telemetry_app,
)
from aptdata.cli.interactive import interactive_command  # noqa: E402

app.add_typer(system_app, name="system")
app.add_typer(plugin_app, name="plugin")
app.add_typer(config_app, name="config")
app.add_typer(telemetry_app, name="telemetry")
app.add_typer(mesh_app, name="mesh")
app.add_typer(agents_app, name="agents")
app.add_typer(project_app, name="project")


@app.command("interactive")
def interactive() -> None:
    """Launch the interactive wizard mode."""
    interactive_command()


@app.command("viz")
def viz(
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    port: int = typer.Option(4570, "--port", "-p", help="HTTP port."),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host."),
) -> None:
    """Launch aptdata-viz — the web view of the agent ecosystem."""
    from aptdata.viz import serve  # noqa: PLC0415

    serve(agents_file=file, host=host, port=port)


@schema_app.command("export")
def schema_export(
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output path for the generated JSON Schema.",
    ),
) -> None:
    """Export JSON Schema for declarative YAML configs."""
    started_at = time.time()
    _emit({"event": "schema.export.started", "output": str(output)})
    try:
        write_domain_schema(output)
        elapsed = round(time.time() - started_at, 3)
        _emit(
            {
                "event": "schema.export.completed",
                "output": str(output),
                "elapsed_seconds": elapsed,
            }
        )
        raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001
        elapsed = round(time.time() - started_at, 3)
        _emit(
            {
                "event": "schema.export.error",
                "output": str(output),
                "error": str(exc),
                "elapsed_seconds": elapsed,
            },
            error=True,
        )
        raise SystemExit(1) from exc
