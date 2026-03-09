"""Data lineage graph for tracking dataset transformations and provenance.

Provides :class:`LineageGraph` which is built up during a workflow run and
stores :class:`LineageNode` instances that capture every read, transform,
quality-check, and write event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class LineageEventType(str, Enum):
    """Enumeration of lineage event types."""

    READ = "READ"
    TRANSFORM = "TRANSFORM"
    QUALITY_CHECK = "QUALITY_CHECK"
    BUSINESS_RULE = "BUSINESS_RULE"
    WRITE = "WRITE"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"


@dataclass
class ColumnLineage:
    """Column-level lineage mapping a target column to its source columns.

    Parameters
    ----------
    target_column:
        Name of the output column.
    source_columns:
        Names of the input columns that contributed to *target_column*.
    transformation:
        Human-readable description of the transformation applied.
    source_dataset_uri:
        URI of the dataset that contains the source columns.
    """

    target_column: str
    source_columns: list[str] = field(default_factory=list)
    transformation: str = ""
    source_dataset_uri: str = ""


@dataclass
class LineageNode:
    """A single event node in the lineage graph.

    Parameters
    ----------
    dataset_uri:
        Logical URI of the dataset involved in this event.
    event_type:
        The kind of lineage event (see :class:`LineageEventType`).
    workflow_name:
        Name of the workflow that produced this node.
    step_name:
        Name of the individual step within the workflow.
    transformer_name:
        Name of the transformer (for TRANSFORM events).
    engine:
        Processing engine (e.g. ``"pandas"`` or ``"pyspark"``).
    rows_in:
        Number of input rows.
    rows_out:
        Number of output rows.
    columns_in:
        List of input column names.
    columns_out:
        List of output column names.
    column_lineage:
        Column-level lineage mappings.
    business_rules_applied:
        IDs of business rules applied during this event.
    quality_checks:
        Names of quality checks executed.
    quality_status:
        Overall quality check outcome (e.g. ``"PASSED"`` or ``"FAILED"``).
    trace_id:
        OpenTelemetry trace identifier.
    span_id:
        OpenTelemetry span identifier.
    parent_node_ids:
        IDs of upstream :class:`LineageNode` objects.
    metadata:
        Arbitrary extra metadata.
    node_id:
        Auto-generated unique identifier (UUID hex).
    timestamp:
        UTC ISO-8601 timestamp of the event.
    """

    dataset_uri: str
    event_type: LineageEventType
    workflow_name: str = ""
    step_name: str = ""
    transformer_name: str = ""
    engine: str = ""
    rows_in: int = 0
    rows_out: int = 0
    columns_in: list[str] = field(default_factory=list)
    columns_out: list[str] = field(default_factory=list)
    column_lineage: list[ColumnLineage] = field(default_factory=list)
    business_rules_applied: list[str] = field(default_factory=list)
    quality_checks: list[str] = field(default_factory=list)
    quality_status: str = ""
    trace_id: str = ""
    span_id: str = ""
    parent_node_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    node_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this node to a plain dictionary."""
        return {
            "node_id": self.node_id,
            "dataset_uri": self.dataset_uri,
            "event_type": self.event_type.value,
            "workflow_name": self.workflow_name,
            "step_name": self.step_name,
            "transformer_name": self.transformer_name,
            "engine": self.engine,
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "columns_in": self.columns_in,
            "columns_out": self.columns_out,
            "column_lineage": [
                {
                    "target_column": cl.target_column,
                    "source_columns": cl.source_columns,
                    "transformation": cl.transformation,
                    "source_dataset_uri": cl.source_dataset_uri,
                }
                for cl in self.column_lineage
            ],
            "business_rules_applied": self.business_rules_applied,
            "quality_checks": self.quality_checks,
            "quality_status": self.quality_status,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_node_ids": self.parent_node_ids,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class LineageGraph:
    """A complete lineage graph for a single workflow run.

    Parameters
    ----------
    run_id:
        Unique identifier for the workflow run.
    workflow_name:
        Human-readable name of the workflow.
    nodes:
        Ordered list of :class:`LineageNode` objects.
    started_at:
        UTC ISO-8601 timestamp when the run started.
    """

    run_id: str
    workflow_name: str
    nodes: list[LineageNode] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_node(self, node: LineageNode) -> None:
        """Append *node* to the graph."""
        self.nodes.append(node)

    def get_upstream(self, node_id: str) -> list[LineageNode]:
        """Return all nodes that are direct parents of *node_id*.

        Nodes are considered parents when their ``node_id`` appears in
        the target node's :attr:`~LineageNode.parent_node_ids` list.
        """
        target = next((n for n in self.nodes if n.node_id == node_id), None)
        if target is None:
            return []
        parent_ids = set(target.parent_node_ids)
        return [n for n in self.nodes if n.node_id in parent_ids]

    def get_downstream(self, node_id: str) -> list[LineageNode]:
        """Return all nodes that list *node_id* as a parent."""
        return [n for n in self.nodes if node_id in n.parent_node_ids]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full graph to a plain dictionary."""
        return {
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "started_at": self.started_at,
            "nodes": [n.to_dict() for n in self.nodes],
        }


__all__ = [
    "LineageEventType",
    "ColumnLineage",
    "LineageNode",
    "LineageGraph",
]
