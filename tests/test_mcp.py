"""Tests for the MCP server integration (aptdata.mcp.server)."""

from __future__ import annotations

import json

import pytest
from pydantic.dataclasses import dataclass as pydantic_dataclass

from aptdata.core.system import BaseSystem

pytest.importorskip("mcp")

from aptdata.mcp.server import (  # noqa: E402
    get_dataset_schema,
    get_mcp_status,
    get_plugin_schema,
    list_available_plugins,
    list_registered_systems,
    mcp,
    preview_dataset,
    run_flow,
)
from aptdata.plugins import registry  # noqa: E402

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
        assert mcp.name == "aptdata"

    def test_mcp_has_registered_tools(self) -> None:
        tools = mcp._tool_manager.list_tools()
        tool_names = [t.name for t in tools]
        assert "run_flow" in tool_names
        assert "list_registered_systems" in tool_names
        assert "list_available_plugins" in tool_names
        assert "get_plugin_schema" in tool_names
        assert "preview_dataset" in tool_names


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


class TestPluginExplorerTools:
    def test_list_available_plugins(self) -> None:
        result = list_available_plugins()
        assert "plugins" in result
        assert "readers" in result["plugins"]
        assert "api_reader" in result["plugins"]["readers"]

    def test_get_plugin_schema(self) -> None:
        result = get_plugin_schema("postgres_reader")
        argument_names = [arg["name"] for arg in result["arguments"]]
        assert "connection_url" in argument_names
        assert "query" in argument_names

    def test_preview_dataset_returns_error_for_missing_plugin(self) -> None:
        result = preview_dataset("unknown_reader")
        assert result["status"] == "error"

    def test_mcp_status_tracks_requests(self) -> None:
        before = get_mcp_status()["request_count"]
        list_registered_systems()
        after = get_mcp_status()["request_count"]
        assert after == before + 1


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

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["mcp-start", "--help"])
        assert result.exit_code == 0
        assert "transport" in result.output.lower()
