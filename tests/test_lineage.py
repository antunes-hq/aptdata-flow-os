"""Tests for smart_data.core.lineage — LineageNode, ColumnLineage, LineageGraph."""

from __future__ import annotations

import pytest

from smart_data.core.lineage import (
    ColumnLineage,
    LineageEventType,
    LineageGraph,
    LineageNode,
)


class TestColumnLineage:
    def test_defaults(self) -> None:
        cl = ColumnLineage(target_column="revenue")
        assert cl.target_column == "revenue"
        assert cl.source_columns == []
        assert cl.transformation == ""
        assert cl.source_dataset_uri == ""

    def test_with_values(self) -> None:
        cl = ColumnLineage(
            target_column="revenue",
            source_columns=["price", "quantity"],
            transformation="price * quantity",
            source_dataset_uri="s3://bucket/orders.parquet",
        )
        assert cl.source_columns == ["price", "quantity"]
        assert cl.transformation == "price * quantity"


class TestLineageEventType:
    def test_all_members(self) -> None:
        expected = {"READ", "TRANSFORM", "QUALITY_CHECK", "BUSINESS_RULE", "WRITE", "SCHEMA_CHANGE"}
        assert {e.value for e in LineageEventType} == expected

    def test_string_value(self) -> None:
        assert LineageEventType.READ == "READ"


class TestLineageNode:
    def test_auto_generated_node_id(self) -> None:
        n = LineageNode(dataset_uri="memory://test", event_type=LineageEventType.READ)
        assert len(n.node_id) == 32  # UUID hex

    def test_two_nodes_have_different_ids(self) -> None:
        n1 = LineageNode(dataset_uri="memory://test", event_type=LineageEventType.READ)
        n2 = LineageNode(dataset_uri="memory://test", event_type=LineageEventType.READ)
        assert n1.node_id != n2.node_id

    def test_timestamp_is_set(self) -> None:
        n = LineageNode(dataset_uri="memory://test", event_type=LineageEventType.READ)
        assert "T" in n.timestamp  # ISO-8601 format

    def test_defaults(self) -> None:
        n = LineageNode(dataset_uri="s3://bucket/data", event_type=LineageEventType.WRITE)
        assert n.workflow_name == ""
        assert n.rows_in == 0
        assert n.rows_out == 0
        assert n.columns_in == []
        assert n.column_lineage == []
        assert n.parent_node_ids == []

    def test_to_dict_keys(self) -> None:
        n = LineageNode(
            dataset_uri="s3://bucket/data",
            event_type=LineageEventType.TRANSFORM,
            workflow_name="wf",
            step_name="step1",
            rows_in=100,
            rows_out=95,
        )
        d = n.to_dict()
        assert d["dataset_uri"] == "s3://bucket/data"
        assert d["event_type"] == "TRANSFORM"
        assert d["workflow_name"] == "wf"
        assert d["rows_in"] == 100
        assert d["rows_out"] == 95
        assert "node_id" in d
        assert "timestamp" in d

    def test_to_dict_column_lineage(self) -> None:
        cl = ColumnLineage(
            target_column="revenue",
            source_columns=["price", "qty"],
            transformation="price * qty",
        )
        n = LineageNode(
            dataset_uri="memory://test",
            event_type=LineageEventType.TRANSFORM,
            column_lineage=[cl],
        )
        d = n.to_dict()
        assert len(d["column_lineage"]) == 1
        assert d["column_lineage"][0]["target_column"] == "revenue"

    def test_serialization_roundtrip(self) -> None:
        n = LineageNode(
            dataset_uri="memory://test",
            event_type=LineageEventType.QUALITY_CHECK,
            quality_checks=["not_null_id"],
            quality_status="PASSED",
            trace_id="abc123",
        )
        d = n.to_dict()
        assert d["quality_checks"] == ["not_null_id"]
        assert d["quality_status"] == "PASSED"
        assert d["trace_id"] == "abc123"


class TestLineageGraph:
    def test_add_node(self) -> None:
        graph = LineageGraph(run_id="run-1", workflow_name="test_wf")
        n = LineageNode(dataset_uri="memory://test", event_type=LineageEventType.READ)
        graph.add_node(n)
        assert len(graph.nodes) == 1

    def test_get_upstream(self) -> None:
        graph = LineageGraph(run_id="run-1", workflow_name="wf")
        n1 = LineageNode(dataset_uri="memory://a", event_type=LineageEventType.READ)
        n2 = LineageNode(
            dataset_uri="memory://b",
            event_type=LineageEventType.TRANSFORM,
            parent_node_ids=[n1.node_id],
        )
        graph.add_node(n1)
        graph.add_node(n2)
        upstream = graph.get_upstream(n2.node_id)
        assert len(upstream) == 1
        assert upstream[0].node_id == n1.node_id

    def test_get_upstream_missing_node(self) -> None:
        graph = LineageGraph(run_id="run-1", workflow_name="wf")
        assert graph.get_upstream("nonexistent") == []

    def test_get_downstream(self) -> None:
        graph = LineageGraph(run_id="run-1", workflow_name="wf")
        n1 = LineageNode(dataset_uri="memory://a", event_type=LineageEventType.READ)
        n2 = LineageNode(
            dataset_uri="memory://b",
            event_type=LineageEventType.TRANSFORM,
            parent_node_ids=[n1.node_id],
        )
        graph.add_node(n1)
        graph.add_node(n2)
        downstream = graph.get_downstream(n1.node_id)
        assert len(downstream) == 1
        assert downstream[0].node_id == n2.node_id

    def test_get_downstream_leaf_node(self) -> None:
        graph = LineageGraph(run_id="run-1", workflow_name="wf")
        n = LineageNode(dataset_uri="memory://a", event_type=LineageEventType.WRITE)
        graph.add_node(n)
        assert graph.get_downstream(n.node_id) == []

    def test_to_dict(self) -> None:
        graph = LineageGraph(run_id="run-xyz", workflow_name="my_workflow")
        n = LineageNode(dataset_uri="memory://test", event_type=LineageEventType.READ)
        graph.add_node(n)
        d = graph.to_dict()
        assert d["run_id"] == "run-xyz"
        assert d["workflow_name"] == "my_workflow"
        assert len(d["nodes"]) == 1
        assert "started_at" in d

    def test_to_dict_empty_graph(self) -> None:
        graph = LineageGraph(run_id="run-empty", workflow_name="empty")
        d = graph.to_dict()
        assert d["nodes"] == []

    def test_chain_upstream_downstream(self) -> None:
        """A → B → C: upstream of C is B; downstream of A is B."""
        graph = LineageGraph(run_id="chain", workflow_name="wf")
        a = LineageNode(dataset_uri="memory://a", event_type=LineageEventType.READ)
        b = LineageNode(
            dataset_uri="memory://b",
            event_type=LineageEventType.TRANSFORM,
            parent_node_ids=[a.node_id],
        )
        c = LineageNode(
            dataset_uri="memory://c",
            event_type=LineageEventType.WRITE,
            parent_node_ids=[b.node_id],
        )
        for node in (a, b, c):
            graph.add_node(node)

        assert graph.get_upstream(c.node_id)[0].node_id == b.node_id
        assert graph.get_downstream(a.node_id)[0].node_id == b.node_id
        assert graph.get_downstream(b.node_id)[0].node_id == c.node_id
