"""Tests for workflow abstractions."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic.dataclasses import dataclass as pydantic_dataclass

from aptdata.core.context import ExecutionContext
from aptdata.core.dataset import BaseDataset, IDataset
from aptdata.core.system import BaseComponent
from aptdata.core.workflow import BaseWorkflow, IWorkflow, WorkflowEdge, WorkflowNode


@pydantic_dataclass
class _MemDataset(BaseDataset):
    def __post_init__(self) -> None:
        self._data: Any = None

    def read(self) -> Any:
        return self._data

    def write(self, data: Any) -> None:
        self._data = data


@pydantic_dataclass
class _DoubleComponent(BaseComponent):
    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return len(inputs) == 1

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        out = _MemDataset(uri=f"memory://{self.component_id}")
        out.write([value * 2 for value in inputs[0].read()])
        return [out]


@pydantic_dataclass
class _RecordingWorkflow(BaseWorkflow):
    def before_run(self, initial_inputs: list[IDataset]) -> None:
        super().before_run(initial_inputs)
        self.context.set("hook.before_called", True)

    def after_run(self, outputs: list[IDataset]) -> None:
        super().after_run(outputs)
        self.context.set("hook.after_called", True)


class TestWorkflowPrimitives:
    def test_workflow_edge_defaults(self):
        edge = WorkflowEdge(source_id="a", target_id="b")
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.condition is None

    def test_workflow_node_defaults(self):
        component = _DoubleComponent(component_id="c1")
        node = WorkflowNode(component=component)
        assert node.component is component
        assert node.workflow is None


class TestIWorkflow:
    def test_cannot_instantiate_interface(self):
        with pytest.raises(TypeError):
            IWorkflow()  # type: ignore[abstract]

    def test_workflow_default_context(self):
        workflow = BaseWorkflow(workflow_id="wf")
        assert workflow.workflow_id == "wf"
        assert isinstance(workflow.context, ExecutionContext)

    def test_add_component_sets_back_reference(self):
        workflow = BaseWorkflow(workflow_id="wf")
        component = _DoubleComponent(component_id="c1")
        workflow.add_component(component)
        assert workflow._nodes["c1"].workflow is workflow

    def test_compile_builds_adjacency_and_order(self):
        workflow = BaseWorkflow(workflow_id="wf")
        workflow.add_component(_DoubleComponent(component_id="c1"))
        workflow.add_component(_DoubleComponent(component_id="c2"))
        workflow.connect("c1", "c2")
        workflow.compile()
        assert workflow._adjacency["c1"][0].target_id == "c2"
        assert workflow._execution_order == ["c1", "c2"]

    def test_compile_empty_workflow_raises(self):
        workflow = BaseWorkflow(workflow_id="wf")
        with pytest.raises(ValueError, match="no components"):
            workflow.compile()

    def test_compile_unknown_nodes_raise(self):
        workflow = BaseWorkflow(workflow_id="wf")
        workflow.add_component(_DoubleComponent(component_id="c1"))
        workflow.connect("missing", "c1")
        with pytest.raises(ValueError, match="Unknown source_id"):
            workflow.compile()

    def test_compile_cycle_raises(self):
        workflow = BaseWorkflow(workflow_id="wf")
        workflow.add_component(_DoubleComponent(component_id="c1"))
        workflow.add_component(_DoubleComponent(component_id="c2"))
        workflow.connect("c1", "c2")
        workflow.connect("c2", "c1")
        with pytest.raises(ValueError, match="cycle"):
            workflow.compile()

    def test_run_requires_compile(self):
        workflow = BaseWorkflow(workflow_id="wf")
        workflow.add_component(_DoubleComponent(component_id="c1"))
        dataset = _MemDataset(uri="memory://in")
        dataset.write([1])
        with pytest.raises(RuntimeError, match="not compiled"):
            workflow.run([dataset])

    def test_run_executes_components_and_hooks(self):
        workflow = _RecordingWorkflow(workflow_id="wf")
        workflow.add_component(_DoubleComponent(component_id="c1"))
        workflow.add_component(_DoubleComponent(component_id="c2"))
        workflow.connect("c1", "c2")
        workflow.compile()
        dataset = _MemDataset(uri="memory://in")
        dataset.write([1, 2, 3])
        outputs = workflow.run([dataset])
        assert outputs[0].read() == [4, 8, 12]
        assert workflow.context.get("hook.before_called") is True
        assert workflow.context.get("hook.after_called") is True
        assert workflow.context.get("workflow.last_input_count") == 1
        assert workflow.context.get("workflow.last_output_count") == 1

    def test_run_honors_edge_condition(self):
        workflow = BaseWorkflow(workflow_id="wf")
        workflow.add_component(_DoubleComponent(component_id="c1"))
        workflow.add_component(_DoubleComponent(component_id="c2"))
        workflow.connect("c1", "c2", condition=lambda outputs: False)
        workflow.compile()
        dataset = _MemDataset(uri="memory://in")
        dataset.write([1, 2])
        outputs = workflow.run([dataset])
        assert outputs[0].read() == [2, 4]
