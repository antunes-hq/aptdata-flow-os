"""Workflow abstractions with context-aware execution hooks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from time import sleep, time_ns
from typing import Any
from uuid import uuid4

from opentelemetry import trace
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass as pydantic_dataclass

from aptdata.core.context import ExecutionContext
from aptdata.core.dataset import IDataset
from aptdata.core.state import StateBackend
from aptdata.core.system import DefaultExecutor, IComponent, IExecutor
from aptdata.plugins.dataset import InMemoryDataset
from aptdata.telemetry.instrumentation import (
    record_processed_documents,
    reset_ingestion_metrics,
    set_ingestion_total_documents,
)


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


@pydantic_dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class BaseWorkflow(IWorkflow):
    """Default workflow implementation with adjacency compilation and hooks."""

    workflow_id: str
    context: ExecutionContext = field(default_factory=ExecutionContext)
    executor: IExecutor = field(default_factory=lambda: DefaultExecutor())

    def __post_init__(self) -> None:
        self._nodes: dict[str, WorkflowNode] = {}
        self._edges: list[WorkflowEdge] = []
        self._adjacency: dict[str, list[WorkflowEdge]] = {}
        self._execution_order: list[str] = []
        self._compiled = False

    def add_component(self, component: IComponent) -> None:
        self._nodes[component.component_id] = WorkflowNode(
            component=component, workflow=self
        )
        self._compiled = False

    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[list[IDataset]], bool] | None = None,
    ) -> None:
        self._edges.append(
            WorkflowEdge(source_id=source_id, target_id=target_id, condition=condition)
        )
        self._compiled = False

    def compile(self) -> None:
        if not self._nodes:
            raise ValueError("Workflow has no components.")

        indegree = {component_id: 0 for component_id in self._nodes}
        adjacency: dict[str, list[WorkflowEdge]] = {
            component_id: [] for component_id in self._nodes
        }

        for edge in self._edges:
            if edge.source_id not in self._nodes:
                raise ValueError(f"Unknown source_id: {edge.source_id!r}")
            if edge.target_id not in self._nodes:
                raise ValueError(f"Unknown target_id: {edge.target_id!r}")
            adjacency[edge.source_id].append(edge)
            indegree[edge.target_id] += 1

        queue = deque(
            component_id
            for component_id, in_degree in indegree.items()
            if in_degree == 0
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
        terminal_outputs = self.executor.execute_flow(self, initial_inputs)
        self.after_run(terminal_outputs)
        return terminal_outputs


@dataclass
class _WorkflowStep:
    fn: Callable[..., Any]
    retries: int = 0
    backoff: float = 0.0


class Workflow:
    """Function-oriented workflow with retries, checkpoints and resume."""

    def __init__(
        self,
        name: str,
        *,
        enable_checkpointing: bool = False,
        state_backend: StateBackend | None = None,
        governance_binding: Any | None = None,
    ) -> None:
        self.name = name
        self.enable_checkpointing = enable_checkpointing
        self.state_backend = state_backend or StateBackend()
        self.governance_binding = governance_binding
        self._steps: list[_WorkflowStep] = []

    def add_step(
        self,
        step: Callable[..., Any],
        *,
        retries: int = 0,
        backoff: float = 0.0,
    ) -> None:
        """Add a callable pipeline step with optional retry/backoff policy."""
        self._steps.append(
            _WorkflowStep(fn=step, retries=max(0, retries), backoff=max(0.0, backoff))
        )

    def execute(self, data: Any | None = None) -> Any:
        """Execute workflow from the first step."""
        run_id = f"{self.name}_{time_ns()}_{uuid4().hex[:8]}"
        if self.governance_binding is not None:
            self.governance_binding.start(run_id)
        try:
            result = self._run(run_id=run_id, start_index=0, data=data)
        except Exception as exc:
            if self.governance_binding is not None:
                self.governance_binding.finish(
                    run_id,
                    workflow_name=self.name,
                    success=False,
                    result={"error_type": type(exc).__name__},
                )
            raise
        if self.governance_binding is not None:
            self.governance_binding.finish(
                run_id,
                workflow_name=self.name,
                success=True,
                result=result,
            )
        return result

    def resume(self, run_id: str, data: Any | None = None) -> Any:
        """Resume execution from the last checkpoint for *run_id*."""
        state = self.state_backend.load(run_id)
        restored_data = self._deserialize_payload(state.get("data"))

        # If restored_data is an empty dataset (e.g. records were not serialized)
        # we might prefer the provided data if it's more complete.
        use_data = restored_data
        if restored_data is not None and isinstance(restored_data, InMemoryDataset):
            if not restored_data.read() and data is not None:
                use_data = data

        return self._run(
            run_id=run_id,
            start_index=int(state.get("next_step_index", 0)),
            data=use_data if use_data is not None else data,
        )

    def _run(self, *, run_id: str, start_index: int, data: Any | None) -> Any:
        if not self._steps:
            return data
        reset_ingestion_metrics()
        trace_id = None
        with trace.get_tracer("aptdata.workflow").start_as_current_span(
            f"{self.name}.run"
        ) as span:
            trace_id = f"{span.get_span_context().trace_id:032x}"
            payload = self._attach_lineage(data, trace_id=trace_id)
            set_ingestion_total_documents(self._count_records(payload))
            for step_index in range(start_index, len(self._steps)):
                step = self._steps[step_index]
                payload = self._run_step(
                    step=step,
                    payload=payload,
                    step_index=step_index,
                    run_id=run_id,
                    trace_id=trace_id,
                )
                record_processed_documents(self._count_records(payload))
                if self.enable_checkpointing:
                    self.state_backend.save(
                        run_id,
                        {
                            "run_id": run_id,
                            "next_step_index": step_index + 1,
                            "data": self._serialize_payload(payload),
                        },
                    )
            return payload

    def _run_step(
        self,
        *,
        step: _WorkflowStep,
        payload: Any | None,
        step_index: int,
        run_id: str,
        trace_id: str,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(step.retries + 1):
            with trace.get_tracer("aptdata.workflow").start_as_current_span(
                f"{self.name}.step.{step_index}"
            ) as span:
                span.set_attribute("aptdata.step.index", step_index)
                span.set_attribute(
                    "aptdata.step.name", getattr(step.fn, "__name__", "step")
                )
                span.set_attribute("aptdata.retry.attempt", attempt + 1)
                span.set_attribute("aptdata.retry.max_attempts", step.retries + 1)
                span.set_attribute("aptdata.trace_id", trace_id)
                try:
                    result = step.fn() if payload is None else step.fn(payload)
                    return self._attach_lineage(result, trace_id=trace_id)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    span.record_exception(exc)
                    if attempt < step.retries:
                        backoff_seconds = (
                            step.backoff * (2**attempt) if step.backoff else 0.0
                        )
                        sleep(min(backoff_seconds, 30.0))
        if self.enable_checkpointing:
            self.state_backend.save(
                run_id,
                {
                    "run_id": run_id,
                    "next_step_index": step_index,
                    "data": self._serialize_payload(payload),
                    "error": str(last_error) if last_error else "unknown error",
                },
            )
        if last_error is not None:
            raise last_error
        raise RuntimeError("Workflow step failed with unknown error.")

    @staticmethod
    def _count_records(payload: Any | None) -> int:
        if isinstance(payload, InMemoryDataset):
            return len(payload.read())
        if isinstance(payload, list):
            return len(payload)
        return 0

    @staticmethod
    def _attach_lineage(payload: Any | None, *, trace_id: str) -> Any | None:
        if payload is None:
            return None
        if isinstance(payload, InMemoryDataset):
            records = payload.read()
            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    continue
                record.setdefault("trace_id", trace_id)
                record.setdefault("document_id", record.get("id") or f"doc-{index}")
            payload.write(records)
            return payload
        if isinstance(payload, list):
            for index, record in enumerate(payload):
                if not isinstance(record, dict):
                    continue
                record.setdefault("trace_id", trace_id)
                record.setdefault("document_id", record.get("id") or f"doc-{index}")
            return payload
        return payload

    @staticmethod
    def _serialize_payload(payload: Any | None) -> Any:
        if isinstance(payload, InMemoryDataset):
            return {
                "__type__": "InMemoryDataset",
                "uri": payload.uri,
                "schema_metadata": payload.schema_metadata,
            }
        return payload

    @staticmethod
    def _deserialize_payload(payload: Any | None) -> Any | None:
        if not isinstance(payload, dict):
            return payload
        if payload.get("__type__") != "InMemoryDataset":
            return payload
        dataset = InMemoryDataset(
            uri=payload.get("uri", "memory://checkpoint"),
            schema_metadata=payload.get("schema_metadata", {}),
        )
        # Note: Records are not stored in state backend to avoid OOM
        # and to delegate blob storage to external services.
        return dataset
