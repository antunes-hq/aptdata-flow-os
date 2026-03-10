"""CLI sub-commands for telemetry management."""

from __future__ import annotations

import json

import typer

from aptdata.cli.rendering.console import SmartConsole
from aptdata.cli.rendering.tables import telemetry_status_table

telemetry_app = typer.Typer(name="telemetry", help="Inspect OpenTelemetry telemetry status.")


def _get_telemetry_status() -> dict:
    """Return a dict describing the current OTel tracer provider."""
    from opentelemetry import trace  # noqa: PLC0415

    provider = trace.get_tracer_provider()
    provider_type = type(provider).__name__
    configured = provider_type != "ProxyTracerProvider"
    return {
        "configured": configured,
        "provider": provider_type,
        "service": "aptdata",
    }


@telemetry_app.command("status")
def telemetry_status(
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Show OpenTelemetry configuration status."""
    console = SmartConsole(json_mode=json_mode)
    status = _get_telemetry_status()

    if json_mode:
        print(json.dumps(status), flush=True)
    else:
        console.render(telemetry_status_table(status))


@telemetry_app.command("export")
def telemetry_export(
    fmt: str = typer.Option("json", "--format", "-f", help="Export format (json)."),
) -> None:
    """Export collected telemetry spans/metrics."""
    console = SmartConsole(json_mode=False)
    status = _get_telemetry_status()

    if fmt == "json":
        console.print(json.dumps({"telemetry": status}, indent=2, default=str))
    else:
        console.error(f"Unsupported format: {fmt}")
        raise typer.Exit(1)
