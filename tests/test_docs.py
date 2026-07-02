"""Tests for AI-friendly documentation files (docs/llms.txt, docs/llms-full.txt)."""

from __future__ import annotations

import re
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
REPO_ROOT = DOCS_DIR.parent


class TestLlmsTxt:
    def test_file_exists(self) -> None:
        assert (DOCS_DIR / "llms.txt").exists()

    def test_starts_with_heading(self) -> None:
        content = (DOCS_DIR / "llms.txt").read_text(encoding="utf-8")
        assert content.startswith("# ")

    def test_contains_overview_section(self) -> None:
        content = (DOCS_DIR / "llms.txt").read_text(encoding="utf-8")
        assert "## Overview" in content

    def test_contains_documentation_index(self) -> None:
        content = (DOCS_DIR / "llms.txt").read_text(encoding="utf-8")
        assert "## Documentation Index" in content

    def test_relative_links_are_valid(self) -> None:
        content = (DOCS_DIR / "llms.txt").read_text(encoding="utf-8")
        # Find markdown links like [text](path.md)
        links = re.findall(r"\[.*?\]\(((?!https?://).*?\.md)\)", content)
        assert len(links) > 0, "Expected at least one relative link"
        for link in links:
            assert (DOCS_DIR / link).exists(), f"Broken link: {link}"

    def test_valid_markdown_headings(self) -> None:
        content = (DOCS_DIR / "llms.txt").read_text(encoding="utf-8")
        headings = [line for line in content.splitlines() if line.startswith("#")]
        assert len(headings) >= 3


class TestLlmsFullTxt:
    def test_file_exists(self) -> None:
        assert (DOCS_DIR / "llms-full.txt").exists()

    def test_starts_with_heading(self) -> None:
        content = (DOCS_DIR / "llms-full.txt").read_text(encoding="utf-8")
        assert content.startswith("# ")

    def test_contains_architecture_section(self) -> None:
        content = (DOCS_DIR / "llms-full.txt").read_text(encoding="utf-8")
        assert "Architecture" in content

    def test_contains_cli_reference(self) -> None:
        content = (DOCS_DIR / "llms-full.txt").read_text(encoding="utf-8")
        assert "CLI Reference" in content

    def test_contains_mcp_section(self) -> None:
        content = (DOCS_DIR / "llms-full.txt").read_text(encoding="utf-8")
        assert "MCP" in content


class TestCliDocsSync:
    """Check de sincronização docs↔CLI (docs/plans/sync-architecture.md §6).

    Docs são projeção do código: todo comando/grupo registrado no app Typer
    precisa aparecer no README e na referência de CLI. Divergência = falha.
    """

    @staticmethod
    def _cli_surface() -> set[str]:
        from aptdata.cli.app import app

        names = {
            (cmd.name or cmd.callback.__name__).replace("_", "-")
            for cmd in app.registered_commands
        }
        for group in app.registered_groups:
            names.add(group.name or group.typer_instance.info.name)
        return names

    def test_cli_surface_is_nontrivial(self) -> None:
        assert len(self._cli_surface()) >= 10

    def test_readme_documents_every_command(self) -> None:
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        missing = sorted(
            name for name in self._cli_surface() if f"aptdata {name}" not in content
        )
        assert not missing, f"Comandos ausentes no README.md: {missing}"

    def test_cli_reference_documents_every_command(self) -> None:
        content = (DOCS_DIR / "api" / "cli.md").read_text(encoding="utf-8")
        missing = sorted(
            name for name in self._cli_surface() if f"aptdata {name}" not in content
        )
        assert not missing, f"Comandos ausentes em docs/api/cli.md: {missing}"

    def test_scaffold_templates_documented(self) -> None:
        from aptdata.cli.scaffold import TEMPLATE_NAMES

        content = (DOCS_DIR / "scaffold-templates.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for name in TEMPLATE_NAMES:
            assert name in content, f"Template '{name}' fora de scaffold-templates.md"
            assert name in readme, f"Template '{name}' fora do README.md"
