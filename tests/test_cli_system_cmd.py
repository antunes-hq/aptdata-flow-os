"""Tests for aptdata.cli.commands.system_cmd."""

from __future__ import annotations

import json

from pydantic.dataclasses import dataclass as pydantic_dataclass
from typer.testing import CliRunner

from aptdata.cli.app import app
from aptdata.core.system import BaseSystem
from aptdata.plugins import registry

runner = CliRunner()


# ---------------------------------------------------------------------------
# Minimal system for testing
# ---------------------------------------------------------------------------


@pydantic_dataclass
class _SysA(BaseSystem):
    def __post_init__(self) -> None:
        self._flows = []

    def register_flow(self, flow):
        self._flows.append(flow)

    def run(self):
        pass


# Register at module level
registry.register("sys_cmd_test_a", _SysA)


# ---------------------------------------------------------------------------
# system list
# ---------------------------------------------------------------------------


class TestSystemList:
    def test_list_exits_0(self):
        result = runner.invoke(app, ["system", "list"])
        assert result.exit_code == 0

    def test_list_json_mode(self):
        result = runner.invoke(app, ["system", "list", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert len(lines) >= 1
        payload = json.loads(lines[0])
        assert "systems" in payload
        assert isinstance(payload["systems"], list)

    def test_list_json_contains_registered_system(self):
        result = runner.invoke(app, ["system", "list", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        payload = json.loads(lines[0])
        assert "sys_cmd_test_a" in payload["systems"]

    def test_list_rich_mode(self):
        result = runner.invoke(app, ["system", "list"])
        assert result.exit_code == 0
        # Rich output should mention the registered system
        assert "sys_cmd_test_a" in result.output


# ---------------------------------------------------------------------------
# system info
# ---------------------------------------------------------------------------


class TestSystemInfo:
    def test_info_known_system_exits_0(self):
        result = runner.invoke(app, ["system", "info", "sys_cmd_test_a"])
        assert result.exit_code == 0

    def test_info_json_mode(self):
        result = runner.invoke(app, ["system", "info", "sys_cmd_test_a", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        payload = json.loads(lines[0])
        assert payload["name"] == "sys_cmd_test_a"
        assert "class" in payload

    def test_info_unknown_system_exits_1(self):
        result = runner.invoke(app, ["system", "info", "nonexistent_system_xyz"])
        assert result.exit_code == 1

    def test_info_rich_shows_class_name(self):
        result = runner.invoke(app, ["system", "info", "sys_cmd_test_a"])
        assert result.exit_code == 0
        assert "_SysA" in result.output


# ---------------------------------------------------------------------------
# system validate
# ---------------------------------------------------------------------------


class TestSystemValidate:
    def test_validate_known_system_exits_0(self):
        result = runner.invoke(app, ["system", "validate", "sys_cmd_test_a"])
        assert result.exit_code == 0

    def test_validate_unknown_system_exits_1(self):
        result = runner.invoke(app, ["system", "validate", "nonexistent_xyz"])
        assert result.exit_code == 1

    def test_validate_success_message(self):
        result = runner.invoke(app, ["system", "validate", "sys_cmd_test_a"])
        assert result.exit_code == 0
        assert "sys_cmd_test_a" in result.output
