"""CLI sub-commands for the multi-agent registry.

``aptdata agents`` is the single entry point for talking to every backend
(OpenClaw workers, OpenCode, Claude Code, ...) through one uniform interface.
Every outcome is emitted as a JSON line, keeping the orchestrator-friendly
contract of the rest of the CLI.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer

from aptdata.agents.base import observed_send
from aptdata.cli.rendering.console import SmartConsole
from aptdata.observability import Observer

agents_app = typer.Typer(name="agents", help="Talk to the multi-agent ecosystem.")

DEFAULT_FILE = "agents.yaml"
ENV_VAR = "APTDATA_AGENTS_FILE"


def _resolve_file(file: str | None) -> Path:
    """Locate ``agents.yaml`` from --file, env var, or the working directory."""
    candidate = file or os.getenv(ENV_VAR) or DEFAULT_FILE
    path = Path(candidate).expanduser()
    if not path.exists():
        raise typer.BadParameter(
            f"Agents file not found: {path}. Pass --file or set ${ENV_VAR}."
        )
    return path


def _load(file: str | None):
    from aptdata.agents import AgentRegistry  # noqa: PLC0415

    return AgentRegistry.from_yaml(_resolve_file(file))


def _load_router(file: str | None):
    from aptdata.agents import Router  # noqa: PLC0415

    return Router.from_yaml(_resolve_file(file))


@agents_app.command("list")
def agents_list(
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    enabled_only: bool = typer.Option(False, "--enabled", help="Hide disabled."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """List every registered agent and its capabilities."""
    console = SmartConsole(json_mode=json_mode)
    registry = _load(file)
    specs = registry.specs(include_disabled=not enabled_only)
    rows = [
        {
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "location": s.location,
            "enabled": s.enabled,
            "capabilities": s.capabilities,
        }
        for s in sorted(specs, key=lambda s: (not s.enabled, s.id))
    ]

    if json_mode:
        print(json.dumps({"agents": rows, "count": len(rows)}), flush=True)
        return

    if not rows:
        console.warning("No agents registered.")
        return
    for r in rows:
        flag = "●" if r["enabled"] else "○"
        caps = ", ".join(r["capabilities"])
        print(f"{flag} {r['id']:<10} {r['type']:<14} [{r['location']}]  {caps}")


@agents_app.command("send")
def agents_send(
    agent_id: str = typer.Argument(..., help="Target agent id."),
    prompt: str = typer.Argument(..., help="Message / instruction to send."),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Send a prompt to a specific agent and print its reply."""
    console = SmartConsole(json_mode=json_mode)
    registry = _load(file)
    try:
        agent = registry.get(agent_id)
    except KeyError:
        console.error(f"Agent '{agent_id}' is not registered.")
        raise typer.Exit(1)

    with Observer.get().run_context():
        result = observed_send(agent, prompt)
    if json_mode:
        print(json.dumps(result.to_dict()), flush=True)
    elif result.ok:
        print(result.text)
    else:
        console.error(result.error or "send failed")
    if not result.ok:
        raise typer.Exit(1)


@agents_app.command("route")
def agents_route(
    text: str = typer.Argument(..., help="Prompt to route (not sent)."),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Show which agent would handle a prompt and why (prefix/skill/default)."""
    router = _load_router(file)
    decision = router.route(text)
    if json_mode:
        print(json.dumps(decision.to_dict()), flush=True)
    else:
        target = decision.agent_id or "(nenhum)"
        detail = f" via {decision.skill}" if decision.skill else ""
        print(f"{target}  [{decision.mode}{detail}, conf={decision.confidence:.2f}]")


@agents_app.command("dispatch")
def agents_dispatch(
    text: str = typer.Argument(..., help="Prompt to route AND send."),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Route a prompt to the best agent and send it (route + send in one)."""
    console = SmartConsole(json_mode=json_mode)
    router = _load_router(file)
    with Observer.get().run_context():
        decision = router.route(text)
        if decision.agent_id is None:
            console.error("No agent available to handle this prompt.")
            raise typer.Exit(1)

        agent = router.registry.get(decision.agent_id)
        result = observed_send(agent, decision.text)
    if json_mode:
        print(
            json.dumps({"routed_to": decision.agent_id, "mode": decision.mode,
                        **result.to_dict()}),
            flush=True,
        )
    elif result.ok:
        print(f"[{decision.agent_id}] {result.text}")
    else:
        console.error(f"[{decision.agent_id}] {result.error}")
    if not result.ok:
        raise typer.Exit(1)


@agents_app.command("resolve")
def agents_resolve(
    capability: str = typer.Argument(..., help="Capability to route to."),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Show which agent would handle a given capability (best weight wins)."""
    console = SmartConsole(json_mode=json_mode)
    registry = _load(file)
    agent = registry.resolve(capability)

    if agent is None:
        if json_mode:
            print(json.dumps({"capability": capability, "agent": None}), flush=True)
        else:
            console.warning(f"No enabled agent handles '{capability}'.")
        raise typer.Exit(1)

    if json_mode:
        print(
            json.dumps({"capability": capability, "agent": agent.id}), flush=True
        )
    else:
        print(f"{capability} -> {agent.id}")
