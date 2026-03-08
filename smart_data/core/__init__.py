"""Core interfaces and base classes for smart-data."""

from smart_data.core.context import ExecutionContext
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
from smart_data.core.workflow import BaseWorkflow, IWorkflow, WorkflowEdge, WorkflowNode

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
]
