"""Rich table generators for aptdata CLI output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.table import Table

if TYPE_CHECKING:
    from aptdata.config.parser import ParsedConfig


def systems_table(names: list[str]) -> Table:
    """Return a Rich Table of registered system names."""
    table = Table(
        title="Registered Systems", show_header=True, header_style="bold cyan"
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="bold")
    for i, name in enumerate(names, 1):
        table.add_row(str(i), name)
    return table


def plugins_table(plugins: dict[str, list[str]]) -> Table:
    """Return a Rich Table of readers and writers."""
    table = Table(
        title="Registered Plugins", show_header=True, header_style="bold cyan"
    )
    table.add_column("Kind", style="bold magenta", width=10)
    table.add_column("Name", style="bold")
    for name in plugins.get("readers", []):
        table.add_row("reader", name)
    for name in plugins.get("writers", []):
        table.add_row("writer", name)
    return table


def plugin_schema_table(schema: dict[str, Any]) -> Table:
    """Return a Rich Table of constructor arguments for a plugin."""
    table = Table(
        title=f"Plugin Schema: {schema.get('name', '')} ({schema.get('type', '')})",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Argument", style="bold")
    table.add_column("Required", style="bold yellow")
    table.add_column("Default", style="dim")
    for arg in schema.get("arguments", []):
        required = "✓" if arg.get("required") else ""
        default = str(arg.get("default", "")) if not arg.get("required") else "-"
        table.add_row(arg["name"], required, default)
    return table


def config_summary_table(parsed: ParsedConfig) -> Table:
    """Return a Rich Table summarising a parsed YAML config."""
    table = Table(title="Config Summary", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    meta = parsed.metadata
    system = parsed.system

    table.add_row("system_id", system.system_id)
    table.add_row("flows", str(len(getattr(system, "flows", []))))

    for key, value in meta.items():
        table.add_row(f"metadata.{key}", str(value))

    return table


def telemetry_status_table(status: dict[str, Any]) -> Table:
    """Return a Rich Table of OpenTelemetry status."""
    table = Table(title="Telemetry Status", show_header=True, header_style="bold cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in status.items():
        table.add_row(str(key), str(value))
    return table
