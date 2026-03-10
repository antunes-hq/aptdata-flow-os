"""Tests for aptdata.cli.commands.plugin_cmd."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from aptdata.cli.app import app
from aptdata.plugins import plugin_manager
from aptdata.plugins.base import BaseReader, BaseWriter
from aptdata.plugins.dataset import InMemoryDataset

runner = CliRunner()


# ---------------------------------------------------------------------------
# Minimal plugins for testing
# ---------------------------------------------------------------------------


class _MockReader(BaseReader):
    def __init__(self) -> None:
        pass

    def read(self) -> InMemoryDataset:
        ds = InMemoryDataset(uri="memory://mock", schema_metadata={})
        ds.write([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])
        return ds


class _MockWriter(BaseWriter):
    def __init__(self, target: str = "default") -> None:
        self.target = target

    def write(self, dataset) -> None:
        pass


# Register at module level
plugin_manager.register_reader("test_mock_reader", _MockReader)
plugin_manager.register_writer("test_mock_writer", _MockWriter)


# ---------------------------------------------------------------------------
# plugin list
# ---------------------------------------------------------------------------


class TestPluginList:
    def test_list_exits_0(self):
        result = runner.invoke(app, ["plugin", "list"])
        assert result.exit_code == 0

    def test_list_json_mode(self):
        result = runner.invoke(app, ["plugin", "list", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert len(lines) >= 1
        payload = json.loads(lines[0])
        assert "readers" in payload
        assert "writers" in payload

    def test_list_json_contains_reader(self):
        result = runner.invoke(app, ["plugin", "list", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        payload = json.loads(lines[0])
        assert "test_mock_reader" in payload["readers"]

    def test_list_json_contains_writer(self):
        result = runner.invoke(app, ["plugin", "list", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        payload = json.loads(lines[0])
        assert "test_mock_writer" in payload["writers"]

    def test_list_rich_shows_reader(self):
        result = runner.invoke(app, ["plugin", "list"])
        assert result.exit_code == 0
        assert "test_mock_reader" in result.output


# ---------------------------------------------------------------------------
# plugin inspect
# ---------------------------------------------------------------------------


class TestPluginInspect:
    def test_inspect_reader_exits_0(self):
        result = runner.invoke(app, ["plugin", "inspect", "test_mock_reader"])
        assert result.exit_code == 0

    def test_inspect_json_mode(self):
        result = runner.invoke(app, ["plugin", "inspect", "test_mock_reader", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        payload = json.loads(lines[0])
        assert payload["name"] == "test_mock_reader"
        assert payload["type"] == "reader"
        assert "arguments" in payload

    def test_inspect_writer_exits_0(self):
        result = runner.invoke(app, ["plugin", "inspect", "test_mock_writer"])
        assert result.exit_code == 0

    def test_inspect_writer_json_has_args(self):
        result = runner.invoke(app, ["plugin", "inspect", "test_mock_writer", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        payload = json.loads(lines[0])
        assert payload["type"] == "writer"
        # _MockWriter has 'target' arg with a default
        args = {a["name"]: a for a in payload["arguments"]}
        assert "target" in args
        assert args["target"]["required"] is False

    def test_inspect_unknown_exits_1(self):
        result = runner.invoke(app, ["plugin", "inspect", "no_such_plugin_xyz"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# plugin load
# ---------------------------------------------------------------------------


class TestPluginLoad:
    def test_load_stdlib_module(self):
        result = runner.invoke(app, ["plugin", "load", "json"])
        assert result.exit_code == 0
        assert "json" in result.output

    def test_load_nonexistent_module_exits_1(self):
        result = runner.invoke(app, ["plugin", "load", "nonexistent_module_xyz_abc"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# plugin preview
# ---------------------------------------------------------------------------


class TestPluginPreview:
    def test_preview_reader_exits_0(self):
        result = runner.invoke(app, ["plugin", "preview", "test_mock_reader"])
        assert result.exit_code == 0

    def test_preview_unknown_reader_exits_1(self):
        result = runner.invoke(app, ["plugin", "preview", "no_such_reader_xyz"])
        assert result.exit_code == 1
