"""FastMCP server exposing smart-data tools and resources.

The server allows AI agents (Claude Desktop, Copilot, Devin, …) to discover
and execute smart-data pipelines via the Model Context Protocol.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

from mcp.server.fastmcp import FastMCP

from smart_data.plugins import registry
from smart_data.plugins.local_fs import CSVReader, CSVWriter, JSONReader, JSONWriter, ParquetReader, ParquetWriter
from smart_data.plugins.manager import plugin_manager
from smart_data.plugins.postgres import PostgresReader, PostgresWriter
from smart_data.plugins.rest import APIReader
from smart_data.telemetry.instrumentation import mask_telemetry_value

mcp = FastMCP("smart-data")
_MCP_REQUEST_COUNT = 0
_MCP_REQUEST_LOCK = Lock()


def _mark_request() -> None:
    global _MCP_REQUEST_COUNT
    with _MCP_REQUEST_LOCK:
        _MCP_REQUEST_COUNT += 1


def get_mcp_status() -> dict[str, Any]:
    """Return MCP activity status for TUI and diagnostics."""
    with _MCP_REQUEST_LOCK:
        request_count = _MCP_REQUEST_COUNT
    return {"active": True, "request_count": request_count}


def _register_builtin_plugins() -> None:
    plugin_manager.register_reader("csv_reader", CSVReader)
    plugin_manager.register_reader("json_reader", JSONReader)
    plugin_manager.register_reader("parquet_reader", ParquetReader)
    plugin_manager.register_reader("api_reader", APIReader)
    plugin_manager.register_reader("postgres_reader", PostgresReader)
    plugin_manager.register_writer("csv_writer", CSVWriter)
    plugin_manager.register_writer("json_writer", JSONWriter)
    plugin_manager.register_writer("parquet_writer", ParquetWriter)
    plugin_manager.register_writer("postgres_writer", PostgresWriter)


_register_builtin_plugins()


@mcp.tool()
def run_flow(flow_id: str) -> dict[str, Any]:
    """Execute a registered flow/system and return its status.

    Parameters
    ----------
    flow_id:
        The identifier of a system previously registered in the plugin
        registry (e.g. ``"pipeline_x"``).

    Returns
    -------
    dict
        A status dict with keys ``status``, ``flow_id``, and
        ``elapsed_seconds`` on success, or ``status`` and ``error`` on
        failure.
    """
    _mark_request()
    started_at = time.time()
    try:
        system_cls = registry.get(flow_id)
        if system_cls is None:
            return {
                "status": "error",
                "flow_id": flow_id,
                "error": f"Flow '{flow_id}' not found in registry.",
            }
        instance = system_cls(system_id=flow_id)
        instance.run()
        elapsed = round(time.time() - started_at, 3)
        return {
            "status": "completed",
            "flow_id": flow_id,
            "elapsed_seconds": elapsed,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed = round(time.time() - started_at, 3)
        return {
            "status": "error",
            "flow_id": flow_id,
            "error": str(exc),
            "elapsed_seconds": elapsed,
        }


@mcp.tool()
def list_registered_systems() -> dict[str, Any]:
    """Return the names of all systems available in the plugin registry.

    Returns
    -------
    dict
        A dict with ``systems`` (list of names) and ``count``.
    """
    _mark_request()
    systems = registry.list_systems()
    return {"systems": systems, "count": len(systems)}


@mcp.tool()
def list_available_plugins() -> dict[str, Any]:
    """Return all installed plugins grouped by readers and writers."""
    _mark_request()
    plugins = plugin_manager.list_plugins()
    return {"plugins": plugins, "count": len(plugins["readers"]) + len(plugins["writers"])}


@mcp.tool()
def get_plugin_schema(plugin_name: str) -> dict[str, Any]:
    """Return constructor argument schema for a specific plugin."""
    _mark_request()
    try:
        return plugin_manager.get_plugin_schema(plugin_name)
    except KeyError as exc:
        return {"status": "error", "error": str(exc), "plugin_name": plugin_name}


@mcp.tool()
def preview_dataset(plugin: str, **reader_config: Any) -> dict[str, Any]:
    """Execute a reader plugin and return the first five rows."""
    _mark_request()
    try:
        rows = plugin_manager.preview_dataset(plugin, **reader_config)
        return {
            "status": "ok",
            "plugin": plugin,
            "rows": mask_telemetry_value(rows),
            "format": "json",
        }
    except KeyError as exc:
        return {"status": "error", "plugin": plugin, "error": str(exc), "error_type": "KeyError"}
    except ValueError as exc:
        return {"status": "error", "plugin": plugin, "error": str(exc), "error_type": "ValueError"}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "plugin": plugin,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }


@mcp.resource("schema://datasets/{dataset_name}")
def get_dataset_schema(dataset_name: str) -> str:
    """Return metadata for a dataset registered under *dataset_name*.

    This is a placeholder resource – concrete implementations should query
    a dataset catalogue or registry.  For now it returns a JSON string
    describing the dataset name so that agents can discover schema
    information.
    """
    import json

    return json.dumps(
        {
            "dataset": dataset_name,
            "fields": [],
            "description": f"Schema metadata for '{dataset_name}' (no catalogue loaded).",
        }
    )
