"""Workflow abstractions with context-aware execution hooks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from pydantic.dataclasses import dataclass as pydantic_dataclass

from smart_data.core.context import ExecutionContext
from smart_data.core.dataset import IDataset
from smart_data.core.system import IComponent


@dataclass
class WorkflowEdge:
    """A directed edge in a workflow graph."""

    source_id: str
    target_id: str
    condition: Callable[[list[IDataset]], bool] | None = None


@dataclass
class WorkflowNode:
    """A node that wraps a component inside a workflow."""

    component: IComponent
    workflow: IWorkflow | None = field(default=None, repr=False)


@dataclass
class IWorkflow(ABC):
    """Interface for workflow execution."""

    @abstractmethod
    def add_component(self, component: IComponent) -> None:
        """Add a component to the workflow."""

    @abstractmethod
    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[list[IDataset]], bool] | None = None,
    ) -> None:
        """Connect components with an optional condition."""

    @abstractmethod
    def compile(self) -> None:
        """Validate and prepare workflow execution structures."""

    @abstractmethod
    def before_run(self, initial_inputs: list[IDataset]) -> None:
        """Lifecycle hook called before execution."""

    @abstractmethod
    def after_run(self, outputs: list[IDataset]) -> None:
        """Lifecycle hook called after execution."""

    @abstractmethod
    def run(self, initial_inputs: list[IDataset]) -> list[IDataset]:
        """Execute the workflow."""


@pydantic_dataclass
class BaseWorkflow(IWorkflow):
    """Default workflow implementation with adjacency compilation and hooks."""

    workflow_id: str
    context: ExecutionContext = field(default_factory=ExecutionContext)

    def __post_init__(self) -> None:
        self._nodes: dict[str, WorkflowNode] = {}
        self._edges: list[WorkflowEdge] = []
        self._adjacency: dict[str, list[WorkflowEdge]] = {}
        self._execution_order: list[str] = []
        self._compiled = False

    def add_component(self, component: IComponent) -> None:
        self._nodes[component.component_id] = WorkflowNode(component=component, workflow=self)
        self._compiled = False

    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[list[IDataset]], bool] | None = None,
    ) -> None:
        self._edges.append(WorkflowEdge(source_id=source_id, target_id=target_id, condition=condition))
        self._compiled = False

    def compile(self) -> None:
        if not self._nodes:
            raise ValueError("Workflow has no components.")

        indegree = {component_id: 0 for component_id in self._nodes}
        adjacency: dict[str, list[WorkflowEdge]] = {component_id: [] for component_id in self._nodes}

        for edge in self._edges:
            if edge.source_id not in self._nodes:
                raise ValueError(f"Unknown source_id: {edge.source_id!r}")
            if edge.target_id not in self._nodes:
                raise ValueError(f"Unknown target_id: {edge.target_id!r}")
            adjacency[edge.source_id].append(edge)
            indegree[edge.target_id] += 1

        queue = deque(
            component_id for component_id, in_degree in indegree.items() if in_degree == 0
        )
        execution_order: list[str] = []
        while queue:
            current = queue.popleft()
            execution_order.append(current)
            for edge in adjacency[current]:
                indegree[edge.target_id] -= 1
                if indegree[edge.target_id] == 0:
                    queue.append(edge.target_id)

        if len(execution_order) != len(self._nodes):
            raise ValueError("Workflow graph has a cycle.")

        self._adjacency = adjacency
        self._execution_order = execution_order
        self._compiled = True

    def before_run(self, initial_inputs: list[IDataset]) -> None:
        """Lifecycle hook called before execution."""
        self.context.set("workflow.last_input_count", len(initial_inputs))

    def after_run(self, outputs: list[IDataset]) -> None:
        """Lifecycle hook called after execution."""
        self.context.set("workflow.last_output_count", len(outputs))

    def run(self, initial_inputs: list[IDataset]) -> list[IDataset]:
        if not self._compiled:
            raise RuntimeError("Workflow not compiled.")

        self.before_run(initial_inputs)
        pending_inputs: dict[str, list[IDataset]] = {}
        for component_id in self._execution_order:
            pending_inputs[component_id] = []
        if self._execution_order:
            pending_inputs[self._execution_order[0]] = list(initial_inputs)

        # Fallback when no component executes or no branch is traversed.
        terminal_outputs: list[IDataset] = list(initial_inputs)
        for component_id in self._execution_order:
            component = self._nodes[component_id].component
            inputs = pending_inputs.get(component_id, [])
            if not component.validate_inputs(inputs):
                continue

            outputs = component.execute(inputs)
            outgoing = self._adjacency.get(component_id, [])
            if not outgoing:
                terminal_outputs = outputs
                continue

            traversed = False
            for edge in outgoing:
                if edge.condition is None or edge.condition(outputs):
                    pending_inputs[edge.target_id].extend(outputs)
                    traversed = True
            if not traversed:
                terminal_outputs = outputs

        self.after_run(terminal_outputs)
        return terminal_outputs
