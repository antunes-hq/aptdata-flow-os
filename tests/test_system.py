"""Tests for the System, Component, and Flow abstractions."""

from __future__ import annotations

from typing import Any, Callable

import pytest
from pydantic.dataclasses import dataclass as pydantic_dataclass

from smart_data.core.dataset import BaseDataset, IDataset
from smart_data.core.system import (
    BaseComponent,
    BaseFlow,
    BaseSystem,
    ComponentKind,
    ComponentMeta,
    FlowEdge,
    FlowNode,
    IComponent,
    IFlow,
    ISystem,
)


# ---------------------------------------------------------------------------
# Minimal concrete helpers used only within tests
# ---------------------------------------------------------------------------


@pydantic_dataclass
class _MemDataset(BaseDataset):
    """In-memory dataset for testing."""

    def __post_init__(self) -> None:
        self._data: Any = None

    def read(self) -> Any:
        return self._data

    def write(self, data: Any) -> None:
        self._data = data


@pydantic_dataclass
class _DoubleComponent(BaseComponent):
    """Component that doubles every element in a list dataset."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return len(inputs) == 1

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        data = inputs[0].read()
        out = _MemDataset(uri="memory://output", schema_metadata={"type": "list"})
        out.write([x * 2 for x in data])
        return [out]


@pydantic_dataclass
class _SimpleFlow(BaseFlow):
    """A flat, sequential flow used for testing."""

    def __post_init__(self) -> None:
        self._nodes: dict[str, FlowNode] = {}
        self._edges: list[FlowEdge] = []
        self._compiled: bool = False
        self._order: list[str] = []

    def add_component(self, component: IComponent) -> None:
        node = FlowNode(component=component, flow=self)
        self._nodes[component.component_id] = node

    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[list[IDataset]], bool] | None = None,
    ) -> None:
        self._edges.append(FlowEdge(source_id=source_id, target_id=target_id, condition=condition))

    def compile(self) -> None:
        """Build a topological execution order (simple linear walk for tests)."""
        if not self._nodes:
            raise ValueError("Flow has no components.")
        # validate all edge endpoints exist
        for edge in self._edges:
            if edge.source_id not in self._nodes:
                raise ValueError(f"Unknown source_id: {edge.source_id!r}")
            if edge.target_id not in self._nodes:
                raise ValueError(f"Unknown target_id: {edge.target_id!r}")
        # derive execution order: nodes not referenced as a target come first
        targets = {e.target_id for e in self._edges}
        roots = [cid for cid in self._nodes if cid not in targets]
        order: list[str] = []
        queue = list(roots)
        while queue:
            current = queue.pop(0)
            order.append(current)
            for edge in self._edges:
                if edge.source_id == current:
                    queue.append(edge.target_id)
        self._order = order
        self._compiled = True

    def run(self, initial_inputs: list[IDataset]) -> list[IDataset]:
        if not self._compiled:
            raise RuntimeError("Flow not compiled.")
        outputs = initial_inputs
        for cid in self._order:
            component = self._nodes[cid].component
            if component.validate_inputs(outputs):
                outputs = component.execute(outputs)
        return outputs


@pydantic_dataclass
class _SimpleSystem(BaseSystem):
    """A simple system that runs flows sequentially."""

    def __post_init__(self) -> None:
        self._flows: list[IFlow] = []

    def register_flow(self, flow: IFlow) -> None:
        self._flows.append(flow)

    def run(self) -> None:
        ds = _MemDataset(uri="memory://input")
        ds.write([1, 2, 3])
        inputs: list[IDataset] = [ds]
        for flow in self._flows:
            inputs = flow.run(inputs)


# ---------------------------------------------------------------------------
# ComponentMeta / ComponentKind tests
# ---------------------------------------------------------------------------


class TestComponentMeta:
    def test_default_values(self):
        meta = ComponentMeta()
        assert meta.kind == ComponentKind.CUSTOM
        assert meta.tags == []
        assert meta.branch_on == ""
        assert meta.description == ""
        assert meta.extra == {}

    def test_explicit_values(self):
        meta = ComponentMeta(
            kind=ComponentKind.TRANSFORM,
            tags=["etl", "prod"],
            branch_on="status",
            description="Doubles the data.",
            extra={"owner": "team-a"},
        )
        assert meta.kind == ComponentKind.TRANSFORM
        assert "etl" in meta.tags
        assert meta.branch_on == "status"
        assert meta.description == "Doubles the data."
        assert meta.extra["owner"] == "team-a"

    def test_component_kind_values(self):
        assert ComponentKind.TRANSFORM == "transform"
        assert ComponentKind.FILTER == "filter"
        assert ComponentKind.AGGREGATE == "aggregate"
        assert ComponentKind.EXTRACT == "extract"
        assert ComponentKind.LOAD == "load"
        assert ComponentKind.CUSTOM == "custom"


# ---------------------------------------------------------------------------
# IComponent / BaseComponent tests
# ---------------------------------------------------------------------------


class TestIComponent:
    def test_cannot_instantiate_interface(self):
        with pytest.raises(TypeError):
            IComponent()  # type: ignore[abstract]

    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            BaseComponent(component_id="c1")  # type: ignore[abstract]

    def test_component_id_field(self):
        comp = _DoubleComponent(component_id="double")
        assert comp.component_id == "double"

    def test_default_metadata(self):
        comp = _DoubleComponent(component_id="c1")
        assert isinstance(comp.meta, ComponentMeta)
        assert comp.meta.kind == ComponentKind.CUSTOM

    def test_custom_metadata(self):
        meta = ComponentMeta(kind=ComponentKind.TRANSFORM, tags=["test"])
        comp = _DoubleComponent(component_id="c1", metadata=meta)
        assert comp.meta.kind == ComponentKind.TRANSFORM
        assert "test" in comp.meta.tags

    def test_validate_inputs_valid(self):
        ds = _MemDataset(uri="memory://in")
        comp = _DoubleComponent(component_id="c1")
        assert comp.validate_inputs([ds]) is True

    def test_validate_inputs_invalid(self):
        comp = _DoubleComponent(component_id="c1")
        assert comp.validate_inputs([]) is False

    def test_execute_returns_list(self):
        ds = _MemDataset(uri="memory://in")
        ds.write([1, 2, 3])
        comp = _DoubleComponent(component_id="c1")
        result = comp.execute([ds])
        assert isinstance(result, list)
        assert result[0].read() == [2, 4, 6]

    def test_concrete_is_instance_of_interface(self):
        comp = _DoubleComponent(component_id="c1")
        assert isinstance(comp, IComponent)
        assert isinstance(comp, BaseComponent)


# ---------------------------------------------------------------------------
# FlowEdge / FlowNode tests
# ---------------------------------------------------------------------------


class TestFlowEdge:
    def test_basic_edge(self):
        edge = FlowEdge(source_id="a", target_id="b")
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.condition is None

    def test_conditional_edge(self):
        cond = lambda outputs: len(outputs) > 0  # noqa: E731
        edge = FlowEdge(source_id="a", target_id="b", condition=cond)
        ds = _MemDataset(uri="memory://x")
        assert edge.condition is not None
        assert edge.condition([ds]) is True
        assert edge.condition([]) is False


class TestFlowNode:
    def test_flow_node_back_ref(self):
        comp = _DoubleComponent(component_id="c1")
        node = FlowNode(component=comp)
        assert node.component is comp
        assert node.flow is None


# ---------------------------------------------------------------------------
# IFlow / BaseFlow tests
# ---------------------------------------------------------------------------


class TestIFlow:
    def test_cannot_instantiate_interface(self):
        with pytest.raises(TypeError):
            IFlow()  # type: ignore[abstract]

    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            BaseFlow(flow_id="f1")  # type: ignore[abstract]

    def test_flow_id_field(self):
        flow = _SimpleFlow(flow_id="f1")
        assert flow.flow_id == "f1"

    def test_add_component(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        assert "c1" in flow._nodes

    def test_connect_creates_edge(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.add_component(_DoubleComponent(component_id="c2"))
        flow.connect("c1", "c2")
        assert len(flow._edges) == 1
        assert flow._edges[0].source_id == "c1"
        assert flow._edges[0].target_id == "c2"

    def test_compile_single_node(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.compile()
        assert flow._compiled is True
        assert flow._order == ["c1"]

    def test_compile_rejects_unknown_source(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.connect("unknown", "c1")
        with pytest.raises(ValueError, match="Unknown source_id"):
            flow.compile()

    def test_compile_rejects_unknown_target(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.connect("c1", "unknown")
        with pytest.raises(ValueError, match="Unknown target_id"):
            flow.compile()

    def test_compile_empty_flow_raises(self):
        flow = _SimpleFlow(flow_id="f1")
        with pytest.raises(ValueError, match="no components"):
            flow.compile()

    def test_run_without_compile_raises(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        ds = _MemDataset(uri="memory://in")
        ds.write([1])
        with pytest.raises(RuntimeError, match="not compiled"):
            flow.run([ds])

    def test_run_doubles_values(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.compile()
        ds = _MemDataset(uri="memory://in")
        ds.write([1, 2, 3])
        result = flow.run([ds])
        assert result[0].read() == [2, 4, 6]

    def test_run_chained_components(self):
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.add_component(_DoubleComponent(component_id="c2"))
        flow.connect("c1", "c2")
        flow.compile()
        ds = _MemDataset(uri="memory://in")
        ds.write([1, 2, 3])
        result = flow.run([ds])
        assert result[0].read() == [4, 8, 12]

    def test_concrete_is_instance_of_interface(self):
        flow = _SimpleFlow(flow_id="f1")
        assert isinstance(flow, IFlow)
        assert isinstance(flow, BaseFlow)


# ---------------------------------------------------------------------------
# ISystem / BaseSystem tests
# ---------------------------------------------------------------------------


class TestISystem:
    def test_cannot_instantiate_interface(self):
        with pytest.raises(TypeError):
            ISystem()  # type: ignore[abstract]

    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            BaseSystem(system_id="s1")  # type: ignore[abstract]

    def test_system_id_field(self):
        system = _SimpleSystem(system_id="s1")
        assert system.system_id == "s1"

    def test_register_flow(self):
        system = _SimpleSystem(system_id="s1")
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.compile()
        system.register_flow(flow)
        assert len(system._flows) == 1

    def test_run_executes_flows(self):
        system = _SimpleSystem(system_id="s1")
        flow = _SimpleFlow(flow_id="f1")
        flow.add_component(_DoubleComponent(component_id="c1"))
        flow.compile()
        system.register_flow(flow)
        system.run()  # should not raise

    def test_concrete_is_instance_of_interface(self):
        system = _SimpleSystem(system_id="s1")
        assert isinstance(system, ISystem)
        assert isinstance(system, BaseSystem)
