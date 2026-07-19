"""``aptdata modes`` — descoberta dos modos de execução (ADR-002 §2.3).

Lista os 4 modos canônicos (oneshot / converse / project / orchestrated) com
descrição e qual comando CLI corresponde — ajuda o operador a entender qual
superfície de execução usar para cada tarefa.
"""

from __future__ import annotations

import json

import typer

from aptdata.cli.rendering.console import SmartConsole

modes_app = typer.Typer(
    name="modes",
    help=(
        "List the agent execution modes "
        "(oneshot / converse / project / orchestrated)."
    ),
)


@modes_app.command("list")
def modes_list(
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """List the 4 execution modes with description + matching CLI command."""
    from aptdata.agents.modes import MODE_DOCS  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    rows = [
        {
            "mode": doc.mode.value,
            "short": doc.short,
            "description": doc.description,
            "cli_command": doc.cli_command,
        }
        for doc in MODE_DOCS
    ]

    if json_mode:
        print(json.dumps({"modes": rows, "count": len(rows)}), flush=True)
        return

    if not rows:
        console.warning("No execution modes registered.")
        return

    for r in rows:
        print(f"● {r['mode']:<12} {r['short']}")
        print(f"  {r['description']}")
        print(f"  $ {r['cli_command']}")
        print()


__all__ = ["modes_app"]
