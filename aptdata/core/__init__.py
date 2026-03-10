"""Core interfaces and base classes for aptdata."""

from aptdata.core.context import ExecutionContext
from aptdata.core.dataset import BaseDataset, IDataset
from aptdata.core.state import StateBackend
from aptdata.core.system import (
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
from aptdata.core.workflow import BaseWorkflow, IWorkflow, Workflow, WorkflowEdge, WorkflowNode

__all__ = [
    "IDataset",
    "BaseDataset",
    "ExecutionContext",
    "ComponentKind",
    "ComponentMeta",
    "IComponent",
    "BaseComponent",
    "FlowEdge",
    "FlowNode",
    "IFlow",
    "BaseFlow",
    "ISystem",
    "BaseSystem",
    "WorkflowEdge",
    "WorkflowNode",
    "IWorkflow",
    "BaseWorkflow",
    "Workflow",
    "StateBackend",
]
