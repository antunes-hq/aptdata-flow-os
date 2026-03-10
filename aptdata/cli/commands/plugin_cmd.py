"""CLI sub-commands for plugin management."""

from __future__ import annotations

import json

import typer

from aptdata.cli.rendering.console import SmartConsole
from aptdata.cli.rendering.tables import plugins_table, plugin_schema_table

plugin_app = typer.Typer(name="plugin", help="Manage and inspect plugins.")


@plugin_app.command("list")
def plugin_list(
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """List all registered reader and writer plugins."""
    from aptdata.plugins import plugin_manager  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    plugins = plugin_manager.list_plugins()

    if json_mode:
        print(json.dumps(plugins), flush=True)
    else:
        if not plugins.get("readers") and not plugins.get("writers"):
            console.warning("No plugins registered.")
        else:
            console.render(plugins_table(plugins))


@plugin_app.command("inspect")
def plugin_inspect(
    name: str = typer.Argument(..., help="Plugin name."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Show constructor schema for a plugin."""
    from aptdata.plugins import plugin_manager  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)

    try:
        schema = plugin_manager.get_plugin_schema(name)
    except KeyError as exc:
        console.error(str(exc))
        raise typer.Exit(1) from exc

    if json_mode:
        print(json.dumps(schema, default=str), flush=True)
    else:
        console.render(plugin_schema_table(schema))


@plugin_app.command("preview")
def plugin_preview(
    reader: str = typer.Argument(..., help="Reader plugin name."),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of records to preview."),
) -> None:
    """Execute a reader plugin and preview the first N records."""
    from aptdata.plugins import plugin_manager  # noqa: PLC0415

    console = SmartConsole(json_mode=False)

    try:
        with console.spinner(f"Reading from '{reader}'..."):
            records = plugin_manager.preview_dataset(reader)
        records = records[:limit]
        if not records:
            console.warning("No records returned.")
        else:
            from rich.table import Table  # noqa: PLC0415

            table = Table(title=f"Preview: {reader} (first {len(records)} records)")
            for col in records[0].keys():
                table.add_column(str(col))
            for row in records:
                table.add_row(*[str(v) for v in row.values()])
            console.render(table)
    except KeyError as exc:
        console.error(str(exc))
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.error(f"Preview failed: {exc}")
        raise typer.Exit(1) from exc


@plugin_app.command("load")
def plugin_load(
    module_path: str = typer.Argument(..., help="Dotted Python module path to load."),
) -> None:
    """Dynamically import a plugin module."""
    from aptdata.plugins import plugin_manager  # noqa: PLC0415

    console = SmartConsole(json_mode=False)

    try:
        with console.spinner(f"Loading '{module_path}'..."):
            mod = plugin_manager.load_module(module_path)
        console.success(f"Module '{mod.__name__}' loaded successfully.")
    except ModuleNotFoundError as exc:
        console.error(f"Module not found: {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.error(f"Load failed: {exc}")
        raise typer.Exit(1) from exc
