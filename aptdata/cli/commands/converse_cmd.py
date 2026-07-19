"""CLI do ConversationEngine — ``aptdata converse``.

Transporte fino sobre o engine (a mesma regra do Telegram/MCP): nenhuma
decisão de rota, threshold ou estado de conversa vive aqui.

Execution mode: ``converse`` (ADR-002 §2.3). ``--mode`` override + ``--dry-run``
que mostra a ``RouteDecision`` e o outcome da ``DecisionPolicy`` sem despachar.
"""

from __future__ import annotations

import json
from typing import Any

import typer

from aptdata.cli.commands.agents_cmd import _resolve_file, _resolve_mode
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
    mode: str = typer.Option(
        None,
        "--mode",
        help=(
            "ExecutionMode override (oneshot | converse | project | "
            "orchestrated). Default: converse or .aptdata/ default_mode."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show the RouteDecision + policy outcome without dispatching.",
    ),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Converse com o ecossistema: decide, confirma quando preciso, despacha."""
    from aptdata.agents.conversation import ConversationEngine  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    resolved_mode = _resolve_mode(file, mode, "converse", "")
    engine = ConversationEngine.from_yaml(_resolve_file(file))

    if dry_run and confirm:
        console.error("--dry-run cannot be combined with --confirm.")
        raise typer.Exit(2)

    if dry_run:
        # Plan-only: roteia e classifica o outcome sem despachar nem gravar
        # sessão. Reaproveita o Router + DecisionPolicy do engine.
        if text is None:
            console.error("Provide TEXT to dry-run converse.")
            raise typer.Exit(2)

        # follow-up reusa o último agente da sessão — ainda no dry-run, só
        # não despacha.
        session_state = engine.store.get(session)
        decision = engine._followup_decision(session_state, text)
        if decision is None:
            decision = engine.router.route(text)
        action = engine.policy.decide(decision, engine.router)
        payload: dict[str, Any] = {
            "mode": str(resolved_mode),
            "dry_run": True,
            "action": action,  # dispatch | confirm | clarify
            "decision": decision.to_dict(),
            "session": session,
        }
        if json_mode:
            print(json.dumps(payload, ensure_ascii=False), flush=True)
        else:
            target = decision.agent_id or "(nenhum)"
            skill = f" via {decision.skill}" if decision.skill else ""
            print(
                f"[dry-run] {target} [{decision.mode}{skill}, "
                f"conf={decision.confidence:.2f}] -> {action}"
            )
        return

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
        payload = {"mode": str(resolved_mode), **turn.to_dict()}
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    else:
        console.print(turn.text)
        if turn.type == "needs_confirmation":
            console.print(
                f"[dim]confirme com:[/dim] aptdata converse --confirm"
                f" {turn.decision_id} -s {session}" + (f" -f {file}" if file else "")
            )

    if turn.response is not None and not turn.response.ok:
        raise typer.Exit(1)
