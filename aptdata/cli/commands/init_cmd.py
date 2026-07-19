"""``aptdata init`` — scaffold the ``.aptdata/`` dotdir (ADR-002 §2.2/§4.1).

Two modes:

* ``aptdata init`` — creates ``.aptdata/`` at the project root with starter
  ``system.yaml`` / ``agents.yaml`` / ``config.yaml`` and the three versioned
  JSON Schemas under ``.aptdata/schemas/``.
* ``aptdata init --migrate`` — moves legacy root-level ``aptdata.yaml`` and
  ``agents.yaml`` into ``.aptdata/`` (renaming ``aptdata.yaml`` to
  ``system.yaml``) and then writes the schemas. Per ADR-002 §4.1 (exceção Q6),
  migration is **immediate**: there is no dual-read fallback. After
  ``--migrate`` only the dotdir is read by the framework.

The command refuses to clobber existing files by default; ``--force``
overwrites. ``--json`` emits one JSON line per action taken (machine-friendly).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import typer

from aptdata.cli.rendering.console import SmartConsole
from aptdata.config.loader import (
    APTDATA_DIR_NAME,
    LEGACY_TO_DOTDIR,
    ProjectConfig,
    detect_legacy_files,
    locate_project_optional,
)
from aptdata.config.schema import write_all_schemas

init_app = typer.Typer(name="init", help="Create the .aptdata/ dotdir for a project.")


# ---------------------------------------------------------------------------
# Starter templates
# ---------------------------------------------------------------------------


_STARTER_SYSTEM_YAML = """\
# .aptdata/system.yaml — system manifest (ADR-002 §2.2)
# Replaces the legacy root-level aptdata.yaml. Consumed by YamlSystemBuilder.
system:
  id: default
  flows: []
imports: []
"""

_STARTER_AGENTS_YAML = """\
# .aptdata/agents.yaml — agent registry + routing (ADR-002 §2.2)
# Replaces the legacy root-level agents.yaml. Consumed by AgentRegistry / Router
# / ConversationEngine. Validates against .aptdata/schemas/agents.json.
agents: {}
skills: []
routing:
  dispatch_above: 0.75
  guarded_capabilities: [deploy, ssh, docker, ops]
transports: {}
# ADR-002 §2.3 — modo de execução canônico do projeto. Quando setado, é o
# default do --mode em todos os comandos de execução do CLI (oneshot |
# converse | project | orchestrated). Omita para usar o default de cada
# comando (send=oneshot, converse=converse, project run=project, dispatch=orchestrated).
# default_mode: oneshot
"""

_STARTER_CONFIG_YAML = """\
# .aptdata/config.yaml — declarative pipeline config (ADR-002 §2.2)
# Validates against .aptdata/schemas/config.json.
metadata: {}
system:
  system_id: default
  flows: []
"""


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------


def _migrate_legacy_files(
    root: Path, project: ProjectConfig, *, force: bool
) -> list[dict[str, Any]]:
    """Move legacy root-level YAMLs into ``.aptdata/``.

    Returns a list of action records (one per file moved) for the JSON log.
    """
    actions: list[dict[str, Any]] = []
    legacy = detect_legacy_files(root)
    if not legacy:
        return actions

    for legacy_path_str, legacy_path in legacy.items():
        target_name = LEGACY_TO_DOTDIR[Path(legacy_path_str).name]
        target = project.aptdata_dir / target_name
        if target.is_file() and not force:
            actions.append(
                {
                    "action": "skip",
                    "from": str(legacy_path),
                    "to": str(target),
                    "reason": "target exists; use --force to overwrite",
                }
            )
            continue
        # Move (not copy) — migration is destructive by design (single source).
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy_path), str(target))
        actions.append(
            {"action": "migrate", "from": str(legacy_path), "to": str(target)}
        )
    return actions


def _write_starter_files(
    project: ProjectConfig, *, force: bool
) -> list[dict[str, Any]]:
    """Write starter ``system/agents/config.yaml`` when absent (or with --force)."""
    actions: list[dict[str, Any]] = []
    starters = {
        "system.yaml": _STARTER_SYSTEM_YAML,
        "agents.yaml": _STARTER_AGENTS_YAML,
        "config.yaml": _STARTER_CONFIG_YAML,
    }
    for name, content in starters.items():
        target = project.aptdata_dir / name
        if target.is_file() and not force:
            actions.append(
                {"action": "keep", "path": str(target), "reason": "already exists"}
            )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        actions.append({"action": "write", "path": str(target)})
    return actions


def _write_schemas(project: ProjectConfig) -> list[dict[str, Any]]:
    """(Re)generate the three JSON Schemas under ``.aptdata/schemas/``."""
    written = write_all_schemas(project.schemas_dir)
    return [
        {"action": "schema", "kind": kind, "path": str(path)}
        for kind, path in sorted(written.items())
    ]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@init_app.callback(invoke_without_command=True)
def init(
    ctx: typer.Context,
    path: Path = typer.Option(
        Path.cwd(),
        "--path",
        "-p",
        help="Project root to initialise (defaults to the current directory).",
    ),
    migrate: bool = typer.Option(
        False,
        "--migrate",
        help="Move legacy aptdata.yaml/agents.yaml at the root into .aptdata/.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing .aptdata/ files (starter files only).",
    ),
    json_mode: bool = typer.Option(
        False, "--json", help="Emit one JSON line per action taken."
    ),
) -> None:
    """Create the ``.aptdata/`` dotdir (ADR-002 §2.2).

    Without ``--migrate`` it writes starter templates (empty registry/flows).
    With ``--migrate`` it moves legacy root-level ``aptdata.yaml`` and
    ``agents.yaml`` into ``.aptdata/`` (renaming ``aptdata.yaml`` →
    ``system.yaml``). The three versioned JSON Schemas are always
    (re)generated under ``.aptdata/schemas/``.
    """
    console = SmartConsole(json_mode=json_mode)
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # Reuse an existing .aptdata/ if present (walk-up discovery), else create one.
    existing = locate_project_optional(root)
    if existing is not None and existing.root == root:
        project = existing
    elif existing is not None and existing.root != root:
        # Found a parent project — refuse to nest, point the user at it.
        msg = (
            f"Found an existing {APTDATA_DIR_NAME}/ at {existing.root}, "
            f"refusing to nest another one at {root}."
        )
        if json_mode:
            print(json.dumps({"action": "error", "error": msg}), flush=True)
        else:
            console.error(msg)
        raise typer.Exit(1)
    else:
        project = ProjectConfig(root=root, aptdata_dir=root / APTDATA_DIR_NAME)
        project.aptdata_dir.mkdir(parents=True, exist_ok=True)

    actions: list[dict[str, Any]] = []

    if migrate:
        actions.extend(_migrate_legacy_files(root, project, force=force))
    actions.extend(_write_starter_files(project, force=force))
    actions.extend(_write_schemas(project))

    # Emit a summary line for every action.
    if json_mode:
        for action in actions:
            print(json.dumps(action, default=str), flush=True)
        print(
            json.dumps(
                {
                    "action": "done",
                    "project_root": str(project.root),
                    "aptdata_dir": str(project.aptdata_dir),
                    "actions_count": len(actions),
                }
            ),
            flush=True,
        )
        return

    for action in actions:
        verb = action.get("action", "?")
        if verb == "migrate":
            console.success(f"moved {action['from']} -> {action['to']}")
        elif verb == "write":
            console.success(f"wrote {action['path']}")
        elif verb == "keep":
            console.warning(f"kept {action['path']} ({action.get('reason', '')})")
        elif verb == "skip":
            console.warning(f"skipped {action['from']} ({action.get('reason', '')})")
        elif verb == "schema":
            console.success(f"schema {action['kind']} -> {action['path']}")

    console.success(
        f"{APTDATA_DIR_NAME}/ ready at {project.aptdata_dir} "
        f"({len(actions)} action(s))."
    )
    console.print(
        "  Next: edit .aptdata/agents.yaml, then run `aptdata doctor` to validate."
    )
    if ctx.invoked_subcommand is None:
        return


__all__ = ["init_app"]
