"""CLI do ConversationEngine — ``aptdata converse``.

Transporte fino sobre o engine (a mesma regra do Telegram/MCP): nenhuma
decisão de rota, threshold ou estado de conversa vive aqui.
"""

from __future__ import annotations

import json

import typer

from aptdata.cli.commands.agents_cmd import _resolve_file
from aptdata.cli.rendering.console import SmartConsole


def converse_command(
    text: str = typer.Argument(
        None, help="Message for the conversation engine (omit with --confirm)."
    ),
    session: str = typer.Option(
        "default", "--session", "-s", help="Conversation session id."
    ),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    confirm: str = typer.Option(
        None, "--confirm", help="Pending decision id to confirm instead of routing."
    ),
    choose: str = typer.Option(
        None, "--choose", help="Agent id override when confirming."
    ),
    yes: bool = typer.Option(
        False, "--yes", help="Auto-confirm when the engine asks for confirmation."
    ),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Converse com o ecossistema: decide, confirma quando preciso, despacha."""
    from aptdata.agents.conversation import ConversationEngine  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    engine = ConversationEngine.from_yaml(_resolve_file(file))

    if confirm:
        turn = engine.confirm(session, confirm, choice=choose)
    elif text is None:
        console.error("Provide TEXT to converse or --confirm DECISION_ID.")
        raise typer.Exit(2)
    else:
        turn = engine.handle(session, text)
        if turn.type == "needs_confirmation" and yes:
            turn = engine.confirm(session, turn.decision_id, choice=choose)

    if json_mode:
        print(json.dumps(turn.to_dict(), ensure_ascii=False), flush=True)
    else:
        console.print(turn.text)
        if turn.type == "needs_confirmation":
            console.print(
                f"[dim]confirme com:[/dim] aptdata converse --confirm"
                f" {turn.decision_id} -s {session}"
                + (f" -f {file}" if file else "")
            )

    if turn.response is not None and not turn.response.ok:
        raise typer.Exit(1)
