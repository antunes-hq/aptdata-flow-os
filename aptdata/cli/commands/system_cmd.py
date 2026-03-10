"""CLI sub-commands for system registry management."""

from __future__ import annotations

import json

import typer

from aptdata.cli.rendering.console import SmartConsole
from aptdata.cli.rendering.tables import systems_table
from aptdata.cli.rendering.panels import system_detail_panel

system_app = typer.Typer(name="system", help="Inspect and validate registered systems.")


@system_app.command("list")
def system_list(
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """List all registered systems."""
    from aptdata.plugins import registry  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    names = registry.list_systems()

    if json_mode:
        print(json.dumps({"systems": names, "count": len(names)}), flush=True)
    else:
        if not names:
            console.warning("No systems registered.")
        else:
            console.render(systems_table(names))


@system_app.command("info")
def system_info(
    name: str = typer.Argument(..., help="System name."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Show detailed info about a registered system."""
    from aptdata.plugins import registry  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    system_cls = registry.get(name)

    if system_cls is None:
        console.error(f"System '{name}' not found in registry.")
        raise typer.Exit(1)

    if json_mode:
        print(
            json.dumps(
                {
                    "name": name,
                    "class": system_cls.__name__,
                    "module": getattr(system_cls, "__module__", "unknown"),
                    "doc": (system_cls.__doc__ or "").strip(),
                }
            ),
            flush=True,
        )
    else:
        console.render(system_detail_panel(name, system_cls))


@system_app.command("validate")
def system_validate(
    name: str = typer.Argument(..., help="System name."),
) -> None:
    """Instantiate a system and compile all its flows without executing."""
    from aptdata.plugins import registry  # noqa: PLC0415

    console = SmartConsole(json_mode=False)
    system_cls = registry.get(name)

    if system_cls is None:
        console.error(f"System '{name}' not found in registry.")
        raise typer.Exit(1)

    try:
        with console.spinner(f"Validating system '{name}'..."):
            instance = system_cls(system_id=name)
            flows = getattr(instance, "_flows", None) or getattr(instance, "flows", [])
            for flow in flows:
                if hasattr(flow, "compile"):
                    flow.compile()
        console.success(f"System '{name}' validated successfully.")
    except Exception as exc:  # noqa: BLE001
        console.error(f"Validation failed: {exc}")
        raise typer.Exit(1) from exc
