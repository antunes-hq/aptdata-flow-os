"""System, Component, and Flow — the universal architecture for smart-data.

This module provides the three foundational abstractions:

* :class:`IComponent` / :class:`BaseComponent` — a reusable, metadata-rich
  unit of work that replaces the legacy ``Step`` abstraction.
* :class:`IFlow` / :class:`BaseFlow` — a directed execution graph that
  replaces the DAG management in the legacy ``Pipeline``.
* :class:`ISystem` / :class:`BaseSystem` — the top-level orchestrator that
  owns one or more :class:`IFlow` instances.

Design goals
------------
* **SOLID** — each class has a single, well-defined responsibility.
* **Pydantic** — all concrete base classes use ``pydantic.dataclasses`` for
  runtime field validation.
* **Metadata-driven** — :class:`ComponentMeta` carries rich information about
  a component's role, tags, and branching behaviour so that the framework can
  make decisions without inspecting component internals.
* **Dependency Injection** — dependencies (datasets, services) are passed in
  explicitly at call time; nothing is resolved from global state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from pydantic.dataclasses import dataclass as pydantic_dataclass

from smart_data.core.dataset import IDataset


# ---------------------------------------------------------------------------
# Component metadata
# ---------------------------------------------------------------------------


class ComponentKind(str, Enum):
    """Supported processing paradigms for a :class:`BaseComponent`."""

    TRANSFORM = "transform"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    EXTRACT = "extract"
    LOAD = "load"
    CUSTOM = "custom"


@dataclass
class ComponentMeta:
    """Rich metadata describing a component's role and branching behaviour.

    Attributes
    ----------
    kind:
        The processing paradigm this component belongs to.
    tags:
        Arbitrary string labels for filtering, grouping, or discovery.
    branch_on:
        When non-empty, names the output field or condition key on which the
        flow should branch after this component executes.
    description:
        Human-readable summary of what this component does.
    extra:
        Open-ended mapping for framework extensions or user-defined metadata.
    """

    kind: ComponentKind = ComponentKind.CUSTOM
    tags: list[str] = field(default_factory=list)
    branch_on: str = ""
    description: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Component (replaces Step)
# ---------------------------------------------------------------------------


@dataclass
class IComponent(ABC):
    """Interface for a reusable unit of work.

    A component receives a list of :class:`~smart_data.core.dataset.IDataset`
    inputs, validates them, executes its logic, and returns a list of
    :class:`~smart_data.core.dataset.IDataset` outputs.  Unlike the legacy
    ``IStep``, it may produce *multiple* output datasets to support branching
    flows.
    """

    @property
    @abstractmethod
    def meta(self) -> ComponentMeta:
        """Metadata describing this component."""

    @abstractmethod
    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        """Return ``True`` when *inputs* are valid for this component."""

    @abstractmethod
    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        """Execute the component logic and return its output datasets."""


@pydantic_dataclass
class BaseComponent(IComponent):
    """Base component with Pydantic-validated identity and metadata.

    Concrete component implementations must inherit from this class and
    implement the :meth:`validate_inputs` and :meth:`execute` abstract
    methods inherited from :class:`IComponent`.

    Parameters
    ----------
    component_id:
        A unique identifier for this component within a flow.
    metadata:
        A :class:`ComponentMeta` instance describing the component's role.
    """

    component_id: str
    metadata: ComponentMeta = field(default_factory=ComponentMeta)

    @property
    def meta(self) -> ComponentMeta:
        return self.metadata


# ---------------------------------------------------------------------------
# Flow graph primitives
# ---------------------------------------------------------------------------


@dataclass
class FlowEdge:
    """A directed edge in a :class:`BaseFlow` execution graph.

    Optionally carries a *condition* callable; when present the edge is only
    traversed when ``condition(outputs)`` evaluates to ``True``, enabling
    conditional / branching flows.

    Parameters
    ----------
    source_id:
        The :attr:`~BaseComponent.component_id` of the upstream component.
    target_id:
        The :attr:`~BaseComponent.component_id` of the downstream component.
    condition:
        Optional predicate evaluated against the source component's outputs.
    """

    source_id: str
    target_id: str
    condition: Callable[[list[IDataset]], bool] | None = None


@dataclass
class FlowNode:
    """A node wrapping a :class:`IComponent` inside a :class:`IFlow` graph.

    Parameters
    ----------
    component:
        The component held by this node.
    flow:
        Back-reference to the owning flow (set by the flow on insertion).
    """

    component: IComponent
    flow: IFlow | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Flow (replaces the DAG management in Pipeline)
# ---------------------------------------------------------------------------


@dataclass
class IFlow(ABC):
    """Interface for a directed execution graph of :class:`IComponent` nodes.

    A flow owns a set of components and the directed edges that connect them.
    It is responsible for validating the graph structure (:meth:`compile`)
    and driving execution (:meth:`run`).
    """

    @abstractmethod
    def add_component(self, component: IComponent) -> None:
        """Add *component* as a node in this flow."""

    @abstractmethod
    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[list[IDataset]], bool] | None = None,
    ) -> None:
        """Create a directed edge from *source_id* to *target_id*.

        Parameters
        ----------
        source_id:
            The :attr:`~BaseComponent.component_id` of the upstream component.
        target_id:
            The :attr:`~BaseComponent.component_id` of the downstream component.
        condition:
            Optional predicate that gates traversal of the edge.
        """

    @abstractmethod
    def compile(self) -> None:
        """Validate the graph structure before execution.

        Implementations should raise :exc:`ValueError` when the graph is
        invalid (e.g. unknown node references, cycles in a DAG-only flow).
        """

    @abstractmethod
    def run(self, initial_inputs: list[IDataset]) -> list[IDataset]:
        """Execute the flow starting with *initial_inputs*.

        Returns the outputs produced by the terminal component(s).
        """


@pydantic_dataclass
class BaseFlow(IFlow):
    """Base flow with Pydantic-validated identity and a managed graph.

    Concrete flow implementations must inherit from this class and implement
    the :meth:`add_component`, :meth:`connect`, :meth:`compile` and
    :meth:`run` abstract methods inherited from :class:`IFlow`.

    Parameters
    ----------
    flow_id:
        A unique identifier for this flow within a system.
    """

    flow_id: str


# ---------------------------------------------------------------------------
# System (top-level orchestrator)
# ---------------------------------------------------------------------------


@dataclass
class ISystem(ABC):
    """Interface for a system that orchestrates one or more :class:`IFlow` instances."""

    @abstractmethod
    def register_flow(self, flow: IFlow) -> None:
        """Register *flow* in this system."""

    @abstractmethod
    def run(self) -> None:
        """Execute all registered flows."""


@pydantic_dataclass
class BaseSystem(ISystem):
    """Base system with Pydantic-validated identity.

    Concrete system implementations must inherit from this class and implement
    the :meth:`register_flow` and :meth:`run` abstract methods inherited from
    :class:`ISystem`.

    Parameters
    ----------
    system_id:
        A unique identifier for this system.
    """

    system_id: str
