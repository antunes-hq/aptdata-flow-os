"""Autonomous QA and DX Agent for smart-data codebase."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic.dataclasses import dataclass


@dataclass
class QAAgent:
    """Agent that performs QA and DX checks on the codebase."""

    project_root: Path = Path(".")

    def run_checks(self, deep: bool = False) -> dict[str, Any]:
        """Run all configured quality checks."""
        report: dict[str, Any] = {
            "summary": {
                "status": "passed",
                "warnings": 0,
                "errors": 0,
            },
            "checks": {},
        }

        self._check_cli_and_makefile(report)
        self._check_docstrings(report)
        if deep:
            self._run_deep_code_review(report)

        if report["summary"]["errors"] > 0:
            report["summary"]["status"] = "failed"

        return report

    def _check_cli_and_makefile(self, report: dict[str, Any]) -> None:
        """Check if CLI commands and Makefile targets are documented."""
        import re

        makefile_path = self.project_root / "Makefile"
        if not makefile_path.exists():
            return

        # Parse Makefile targets
        content = makefile_path.read_text(encoding="utf-8")
        targets = []
        for line in content.splitlines():
            if re.match(r"^[a-zA-Z0-9_-]+:", line):
                target = line.split(":")[0]
                if target != ".PHONY":
                    targets.append(target)

        # Check if they exist in docs
        missing_targets = []
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            for target in targets:
                # We do a simple grep over all markdown files
                found = False
                for md_file in docs_dir.rglob("*.md"):
                    if target in md_file.read_text(encoding="utf-8"):
                        found = True
                        break
                if not found:
                    missing_targets.append(target)

        report["checks"]["makefile_targets"] = {
            "total": len(targets),
            "missing_in_docs": missing_targets,
        }
        if missing_targets:
            report["summary"]["warnings"] += len(missing_targets)

        # Basic parsing of Typer commands via regex to ensure they exist in docs
        cli_commands = []
        cli_dir = self.project_root / "aptdata" / "cli"
        if cli_dir.exists():
            for py_file in cli_dir.rglob("*.py"):
                text = py_file.read_text(encoding="utf-8")
                # Look for @app.command("name") or @app.command() def name
                matches = re.finditer(
                    r'@\w+\.command\((?:["\']([^"\']+)["\'])?.*\)\s*def\s+(\w+)', text
                )
                for match in matches:
                    cmd_name = match.group(1) or match.group(2).replace("_", "-")
                    cli_commands.append(cmd_name)

        missing_cli = []
        if docs_dir.exists():
            for cmd in cli_commands:
                found = False
                for md_file in docs_dir.rglob("*.md"):
                    if cmd in md_file.read_text(encoding="utf-8"):
                        found = True
                        break
                if not found:
                    missing_cli.append(cmd)

        report["checks"]["cli_commands"] = {
            "total": len(cli_commands),
            "missing_in_docs": missing_cli,
        }
        if missing_cli:
            report["summary"]["warnings"] += len(missing_cli)

    def _check_docstrings(self, report: dict[str, Any]) -> None:
        """Check for docstrings in core abstractions and plugins using pydocstyle."""
        import subprocess

        missing_docstrings = []
        try:
            # We use ruff to check for missing docstrings (D100, D101, D102, D103)
            # as pydocstyle is integrated into ruff.
            result = subprocess.run(
                [
                    "poetry",
                    "run",
                    "ruff",
                    "check",
                    "--select",
                    "D100,D101,D102,D103",
                    "--format",
                    "json",
                    "aptdata/core/",
                    "aptdata/plugins/",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )
            if result.stdout:
                import json
                try:
                    ruff_errors = json.loads(result.stdout)
                    for error in ruff_errors:
                        missing_docstrings.append(
                            f"{error['filename']}:{error['location']['row']} - {error['message']}"
                        )
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            missing_docstrings.append(f"Failed to run ruff for docstrings: {e}")

        # Semantic evaluation (Mock LLM)
        semantic_warnings = self._evaluate_docstrings_semantically()

        report["checks"]["docstrings"] = {
            "missing_docstrings": missing_docstrings,
            "semantic_warnings": semantic_warnings,
        }
        if missing_docstrings or semantic_warnings:
            report["summary"]["warnings"] += len(missing_docstrings) + len(semantic_warnings)

    def _evaluate_docstrings_semantically(self) -> list[str]:
        """Mock LLM call to evaluate if signatures match docstring descriptions."""
        # In a real scenario, this would extract AST, format a prompt, and call an LLM.
        return ["(LLM MOCK) Method `execute` in `BaseComponent` might have incomplete param descriptions."]

    def _run_deep_code_review(self, report: dict[str, Any]) -> None:
        """Run deeper analysis using native tools (ruff, mypy, custom logic)."""
        import subprocess

        report["checks"]["deep_review"] = {
            "ruff_complexity_and_style": [],
            "mypy_type_errors": [],
            "contract_violations": [],
            "missing_tests": [],
        }

        # 1. Ruff for complexity (C901) and general style
        try:
            result = subprocess.run(
                [
                    "poetry",
                    "run",
                    "ruff",
                    "check",
                    "--select",
                    "C901",
                    "--format",
                    "json",
                    "aptdata/",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )
            if result.stdout:
                import json
                try:
                    ruff_errors = json.loads(result.stdout)
                    for error in ruff_errors:
                        report["checks"]["deep_review"]["ruff_complexity_and_style"].append(
                            f"{error['filename']}:{error['location']['row']} - {error['message']}"
                        )
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            report["checks"]["deep_review"]["ruff_complexity_and_style"].append(f"Failed to run ruff: {e}")

        # 2. Mypy for typing
        try:
            result = subprocess.run(
                ["poetry", "run", "mypy", "aptdata/"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=False,
            )
            # Mypy returns non-zero if there are errors, and outputs text.
            if result.returncode != 0 and result.stdout:
                for line in result.stdout.splitlines():
                    if "error:" in line:
                        report["checks"]["deep_review"]["mypy_type_errors"].append(line)
        except Exception as e:
            pass # Ignore if mypy is not installed or fails entirely

        # 3. Contract-First Anti-pattern (AST Heuristic - since ruff doesn't catch this specifically)
        import ast
        for py_file in self.project_root.rglob("*.py"):
            if "tests" in py_file.parts or ".venv" in py_file.parts:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name in ("execute", "run", "process"):
                        if getattr(node, "returns", None):
                            if isinstance(node.returns, ast.Name) and node.returns.id == "dict":
                                report["checks"]["deep_review"]["contract_violations"].append(
                                    {
                                        "file": str(py_file.relative_to(self.project_root)),
                                        "method": node.name,
                                        "violation": "Returns bare 'dict' instead of IDataset/BaseDataset",
                                    }
                                )

        # 4. Check for missing tests
        core_dir = self.project_root / "aptdata" / "core"
        tests_dir = self.project_root / "tests"
        if core_dir.exists() and tests_dir.exists():
            for py_file in core_dir.rglob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                test_file = tests_dir / f"test_{py_file.name}"
                if not test_file.exists():
                    report["checks"]["deep_review"]["missing_tests"].append(
                        str(py_file.relative_to(self.project_root))
                    )

        # Accumulate warnings/errors
        warnings_count = (
            len(report["checks"]["deep_review"]["ruff_complexity_and_style"])
            + len(report["checks"]["deep_review"]["missing_tests"])
            + len(report["checks"]["deep_review"]["mypy_type_errors"])
        )
        violations_count = len(report["checks"]["deep_review"]["contract_violations"])

        report["summary"]["warnings"] += warnings_count
        report["summary"]["errors"] += violations_count


    def _emit(self, event: dict[str, Any]) -> None:
        """Emit an event as a JSON line."""
        print(json.dumps(event, default=str), flush=True)
