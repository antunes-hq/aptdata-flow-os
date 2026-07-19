"""CLI sub-commands for agent-orchestrated projects.

``aptdata project`` turns a declarative ``*.project.yaml`` into real work:
scaffold one, preview how each task routes, then run it across agents.

Execution mode: ``project`` (ADR-002 §2.3). ``--mode`` override + ``--dry-run``
em ``run`` que mostra o plano sem executar (alias de ``plan``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from aptdata.cli.commands.agents_cmd import _resolve_file, _resolve_mode
from aptdata.cli.rendering.console import SmartConsole

project_app = typer.Typer(name="project", help="Orchestrate projects across agents.")


def _router(agents_file: str | None):
    from aptdata.agents import Router  # noqa: PLC0415

    return Router.from_yaml(_resolve_file(agents_file))


def _load_project(path: str):
    from aptdata.agents import Project  # noqa: PLC0415

    p = Path(path).expanduser()
    if not p.exists():
        raise typer.BadParameter(f"Project file not found: {p}")
    return Project.from_yaml(p)


@project_app.command("init")
def project_init(
    name: str = typer.Argument(..., help="Project name."),
    out: str = typer.Option(None, "--out", "-o", help="Output path."),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Scaffold a starter ``<name>.project.yaml``."""
    from aptdata.agents import scaffold_project  # noqa: PLC0415

    console = SmartConsole(json_mode=json_mode)
    path = Path(out or f"{name}.project.yaml").expanduser()
    if path.exists():
        console.error(f"{path} already exists; refusing to overwrite.")
        raise typer.Exit(1)

    project = scaffold_project(name)
    project.to_yaml(path)
    if json_mode:
        print(
            json.dumps({"created": str(path), "tasks": len(project.tasks)}), flush=True
        )
    else:
        print(f"✓ {path} ({len(project.tasks)} tasks)")


@project_app.command("plan")
def project_plan(
    project_file: str = typer.Argument(..., help="Path to *.project.yaml."),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    mode: str = typer.Option(
        None,
        "--mode",
        help=("ExecutionMode override. Default: project or .aptdata/ default_mode."),
    ),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Dry-run: show which agent each task routes to (nothing is sent).

    ``plan`` é o dry-run nativo do modo ``project`` — sempre plan-only.
    """
    from aptdata.agents import ProjectRunner  # noqa: PLC0415

    resolved_mode = _resolve_mode(file, mode, "project", "plan")
    project = _load_project(project_file)
    runner = ProjectRunner(project, _router(file))
    results = runner.plan()

    if json_mode:
        payload: dict[str, Any] = {
            "mode": str(resolved_mode),
            "dry_run": True,
            "project": project.name,
            "plan": [r.to_dict() for r in results],
        }
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return
    print(f"📋 {project.name} — {len(results)} tasks")
    for r in results:
        target = r.agent_id or "(sem rota)"
        print(f"  {r.task_id:<12} → {target:<10} [{r.mode}]")


@project_app.command("run")
def project_run(
    project_file: str = typer.Argument(..., help="Path to *.project.yaml."),
    file: str = typer.Option(None, "--file", "-f", help="Path to agents.yaml."),
    mode: str = typer.Option(
        None,
        "--mode",
        help=(
            "ExecutionMode override (oneshot | converse | project | "
            "orchestrated). Default: project or .aptdata/ default_mode."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Plan-only: show the routed tasks without executing any send.",
    ),
    json_mode: bool = typer.Option(False, "--json", help="Emit JSON lines."),
) -> None:
    """Execute every task, routing and sending to the chosen agents.

    Execution mode: ``project`` (default). ``--dry-run`` aliases ``plan``
    (mesmo output, sem despachar nenhum send).
    """
    from aptdata.agents import ProjectRunner  # noqa: PLC0415

    resolved_mode = _resolve_mode(file, mode, "project", "run")
    project = _load_project(project_file)
    runner = ProjectRunner(project, _router(file))

    if dry_run:
        results = runner.plan()
        if json_mode:
            payload = {
                "mode": str(resolved_mode),
                "dry_run": True,
                "project": project.name,
                "plan": [r.to_dict() for r in results],
            }
            print(json.dumps(payload, ensure_ascii=False), flush=True)
        else:
            print(f"📋 [dry-run] {project.name} — {len(results)} tasks")
            for r in results:
                target = r.agent_id or "(sem rota)"
                print(f"  {r.task_id:<12} → {target:<10} [{r.mode}]")
        return

    results = runner.run()
    ok = sum(1 for r in results if r.ok)

    if json_mode:
        payload = {
            "mode": str(resolved_mode),
            "project": project.name,
            "ok": ok,
            "total": len(results),
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    else:
        print(f"▶ {project.name} — {ok}/{len(results)} ok")
        for r in results:
            mark = "✓" if r.ok else ("∅" if r.skipped else "✗")
            detail = r.error or (r.text[:60] if r.text else "")
            print(f"  {mark} {r.task_id:<12} {r.agent_id or '-':<10} {detail}")

    if ok < len(results):
        raise typer.Exit(1)
