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
from typing import Any

import typer

from aptdata.agents.base import observed_send
from aptdata.cli.rendering.console import SmartConsole
from aptdata.observability import Observer

agents_app = typer.Typer(name="agents", help="Talk to the multi-agent ecosystem.")

DEFAULT_FILE = "agents.yaml"
ENV_VAR = "APTDATA_AGENTS_FILE"


def _resolve_file(file: str | None) -> Path:
    """Locate ``agents.yaml`` from --file, env var, APTDATA_AGENTS_FILE or .aptdata/.

    Resolution order (ADR-002 §2.2):

    1. ``--file`` flag (explicit path).
    2. ``$APTDATA_AGENTS_FILE`` env var (path).
    3. The ``.aptdata/agents.yaml`` of the project containing the CWD
       (walks up the tree like ``git``).
    4. The legacy ``agents.yaml`` at the CWD (still accepted so existing
       projects without ``.aptdata/`` keep working until they migrate).
    """
    if file:
        path = Path(file).expanduser()
    elif os.getenv(ENV_VAR):
        path = Path(os.getenv(ENV_VAR)).expanduser()  # type: ignore[arg-type]
    else:
        # ADR-002 §2.2: prefer the .aptdata/ dotdir over the legacy root file.
        from aptdata.config.loader import locate_project_optional  # noqa: PLC0415

        project = locate_project_optional()
        if project is not None and project.agents_yaml.is_file():
            path = project.agents_yaml
        else:
            path = Path(DEFAULT_FILE)

    if not path.exists():
        raise typer.BadParameter(
            f"Agents file not found: {path}. Pass --file, set ${ENV_VAR}, "
            "or run 'aptdata init' to create a .aptdata/ project."
        )
    return path


def _load(file: str | None):
    from aptdata.agents import AgentRegistry  # noqa: PLC0415

    return AgentRegistry.from_yaml(_resolve_file(file))


def _load_router(file: str | None):
    from aptdata.agents import Router  # noqa: PLC0415

    return Router.from_yaml(_resolve_file(file))


def _project_default_mode(file: str | None):
    """Lê ``default_mode`` do ``.aptdata/agents.yaml`` (se houver projeto)."""
    from aptdata.config.loader import load_default_mode  # noqa: PLC0415

    try:
        path = _resolve_file(file)
    except typer.BadParameter:
        return None
    return load_default_mode(path)


def _resolve_mode(
    file: str | None,
    explicit: str | None,
    group: str,
    command: str = "",
):
    """Resolve o ``ExecutionMode`` efetivo.

    Ordem: ``--mode`` explícito > ``default_mode`` do projeto > default do
    comando (mapa em :mod:`aptdata.agents.modes`).
    """
    from aptdata.agents.modes import resolve_mode  # noqa: PLC0415

    return resolve_mode(
        explicit=explicit,
        group=group,
        command=command,
        project_default=_project_default_mode(file),
    )


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
    mode: str = typer.Option(
        None,
        "--mode",
        help=(
            "ExecutionMode override (oneshot | converse | project | "
            "orchestrated). Default: deduced from the command or "
            ".aptdata/agents.yaml's default_mode."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show the target agent without calling send().",
    ),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Send a prompt to a specific agent and print its reply.

    Execution mode: ``oneshot`` (default). ``--dry-run`` validates that the
    agent exists and prints the planned send without dispatching.
    """
    console = SmartConsole(json_mode=json_mode)
    resolved_mode = _resolve_mode(file, mode, "agents", "send")
    registry = _load(file)
    try:
        agent = registry.get(agent_id)
    except KeyError:
        console.error(f"Agent '{agent_id}' is not registered.")
        raise typer.Exit(1)

    if dry_run:
        # oneshot não tem roteamento — a "decisão" é só validar o alvo.
        payload: dict[str, Any] = {
            "mode": str(resolved_mode),
            "dry_run": True,
            "agent_id": agent.id,
            "prompt": prompt,
            "ok": True,
            "would_send": True,
        }
        if json_mode:
            print(json.dumps(payload, ensure_ascii=False), flush=True)
        else:
            print(
                f"[dry-run] would send to {agent.id} "
                f"({agent.spec.type}, {len(prompt)} chars)"
            )
        return

    with Observer.get().run_context():
        result = observed_send(agent, prompt)
    if json_mode:
        payload = {"mode": str(resolved_mode), **result.to_dict()}
        print(json.dumps(payload, ensure_ascii=False), flush=True)
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
    mode: str = typer.Option(
        None,
        "--mode",
        help=(
            "ExecutionMode override. Default: orchestrated (route is the "
            "dry-run variant of dispatch)."
        ),
    ),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Show which agent would handle a prompt and why (prefix/skill/default).

    This is the implicit dry-run of the ``orchestrated`` mode — it never
    sends. The ``mode`` field appears in ``--json`` so the orchestrator can
    tell which execution surface produced the decision.
    """
    resolved_mode = _resolve_mode(file, mode, "agents", "route")
    router = _load_router(file)
    decision = router.route(text)
    if json_mode:
        # `mode` é o ExecutionMode (orchestrated); `routing_mode` preserva o
        # RouteDecision.mode (prefix/skill/llm/default/none) — dimensões
        # diferentes, ambas úteis (ADR-002 §2.3).
        payload = {
            **decision.to_dict(),
            "routing_mode": decision.mode,
            "mode": str(resolved_mode),
        }
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    else:
        target = decision.agent_id or "(nenhum)"
        detail = f" via {decision.skill}" if decision.skill else ""
        print(f"{target}  [{decision.mode}{detail}, conf={decision.confidence:.2f}]")


@agents_app.command("dispatch")
def agents_dispatch(
    text: str = typer.Argument(..., help="Prompt to route AND send."),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    mode: str = typer.Option(
        None,
        "--mode",
        help=(
            "ExecutionMode override (oneshot | converse | project | "
            "orchestrated). Default: orchestrated or .aptdata/ default_mode."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show the routing decision without calling send().",
    ),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Route a prompt to the best agent and send it (route + send in one).

    Execution mode: ``orchestrated`` (default). ``--dry-run`` prints the
    ``RouteDecision`` without dispatching.
    """
    console = SmartConsole(json_mode=json_mode)
    resolved_mode = _resolve_mode(file, mode, "agents", "dispatch")
    router = _load_router(file)

    if dry_run:
        # Dry-run: route only, no run_context (plan-only, consistent with `route` cmd).
        decision = router.route(text)
        if decision.agent_id is None:
            if json_mode:
                print(
                    json.dumps(
                        {
                            **decision.to_dict(),
                            "routing_mode": decision.mode,
                            "mode": str(resolved_mode),
                            "dry_run": True,
                            "ok": False,
                            "error": "no agent available",
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            else:
                console.error("No agent available to handle this prompt.")
            raise typer.Exit(1)

        payload = {
            **decision.to_dict(),
            "routing_mode": decision.mode,
            "mode": str(resolved_mode),
            "dry_run": True,
            "ok": True,
            "would_send": True,
        }
        if json_mode:
            print(json.dumps(payload, ensure_ascii=False), flush=True)
        else:
            skill = f" via {decision.skill}" if decision.skill else ""
            print(
                f"[dry-run] would dispatch to {decision.agent_id} "
                f"[{decision.mode}{skill}, conf={decision.confidence:.2f}]"
            )
        return

    # Real dispatch: wrap routing + send so that routing.decision + agent.*
    # share the same run_id (critical for correlation in obs/observability).
    with Observer.get().run_context():
        decision = router.route(text)
        if decision.agent_id is None:
            if json_mode:
                print(
                    json.dumps(
                        {
                            **decision.to_dict(),
                            "routing_mode": decision.mode,
                            "mode": str(resolved_mode),
                            "ok": False,
                            "error": "no agent available",
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            else:
                console.error("No agent available to handle this prompt.")
            raise typer.Exit(1)

        agent = router.registry.get(decision.agent_id)
        result = observed_send(agent, decision.text)

    if json_mode:
        payload = {
            "mode": str(resolved_mode),
            "routed_to": decision.agent_id,
            "routing_mode": decision.mode,
            **result.to_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False), flush=True)
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
        print(json.dumps({"capability": capability, "agent": agent.id}), flush=True)
    else:
        print(f"{capability} -> {agent.id}")
