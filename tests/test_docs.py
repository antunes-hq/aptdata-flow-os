"""Tests for AI-friendly documentation files (docs/llms.txt, docs/llms-full.txt)."""

from __future__ import annotations

import re
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


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
