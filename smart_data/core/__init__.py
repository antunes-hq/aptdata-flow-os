"""Core interfaces and base classes for smart-data."""

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

__all__ = [
    "IDataset",
    "BaseDataset",
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
]
