"""Core interfaces and base classes for aptdata."""

from aptdata.core.context import ExecutionContext, IContext
from aptdata.core.dataset import BaseDataset, DataContractError, IDataset, PydanticDataset
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
from aptdata.core.workflow import (
    BaseWorkflow,
    IWorkflow,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)

__all__ = [
    "IDataset",
    "BaseDataset",
    "PydanticDataset",
    "DataContractError",
    "ExecutionContext",
    "IContext",
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
