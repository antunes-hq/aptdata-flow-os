"""Tests for the ``aptdata plugins`` (plural) CLI subcommand (ADR-002 §2.4).

Distinct from ``aptdata plugin`` (singular, which manages reader/writer
plugins registered imperatively on the global ``plugin_manager``). The
plural namespace is the entry-point discovery surface — it lists what
``importlib.metadata.entry_points`` reports across the ``aptdata.*`` groups.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from aptdata.cli.app import app
from aptdata.cli.commands.plugin_cmd import ENTRY_POINT_GROUPS, _discover_entry_points

runner = CliRunner()


# ---------------------------------------------------------------------------
# Entry-point discovery helper
# ---------------------------------------------------------------------------


class TestDiscoverEntryPoints:
    def test_returns_one_record_per_built_in_agent(self):
        records = _discover_entry_points()
        agent_records = [r for r in records if r["group"] == "aptdata.agents"]
        names = {r["name"] for r in agent_records}
        assert names >= {
            "anthropic",
            "openclaw",
            "claude_code",
            "opencode",
            "placeholder",
        }

    def test_every_record_has_required_fields(self):
        records = _discover_entry_points()
        assert records, "expected at least one entry-point record"
        for record in records:
            assert set(record) >= {"group", "name", "value", "loaded", "error"}

    def test_built_in_adapters_load_successfully(self):
        records = _discover_entry_points()
        agent_records = [r for r in records if r["group"] == "aptdata.agents"]
        for record in agent_records:
            assert (
                record["loaded"] is True
            ), f"built-in {record['name']} should load: {record['error']}"
            assert record["error"] is None

    def test_all_advertised_groups_inspected(self):
        """Discovery touches every group in ENTRY_POINT_GROUPS — even empty ones."""
        records = _discover_entry_points()
        seen_groups = {r["group"] for r in records}
        # All advertised groups are at least attempted (empty groups yield no records
        # but the aptdata.agents group is non-empty so we always see at least it).
        assert "aptdata.agents" in seen_groups
        # No group outside the advertised set sneaks in
        assert seen_groups <= set(ENTRY_POINT_GROUPS)

    def test_broken_entry_point_surfaces_error(self, monkeypatch):
        """A broken entry point is reported (loaded=False, error populated)."""

        class _BrokenEP:
            name = "broken_plugin"
            value = "nonexistent.module:Thing"

            def load(self):  # noqa: ANN201
                raise ImportError("module not found")

        def _fake_eps(*, group):
            if group == "aptdata.agents":
                return [_BrokenEP()]
            return []

        monkeypatch.setattr("aptdata.cli.commands.plugin_cmd.entry_points", _fake_eps)

        records = _discover_entry_points()
        broken = next(r for r in records if r["name"] == "broken_plugin")
        assert broken["loaded"] is False
        assert "module not found" in (broken["error"] or "")

    def test_group_level_failure_reported_as_record(self, monkeypatch):
        """If entry_points() itself raises for a group, that becomes a record
        (so the CLI can surface it instead of crashing)."""

        def _broken_eps(*, group):
            if group == "aptdata.commands":
                raise RuntimeError("metadata corrupted")
            return []

        monkeypatch.setattr("aptdata.cli.commands.plugin_cmd.entry_points", _broken_eps)

        records = _discover_entry_points()
        group_error = next(
            r
            for r in records
            if r["group"] == "aptdata.commands" and r["name"] == "<group-error>"
        )
        assert group_error["loaded"] is False
        assert "metadata corrupted" in (group_error["error"] or "")


# ---------------------------------------------------------------------------
# `aptdata plugins list` CLI surface
# ---------------------------------------------------------------------------


class TestPluginsListCommand:
    def test_list_exits_0(self):
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0

    def test_list_rich_mode_lists_built_in_agents(self):
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        # Each built-in adapter should be visible in the table
        for name in ("anthropic", "openclaw", "claude_code", "opencode", "placeholder"):
            assert name in result.output

    def test_list_rich_mode_shows_group_column(self):
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        assert "aptdata.agents" in result.output

    def test_list_rich_mode_shows_status(self):
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        assert "ok" in result.output

    def test_list_json_mode_emits_one_line_per_entry_point(self):
        result = runner.invoke(app, ["plugins", "list", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert len(lines) >= 5  # at least the five built-in agents
        for line in lines:
            payload = json.loads(line)
            assert {"group", "name", "value", "loaded", "error"} <= set(payload)

    def test_list_json_contains_built_in_agents(self):
        result = runner.invoke(app, ["plugins", "list", "--json"])
        assert result.exit_code == 0
        payloads = [
            json.loads(line)
            for line in result.output.strip().splitlines()
            if line.strip()
        ]
        names = {p["name"] for p in payloads if p["group"] == "aptdata.agents"}
        assert names >= {
            "anthropic",
            "openclaw",
            "claude_code",
            "opencode",
            "placeholder",
        }

    def test_list_json_built_ins_loaded_true(self):
        result = runner.invoke(app, ["plugins", "list", "--json"])
        assert result.exit_code == 0
        payloads = [
            json.loads(line)
            for line in result.output.strip().splitlines()
            if line.strip()
        ]
        for p in payloads:
            if p["group"] == "aptdata.agents":
                assert p["loaded"] is True
                assert p["error"] is None

    def test_list_with_no_entry_points_warns(self, monkeypatch):
        """When no entry points exist at all, the CLI emits a friendly warning."""

        def _empty_eps(*, group):
            return []

        monkeypatch.setattr("aptdata.cli.commands.plugin_cmd.entry_points", _empty_eps)

        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        assert "No entry-point plugins discovered" in result.output

    def test_list_json_with_no_entry_points_emits_nothing(self, monkeypatch):
        def _empty_eps(*, group):
            return []

        monkeypatch.setattr("aptdata.cli.commands.plugin_cmd.entry_points", _empty_eps)

        result = runner.invoke(app, ["plugins", "list", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert lines == []
