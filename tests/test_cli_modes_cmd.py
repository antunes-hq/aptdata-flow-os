"""Tests for ``aptdata modes list`` (ADR-002 §2.3)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from aptdata.cli.app import app

runner = CliRunner()


class TestModesList:
    def test_text_lists_four_modes(self):
        r = runner.invoke(app, ["modes", "list"])
        assert r.exit_code == 0, r.output
        for mode in ("oneshot", "converse", "project", "orchestrated"):
            assert mode in r.output
        # cada modo mostra o comando CLI correspondente
        assert "aptdata agents send" in r.output
        assert "aptdata converse" in r.output
        assert "aptdata project run" in r.output
        assert "aptdata agents dispatch" in r.output

    def test_json_lists_four_modes(self):
        r = runner.invoke(app, ["modes", "list", "--json"])
        assert r.exit_code == 0, r.output
        data = json.loads(r.output)
        assert data["count"] == 4
        modes = {m["mode"] for m in data["modes"]}
        assert modes == {"oneshot", "converse", "project", "orchestrated"}

    def test_json_row_has_description_and_cli_command(self):
        r = runner.invoke(app, ["modes", "list", "--json"])
        assert r.exit_code == 0
        data = json.loads(r.output)
        for row in data["modes"]:
            assert {"mode", "short", "description", "cli_command"} <= set(row)
            assert row["cli_command"].startswith("aptdata ")
            assert row["description"]
            assert row["short"]
