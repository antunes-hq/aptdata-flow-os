"""``aptdata doctor`` — validate ``.aptdata/`` against versioned JSON Schemas.

(ADR-002 §2.4 / §2.2)

For each file in ``.aptdata/`` (``system.yaml``, ``agents.yaml``,
``config.yaml``), doctor runs ``check-jsonschema`` against the matching
versioned schema (under ``.aptdata/schemas/``). Missing files are reported
as warnings (not failures); broken schemas are reported as errors.

Exit codes
----------
* ``0`` — every present file validates.
* ``1`` — at least one file failed validation (or a required file is missing).

The command never raises: every problem is collected into a report so a
single run surfaces everything that needs fixing.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer

from aptdata.cli.rendering.console import SmartConsole
from aptdata.config.loader import (
    APTDATA_DIR_NAME,
    SCHEMA_FILES,
    ProjectConfig,
    locate_project_optional,
)

doctor_app = typer.Typer(name="doctor", help="Validate .aptdata/ against JSON Schemas.")


#: Files considered required (missing → error). config.yaml is optional — a
#: project can declare just agents without pipelines.
_REQUIRED_FILES: set[str] = {"agents.yaml"}


def _run_check_jsonschema(schema: Path, target: Path) -> tuple[bool, str]:
    """Invoke ``check-jsonschema`` as a subprocess.

    Returns ``(ok, output)``. ``output`` is the combined stdout+stderr for
    diagnostics. We use a subprocess (rather than importing the lib) so the
    command surface is identical to the pre-commit hook — same lib, same CLI,
    same error messages.
    """
    cmd = [
        sys.executable,
        "-m",
        "check_jsonschema",
        "--schemafile",
        str(schema),
        str(target),
    ]
    try:
        proc = subprocess.run(  # noqa: S603 - argv list, no shell
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        return False, f"check-jsonschema not available: {exc}"
    except subprocess.TimeoutExpired:
        return False, "check-jsonschema timed out after 30s"
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output


def run_doctor(project: ProjectConfig) -> dict[str, Any]:
    """Run validation for every ``.aptdata/`` file with a schema.

    Returns a report dict suitable for JSON output:

    ::

        {
          "ok": bool,
          "project_root": str,
          "checks": [
            {"file": "agents.yaml", "ok": true/false, "detail": "..."}
          ]
        }
    """
    checks: list[dict[str, Any]] = []

    for target_name, schema_rel in SCHEMA_FILES.items():
        target = project.aptdata_dir / target_name
        schema = project.aptdata_dir / schema_rel

        if not target.is_file():
            required = target_name in _REQUIRED_FILES
            checks.append(
                {
                    "file": target_name,
                    "ok": not required,
                    "required": required,
                    "detail": "missing"
                    + (" (required)" if required else " (optional)"),
                }
            )
            continue

        if not schema.is_file():
            checks.append(
                {
                    "file": target_name,
                    "ok": False,
                    "required": target_name in _REQUIRED_FILES,
                    "detail": (
                        f"schema missing: {schema_rel} "
                        "(run 'aptdata init' to regenerate)"
                    ),
                }
            )
            continue

        ok, output = _run_check_jsonschema(schema, target)
        checks.append(
            {
                "file": target_name,
                "ok": ok,
                "required": target_name in _REQUIRED_FILES,
                "detail": "valid" if ok else output.strip() or "validation failed",
            }
        )

    return {
        "ok": all(c["ok"] for c in checks if c.get("required")),
        "project_root": str(project.root),
        "checks": checks,
    }


@doctor_app.callback(invoke_without_command=True)
def doctor(
    ctx: typer.Context,
    path: Path = typer.Option(
        Path.cwd(),
        "--path",
        "-p",
        help="Project root to inspect (defaults to the current directory).",
    ),
    json_mode: bool = typer.Option(
        False, "--json", help="Emit the report as a single JSON line."
    ),
) -> None:
    """Validate ``.aptdata/`` against its versioned JSON Schemas.

    Walks up the tree from *path* to find the project's ``.aptdata/``.
    For each of ``system.yaml`` / ``agents.yaml`` / ``config.yaml``, runs
    ``check-jsonschema`` against the matching schema under
    ``.aptdata/schemas/``. Exits 0 when every required file validates, 1
    otherwise.
    """
    console = SmartConsole(json_mode=json_mode)
    project = locate_project_optional(Path(path).resolve())
    if project is None:
        msg = (
            f"No {APTDATA_DIR_NAME}/ directory found walking up from "
            f"{Path(path).resolve()}. Run 'aptdata init' first."
        )
        if json_mode:
            print(json.dumps({"ok": False, "error": msg}), flush=True)
        else:
            console.error(msg)
        raise typer.Exit(1)

    report = run_doctor(project)

    if json_mode:
        print(json.dumps(report, ensure_ascii=False, default=str), flush=True)
    else:
        for check in report["checks"]:
            mark = "✅" if check["ok"] else ("❌" if check.get("required") else "⚠️ ")
            console.print(f"{mark} {check['file']}: {check['detail']}")
        verdict = "doctor ok" if report["ok"] else "doctor failed"
        console.print(f"[bold]{verdict}[/bold]")

    if not report["ok"]:
        raise typer.Exit(1)
    if ctx.invoked_subcommand is None:
        return


__all__ = ["doctor_app", "run_doctor"]
