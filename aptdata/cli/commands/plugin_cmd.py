"""CLI sub-commands for plugin management."""

from __future__ import annotations

import json
from importlib.metadata import entry_points
from typing import Any

import typer

from aptdata.cli.rendering.console import SmartConsole
from aptdata.cli.rendering.tables import plugin_schema_table, plugins_table

plugin_app = typer.Typer(name="plugin", help="Manage and inspect plugins.")
#: ``plugins`` (plural) — entry-point discovery surface (ADR-002 §2.1/§2.4).
#: Distinct from ``plugin`` (singular, which manages reader/writer plugins
#: registered imperatively on the global ``plugin_manager``).
plugins_app = typer.Typer(name="plugins", help="Discover plugins via entry points.")


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


# ---------------------------------------------------------------------------
# aptdata plugins — entry-point discovery (ADR-002 §2.1 / §2.4)
# ---------------------------------------------------------------------------

#: Entry-point groups surfaced by ``aptdata plugins list``. Each group
#: represents one extension axis of the framework.
ENTRY_POINT_GROUPS: tuple[str, ...] = (
    "aptdata.agents",
    "aptdata.plugins",
    "aptdata.systems",
    "aptdata.components",
    "aptdata.commands",
)


def _discover_entry_points() -> list[dict[str, Any]]:
    """Inspect each declared entry-point group and report what was found.

    Returns a list of records (one per entry point) with name, group,
    value (``module:attr``), and a ``loaded`` flag indicating whether
    ``EntryPoint.load()`` succeeded. Failures are surfaced (not raised)
    so the CLI can show broken plugins.
    """
    records: list[dict[str, Any]] = []
    for group in ENTRY_POINT_GROUPS:
        try:
            eps = list(entry_points(group=group))
        except Exception as exc:  # noqa: BLE001 — never crash discovery
            records.append(
                {
                    "group": group,
                    "name": "<group-error>",
                    "value": str(exc),
                    "loaded": False,
                    "error": str(exc),
                }
            )
            continue
        for ep in eps:
            record: dict[str, Any] = {
                "group": group,
                "name": ep.name,
                "value": ep.value,
                "loaded": False,
                "error": None,
            }
            try:
                ep.load()
                record["loaded"] = True
            except Exception as exc:  # noqa: BLE001 — broken plugin ≠ broken CLI
                record["error"] = str(exc)
            records.append(record)
    return records


@plugins_app.command("list")
def plugins_list(
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """List plugins discovered via entry points (groups ``aptdata.*``).

    Shows name, group, ``module:attr`` value, and whether the entry point
    loaded successfully. Broken plugins are surfaced (with their error)
    rather than hidden — this is the diagnostic surface promised by
    ADR-002 §4 ("entry points tornam a origem menos óbvia; mitiga-se com
    ``aptdata plugins``").
    """
    console = SmartConsole(json_mode=json_mode)
    records = _discover_entry_points()

    if json_mode:
        for record in records:
            print(json.dumps(record, default=str), flush=True)
        return

    if not records:
        console.warning("No entry-point plugins discovered.")
        return

    from rich.table import Table  # noqa: PLC0415

    table = Table(
        title="Entry-Point Plugins", show_header=True, header_style="bold cyan"
    )
    table.add_column("Group", style="bold magenta")
    table.add_column("Name", style="bold")
    table.add_column("Module:Attr")
    table.add_column("Status")
    for record in records:
        status = "ok" if record["loaded"] else f"FAIL: {record['error']}"
        style = "green" if record["loaded"] else "red"
        table.add_row(
            record["group"],
            record["name"],
            record["value"],
            f"[{style}]{status}[/{style}]",
        )
    console.render(table)
