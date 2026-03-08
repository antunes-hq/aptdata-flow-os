"""Typer-based static CLI for smart-data.

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

from smart_data.cli.scaffold import scaffold
from smart_data.config.schema import write_domain_schema

app = typer.Typer(
    name="smart-data",
    help="Smart Data – declarative data-pipeline framework.",
    add_completion=False,
)
schema_app = typer.Typer(help="Schema utilities for declarative configuration.")


def _emit(payload: dict, *, error: bool = False) -> None:
    """Emit *payload* as a single JSON line to stdout or stderr."""
    line = json.dumps(payload, default=str)
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
    smart-data run pipeline_x --env prod
    smart-data run pipeline_x --env staging --dry-run
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
        from smart_data.plugins import registry  # noqa: PLC0415

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
    smart-data monitor
    smart-data monitor --refresh 0.5
    """
    from smart_data.tui.monitor import MonitorApp  # noqa: PLC0415

    app_instance = MonitorApp(refresh_interval=refresh)
    app_instance.run()


app.command()(scaffold)
app.add_typer(schema_app, name="schema")


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
