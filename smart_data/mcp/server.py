"""FastMCP server exposing smart-data tools and resources.

The server allows AI agents (Claude Desktop, Copilot, Devin, …) to discover
and execute smart-data pipelines via the Model Context Protocol.
"""

from __future__ import annotations

import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from smart_data.plugins import registry

mcp = FastMCP("smart-data")


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
    systems = registry.list_systems()
    return {"systems": systems, "count": len(systems)}


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
