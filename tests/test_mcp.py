"""Tests for the MCP server integration (smart_data.mcp.server)."""

from __future__ import annotations

import json

from pydantic.dataclasses import dataclass as pydantic_dataclass

from smart_data.core.system import BaseSystem
from smart_data.mcp.server import (
    get_dataset_schema,
    list_registered_systems,
    mcp,
    run_flow,
)
from smart_data.plugins import registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pydantic_dataclass
class _MCPMockSystem(BaseSystem):
    def __post_init__(self) -> None:
        self._flows: list = []

    def register_flow(self, flow: object) -> None:
        self._flows.append(flow)

    def run(self) -> None:
        pass  # no-op for tests


# Register a system specifically for MCP tests
registry.register("mcp_test_pipeline", _MCPMockSystem)


# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------


class TestFastMCPInstance:
    def test_mcp_instance_name(self) -> None:
        assert mcp.name == "smart-data"

    def test_mcp_has_registered_tools(self) -> None:
        tools = mcp._tool_manager.list_tools()
        tool_names = [t.name for t in tools]
        assert "run_flow" in tool_names
        assert "list_registered_systems" in tool_names


# ---------------------------------------------------------------------------
# run_flow tool
# ---------------------------------------------------------------------------


class TestRunFlowTool:
    def test_run_known_flow_returns_completed(self) -> None:
        result = run_flow(flow_id="mcp_test_pipeline")
        assert isinstance(result, dict)
        assert result["status"] == "completed"
        assert result["flow_id"] == "mcp_test_pipeline"
        assert "elapsed_seconds" in result

    def test_run_unknown_flow_returns_error(self) -> None:
        result = run_flow(flow_id="nonexistent_flow")
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert result["flow_id"] == "nonexistent_flow"
        assert "not found" in result["error"]

    def test_run_flow_exception_does_not_propagate(self) -> None:
        """Internal exceptions must be caught and returned as error dicts."""

        @pydantic_dataclass
        class _FailSystem(BaseSystem):
            def __post_init__(self) -> None:
                self._flows: list = []

            def register_flow(self, flow: object) -> None:
                self._flows.append(flow)

            def run(self) -> None:
                raise RuntimeError("boom")

        registry.register("_fail_system", _FailSystem)
        result = run_flow(flow_id="_fail_system")
        assert result["status"] == "error"
        assert "boom" in result["error"]

    def test_run_flow_return_types(self) -> None:
        """Ensure strict typing of the return dict."""
        result = run_flow(flow_id="mcp_test_pipeline")
        assert isinstance(result["status"], str)
        assert isinstance(result["flow_id"], str)
        assert isinstance(result["elapsed_seconds"], float)


# ---------------------------------------------------------------------------
# list_registered_systems tool
# ---------------------------------------------------------------------------


class TestListRegisteredSystems:
    def test_returns_dict_with_systems_key(self) -> None:
        result = list_registered_systems()
        assert isinstance(result, dict)
        assert "systems" in result
        assert "count" in result

    def test_contains_registered_pipeline(self) -> None:
        result = list_registered_systems()
        assert "mcp_test_pipeline" in result["systems"]

    def test_count_matches_list_length(self) -> None:
        result = list_registered_systems()
        assert result["count"] == len(result["systems"])


# ---------------------------------------------------------------------------
# dataset resource
# ---------------------------------------------------------------------------


class TestDatasetResource:
    def test_resource_returns_valid_json(self) -> None:
        raw = get_dataset_schema("sales")
        data = json.loads(raw)
        assert data["dataset"] == "sales"
        assert isinstance(data["fields"], list)

    def test_resource_placeholder_description(self) -> None:
        raw = get_dataset_schema("users")
        data = json.loads(raw)
        assert "users" in data["description"]


# ---------------------------------------------------------------------------
# CLI mcp-start command (unit-level)
# ---------------------------------------------------------------------------


class TestMCPStartCommand:
    def test_help(self) -> None:
        from typer.testing import CliRunner

        from smart_data.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["mcp-start", "--help"])
        assert result.exit_code == 0
        assert "transport" in result.output.lower()
